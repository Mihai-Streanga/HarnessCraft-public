"""Pasii pe un candidat, aceiasi pentru comanda din terminal si pentru butonul din interfata (doua usi la o functie).

Interfata nu calculeaza nimic al ei: cheama functiile de aici si pe cele din `interviu.py` si `tintite.py`.
"""
import os
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor

from harnesscraft import extractori, instructiuni, istoric, legare
from harnesscraft.fisa import NIVELURI, fisa
from harnesscraft.harness import harness
from harnesscraft.istoric_separat import agrega
from harnesscraft.stare import CheiPeDrum, stare


def fisa_proiect(p, commits=None):
    """Fisa intreaga la ultimul commit, cu istoricul ca informatie si commit-ul intrebarii de legare."""
    commits = commits or istoric.citeste(p)
    c = commits[-1]
    ist = agrega(extractori.toate(p, commits, instructiuni.gaseste(p, commits, c.sha)))
    return {**fisa(p, stare(p, commits, c.sha), harness(p, c.sha), ist), "legare": legare.alege(p, c.sha)}


def drumul(p, commits=None):
    """Fisa la ultimul commit din fiecare zi: drumul, nu starea."""
    commits = commits or istoric.citeste(p)
    zile = {c.data[:10]: i for i, c in enumerate(commits)}
    cheile = CheiPeDrum(p, [commits[i].sha for i in zile.values()]) if zile else None

    def ziua(d, i):
        c = commits[i]
        f = fisa(p, stare(p, commits[:i + 1], c.sha, chei_la=cheile), harness(p, c.sha))
        return {"ziua": d, "commit": c.sha[:7], "commituri": i + 1, "nivel": f["nivel"],
                "nivel_nume": NIVELURI[f["nivel"]], "total": f["total"], "lipseste": f["pentru_urmatorul"]}

    # Zilele sunt independente, iar timpul e in procesele git: in paralel, ordinea rezultatului ramane a zilelor.
    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as ex:
        return list(ex.map(ziua, zile.keys(), zile.values()))


ZILE_BRUSC = 14  # fereastra, in zile, nu fractie din istoric: proiectele vechi primesc regulile pentru AI tarziu


def crestere(drum):
    """Punctajul din urma cu `ZILE_BRUSC` zile fata de cel de la capat, cand mai mult de jumatate a aparut in fereastra;
    altfel None. Fara nota: aduce numai o intrebare in ghid (rapoarte/plan-legare-si-crestere.md, decizia autorului)."""
    if not drum or not drum[-1]["total"]:
        return None
    capat = date.fromisoformat(drum[-1]["ziua"])
    prag = (capat - timedelta(days=ZILE_BRUSC)).isoformat()
    inainte = next((z["total"] for z in reversed(drum) if z["ziua"] <= prag), 0)
    acum = drum[-1]["total"]
    return {"zile": ZILE_BRUSC, "inainte": inainte, "acum": acum} if 2 * (acum - inainte) >= acum else None
