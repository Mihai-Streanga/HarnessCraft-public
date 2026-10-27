"""Manifestul esantionului: fiecare proiect fixat pe un commit exact.

De ce: scorul trebuie sa fie reproductibil, iar autorii proiectelor urca in continuare.
Clonele din `depozite/` nu intra in git; se refac de aici, la commit-ul fixat.
"""
import csv
import subprocess
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
MANIFEST = RADACINA / "esantion" / "manifest.csv"
DEPOZITE = RADACINA / "depozite"
# runda 2 pe fisa: proiecte noi, alt clasament orb, alte clone (rapoarte/runda2-fisa.md)
RUNDE = {1: ("esantion", "depozite"), 2: ("esantion-runda2", "depozite-runda2")}


def git(cale, *args):
    r = subprocess.run(["git", "-C", str(cale), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} in {cale}: {r.stderr.strip()}")
    return r.stdout


def citeste(cale=MANIFEST):
    with open(cale, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def cale_clona(rand, radacina=DEPOZITE):
    return Path(radacina) / rand["depozit"].replace("/", "__")


def cloneaza(rand, radacina=DEPOZITE):
    """Cloneaza o data; la a doua chemare doar muta HEAD pe commit-ul din manifest."""
    tinta = cale_clona(rand, radacina)
    if not (tinta / ".git").exists():
        tinta.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", "--no-checkout",
                        f"https://github.com/{rand['depozit']}.git", str(tinta)], check=True)
    git(tinta, "-c", "advice.detachedHead=false", "checkout", "--quiet", "--detach", rand["commit"])
    return tinta


def gardian_c1(rand, radacina=DEPOZITE):
    """C1: clona sta exact pe commit-ul din manifest. Intoarce mesajul abaterii sau None."""
    tinta = cale_clona(rand, radacina)
    if not (tinta / ".git").exists():
        return f"{rand['depozit']}: clona lipseste"
    head = git(tinta, "rev-parse", "HEAD").strip()
    if head != rand["commit"]:
        return f"{rand['depozit']}: HEAD {head[:10]}, manifestul cere {rand['commit'][:10]}"
    return None


def comise(*fisiere):
    """Regulile (si cifrele) se comit inaintea rularii care le-ar putea potrivi dupa clasament."""
    for f in fisiere:
        if not git(RADACINA, "log", "-1", "--format=%H", "--", f).strip() or \
                git(RADACINA, "status", "--porcelain", "--", f).strip():
            print(f"{f} nu e comis, sau are modificari necomise: se comite inaintea rularii")
            return False
    return True
