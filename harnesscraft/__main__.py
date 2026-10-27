"""Linia de comanda a aplicatiei: `python -m harnesscraft <comanda>`. Comenzile cercetarii, pe esantioane, sunt
separate: raman in depozitul privat, cu esantioanele."""
import sys

from harnesscraft import manifest


def studiu():
    """Studiul de caz (SPEC, pasul 6): fisa unui proiect dat intreg, la ultimul commit din fiecare zi, apoi
    fisa intreaga la ultimul commit. Drumul, nu starea. Iesirea ramane in depozitul privat."""
    from harnesscraft import istoric
    from harnesscraft.fisa import randare
    from harnesscraft.pasi import drumul, fisa_proiect
    if len(sys.argv) < 3:
        print("folosire: python -m harnesscraft studiu <cale proiect>")
        return 1
    if not manifest.comise("harnesscraft/fisa.py", "harnesscraft/harness.py"):
        return 1
    p = sys.argv[2]
    commits = istoric.citeste(p)
    for z in drumul(p, commits):
        print(f"{z['ziua']}  {z['commit']}  {z['commituri']:4} commit-uri  {z['nivel'] + 1}. {z['nivel_nume']:24} "
              f"{z['total']:5.1f}" + (f"  lipseste: {'; '.join(z['lipseste'])}" if z["lipseste"] else ""), flush=True)
    print()
    print(randare(fisa_proiect(p, commits)))
    return 0


def interviu():
    """Ghidul de interviu pentru un proiect dat intreg, din fisa lui la ultimul commit (etapa 2, piesa 1).
    Iese pe ecran; se redirectioneaza intr-un fisier pe care il completeaza recrutorul."""
    from harnesscraft import istoric, legare
    from harnesscraft.fisa import fisa as calculeaza
    from harnesscraft.harness import harness
    from harnesscraft.interviu import ghid
    from harnesscraft.pasi import crestere, drumul
    from harnesscraft.stare import stare
    if len(sys.argv) < 3:
        print("folosire: python -m harnesscraft interviu <cale proiect> [--demonstrativ]")
        return 1
    if not manifest.comise("harnesscraft/fisa.py", "harnesscraft/harness.py", "harnesscraft/interviu.py", "harnesscraft/legare.py"):
        return 1
    p = sys.argv[2]
    commits = istoric.citeste(p)
    c = commits[-1]
    sys.stdout.reconfigure(encoding="utf-8")
    f = {**calculeaza(p, stare(p, commits, c.sha), harness(p, c.sha)), "legare": legare.alege(p, c.sha),
         "crestere": crestere(drumul(p, commits))}
    print(ghid(f, demonstrativ="--demonstrativ" in sys.argv))
    return 0


def interviu_scor():
    """Punctajul din ghidul completat de recrutor: codul aduna, nu judeca."""
    from pathlib import Path
    from harnesscraft.interviu import randare_scor, scor as calculeaza
    if len(sys.argv) < 3:
        print("folosire: python -m harnesscraft interviu-scor <ghid completat>")
        return 1
    try:
        s = calculeaza(Path(sys.argv[2]).read_text(encoding="utf-8"))
    except ValueError as e:
        print(f"ghidul nu se poate puncta: {e}")
        return 1
    sys.stdout.reconfigure(encoding="utf-8")
    print(randare_scor(s))
    return 0


def set_exemple():
    """Setul de date al exemplelor, refacut de la zero."""
    from harnesscraft import set_exemple as s
    sys.stdout.reconfigure(encoding="utf-8")  # numele si treptele au diacritice; consola Windows nu e UTF-8
    rez = s.reface()
    print(s.randare(rez))
    print(f"Cifrele capitolului din manual: {s.scrie_rezultate(rez)}")
    return 0


COMENZI = {"set-exemple": set_exemple, "studiu": studiu, "interviu": interviu, "interviu-scor": interviu_scor}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMENZI:
        sys.exit(f"comenzi: {', '.join(COMENZI)}")
    sys.exit(COMENZI[sys.argv[1]]())
