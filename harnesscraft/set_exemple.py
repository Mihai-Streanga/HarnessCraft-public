"""Setul de date al exemplelor: capitolul din manual si capturile.

Numele celor cinci sunt inventate de agent, fara sursa (prenume si nume obisnuite, combinate): orice potrivire cu o
persoana reala e intamplatoare. E-mailurile lor sunt pe example.com, domeniu rezervat pentru exemple.

Cinci candidati inventati si autorul, trecuti prin aceleasi functii ca butoanele (`candidati.py`), intr-un dosar
separat, `tmp-set-exemple/`, refacut de la zero la fiecare rulare: `candidaturi/` nu se atinge. Proiectele de
portofoliu ale celor inventati le face scriptul, cu autor, mesaje si date fixe: aceleasi commit-uri la fiecare rulare,
deci aceleasi cifre. Treapta o calculeaza fisa; scriptul se opreste daca iese alta decat cea ceruta tipului.

Apoi `completeaza`: raspunsurile, bifele, decizia de proba, acordul si tabelul predat, din `exemple-candidati/«id».md`
(scrise de agent; bifele, date de agent la cererea autorului), trecute tot prin functiile butoanelor.
Autorul vine din dosarul lui: ghidul, decizia, tabelul si foaia probei de acolo.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from harnesscraft import candidati, formular, proba, xlsx
from harnesscraft.fisa import NUME_TREPTE
from harnesscraft.manifest import RADACINA
from harnesscraft.total import PLAFON_FARA_COD, PONDERE

SET = RADACINA / "tmp-set-exemple"
SURSE = RADACINA / "exemple-candidati"
REZULTATE = SURSE / "rezultate.json"  # cifrele capitolului din manual, scrise de `set-exemple`
PROIECT_AUTOR = RADACINA.parent / "Metoda"  # proiectul autorului, langa acesta, pe masina lui
AUTORUL = RADACINA / "candidaturi" / "finalizate" / "mihai-streanga"  # citit, nu scris
_CAMP = re.compile(r"^\*\*(.+?):\*\* ?(.*)$", re.M)
_RAND_TABEL = re.compile(r"^\| (\d+) \| (.+?) \| (.+?) \| (.+?) \| (.*?) \|$", re.M)

# --- programul candidatilor inventati: un calculator de concedii, acelasi la toti; difera ce l-a insotit ---

SARBATORI = '''"""Sarbatorile legale din 2026, zile libere (Codul muncii, art. 139)."""
from datetime import date

SARBATORI = {
    date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 6), date(2026, 1, 7), date(2026, 1, 24),
    date(2026, 4, 10), date(2026, 4, 12), date(2026, 4, 13), date(2026, 5, 1), date(2026, 5, 31),
    date(2026, 6, 1), date(2026, 8, 15), date(2026, 11, 30), date(2026, 12, 1), date(2026, 12, 25),
    date(2026, 12, 26),
}
'''

CALCUL = '''"""Zilele de concediu de odihna: cate zile lucratoare intra intr-o cerere si cat ramane din dreptul pe an."""
from datetime import timedelta

from concedii.sarbatori import SARBATORI


def zile_lucratoare(inceput, sfarsit):
    zile, d = 0, inceput
    while d <= sfarsit:
        if d.weekday() < 5 and d not in SARBATORI:
            zile += 1
        d += timedelta(days=1)
    return zile


def sold(drept, cereri):
    """Zilele ramase: dreptul pe an minus zilele lucratoare din fiecare cerere (inceput, sfarsit)."""
    return drept - sum(zile_lucratoare(i, s) for i, s in cereri)
'''

CALCUL_CU_VERIFICARE = CALCUL + '''

def verifica_cererea(inceput, sfarsit, ramase):
    """Motivul pentru care cererea nu se poate aproba, sau None."""
    if sfarsit < inceput:
        return "sfarsitul e inaintea inceputului"
    if zile_lucratoare(inceput, sfarsit) > ramase:
        return "cererea depaseste zilele ramase"
    return None
'''

TESTE = '''from datetime import date

from concedii.calcul import sold, zile_lucratoare


def test_o_saptamana_fara_sarbatori():
    assert zile_lucratoare(date(2026, 9, 7), date(2026, 9, 13)) == 5


def test_sarbatoarea_nu_se_numara():
    assert zile_lucratoare(date(2026, 11, 30), date(2026, 12, 4)) == 3


def test_soldul():
    assert sold(21, [(date(2026, 9, 7), date(2026, 9, 11))]) == 16
'''

TESTE_VERIFICARE = TESTE + '''

def test_cererea_peste_sold():
    from concedii.calcul import verifica_cererea
    assert verifica_cererea(date(2026, 9, 7), date(2026, 9, 18), 5) == "cererea depaseste zilele ramase"
'''

INIT = '"""Calculatorul de concedii."""\n'

README = """# Concedii

