"""Statul de plata al probei: o firma inventata, 22 de angajati inventati, septembrie 2026, cu greseli plantate.

Regulile si sursele lor: `rapoarte/proba-reguli-si-erori.md` (citite pe 15 octombrie 2026). Erorile, aprobate de autor
in aceeasi zi: 5 de gasit (E1-E5) si una plantata care pare gresita, dar e corecta (C). Fiecare greseala sta pe alt
angajat si se propaga in coloanele care decurg din ea, ca intr-un motor de salarii real.

Statul ocoleste doua reguli pe care nu le-am gasit scrise: cei cu suma netaxabila au venitul brut egal cu minimul
(treapta deducerii e aceeasi cu sau fara ea), iar cine primeste tichete castiga peste minim + 2.000 (n-are deducere).
Deducerile alese dau sume intregi (20 / 16 / 12 / 8 / 4% din minim), ca rotunjirea lor sa nu conteze.
CAM si totalurile angajatorului lipsesc: CAM pe suma netaxabila nu e lamurit in OUG 89/2025.
"""
import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from . import xlsx

LUNA, ANUL = 9, 2026
FIRMA = "Exemplu Distributie SRL"
ZILE_LUCRATOARE = 22  # septembrie 2026: 30 de zile, 8 de weekend, nicio sarbatoare legala
ORE_NORMA = ZILE_LUCRATOARE * 8
TICHET = 30  # alegerea firmei, sub plafonul legal

SALARIU_MINIM = 4325          # HG 146/2026, art. 1, de la 1 iulie 2026
NETAXABIL = 200               # OUG 89/2025, art. III: iulie-decembrie 2026 (300 in ianuarie-iunie)
NETAXABIL_VECHI = 300
PLAFON_NETAXABIL = 4600       # OUG 89/2025, art. III alin. (1) lit. b), iulie-decembrie 2026
COTA_CAS = Decimal("0.25")    # Codul fiscal, art. 138 lit. a); tichetele nu intra in baza (art. 142 lit. r)
COTA_CASS = Decimal("0.10")   # art. 156; tichetele intra in baza (art. 157 alin. (1) lit. t si alin. (2))
COTA_IMPOZIT = Decimal("0.10")  # art. 64 alin. (1) lit. b); baza: art. 78 alin. (2) lit. a)
SPOR_ORE_SUPLIMENTARE = Decimal("0.75")  # Codul muncii, art. 123 alin. (2): cel putin 75%

# marca, nume, prenume, salariu de baza, ore suplimentare, bonus, tichete (da/nu), avans
ANGAJATI = [
    (1001, "Adamescu", "Adam", 4325, 0, 0, False, 0),
    (1002, "Barbulescu", "Barbu", 4325, 0, 0, False, 0),
    (1003, "Constantinescu", "Constantin", 4325, 9, 0, False, 0),
    (1004, "Dumitrescu", "Dumitru", 4700, 0, 0, False, 0),
    (1005, "Enache", "Elena", 5100, 0, 0, False, 0),
    (1006, "Florescu", "Florin", 5500, 0, 0, False, 0),
    (1007, "Georgescu", "George", 5900, 0, 0, False, 0),
    (1008, "Haiducu", "Horia", 6500, 0, 0, True, 0),
    (1009, "Ionescu", "Ion", 7000, 0, 0, True, 1500),
    (1010, "Jitaru", "Julia", 7200, 6, 0, True, 0),
    (1011, "Kovacs", "Katalin", 7500, 0, 0, True, 0),
    (1012, "Lungu", "Laura", 8000, 0, 1000, True, 0),
    (1013, "Marinescu", "Marin", 8200, 8, 0, True, 0),
    (1014, "Nicolescu", "Nicoleta", 8500, 0, 0, True, 2000),
    (1015, "Olteanu", "Oana", 9000, 0, 0, True, 0),
    (1016, "Popescu", "Petru", 9500, 4, 0, True, 0),
    (1017, "Radulescu", "Radu", 10000, 0, 0, True, 2000),
    (1018, "Stanescu", "Stefan", 11000, 0, 1500, True, 0),
    (1019, "Tudorache", "Tudor", 12000, 0, 0, True, 0),
    (1020, "Ursu", "Ursula", 13500, 0, 0, True, 0),
    (1021, "Vasilescu", "Vasile", 15000, 0, 2000, True, 0),
    (1022, "Zamfirescu", "Zamfir", 18000, 0, 0, True, 0),
]

