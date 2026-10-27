"""Totalul candidatului: o treime portofoliul (fisa pasului 1), o treime interviul, o treime proba (decizia autorului, 13 octombrie).

NECALIBRAT: ponderi egale, ca in SPEC („In etapa 1, scorul total are ponderi egale”). Fiecare componenta se
aduce la 0-1 fata de maximul ei, apoi valoreaza cel mult 100/3 puncte:
- fisa: totalul pe principii / maximul (16);
- interviul: (media pe intrebarile puse - 1) / 3, pentru ca nota 1 inseamna niciun „da”;
- proba: nota din proba.py (cheia, conversatiile, discutia, pe treimi); incompleta, lipseste.
O componenta lipsa nu se inlocuieste cu o cifra: totalul se arata „incomplet”, cu ce lipseste.
Fara proiect cu cod (decizia autorului, 16 octombrie, datoria 12): hotararea recrutorului, nu o lipsa. Portofoliul
intra cu 0, etichetat, totalul e complet, pe aceeasi scara: codul e bonusul, deci omul fara cod ia cel mult doua treimi.
"""
PONDERE = 100 / 3
PLAFON_FARA_COD = round(2 * PONDERE, 1)


def total(fisa=None, interviu=None, proba=None, fara_cod=False):
    """fisa: (total, maxim); interviu: media 1-4 sau None; proba: 0-1 sau None; fara_cod: fara fisa, cu 0."""
    if fara_cod and fisa:
        raise ValueError("portofoliul: are fișă, deci nu e „fără proiect cu cod”")
    parti = {"portofoliul": 0 if fara_cod else fisa[0] / fisa[1] if fisa else None,
             "interviul": (interviu - 1) / 3 if interviu is not None else None,
             "proba": proba}
    for nume, x in parti.items():
        if x is not None and not 0 <= x <= 1:
            raise ValueError(f"{nume}: {x} în afara 0–1")
    exacte = {n: x * PONDERE for n, x in parti.items() if x is not None}
    puncte = {n: round(exacte[n], 1) if n in exacte else None for n in parti}
    lipsa = [n for n, p in puncte.items() if p is None]
    return {"puncte": puncte, "total": round(sum(exacte.values()), 1),  # rotunjit o data, la sfarsit
            "lipsa": lipsa, "complet": not lipsa, "fara_cod": bool(fara_cod),
            "plafon": PLAFON_FARA_COD if fara_cod else 100}


def randare(t):
    r = ["Totalul, pe treimi (necalibrat):"]
    r += [f"  {n}: " + (f"{p:g} din {PONDERE:.1f}" if p is not None else "lipsă") +
          (" — fără proiect cu cod, hotărârea recrutorului" if n == "portofoliul" and t.get("fara_cod") else "")
          for n, p in t["puncte"].items()]
    r.append(f"  total: {t['total']:g} din 100" + ("" if t["complet"] else f" — incomplet, lipsește: {', '.join(t['lipsa'])}")
             + (f" — fără proiect cu cod: cel mult {t['plafon']:g} din 100" if t.get("fara_cod") else ""))
    return "\n".join(r)
