"""Detectorii partii „stare”: teste, CI, chei urcate, licenta, transparenta AI.

De ce: SPEC, „Ce face”: semnalele se calculeaza mecanic. Detectorii dau fapte (ce fisiere,
cate gasiri), nu note: ponderile sunt v2. Orice rulare trece prin gardianul C2, ca pe
esantion sa nu existe semnale inaintea clasamentului orb.

Neacoperit: licentele dependentelor. Cere metadatele fiecarui pachet, adica retea si un
registru pe ecosistem; aici se raporteaza doar manifestele de dependente gasite.
"""
import io
import json
import os
import re
import subprocess
import tarfile
import tempfile
import threading
from pathlib import Path, PurePosixPath

from harnesscraft.gardieni import cere_clasament
from harnesscraft.manifest import git

TESTE_DOSARE = {"test", "tests", "__tests__", "spec", "specs", "testing"}
TESTE_FISIERE = re.compile(
    r"(^test_.+\.py$|.+_test\.(py|go|rs|rb|exs?)$|.+\.(test|spec)\.[cm]?[jt]sx?$"
    r"|.+(Test|Tests|Spec)\.(java|kt|cs|swift|scala|php)$|^test.+\.(js|ts)$)")
SURSA = re.compile(r"\.(py|go|rs|rb|exs?|[cm]?[jt]sx?|java|kt|cs|swift|scala|php|c|cc|cpp|h|hpp|zig|clj[sc]?)$")

CI = re.compile(r"^(\.github/workflows/[^/]+\.ya?ml|\.gitlab-ci\.yml|\.circleci/config\.ya?ml"
                r"|azure-pipelines\.ya?ml|Jenkinsfile|\.travis\.yml|bitbucket-pipelines\.yml"
                r"|\.woodpecker(\.ya?ml|/[^/]+\.ya?ml)|\.drone\.yml|\.buildkite/[^/]+\.ya?ml)$")

LICENTA = re.compile(r"^(licen[cs]e|copying|unlicense)(\.[a-z]+)?$", re.I)
SPDX = [("Apache-2.0", r"apache license,?\s+version 2\.0"), ("AGPL-3.0", r"gnu affero general public license"),
        ("LGPL", r"gnu lesser general public license"), ("GPL-3.0", r"gnu general public license.{0,40}version 3"),
        ("GPL-2.0", r"gnu general public license.{0,40}version 2"), ("MPL-2.0", r"mozilla public license"),
        ("BSD-3-Clause", r"neither the name of"), ("BSD-2-Clause", r"redistributions in binary form"),
        ("MIT", r"permission is hereby granted, free of charge"), ("ISC", r"permission to use, copy, modify, and/or distribute"),
        ("Unlicense", r"this is free and unencumbered software")]

DEPENDENTE = {"package.json", "requirements.txt", "pyproject.toml", "go.mod", "cargo.toml", "gemfile",
              "pom.xml", "build.gradle", "build.gradle.kts", "composer.json", "mix.exs", "deps.edn",
              "project.clj", "pubspec.yaml", "package.swift", "build.zig.zon"}

# urme lasate de unelte in mesajul commit-ului; e-mailul e mai sigur decat numele
UNELTE_AI = re.compile(
    r"(co-authored-by:[^\n]*(claude|anthropic|copilot|cursor|aider|codex|openai|devin|gemini|windsurf|codeium|jules)"
    r"|generated with \[?claude code|🤖 generated with|cursor agent)", re.I)


def fisiere_la(depozit, rev="HEAD"):
    return git(depozit, "-c", "core.quotepath=false", "ls-tree", "-r", "--name-only", rev).splitlines()


def teste(cai):
    gasite = [c for c in cai if SURSA.search(c) and (
        TESTE_FISIERE.match(PurePosixPath(c).name) or set(PurePosixPath(c).parts[:-1]) & TESTE_DOSARE)]
    return {"fisiere_test": len(gasite), "exemple": gasite[:5]}


def ci(cai):
    return {"fisiere_ci": sorted(c for c in cai if CI.match(c))}


def licenta(depozit, cai, rev="HEAD"):
    radacina = [c for c in cai if "/" not in c and LICENTA.match(c)]
    tip = None
    if radacina:
        text = " ".join(git(depozit, "show", f"{rev}:{radacina[0]}").lower().split())
        tip = next((n for n, tipar in SPDX if re.search(tipar, text)), "necunoscut")
    manifeste = sorted(c for c in cai if PurePosixPath(c).name.lower() in DEPENDENTE)
    return {"fisier_licenta": radacina[0] if radacina else None, "tip": tip,
            "manifeste_dependente": manifeste[:10], "licente_dependente": "neacoperit"}


def transparenta_ai(commits):
    cu_urma = [c for c in commits if UNELTE_AI.search(c.mesaj)]
    return {"commits_cu_urma_ai": len(cu_urma), "din": len(commits),
            "primul": cu_urma[0].data[:10] if cu_urma else None}


