"""Partea de istoric pe esantion, urmarita separat de scor (datoria 1).

NU intra in `esantion/scor.json` si nu se aduna la totalul etapei 1. Se compara cu clasamentul orb
dupa aceeasi regula ca scorul (`ipoteza.py`), ca autorul sa decida daca intra in versiunea urmatoare.

Regulile cazurilor sunt cele reparate din `extractori.py`, neschimbate. Aici se fixeaza numai cum se strang
cazurile unui proiect intr-o cifra, scrisa si comisa inaintea comparatiei:
  - pe fiecare zona, proportia cazurilor pe care regula le accepta (0-1). Proportia, nu numarul:
    numarul creste cu marimea proiectului, nu cu metoda (ca la teste, `scor.py`);
  - fara niciun caz in zona, 0: fara modificari ale instructiunilor nu exista cicatrice, iar fara
    schimbari de structura nu exista arhitectura tinuta la zi;
  - totalul e suma celor doua, ponderi egale, maxim 2.
Se compara cu clasamentul totalul si, separat, fiecare zona; se raporteaza toate trei.

Limita: agentul a vazut clasamentul inaintea acestei reguli de agregare. Ea e cea mai simpla in
forma scorului de stare, dar nu e oarba.
"""

ZONE = ("cicatrice", "arhitectura")


def agrega(cazuri):
    rez = {}
    for zona in ZONE:
        din_zona = [c for c in cazuri if c["zona"] == zona]
        acceptate = sum(c["regula"] for c in din_zona)
        rez[zona] = {"acceptate": acceptate, "cazuri": len(din_zona),
                     "puncte": round(acceptate / len(din_zona), 4) if din_zona else 0.0}
    rez["total"] = round(sum(rez[z]["puncte"] for z in ZONE), 4)
    rez["maxim"] = float(len(ZONE))
    return rez