Calculează zilele lucrătoare dintr-o cerere de concediu de odihnă și soldul rămas pe an, cu sărbătorile legale din 2026.
"""

MIT = """MIT License

Copyright (c) 2026 {nume}

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
"""

CI = """name: teste
on: [push, pull_request]
jobs:
  teste:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pytest
      - run: python -m pytest -q
"""

SKILL = """---
name: sarbatori-noi
description: Adaugă sărbătorile legale ale unui an nou în calculator.
---

# Sărbătorile unui an nou

1. Cauți lista oficială (Codul muncii, art. 139, și hotărârile de guvern pentru zilele în plus).
2. Le scrii în `concedii/sarbatori.py`, una pe rând, cu data.
3. Adaugi un test cu o săptămână care conține o sărbătoare nouă.
4. Rulezi `py -m pytest -q`; nu închei până nu trec toate.
"""

PRE_COMMIT = """repos:
  - repo: local
    hooks:
      - id: teste
        name: teste
        entry: python -m pytest -q
        language: system
        pass_filenames: false
"""

SETARI_HOOKS = """{
  "hooks": {
    "PostToolUse": [
      {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "python -m pytest -q"}]}
    ]
  }
}
"""

ARHITECTURA = """# Arhitectura

Un pachet, `concedii`, cu două module: `sarbatori.py` ține datele (zilele libere ale anului), `calcul.py` ține
regulile (zile lucrătoare, sold, verificarea cererii). Regulile nu citesc nimic din afară: anul nou intră numai prin
lista de sărbători.

## Decizii

- Sărbătorile stau în cod, nu într-un fișier de configurare: se schimbă o dată pe an și trec prin teste.
- Zilele se numără inclusiv capetele cererii: așa le scrie și formularul de concediu.
"""

CLAUDE_1 = """# Proiect

Calculator de concedii în Python. Scrie cod clar, cu comentarii, și explică-mi ce ai schimbat.
"""

CLAUDE_2 = """# Calculatorul de concedii

Program mic în Python: zilele lucrătoare dintr-o cerere de concediu și soldul pe an.

## Comenzi

- testele: `py -m pytest -q`

## Reguli

- Nu modifica sărbătorile fără sursa oficială: anul și articolul se scriu în comentariu.
- Nu adăuga biblioteci noi fără să mă întrebi.
- Răspunde în română.
"""

CLAUDE_3 = CLAUDE_2 + """
## Sarcini

- Un an nou de sărbători: skill-ul `sarbatori-noi`. Lista stă în `concedii/sarbatori.py`.
- Testele rulează și pe GitHub, la fiecare trimitere; o trimitere cu teste picate nu se unește.
"""

CLAUDE_4 = """# Calculatorul de concedii

Program în Python: zilele lucrătoare dintr-o cerere de concediu, soldul pe an și verificarea cererii.

## Structura

```
concedii/
├── calcul.py       regulile: zile lucrătoare, sold, verificarea cererii
└── sarbatori.py    sărbătorile legale ale anului
tests/
└── test_calcul.py
```

Arhitectura și deciziile: `docs/ARHITECTURA.md`. O schimbare de structură se scrie acolo, în același commit.

## Comenzi

- testele: `py -m pytest -q`
- verificările de dinainte de commit: `pre-commit run --all-files`

## Reguli

- Nu modifica `concedii/sarbatori.py` fără sursa oficială: anul și articolul se scriu în comentariu.
- Nu adăuga biblioteci noi fără să mă întrebi.
- Nu ocoli hook-ul de teste: dacă pică, repari cauza.

## Sarcini