# o gasire „de proba”: un fisier de teste, exemple, fixtures, mock-uri, demo sau documentatie, un model (`.env.example`)
# ori un text, sau o valoare-model. Se numara separat si nu scade punctul. Regula scrisa inaintea rundei pe chei
# (rapoarte/propunere-ce-nu-vede-fisa.md, „Cheile: protocolul”); nu se verifica daca o cheie e vie.
CALE_DE_PROBA = re.compile(r"(^|/)(tests?|__tests__|spec|specs|testdata|test-data|examples?|samples?|fixtures?|mocks?|"
                           r"demo|stubs?|docs?)(/|$)|[._-](test|spec)s?\.[^/]+$|_test\.[^/]+$|\.(example|sample)$|"
                           r"(^|/)[^/]*\.(example|sample)\.[^/]+$|\.(md|mdx|rst|txt|adoc)$", re.I)
VALOARE_MODEL = re.compile(r"x{3,}|your[-_]?\w*(key|token|secret)|changeme|dummy|placeholder|^<[^>]*>$|\*{3,}", re.I)


def cheie_de_proba(fisier, valoare):
    return bool(CALE_DE_PROBA.search(fisier.replace("\\", "/")) or VALOARE_MODEL.search(valoare or ""))


# regula generica a uneltei (un sir lung langa „key”, „token”…) nu scade punctul: pe grupa A a rundei pe chei, toate
# cele patru greseli au venit din ea (lista de functii, scurtatura de tastatura, cheie de cache, constanta de test).
# Raman regulile pe furnizor (GitHub, AWS, Stripe, chei private…). Pretul: un secret prins numai de forma generala
# nu mai scade punctul; se spune langa, ca numar.
REGULI_GENERICE = {"generic-api-key"}


def fel_cheie(g):
    """„scade”, „de_proba” sau „generica”, pentru o gasire gitleaks."""
    if cheie_de_proba(g["File"], g.get("Secret")):
        return "de_proba"
    return "generica" if g["RuleID"] in REGULI_GENERICE else "scade"


GITLEAKS_LIPSA = ("Analiza nu se poate face: lipsește programul care caută cheile de acces în proiecte (gitleaks) pe "
                  "acest calculator. Vezi docs/INSTALARE.md, pasul 2.")


