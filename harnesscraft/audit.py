"""Jurnalul candidatului: urma fiecarui pas, scrisa de program pe loc, din care se citeste raportul de audit.

Decizia autorului (15 octombrie 2026): raportul de audit spune cum s-a ajuns la rezultat,
iar il scrie codul dintr-un jurnal tinut pe loc, nu un model la sfarsit. Jurnalul doar creste: un rand JSON pe intrare,
in `jurnal.jsonl`, langa celelalte fisiere ale candidatului. Fiecare rand spune ora, pasul, cine (programul sau
recrutorul), ce s-a intamplat, versiunea programului care rula si, unde e cazul, starea bifelor dupa schimbare: asa se
vede o bifa schimbata in afara aplicatiei. Textul notitelor nu intra: sta in ghid si in foaia probei.
"""
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

from harnesscraft.manifest import RADACINA

FISIER = "jurnal.jsonl"
PROGRAM, RECRUTOR = "programul", "recrutorul"


def _versiune():
    """Commitul HarnessCraft al codului care ruleaza, citit o data, la pornire: codul incarcat nu se schimba cu un
    commit facut dupa. Cu schimbari necomise, spune asta: regulile nu mai sunt cele din commit."""
    def git(*a):
        r = subprocess.run(["git", "-C", str(RADACINA), *a], capture_output=True, text=True, encoding="utf-8")
        return r.stdout.strip() if r.returncode == 0 else None
    sha = git("rev-parse", "--short=7", "HEAD")
    if not sha:
        return "necunoscută (fără git)"
    murdar = git("status", "--porcelain", "--untracked-files=no", "--", "harnesscraft", "proba")
    return sha + (", cu schimbări nesalvate în istoric" if murdar else "")


VERSIUNE = _versiune()


def scrie(dosar, pas, cine, ce, **date):
    """Adauga o intrare. `date`: ce trebuie ca pasul sa se poata reface (commituri, amprente, cifre, starea bifelor)."""
    rand = {"ora": datetime.now().isoformat(timespec="seconds"), "pas": pas, "cine": cine, "ce": ce,
            "versiune": VERSIUNE, **date}
    with open(Path(dosar) / FISIER, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rand, ensure_ascii=False) + "\n")


def citeste(dosar):
    f = Path(dosar) / FISIER
    if not f.exists():
        return []
    return [json.loads(r) for r in f.read_text(encoding="utf-8").splitlines() if r.strip()]


def amprenta(cale):
    """Amprenta unui fisier predat (primele 12 semne ale SHA-256): acelasi fisier, aceeasi amprenta."""
    return hashlib.sha256(Path(cale).read_bytes()).hexdigest()[:12]


def schimbari(vechi, noi, eticheta, bife, gol="—"):
    """Ce s-a schimbat intre doua stari ale unui formular. Bifele, cu valoarea veche si noua; textele, numai ca s-au
    schimbat. `bife(cheie)` spune daca un camp e bifa; `eticheta(cheie)`, cum il citeste recrutorul; `gol`, numele bifei
    nedate („nepusă” la interviu, „nebifat” la proba), ca pe butonul ei."""
    r = []
    for k in noi:
        a, b = (vechi.get(k) or "").strip(), (noi.get(k) or "").strip()
        if a == b:
            continue
        r.append(f"{eticheta(k)}: {a or gol} → {b or gol}" if bife(k) else f"{eticheta(k)}: text schimbat")
    return r


def ultima_stare(intrari, pas):
    """Starea bifelor din ultima intrare a pasului care o are, sau None."""
    return next((x["bife"] for x in reversed(intrari) if x["pas"] == pas and "bife" in x), None)
