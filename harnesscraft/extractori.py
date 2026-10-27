"""Extractorii de candidati pentru semnalele de istoric: cicatrice, arhitectura tinuta la zi.

De ce: SPEC, „Zonele”: semnalele de istoric sunt mecanice, dar regula se valideaza pe
verdictele autorului pe 5-10 exemple. Extractorul aplica regula scrisa aici si spune, pentru
fiecare caz, ce a decis ea; verdictul autorului se da orb, fara raspunsul regulii.

Regulile, forma reparată (pragurile sunt parametri, ca testele sa le poata schimba):
  cicatrice  - un commit atinge un fisier de instructiuni; el sau unul din cele `k` commit-uri
               dinainte, in cel mult `zile` zile, e o reparatie, iar randurile adaugate numesc
               ceva atins de reparatie (un fisier al ei, sau un termen din titlul ei);
  arhitectura - o schimbare de structura (dosar nou sau fisiere sterse / redenumite in cel
               putin `prag` fisiere de cod) e urmata, in cel mult `k` commit-uri, de un document
               (nu jurnal) care adauga un rand ce numeste dosarul sau fisierul schimbat.

De ce forma reparată: prima formă a fost de acord cu autorul in 9 din 20 de cazuri (`rapoarte/verdicte-comparatie.md`).
Cicatricea din prima formă se aprindea la orice „fix” din apropiere, chiar fara legatura cu regula;
arhitectura din prima formă recunostea documentul numai dupa nume, iar la Metoda documentul are alt nume.
Ordinea document-cod a iesit din etapa 1: autorul nu o poate judeca din istoric, deci nu are
etalon (decizia autorului, 10 oct. 2026).
"""
import re
from datetime import datetime
from pathlib import PurePosixPath

from harnesscraft import instructiuni
from harnesscraft.gardieni import cere_clasament
from harnesscraft.manifest import git
from harnesscraft.stare import SURSA

REPARATIE = re.compile(r"^(fix|hotfix|revert)\b|^fix(\(.+\))?!?:|\b(fix(es|ed)?|bug|repar\w*|corect\w*|regres\w*)\b",
                       re.I)
# Jurnalul spune ce s-a intamplat, nu cum e construit proiectul: nu tine arhitectura la zi.
JURNAL = re.compile(r"(handoff|prompt|rapoarte/|raport|changelog|history|jurnal|news)", re.I)
# Ce numeste o regula: un termen intre backtick-uri, sau o cale / un nume de fisier.
CITAT = re.compile(r"`([^`]+)`")
FISIER = re.compile(r"[\w./\\-]+\.[A-Za-z]{1,5}\b")


def _doc(cale):
    return PurePosixPath(cale).suffix.lower() in {".md", ".mdx", ".rst", ".txt", ".adoc"}


def _cod(cale):
    return bool(SURSA.search(cale)) and not instructiuni.conventia(cale)


def este_reparatie(commit):
    return bool(REPARATIE.search(commit.titlu))


def _zile(a, b):
    return abs((datetime.fromisoformat(a.data) - datetime.fromisoformat(b.data)).total_seconds()) / 86400


def adaugate(depozit, sha, cale):
    """Randurile adaugate de commit in fisier (fara antetul diff-ului)."""
    diff = git(depozit, "-c", "core.quotepath=false", "show", "--format=", "--unified=0", sha, "--", cale)
    return [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]


def _baza(termen):
    return re.split(r"[/\\]", termen.strip().rstrip("/\\"))[-1].lower()


def termeni(linii):
    """Ce numesc randurile: termenii din backtick-uri si numele de fisiere, la baza lor."""
    text = "\n".join(linii)
    gasite = CITAT.findall(text) + FISIER.findall(text)
    return {b for t in gasite if len(b := _baza(t)) >= 3}


def atinge(reparatie, numiti):
    """Reparatia atinge ce numeste regula: un fisier al ei (in afara celor de instructiuni) sau
    un termen din titlul ei."""
    fisiere = {_baza(f.cale) for f in reparatie.fisiere if not instructiuni.conventia(f.cale)}
    titlu = reparatie.titlu.lower()
    return any(t in fisiere or t in titlu for t in numiti)


def cicatrici(commits, fisiere_instr, depozit, k=3, zile=2):
    """Fiecare modificare a unui fisier de instructiuni (nu crearea), cu decizia regulii."""
    index = {c.sha: i for i, c in enumerate(commits)}
    cazuri = []
    for f in fisiere_instr:
        for m in f.modificari:
            i = index.get(m.sha)
            if i is None:
                continue
            fereastra = [c for c in commits[max(0, i - k):i + 1] if _zile(c, m) <= zile]
            numiti = termeni(adaugate(depozit, m.sha, f.cale))
            reparatii = [c for c in fereastra if este_reparatie(c) and atinge(c, numiti)]
            cazuri.append({"zona": "cicatrice", "fisier": f.cale, "commit": m,
                           "reparatie": reparatii[-1] if reparatii else None,
                           "regula": bool(reparatii)})
    return cazuri


def schimbate(commit, dosare_vazute):
    """Dosarele noi si fisierele de cod adaugate / sterse / redenumite, cu numele lor."""
    cod = [f for f in commit.fisiere if _cod(f.cale) or (f.cale_veche and _cod(f.cale_veche))]
    noi = {str(PurePosixPath(f.cale).parent) for f in cod if f.stare in "AR"} - dosare_vazute - {"."}
    mutate = [f for f in cod if f.stare in "DR"]
    return noi, mutate


def schimbare_de_structura(commit, dosare_vazute, prag=3):
    noi, mutate = schimbate(commit, dosare_vazute)
    return bool(noi) or len(mutate) >= prag


def _nume(commit, dosare_vazute):
    noi, _ = schimbate(commit, dosare_vazute)
    fisiere = [f.cale_veche or f.cale for f in commit.fisiere if f.stare in "ADR" and _cod(f.cale)]
    return {_baza(d) + "/" for d in noi} | {_baza(f) for f in fisiere}


def arhitectura(commits, depozit, k=5, prag=3):
    dosare, cazuri = set(), []
    for i, c in enumerate(commits):
        if i and schimbare_de_structura(c, dosare, prag):
            nume = _nume(c, dosare)
            doc = None
            for u in commits[i:i + k + 1]:
                docs = [f.cale for f in u.fisiere if f.stare != "D" and _doc(f.cale) and not JURNAL.search(f.cale)]
                if any(n in l.lower() for d in docs for l in adaugate(depozit, u.sha, d) for n in nume):
                    doc = u
                    break
            cazuri.append({"zona": "arhitectura", "commit": c, "document": doc, "regula": doc is not None})
        dosare |= {str(PurePosixPath(f.cale).parent) for f in c.fisiere}
    return cazuri


def toate(depozit, commits, fisiere_instr):
    cere_clasament(depozit)
    return cicatrici(commits, fisiere_instr, depozit) + arhitectura(commits, depozit)
