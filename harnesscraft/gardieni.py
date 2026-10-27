"""Gardianul clasamentului orb (C2).

De ce: testul ipotezei portante compara clasamentul autorului cu scorul. Daca semnalele
ar rula pe esantion inaintea clasamentului comis, scorul l-ar putea influenta, iar testul
si-ar confirma singur rezultatul. Regula e impusa in cod, nu lasata in proza (principiul 8).
"""
import re
from pathlib import Path

from harnesscraft.manifest import RADACINA, RUNDE, citeste, git


def clasament(runda=1):
    return Path(RUNDE[runda][0]) / "clasament-orb.md"


CLASAMENT = clasament(1)
# fiecare dosar de clone cu clasamentul lui: o runda noua nu trece pe clasamentul celei vechi
GARDATE = [(RADACINA / dep, clasament(n)) for n, (_, dep) in RUNDE.items()]


class ClasamentNecomis(RuntimeError):
    pass


def in_esantion(depozit, depozite):
    try:
        Path(depozit).resolve().relative_to(Path(depozite).resolve())
        return True
    except ValueError:
        return False


def jumatati(text):
    """Depozitele din `### Jumătatea de sus` și `### Jumătatea de jos`, câte unul pe rând `- a/b`."""
    sectiuni = re.split(r"^### ", text, flags=re.M)
    gasite = {}
    for s in sectiuni:
        titlu, _, corp = s.partition("\n")
        if titlu.strip() in ("Jumătatea de sus", "Jumătatea de jos"):
            gasite[titlu.strip()] = re.findall(r"^- (\S+)\s*$", corp, re.M)
    return gasite.get("Jumătatea de sus", []), gasite.get("Jumătatea de jos", [])


def gardian_c2(radacina=RADACINA, clasament=CLASAMENT):
    """C2: clasamentul exista in git, fara modificari necomise, si e complet: doua jumatati egale,
    disjuncte, care acopera manifestul (cand exista). Intoarce motivul sau None.

    De ce complet: clasamentul s-a comis pe bucati, cat a citit autorul; un C2 care cerea doar
    commit-ul ar fi lasat semnalele sa ruleze dupa primele 11 impresii (10 oct. 2026)."""
    if not git(radacina, "log", "-1", "--format=%H", "--", str(clasament)).strip():
        return f"{clasament} nu e comis: semnalele nu ruleaza pe esantion inaintea clasamentului orb"
    if git(radacina, "status", "--porcelain", "--", str(clasament)).strip():
        return f"{clasament} are modificari necomise"
    sus, jos = jumatati((Path(radacina) / clasament).read_text(encoding="utf-8"))
    if not sus or len(sus) != len(jos) or set(sus) & set(jos):
        return (f"{clasament} nu e complet: jumatatile au {len(sus)} si {len(jos)} depozite"
                + (", cu depozite in amandoua" if set(sus) & set(jos) else ""))
    manifest = Path(radacina) / Path(clasament).parent / "manifest.csv"
    if manifest.exists():
        asteptate = {r["depozit"] for r in citeste(manifest)}
        if set(sus) | set(jos) != asteptate:
            return f"{clasament} nu acopera manifestul: jumatatile nu au exact depozitele din {manifest.name}"
    return None


def cere_clasament(depozit, radacina=RADACINA, gardate=None):
    """Se cheama la intrarea oricarui semnal. In afara esantioanelor nu cere nimic."""
    for depozite, cls in gardate or GARDATE:
        if in_esantion(depozit, depozite) and (motiv := gardian_c2(radacina, cls)):
            raise ClasamentNecomis(motiv)