# cheia: greseala, angajatul, coloana unde incepe, ce e gresit
GRESELI = {
    "E1": (1011, "CASS Angajat", "CASS calculat fără tichetele de masă; tichetele intră în baza CASS (Codul fiscal, art. 157)"),
    "E2": (1013, "Suma ore suplimentare", "orele suplimentare plătite fără sporul de 75% (Codul muncii, art. 123)"),
    "E3": (1014, "Rest plata", "avansul nu e scăzut din restul de plată"),
    "E4": (1003, "Suma 300 lei netaxabila", "suma netaxabilă acordată deși venitul brut trece de 4.600 lei (OUG 89/2025, art. III)"),
    "E5": (1002, "Suma 300 lei netaxabila", "300 lei netaxabili, suma din ianuarie–iunie; din iulie 2026 e 200 lei (OUG 89/2025, art. III)"),
}
PLANTATA_CORECTA = (1001, "Suma 300 lei netaxabila",
                    "200 lei netaxabili, corect pentru septembrie 2026; un model care știe numai forma veche zice 300")

COLOANE = [
    "Luna", "Anul", "Marca", "Nume", "Prenume", "Norma", "Zile lucratoare in luna",
    "Ore lucratoare in luna, conf. norma", "Salariu brut lei", "Ore Lucrate", "Suma Ore Lucrate",
    "Ore suplimentare", "Suma ore suplimentare", "Bonus", "Venit brut realizat", "Nr Tichete masa",
    "Tichete de masa", "Suma 300 lei netaxabila", "Baza CAS Angajat", "CAS Angajat", "Baza CASS Angajat",
    "CASS Angajat", "Venit net", "Deducere personala", "Baza calcul impozit", "Impozit", "Salariu net",
    "Avans chenzinal suma", "Rest plata",
]


