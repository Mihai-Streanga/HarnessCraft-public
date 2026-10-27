"""Ghidul de interviu ca formular: interfata citeste si scrie randurile ghidului, nu alt format.

De ce: ghidul markdown ramane singura sursa, iar `interviu-scor` singura regula de punctaj. Un ghid completat in
interfata se puncteaza la fel ca unul completat de mana (testul e in tests/test_formular.py).

Campurile, pe chei stabile:
  S1.1 ... S7.3       - bifele: "", "da" sau "nu";
  nota-parcurs, nota-S1 ... nota-S7, nota-T1 ..., nota-L1 ... - randurile „Note:” din sectiunea lor;
  L1 ... L3           - textul intrebarii recrutorului („**Întrebarea ta 1:**”), fara bife;
  concluzia           - „**Concluzia recrutorului:**”.
Valorile sunt pe un singur rand: un rand nou din formular devine spatiu.
"""
import re

BIFA = re.compile(r"^- (S\d+)\.([123]) \[(.*?)\] (.*)$")
NOTA = re.compile(r"^Note: ?(.*)$")
LIBERA = re.compile(r"^\*\*Întrebarea ta (\d+):\*\* ?(.*)$")
CONCLUZIA = re.compile(r"^\*\*Concluzia recrutorului:\*\* ?(.*)$")
SECTIUNE = [(re.compile(r"^### (S\d+)\. "), lambda m: m.group(1)),
            (re.compile(r"^## (?:2|II)\. Parcursul"), lambda m: "parcurs"),
            (re.compile(r"^\*\*(\d+)\.\*\* "), lambda m: f"T{m.group(1)}"),
            (re.compile(r"^\*\*Întrebarea ta (\d+):\*\*"), lambda m: f"L{m.group(1)}"),
            (re.compile(r"^##+ "), lambda m: None)]


def _context(rand, ctx):
    for tipar, cheie in SECTIUNE:
        if m := tipar.match(rand):
            return cheie(m)
    return ctx


def blocuri(ghid):
    """Ghidul, rand cu rand, ca blocuri pentru formular: ("text", rand) sau (tip, cheie, valoare, eticheta)."""
    rez, ctx = [], None
    for rand in ghid.splitlines():
        ctx = _context(rand, ctx)
        if m := BIFA.match(rand):
            rez.append(("bifa", f"{m.group(1)}.{m.group(2)}", m.group(3).strip().lower(), m.group(4)))
        elif (m := NOTA.match(rand)) and ctx:
            rez.append(("nota", f"nota-{ctx}", m.group(1), "Note"))
        elif m := LIBERA.match(rand):
            rez.append(("libera", f"L{m.group(1)}", m.group(2), f"Întrebarea ta {m.group(1)}"))
        elif m := CONCLUZIA.match(rand):
            rez.append(("concluzia", "concluzia", m.group(1), "Concluzia recrutorului"))
        else:
            rez.append(("text", rand))
    return rez


def valori(ghid):
    return {b[1]: b[2] for b in blocuri(ghid) if b[0] != "text"}


def scrie(ghid, noi):
    """Ghidul cu valorile din formular. O cheie necunoscuta sau o bifa alta decat da / nu / gol e refuzata."""
    cunoscute = valori(ghid)
    if necunoscute := sorted(set(noi) - set(cunoscute)):
        raise ValueError(f"câmpuri care nu sunt în ghid: {', '.join(necunoscute)}")
    rez, ctx = [], None
    for rand in ghid.splitlines():
        ctx = _context(rand, ctx)
        if (m := BIFA.match(rand)) and (k := f"{m.group(1)}.{m.group(2)}") in noi:
            v = noi[k].strip().lower()
            if v not in ("", "da", "nu"):
                raise ValueError(f"{k}: „{v}” nu e „da” sau „nu”")
            rand = f"- {k} [{v}] {m.group(4)}" if v else f"- {k} [ ] {m.group(4)}"
        elif (m := NOTA.match(rand)) and ctx and f"nota-{ctx}" in noi:
            rand = f"Note: {_un_rand(noi[f'nota-{ctx}'])}"
        elif (m := LIBERA.match(rand)) and f"L{m.group(1)}" in noi:
            rand = f"**Întrebarea ta {m.group(1)}:** {_un_rand(noi[f'L{m.group(1)}'])}"
        elif CONCLUZIA.match(rand) and "concluzia" in noi:
            rand = f"**Concluzia recrutorului:** {_un_rand(noi['concluzia'])}"
        rez.append(rand)
    return "\n".join(rez) + ("\n" if ghid.endswith("\n") else "")


def _un_rand(text):
    return " ".join(text.split())