def _gitleaks(*args):
    """Gasirile gitleaks. Fara `--redact`: regula de proba cere valoarea; valorile nu ies din `chei`."""
    with tempfile.TemporaryDirectory() as tmp:
        raport = Path(tmp) / "r.json"
        try:
            r = subprocess.run(["gitleaks", *args, "--no-banner", "--exit-code", "0",
                                "-f", "json", "-r", str(raport), "-l", "error"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
        except FileNotFoundError:  # fara el, motivul se spune pe ecran, nu ca eroare netratata
            raise RuntimeError(GITLEAKS_LIPSA) from None
        if r.returncode:
            raise RuntimeError(f"gitleaks: {r.stderr.strip()[:300]}")
        return json.loads(raport.read_text(encoding="utf-8") or "[]")


NUME_INTERZIS_WINDOWS = re.compile(r'[:*?"<>|]')


def fara_legaturi(membru, destinatie):
    """Filtrul de extragere: legaturile se sar. Pe Windows devin copii, iar una spre o cale absoluta
    (`venv/bin/python3` -> `/usr/bin/python3`) oprea toata analiza; continutul lor e doar o cale.
    Pe Windows se sar si numele pe care sistemul nu le primeste (`x.pdf:Zone.Identifier`, un proiect din esantion)."""
    if membru.issym() or membru.islnk() or (os.name == "nt" and NUME_INTERZIS_WINDOWS.search(membru.name)):
        return None
    return tarfile.data_filter(membru, destinatie)


def extrage(depozit, rev, tmp):
    """Arborele comis la `rev`, extras cu `git archive` in `tmp`. Un commit fara fisiere da o arhiva numai cu
    antetul, pe care `tarfile` n-o deschide (drumul pe un proiect din esantion se oprea): atunci nu se extrage nimic.
    `core.protectNTFS=false`: git pe Windows refuza toata arhiva cand un nume e interzis acolo; numele se sare la
    extragere (`fara_legaturi`)."""
    if not int(git(depozit, "cat-file", "-s", f"{rev}^{{tree}}")):
        return
    arhiva = subprocess.run(["git", "-C", str(depozit), "-c", "core.protectNTFS=false", "archive", "--format=tar", rev],
                            capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(arhiva)) as t:
        t.extractall(tmp, filter=fara_legaturi)


def chei(depozit, rev="HEAD"):
    """gitleaks pe tot istoricul pana la `rev`, apoi pe arborele comis la `rev`, extras cu
    `git archive`: un `.env` local, neurmarit, nu e „urcat in repo”. Valorile se ascund."""
    gasiri = _gitleaks("git", str(depozit), "--log-opts", rev)
    with tempfile.TemporaryDirectory() as tmp:
        extrage(depozit, rev, tmp)
        acum = _relative(_gitleaks("dir", tmp), tmp)
    return _numara(gasiri, acum)


def _relative(gasiri, tmp):
    radacina = Path(tmp).as_posix().rstrip("/") + "/"
    return [dict(g, File=Path(g["File"]).as_posix().split(radacina)[-1]) for g in gasiri]


def _numara(gasiri, acum):
    fel, fel_acum = [fel_cheie(g) for g in gasiri], [fel_cheie(g) for g in acum]
    return {"gasiri": fel.count("scade"), "reguli": sorted({g["RuleID"] for g, f in zip(gasiri, fel) if f == "scade"}),
            "inca_in_arbore": fel_acum.count("scade"),
            **{k: {"gasiri": fel.count(k), "inca_in_arbore": fel_acum.count(k)} for k in ("de_proba", "generica")}}


class CheiPeDrum:
    """`chei` pe fiecare zi a drumului, cu acelasi rezultat, fara sa refaca totul la fiecare zi. Pe un proiect mare
    o zi lua ~25 s (un proiect din esantion, 246 de zile: peste o ora): gitleaks prin tot istoricul si arborele extras, de la
    capat. Aici istoricul se citeste o data, pana la ultima zi, iar o zi pastreaza gasirile din commit-urile ei;
    arborele se citeste pe fisiere, fiecare versiune a unui fisier o data (gitleaks gaseste pe fisier). Regulile
    proiectului (`.gitleaks.toml` la radacina) se pun langa fisiere, ca la arborele intreg, si intra in cheie."""

    def __init__(self, depozit, revs):
        """`revs`: toate zilele; istoricul e reuniunea lor. Ultima le cuprinde de obicei pe toate; o zi necuprinsa
        (ordinea commit-urilor urmeaza datele, nu legaturile) se adauga. Toate deodata depasesc linia de comanda."""
        self.depozit = depozit
        cuprinse = set(git(depozit, "rev-list", revs[-1]).split())
        varfuri = [revs[-1]] + [r for r in revs if r not in cuprinse]
        self.istoric = _gitleaks("git", str(depozit), "--log-opts", " ".join(varfuri))
        self.fisiere = {}  # (reguli, cale, blob) -> gasirile din fisierul acela
        self.lacat = threading.Lock()

    def __call__(self, rev):
        stramosi = set(git(self.depozit, "rev-list", rev).split())
        return _numara([g for g in self.istoric if g["Commit"] in stramosi], self._arbore(rev))

    def _arbore(self, rev):
        fisiere = []
        for rand in git(self.depozit, "ls-tree", "-r", "-z", rev).split("\0"):
            if rand:
                meta, cale = rand.split("\t", 1)
                mod, tip, blob = meta.split()
                if tip == "blob" and mod != "120000" and not (os.name == "nt" and NUME_INTERZIS_WINDOWS.search(cale)):
                    fisiere.append((cale, blob))
        reguli = dict(fisiere).get(".gitleaks.toml")
        # Lacatul pazeste numai dictionarul: zilele scaneaza in paralel; o versiune noua in doua zile deodata se
        # scaneaza de doua ori, cu acelasi rezultat.
        with self.lacat:
            noi = [(c, b) for c, b in fisiere if (reguli, c, b) not in self.fisiere]
        if noi:
            fisier_reguli = [(".gitleaks.toml", reguli)] if reguli else []
            scrise = noi + [x for x in fisier_reguli if x not in noi]
            with tempfile.TemporaryDirectory() as tmp:
                self._scrie(scrise, tmp)
                pe_fisier = {}
                for g in _relative(_gitleaks("dir", tmp), tmp):
                    pe_fisier.setdefault(g["File"], []).append(g)
            with self.lacat:
                for c, b in noi:
                    self.fisiere[(reguli, c, b)] = pe_fisier.get(c, [])
        with self.lacat:
            return [g for c, b in fisiere for g in self.fisiere[(reguli, c, b)]]

    def _scrie(self, fisiere, tmp):
        """Continutul fiecarei versiuni, cu `git cat-file --batch`, la calea ei sub `tmp`."""
        iesire = subprocess.run(["git", "-C", str(self.depozit), "cat-file", "--batch"], check=True,
                                input="".join(f"{b}\n" for _, b in fisiere).encode(), capture_output=True).stdout
        poz = 0
        for cale, _ in fisiere:
            antet_sf = iesire.index(b"\n", poz)
            marime = int(iesire[poz:antet_sf].split()[2])
            tinta = Path(tmp, cale)
            tinta.parent.mkdir(parents=True, exist_ok=True)
            tinta.write_bytes(iesire[antet_sf + 1:antet_sf + 1 + marime])
            poz = antet_sf + 1 + marime + 1


def stare(depozit, commits, rev="HEAD", cu_chei=True, chei_la=None):
    """`chei_la`: o `CheiPeDrum`, cand se calculeaza mai multe zile ale aceluiasi proiect."""
    cere_clasament(depozit)
    cai = fisiere_la(depozit, rev)
    rez = {"teste": teste(cai), "ci": ci(cai), "licenta": licenta(depozit, cai, rev),
           "transparenta_ai": transparenta_ai(commits)}
    if cu_chei:
        rez["chei"] = chei_la(rev) if chei_la else chei(depozit, rev)
    return rez