def _r(x):
    return int(Decimal(x).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def deducere(venit_brut):
    """Deducerea personala de baza, fara persoane in intretinere (Codul fiscal, art. 77 alin. (3)-(4)):
    20% din minim pana la minim, apoi 0,5 puncte mai putin la fiecare 50 de lei, nimic peste minim + 2.000."""
    peste = venit_brut - SALARIU_MINIM
    if peste <= 0:
        procent = Decimal(20)
    elif peste > 2000:
        return 0
    else:
        procent = Decimal(20) - Decimal("0.5") * ((peste + 49) // 50)
    return _r(procent * SALARIU_MINIM / 100)


def rand(angajat, greseala=None):
    """Un rand al statului; `greseala` = codul unei greseli plantate pe angajatul acesta, sau None."""
    marca, nume, prenume, salariu, ore_sup, bonus, cu_tichete, avans = angajat
    tarif = Decimal(salariu) / ORE_NORMA
    suma_ore = _r(tarif * ORE_NORMA)
    spor = 0 if greseala == "E2" else SPOR_ORE_SUPLIMENTARE
    suma_sup = _r(tarif * ore_sup * (1 + spor))
    brut = suma_ore + suma_sup + bonus
    nr_tichete = ZILE_LUCRATOARE if cu_tichete else 0
    tichete = nr_tichete * TICHET
    la_minim = salariu == SALARIU_MINIM
    netaxabil = NETAXABIL if la_minim and brut <= PLAFON_NETAXABIL else 0
    if greseala == "E4":
        netaxabil = NETAXABIL
    if greseala == "E5":
        netaxabil = NETAXABIL_VECHI
    baza_cas = brut - netaxabil
    cas = _r(baza_cas * COTA_CAS)
    baza_cass = brut - netaxabil + (0 if greseala == "E1" else tichete)
    cass = _r(baza_cass * COTA_CASS)
    venit_net = brut - cas - cass
    ded = deducere(brut)
    baza_impozit = max(0, venit_net + tichete - ded - netaxabil)
    impozit = _r(baza_impozit * COTA_IMPOZIT)
    net = venit_net - impozit
    rest = net if greseala == "E3" else net - avans
    valori = [LUNA, ANUL, marca, nume, prenume, 8, ZILE_LUCRATOARE, ORE_NORMA, salariu, ORE_NORMA, suma_ore,
              ore_sup, suma_sup, bonus, brut, nr_tichete, tichete, netaxabil, baza_cas, cas, baza_cass, cass,
              venit_net, ded, baza_impozit, impozit, net, avans, rest]
    return dict(zip(COLOANE, valori))


def stat(cu_greseli=True):
    """Randurile statului; fara greseli, e statul corect, din care se iau valorile corecte ale cheii."""
    pe_marca = {m: cod for cod, (m, _, _) in GRESELI.items()} if cu_greseli else {}
    return [rand(a, pe_marca.get(a[0])) for a in ANGAJATI]


def cheia():
    gresit = {r["Marca"]: r for r in stat(True)}
    corect = {r["Marca"]: r for r in stat(False)}
    erori = []
    for cod, (marca, coloana, ce) in GRESELI.items():
        g, c = gresit[marca], corect[marca]
        erori.append({"cod": cod, "marca": marca, "nume": f"{g['Nume']} {g['Prenume']}", "coloana": coloana,
                      "valoare_in_stat": g[coloana], "valoare_corecta": c[coloana], "ce": ce,
                      "coloane_afectate": [k for k in COLOANE if g[k] != c[k]]})
    marca, coloana, ce = PLANTATA_CORECTA
    r = gresit[marca]
    return {"luna": f"{ANUL}-{LUNA:02d}", "firma": FIRMA, "erori_de_gasit": len(erori), "erori": erori,
            "plantata_corecta": {"marca": marca, "nume": f"{r['Nume']} {r['Prenume']}", "coloana": coloana,
                                 "valoare_in_stat": r[coloana], "ce": ce},
            "toleranta_lei": 1}


def _total(randuri):
    t = ["Total", None, None, FIRMA, None]
    for k in COLOANE[5:]:
        t.append(sum(r[k] for r in randuri) if k not in ("Norma", "Zile lucratoare in luna",
                                                        "Ore lucratoare in luna, conf. norma") else None)
    return t


def pachet():
    """Pachetul payroll al probei (harnesscraft/proba.py, `Pachet`): cuvintele refac la caracter bifele aprobate."""
    return {
        "meseria": "salarizare", "titlu": f"Statul de plată, septembrie {ANUL}",
        "stare_bife": "aprobate de autor una câte una pe 15 octombrie 2026, neîncercate pe candidați",
        "durata": "cel mult 2 ore", "termen": "3 zile",  # ca in Mesaj_pentru_candidat.txt
        "tema": [["statul de plată", f"Stat_{FIRMA.replace(' ', '_')}_{ANUL}-{LUNA:02d}.xlsx"],
                 ["tabelul de răspuns, gol", "Raspuns.xlsx"], ["mesajul pentru candidat", "Mesaj_pentru_candidat.txt"]],
        "raspuns": ["Marca", "Coloana", "Valoarea din stat", "Valoarea corecta", "De ce"],
        "cheia": {"loc": "marca"},
        "locuri": [[a[0], f"{a[1]} {a[2]}"] for a in ANGAJATI],
        "campuri": COLOANE,
        "cuvinte": {"materialul": "statul", "regulile": "regulile lunii", "e_corect": "statul e corect",
                    "sursa": "o cotă sau un plafon", "sursa_unde": "legea, articolul",
                    "unealta": "un program care recalculează statul", "la_material": "la stat",
                    "in_material": "în stat", "locul": "Angajatul",
                    "tema_pe_scurt": "un stat de plată de verificat cu AI-ul"},
        # tine de luna: alta luna, alta capcana, alt text
        "discutia_2": [f"Cum ai aflat cât e, în septembrie {ANUL}, suma care nu se impozitează la salariul minim?",
                       "numește o sursă oficială (ordonanța, Monitorul Oficial, legislatie.just.ro, ANAF), nu „mi-a spus "
                       "AI-ul” sau „știam”"],
    }


def scrie_pachet(dosar):
    (Path(dosar) / "pachet.json").write_text(json.dumps(pachet(), ensure_ascii=False, indent=2) + "\n",
                                             encoding="utf-8", newline="\n")


def scrie(dosar):
    """Scrie statul candidatului, tabelul de raspuns, cheia, amprenta ei si pachetul. Intoarce amprenta cheii."""
    dosar = Path(dosar)
    dosar.mkdir(parents=True, exist_ok=True)
    scrie_pachet(dosar)
    randuri = stat(True)
    xlsx.scrie(dosar / f"Stat_{FIRMA.replace(' ', '_')}_{ANUL}-{LUNA:02d}.xlsx",
               [COLOANE] + [[r[k] for k in COLOANE] for r in randuri] + [_total(randuri)],
               foaie="Stat", latimi=[7, 7, 8, 16, 12] + [14] * (len(COLOANE) - 5))
    xlsx.scrie(dosar / "Raspuns.xlsx", [["Marca", "Coloana", "Valoarea din stat", "Valoarea corecta", "De ce"]],
               foaie="Raspuns", latimi=[10, 28, 18, 18, 60], text_lung=(4,))
    text = json.dumps(cheia(), ensure_ascii=False, indent=2) + "\n"
    (dosar / "cheia.json").write_text(text, encoding="utf-8", newline="\n")
    amprenta = hashlib.sha256(text.encode("utf-8")).hexdigest()
    (dosar / "cheia.sha256").write_text(f"{amprenta}  cheia.json\n", encoding="utf-8", newline="\n")
    return amprenta