- Un an nou de sărbători: skill-ul `.claude/skills/sarbatori-noi/SKILL.md`; testul lui intră în `tests/test_calcul.py`.
"""

CALCUL_ZILE = CALCUL.split("\n\n\ndef sold")[0] + "\n"  # inainte de sold
SARBATORI_GOL = 'from datetime import date\n\nSARBATORI = set()  # de completat\n'

BAZA = {"concedii/__init__.py": INIT, "concedii/sarbatori.py": SARBATORI, "concedii/calcul.py": CALCUL,
        "README.md": README}
AI = "\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

# Commit-urile fiecarui proiect: (ziua, mesajul, fisierele scrise atunci). Ora e fixa: 10:00, cate un minut in plus.
ISTORII = {
    "ioana": [
        ("2026-06-02", "primul calcul de zile", BAZA | {"CLAUDE.md": CLAUDE_1, "concedii/calcul.py": CALCUL_ZILE,
                                                        "concedii/sarbatori.py": SARBATORI_GOL}),
        ("2026-06-09", "sarbatorile pe 2026", {"concedii/sarbatori.py": SARBATORI}),
        ("2026-06-16", "soldul pe an", {"concedii/calcul.py": CALCUL}),
        ("2026-06-30", "cateva teste", {"tests/test_calcul.py": TESTE}),
    ],
    "andrei": [
        ("2026-05-04", "calculatorul de concedii, primul pas", BAZA),
        ("2026-05-06", "reguli pentru AI in CLAUDE.md", {"CLAUDE.md": CLAUDE_2}),
        ("2026-05-11", "teste pentru zilele lucratoare" + AI, {"tests/test_calcul.py": TESTE}),
        ("2026-05-20", "verificarea cererii peste sold" + AI,
         {"concedii/calcul.py": CALCUL_CU_VERIFICARE, "tests/test_calcul.py": TESTE_VERIFICARE}),
        ("2026-05-21", "licenta MIT", {"LICENSE": MIT.format(nume="Andrei Costache")}),
    ],
    "cristina": [
        ("2026-04-01", "calculatorul de concedii", BAZA | {"CLAUDE.md": CLAUDE_2}),
        ("2026-04-03", "teste" + AI, {"tests/test_calcul.py": TESTE}),
        ("2026-04-10", "testele ruleaza pe GitHub la fiecare trimitere", {".github/workflows/teste.yml": CI}),
        ("2026-04-22", "skill pentru sarbatorile unui an nou" + AI,
         {".claude/skills/sarbatori-noi/SKILL.md": SKILL, "CLAUDE.md": CLAUDE_3}),
        ("2026-05-05", "verificarea cererii" + AI,
         {"concedii/calcul.py": CALCUL_CU_VERIFICARE, "tests/test_calcul.py": TESTE_VERIFICARE}),
        ("2026-05-06", "licenta MIT", {"LICENSE": MIT.format(nume="Cristina Pavel")}),
    ],
    # tot proiectul intr-o zi, din primul commit: fisa e buna, istoricul nu arata cum s-a ajuns acolo
    "victor": [
        ("2026-09-14", "initial commit", BAZA | {
            "concedii/calcul.py": CALCUL_CU_VERIFICARE, "tests/test_calcul.py": TESTE_VERIFICARE,
            "CLAUDE.md": CLAUDE_4, "docs/ARHITECTURA.md": ARHITECTURA, ".github/workflows/teste.yml": CI,
            ".claude/skills/sarbatori-noi/SKILL.md": SKILL, ".claude/settings.json": SETARI_HOOKS,
            ".pre-commit-config.yaml": PRE_COMMIT, "LICENSE": MIT.format(nume="Victor Matei")}),
        ("2026-09-14", "update readme" + AI, {"README.md": README + "\nRulează testele cu `py -m pytest -q`.\n"}),
    ],
}

# Cei sase: (tipul din plan, numele, proiectul, treapta ceruta = indicele din NUME_TREPTE, motivul „fara cod”)
CANDIDATI = [
    (1, "Mihai Streanga", "metoda", 3, None),
    (2, "Elena Dobrescu", None, None, "Lucrează cu AI-ul numai în conversații (chat), pentru texte și analize de "
                                      "resurse umane; nu scrie cod."),
    (3, "Andrei Costache", "andrei", 1, None),
    (4, "Ioana Vlădescu", "ioana", 0, None),
    (5, "Victor Matei", "victor", 3, None),
    (6, "Cristina Pavel", "cristina", 2, None),
]
EMAIL = {"ioana": "ioana.vladescu", "andrei": "andrei.costache", "cristina": "cristina.pavel", "victor": "victor.matei"}
NUME = {"ioana": "Ioana Vlădescu", "andrei": "Andrei Costache", "cristina": "Cristina Pavel", "victor": "Victor Matei"}

# fara setarile masinii: aceleasi octeti si aceleasi commit-uri oriunde
GIT = ["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=nu-exista",
       "-c", "init.defaultBranch=main"]


def _git(cale, *args, env=None):
    r = subprocess.run([*GIT, "-C", str(cale), *args], capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, **(env or {})})
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def proiect(cheie, proiecte):
    """Depozitul inventat, din ISTORII; intoarce calea lui."""
    d = proiecte / cheie
    d.mkdir(parents=True)
    _git(d, "init", "-q")
    for i, (ziua, mesaj, fisiere) in enumerate(ISTORII[cheie]):
        for cale, text in fisiere.items():
            (d / cale).parent.mkdir(parents=True, exist_ok=True)
            (d / cale).write_bytes(text.encode("utf-8"))
        ora = f"{ziua}T10:{i:02d}:00+03:00"
        cine = {"GIT_AUTHOR_NAME": NUME[cheie], "GIT_AUTHOR_EMAIL": f"{EMAIL[cheie]}@example.com",
                "GIT_AUTHOR_DATE": ora, "GIT_COMMITTER_NAME": NUME[cheie],
                "GIT_COMMITTER_EMAIL": f"{EMAIL[cheie]}@example.com", "GIT_COMMITTER_DATE": ora}
        _git(d, "add", "-A")
        _git(d, "commit", "-q", "-m", mesaj, env=cine)
    return d


def metoda(proiecte):
    """Proiectul autorului, la commitul fisei din dosarul lui: aceleasi cifre ca in demonstratie. Cand commitul nu mai
    e in proiect (istoricul rescris), cazul se reconstruieste pe commitul de azi: cazul autorului nu lipseste
    pe masina lui (decizia autorului, 21 octombrie 2026). None pe o masina fara proiectul sau fara dosarul autorului."""
    f = AUTORUL / "fisa.json"
    if not (PROIECT_AUTOR / ".git").exists() or not f.exists():
        return None
    commit = json.loads(f.read_text(encoding="utf-8"))["commit"]
    d = proiecte / "metoda"
    subprocess.run([*GIT, "clone", "-q", str(PROIECT_AUTOR), str(d)], check=True, capture_output=True)
    if subprocess.run([*GIT, "-C", str(d), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True).returncode == 0:
        _git(d, "checkout", "-q", commit)
    return d


def construieste(radacina=SET, cu_autorul=True):
    """Setul de la zero, in `radacina`. Intoarce, pe fiecare candidat: tipul, numele, identificatorul, commitul
    proiectului, treapta si punctajul fisei. `cu_autorul=False`: fara cazul 1 (testele, pe orice masina)."""
    if radacina.exists():
        shutil.rmtree(radacina, onexc=candidati._fa_scriibil)
    proiecte, dosar = radacina / "proiecte", radacina / "candidaturi"
    proiecte.mkdir(parents=True)
    rez = []
    for tip, nume, cheie, treapta, fara_cod in CANDIDATI:
        if cheie == "metoda":
            p = metoda(proiecte) if cu_autorul else None
            if p is None:
                rez.append({"tip": tip, "nume": nume, "sarit": "fără proiectul sau fără dosarul autorului"
                            if cu_autorul else "cerut"})
                continue
        else:
            p = proiect(cheie, proiecte) if cheie else None
        id_ = candidati.nou(nume, "" if p is None else str(p), demonstrativ=cheie == "metoda", dosar=dosar,
                            fara_cod=fara_cod)
        c = candidati.citeste(id_, dosar)
        r = {"tip": tip, "nume": nume, "id": id_}
        if p is not None:
            candidati.analizeaza(c)
            fj = candidati.fisa(c)
            f = fj["fisa"]
            if f["nivel"] != treapta:
                raise RuntimeError(f"{nume}: fișa dă treapta „{NUME_TREPTE[f['nivel']]}”, tipul {tip} cere "
                                   f"„{NUME_TREPTE[treapta]}”")
            r |= {"commit": fj["commit"], "treapta": f["nivel"], "total": f["total"], "maxim": f["maxim"]}
        rez.append(r)
    return rez


def _plin(valori):
    return {k: v for k, v in valori.items() if v}


def _tabel(c, randuri):
    """Tabelul de raspuns predat, din randurile sursei, incarcat ca de la butonul „Alege fișierul”."""
    tmp = c["dosar"] / "tmp-tabel-predat.xlsx"
    xlsx.scrie(tmp, [candidati.pachetul_probei(c).raspuns_cap] +
               [[int(m), col, int(a), int(b), de_ce] for m, col, a, b, de_ce in randuri])
    octeti = tmp.read_bytes()
    tmp.unlink()
    candidati.incarca_raspuns(c, octeti)


def _din_sursa(c, text):
    """Un candidat inventat: interviul, decizia, acordul, apoi proba, din `exemple-candidati/«id».md`."""
    interviul, _, rest = text.partition("## Decizia de probă")
    candidati.salveaza_interviu(c, _plin(formular.valori(interviul)))
    campuri = dict(_CAMP.findall(rest.partition("## Proba\n")[0]))
    candidati.hotaraste_proba(c, campuri["Merge la probă (da / nu)"].strip().lower(),
                              campuri.get("Motivul, dacă nu", ""))
    raspuns, data, cum = campuri["Răspunsul candidatului la invitație"].split(" · ", 2)
    candidati.consemneaza_acordul(c, "da" if raspuns == "a acceptat" else "nu", data, cum)
    if raspuns == "a acceptat":
        partea = rest.partition("## Proba\n")[2]
        _tabel(c, _RAND_TABEL.findall(partea))
        candidati.salveaza_proba(c, _plin(proba.valori(partea)))


def _din_dosarul_autorului(c):
    """Autorul: ghidul, decizia, tabelul si foaia probei lui, copiate; programul probei, analizat din nou."""
    stiute = formular.valori(candidati.ghid(c))
    vechi = formular.valori((AUTORUL / "ghid.md").read_text(encoding="utf-8"))
    candidati.salveaza_interviu(c, {k: v for k, v in _plin(vechi).items() if k in stiute})
    d = json.loads((AUTORUL / candidati.DECIZIA).read_text(encoding="utf-8"))
    candidati.hotaraste_proba(c, d["decizia"], d["motivul"])
    a = d["acordul"]
    candidati.consemneaza_acordul(c, a["raspuns"], a["data"], a["cum"])
    candidati.incarca_raspuns(c, (AUTORUL / "Raspuns.xlsx").read_bytes())
    foaia = _plin(proba.valori((AUTORUL / "proba.md").read_text(encoding="utf-8")))
    cod = foaia.pop("cod", "")
    candidati.salveaza_proba(c, foaia)
    if cod and Path(cod).is_dir():
        candidati.analizeaza_proba(c, cod)


def completeaza(rez, radacina=SET):
    """Pasii 2-4 pe fiecare candidat construit, prin functiile butoanelor; adauga in `rez` rezultatul calculat."""
    dosar = radacina / "candidaturi"
    for r in rez:
        if "sarit" in r:
            continue
        c = candidati.citeste(r["id"], dosar)
        if r["tip"] == 1:
            _din_dosarul_autorului(c)
        else:
            _din_sursa(c, (SURSE / f"{r['id']}.md").read_text(encoding="utf-8"))
        c = candidati.citeste(r["id"], dosar)
        s = candidati.rezultat(c)
        r |= {"interviul": s["medie"]["medie"], "proba": s["proba"]["nota"]["parti"],
              "puncte": s["total"]["puncte"], "punctaj": s["total"]["total"], "complet": s["total"]["complet"],
              "fara_proba": candidati.fara_proba(c), "fisa_probei": bool(candidati.fisa_probei(c))}
    return rez


GATA = "gata"  # semnul unui set intreg: aplicatia nu deschide un set facut pe jumatate


def autorul_aici():
    """Ca in `metoda`: fara proiectul autorului sau fara fisa din dosarul lui, cazul 1 se sare."""
    return not ce_lipseste_autorului()


def ce_lipseste_autorului():
    """Motivul pentru care cazul 1 se sare, spus pe ecranul „Exemple”; gol cand nu lipseste nimic. Intr-o clona noua
    lipseste dosarul: `candidaturi/` nu vine cu git, se aduce din copia de siguranta (docs/INSTALARE.md)."""
    lipsa = []
    if not (PROIECT_AUTOR / ".git").exists():
        lipsa.append("proiectul lui nu e pe acest calculator")
    if not (AUTORUL / "fisa.json").exists():
        lipsa.append("dosarul lui nu e printre candidații de pe acest calculator; vine din copia de siguranță a "
                     "candidaturilor")
    return " și ".join(lipsa)


def gata(radacina=SET):
    return (radacina / GATA).is_file()


def reface(radacina=SET):
    """Setul intreg, de la zero, apoi semnul „gata”. Din comanda si din aplicatie. Setul de dinainte sta deoparte cat
    se face cel nou si se intoarce daca refacerea pica: o refacere picata nu strica „Exemple” (decizii-audit-unic.md,
    B4). Mutat, nu copiat: candidatii lui tin caile proiectelor din set, valabile numai la locul lor."""
    deoparte = radacina.with_name(f"{radacina.name}-inainte-de-refacere")
    if deoparte.exists():
        shutil.rmtree(deoparte, onexc=candidati._fa_scriibil)
    if radacina.exists():
        radacina.rename(deoparte)
    try:
        rez = completeaza(construieste(radacina), radacina)
        (radacina / GATA).write_text("", encoding="utf-8")
    except BaseException:
        if radacina.exists():
            shutil.rmtree(radacina, onexc=candidati._fa_scriibil)
        if deoparte.exists():
            deoparte.rename(radacina)
        raise
    if deoparte.exists():
        shutil.rmtree(deoparte, onexc=candidati._fa_scriibil)
    return rez


def rezultate(rez):
    """Cifrele capitolului din manual, gata de citat: procentele probei intregi, treapta numarata de la 1, maximele
    alaturi. Capitolul nu are alta cifra decat de aici (tests/test_set_exemple.py)."""
    out = []
    for r in rez:
        if "punctaj" not in r:
            continue
        are_fisa = "treapta" in r
        out.append({"tip": r["tip"], "nume": r["nume"],
                    "treapta": r["treapta"] + 1 if are_fisa else None,
                    "treapta_nume": NUME_TREPTE[r["treapta"]] if are_fisa else None,
                    "fisa": r["total"] if are_fisa else None, "fisa_maxim": r["maxim"] if are_fisa else None,
                    "interviul": r["interviul"],
                    "proba": {k: None if v is None else round(v * 100) for k, v in r["proba"].items()},
                    "puncte": r["puncte"], "total": r["punctaj"], "complet": r["complet"]})
    return {"parte": round(PONDERE, 1), "maxim": 100, "interviul_maxim": 4, "plafon_fara_cod": PLAFON_FARA_COD,
            "candidati": out}


def scrie_rezultate(rez, cale=REZULTATE):
    """`rezultate.json`, comis. Fara proiectul lui, cazul autorului ramane cel scris inainte, pe masina lui."""
    nou = rezultate(rez)
    tipuri = {c["tip"] for c in nou["candidati"]}
    if cale.exists():
        vechi = json.loads(cale.read_text(encoding="utf-8"))["candidati"]
        nou["candidati"] += [c for c in vechi if c["tip"] not in tipuri]
    nou["candidati"].sort(key=lambda c: c["tip"])
    cale.write_text(json.dumps(nou, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return cale


def _procent(x):
    return "lipsă" if x is None else f"{x * 100:.0f}%"


def randare(rez, radacina=SET):
    randuri = [f"Setul de exemple: {radacina / 'candidaturi'}"]
    for r in rez:
        if "sarit" in r:
            ce = f"sărit: {r['sarit']}"
        elif "treapta" in r:
            ce = f"{NUME_TREPTE[r['treapta']]}, {r['total']:g} din {r['maxim']:g} (commitul {r['commit'][:7]})"
        else:
            ce = "fără proiect cu cod"
        randuri.append(f"  {r['tip']}. {r['nume']}: {ce}")
        if "punctaj" in r:
            p = r["puncte"]
            proba_ = "; ".join(f"{k} {_procent(v)}" for k, v in r["proba"].items())
            randuri.append(f"     interviul {r['interviul']:g} din 4 · proba: {proba_}"
                           + (" · fișa probei" if r["fisa_probei"] else ""))
            randuri.append(f"     total {r['punctaj']:g} din 100 ("
                           + ", ".join(f"{k} {'lipsă' if v is None else f'{v:g}'}" for k, v in p.items()) + ")"
                           + ("" if r["complet"] else f" · incomplet: {r['fara_proba'] or 'lipsește o parte'}"))
    return "\n".join(randuri)
