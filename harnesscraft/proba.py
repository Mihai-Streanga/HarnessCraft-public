"""Nota probei: trei parti egale, calculate de cod (rapoarte/plan-proba.md, sectiunea 2).

NECALIBRAT, ca restul: ponderi egale, alese, nu masurate. Partile, fiecare intre 0 si 1:
- cheia: (erori gasite - semnalari gresite) / erorile de gasit, cel putin 0, din tabelul predat de candidat;
- conversatiile: numarul de „da” / 4, bifele recrutorului;
- discutia de dupa predare: numarul de „da” / 3.
O parte lipsa face proba „incompleta”, nu zero, ca in total.py. Niciun model.

Proba are un cadru, acelasi pentru toti (codul de aici), si un pachet al meseriei (date: un dosar din `proba/`, cu
tema, cheia, amprenta ei si `pachet.json`). Pachetul da cuvintele bifelor, locurile si campurile tabelului de raspuns si
intrebarea 2 a discutiei (capcana). Decizia: principii/DECIZII_INCHISE.md; rapoarte/propunere-proba-alte-meserii.md.

Potrivirea cu cheia se face pe loc, nu pe rand (regula aprobata de autor, 15 octombrie; la payroll locul e angajatul):
o eroare e gasita daca locul ei are un rand pe un camp in care se vede eroarea; un loc fara eroare semnalat, sau unul
cu eroare semnalat numai pe campuri corecte, e o semnalare gresita, o data pe loc. Valoarea corecta scrisa de candidat
nu intra in nota: o vede recrutorul langa cheie.
"""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from harnesscraft import xlsx
from harnesscraft.manifest import RADACINA

PACHETE = RADACINA / "proba"  # un dosar pe pachet; payroll il scrie proba_stat.scrie
IMPLICIT = "septembrie-2026"  # payroll, primul pachet: foile scrise inainte de pachete au fost pe el

# cadrul; {cuvintele} vin din pachet. La payroll ies la caracter ca textele aprobate de autor (tests/date/bifele-probei.md);
# o schimbare aici cere iar acordul lui
TIPAR_CONVERSATII = [
    "i-a dat AI-ului {materialul} și {regulile}, lipite în conversație sau ca fișier, nu doar întrebarea dacă {e_corect}",
    "a cerut AI-ului de unde are {sursa} ({sursa_unde}) sau a adus el sursa oficială în conversație",
    "a contrazis AI-ul cel puțin o dată, cu ce e greșit și de ce, nu doar cu „mai verifică” sau „ești sigur?”",
    "a făcut, cu AI-ul, {unealta} și s-a folosit de ce a ieșit (cod: în dosarul predat sau în conversație)",
]
# (intrebarea, bifa); a doua, None: o da pachetul, pentru ca tine de capcana lui (alta luna, alta capcana, alt text)
TIPAR_DISCUTIE = [
    ("Unde a greșit AI-ul în lucrul {la_material}?",
     "numește o greșeală anume a AI-ului (o cifră, o regulă), pe care recrutorul o găsește în conversațiile predate, "
     "nu doar „uneori greșește”"),
    None,
    ("Ce ai lăsat neverificat {in_material}, și de ce?",
     "numește ceva anume pe care nu l-a verificat și motivul (timpul, nu știa cum, nu i s-a părut important), nu „am "
     "verificat tot”"),
]
# cuvintele pe care le da fiecare pachet: in bife, in intrebari si pe ecranul probei
CUVINTE = ["materialul", "regulile", "e_corect", "sursa", "sursa_unde", "unealta", "la_material", "in_material", "locul",
           "tema_pe_scurt"]


def _fara_semne(text):
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return " ".join(t.lower().split())


class Pachet:
    """Pachetul meseriei, citit din `dosar/pachet.json`. Un cuvant lipsa il opreste: altfel o bifa ar iesi cu
    „{materialul}” in ea."""

    def __init__(self, dosar):
        self.dosar = Path(dosar)
        self.id = self.dosar.name
        d = json.loads((self.dosar / "pachet.json").read_text(encoding="utf-8"))
        if lipsa := [c for c in CUVINTE if c not in d["cuvinte"]]:
            raise ValueError(f"pachetul {self.id} nu are cuvintele: {', '.join(lipsa)}")
        self.meseria, self.titlu, self.stare_bife = d["meseria"], d["titlu"], d["stare_bife"]
        self.durata, self.termen = d["durata"], d["termen"]  # spuse candidatului inainte de acord
        self.tema = [tuple(x) for x in d["tema"]]  # ce primeste candidatul; cheia nu e aici si nu se descarca
        self.raspuns_cap = d["raspuns"]  # capul tabelului de raspuns: locul, campul, apoi ce scrie candidatul
        self.loc_in_cheie = d["cheia"]["loc"]  # cum se numeste locul in cheia.json (payroll: „marca”)
        self.locuri = {x[0]: x[1] for x in d["locuri"]}  # locul -> cum il vede recrutorul
        self.campuri = d["campuri"]
        self.cuvinte = c = d["cuvinte"]
        self.conversatii = [x.format(**c) for x in TIPAR_CONVERSATII]
        self.discutie = [tuple(d["discutia_2"]) if x is None else (x[0].format(**c), x[1].format(**c))
                         for x in TIPAR_DISCUTIE]
        # o foaie scrisa cu alte texte nu se noteaza cu acestea: amprenta lor sta in foaie, ca la ghidul interviului
        self.amprenta = hashlib.sha256("\n".join(self.conversatii + [x for q in self.discutie for x in q])
                                       .encode()).hexdigest()[:12]
        self._locuri = {_fara_semne(k): k for k in self.locuri}
        self._campuri = {_fara_semne(k): k for k in self.campuri}

    def cheia(self):
        """Cheia, cu amprenta verificata, si `loc` pe fiecare eroare si pe cazul corect, oricum l-ar numi pachetul."""
        ch = cheia(self.dosar)
        for x in ch["erori"] + [ch["plantata_corecta"]]:
            x["loc"] = x[self.loc_in_cheie]
        return ch

    def raspuns(self, cale):
        """Randurile tabelului predat, ca (locul, campul, valoarea corecta scrisa, de ce). Nu se ghiceste: un loc sau un
        camp necunoscut opreste citirea, cu randul lui; literele mari, diacriticele si spatiile in plus nu conteaza."""
        cap, unde = self.raspuns_cap, self.cuvinte["in_material"]
        randuri = xlsx.citeste(cale)
        if not randuri or [str(x).strip() if x is not None else "" for x in randuri[0][:len(cap)]] != cap:
            raise ValueError(f"primul rând nu e capul tabelului de răspuns: {', '.join(cap)}")
        gasite, probleme = [], []
        for nr, r in enumerate(randuri[1:], 2):
            loc, camp, _, corecta, de_ce = (list(r) + [None] * 5)[:5]
            if all(x in (None, "") for x in r):
                continue
            if _fara_semne(loc) not in self._locuri:
                probleme.append(f"rândul {nr}: {cap[0].lower()} „{str(loc).strip()}” nu e {unde}")
            elif _fara_semne(camp) not in self._campuri:
                probleme.append(f"rândul {nr}: {cap[1].lower()} „{camp}” nu e {unde}")
            else:
                gasite.append((self._locuri[_fara_semne(loc)], self._campuri[_fara_semne(camp)], corecta, de_ce or ""))
        if probleme:
            raise ValueError("; ".join(probleme))
        return gasite


def pachete():
    """Pachetele din `PACHETE`: payroll primul, apoi dupa meserie."""
    gasite = [Pachet(d) for d in sorted(PACHETE.iterdir()) if (d / "pachet.json").exists()]
    return sorted(gasite, key=lambda p: (p.id != IMPLICIT, p.meseria, p.titlu))


def pachet(id_=None):
    id_ = id_ or IMPLICIT
    if not re.fullmatch(r"[\w.-]+", id_) or not (PACHETE / id_ / "pachet.json").exists():
        raise ValueError(f"proba „{id_}” nu există")
    return Pachet(PACHETE / id_)


def cheia(dosar):
    """Cheia probei din `dosar`, numai daca amprenta ei e cea comisa: altfel candidatii s-ar nota pe chei diferite."""
    dosar = Path(dosar)
    octeti = (dosar / "cheia.json").read_bytes()
    comisa = (dosar / "cheia.sha256").read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(octeti).hexdigest() != comisa:
        raise ValueError("cheia nu are amprenta salvată în istoricul aplicației (git): s-a schimbat după ce a fost verificată")
    return json.loads(octeti.decode("utf-8"))


def nota_cheie(semnalate, ch):
    """semnalate: (locul, campul, ...), din `Pachet.raspuns`; ch: cheia, din `Pachet.cheia`. Intoarce erorile gasite,
    cele ratate, locurile semnalate gresit si fractia."""
    pe_loc = {}
    for loc, camp, *_ in semnalate:
        pe_loc.setdefault(loc, set()).add(camp)
    gasite, ratate = [], []
    for e in ch["erori"]:
        (gasite if pe_loc.get(e["loc"], set()) & set(e["coloane_afectate"]) else ratate).append(e["cod"])
    cu_eroare = {e["loc"] for e in ch["erori"] if e["cod"] in gasite}
    gresite = sorted(m for m in pe_loc if m not in cu_eroare)
    return {"gasite": gasite, "ratate": ratate, "gresite": gresite,
            "fractie": max(0, len(gasite) - len(gresite)) / ch["erori_de_gasit"]}


def _bife(bife, cate, nume):
    """Fractia de „da”; None daca partea nu s-a facut. Pe jumatate completata: refuzata."""
    if bife is None or all(x is None for x in bife):
        return None
    if len(bife) != cate:
        raise ValueError(f"{nume}: {len(bife)} bife, nu {cate}")
    if any(x is None for x in bife):
        raise ValueError(f"{nume}: completată pe jumătate")
    return sum(bool(x) for x in bife) / cate


def nota(cheie=None, conversatii=None, discutie=None):
    """cheie: rezultatul lui `nota_cheie` sau None; conversatii: 4 bife; discutie: 3 bife (True / False / None).
    `nota` e fractia care intra in total.py, sau None cat timp lipseste o parte."""
    parti = {"cheia": cheie["fractie"] if cheie else None,
             "conversațiile": _bife(conversatii, len(TIPAR_CONVERSATII), "conversațiile"),
             "discuția": _bife(discutie, len(TIPAR_DISCUTIE), "discuția")}
    lipsa = [n for n, x in parti.items() if x is None]
    return {"parti": parti, "lipsa": lipsa, "complet": not lipsa,
            "nota": None if lipsa else sum(parti.values()) / len(parti)}


def randare(n, ch=None, cheie=None):
    r = ["Proba, pe treimi (necalibrat):"]
    for nume, x in n["parti"].items():
        r.append(f"  {nume}: " + (f"{x * 100:.0f}%" if x is not None else "lipsă"))
    if cheie and ch:
        r.append(f"  din cheie: {len(cheie['gasite'])} din {ch['erori_de_gasit']} găsite, "
                 f"{len(cheie['gresite'])} semnalări greșite")
    r.append("  proba: " + (f"{n['nota'] * 100:.0f}%" if n["complet"] else
                            f"incompletă, lipsește: {', '.join(n['lipsa'])}"))
    return "\n".join(r)


# ── Foaia probei a candidatului: proba.md, un fisier text care se deschide si fara program, ca ghidul interviului ──

CAMPURI = {"linkuri": "Linkurile conversațiilor", "cod": "Dosarul de cod", "nota-C": "Notițe despre conversații",
           **{f"nota-D{i}": f"Ce a răspuns ({i})" for i in range(1, len(TIPAR_DISCUTIE) + 1)}}
_DUPA_ETICHETA = {v: k for k, v in CAMPURI.items()}
_BIFA = re.compile(r"^- ([CD]\d) \[(.*?)\] (.*)$")
_CAMP = re.compile(r"^\*\*(.+?):\*\* ?(.*)$")
_TEMA = re.compile(r"^Tema: `proba/([\w.-]+)`", re.M)


# Ce i se spune candidatului inainte de proba, ca sa poata accepta sau refuza (rapoarte/cercetare-gdpr-proba.md):
# ce face, cat dureaza, ce preda, cum se evalueaza si ce se intampla cu ce preda. Ce tine de firma (cine prelucreaza
# datele, temeiul, cat le pastreaza) aplicatia nu stie: ramane loc gol, intre paranteze drepte, de completat de firma.
# Textul, aprobat de autor pe 15 octombrie 2026; fixat la caracter in tests/date/invitatia-probei.md.
FIRMA_COMPLETEAZA = "[Firma completează]"


def invitatie(nume, p=None):
    p = p or pachet()
    return "\n".join([
        f"Bună ziua, {nume},",
        "",
        "Vă mulțumim pentru interviu. Vă propunem un pas următor: o probă practică de "
        f"{p.meseria}, {p.cuvinte['tema_pe_scurt']}.",
        "",
        "CE ESTE",
        f"Primiți un material cu date inventate și îl lucrați cu inteligența artificială, cum lucrați de obicei. Proba e "
        f"gândită pentru {p.durata} de lucru; aveți {p.termen} să o predați.",
        "",
        "CE PREDAȚI",
        "Tabelul de răspuns; linkul de partajare al fiecărei conversații cu AI-ul despre probă (o conversație, nu tot "
        "contul); dosarul de lucru, dacă ați lucrat și cu cod; câteva rânduri despre cum ați lucrat. Vă rugăm să nu "
        "puneți în conversații alte date personale decât cele de care e nevoie pentru probă.",
        "",
        "CUM SE EVALUEAZĂ",
        "O parte din notă o calculează un program, după reguli scrise, din tabelul predat; restul îl dă recrutorul, din "
        "conversații și dintr-o discuție scurtă după predare. Decizia o ia un om, nu programul.",
        "",
        "CE SE ÎNTÂMPLĂ CU CE PREDAȚI",
        "Folosim ce predați numai ca să evaluăm proba pentru acest post. După evaluare puteți opri partajarea "
        "conversațiilor.",
        f"{FIRMA_COMPLETEAZA}: cine prelucrează datele și cum îl contactați; temeiul prelucrării; cât timp se păstrează "
        "datele; dreptul de a cere accesul la ele, corectarea sau ștergerea lor și de a vă opune; dreptul de a face "
        "plângere la Autoritatea Națională de Supraveghere (ANSPDCP).",
        "",
        "Puteți refuza proba. Dacă sunteți de acord, răspundeți la acest mesaj și vă trimitem tema.",
    ])


def foaie(nume, demonstrativ=False, p=None):
    p = p or pachet()
    r = [f"# Proba — {nume}", ""]
    if demonstrativ:
        r += ["**Autoevaluare, demonstrativ:** candidatul răspunde și bifează singur.", ""]
    r += [f"Tema: `proba/{p.id}` · cheia `{(p.dosar / 'cheia.sha256').read_text(encoding='utf-8')[:12]}` · "
          f"bifele `{p.amprenta}`, {p.stare_bife}.", "",
          "Bifele se scriu „da” sau „nu” între paranteze; goale, partea nu e încă făcută. Nota o calculează programul.",
          "", "## Ce a predat", "", "**Linkurile conversațiilor:** ", "**Dosarul de cod:** ", "",
          "## Conversațiile", ""]
    r += [f"- C{i} [ ] {b}" for i, b in enumerate(p.conversatii, 1)]
    r += ["", "**Notițe despre conversații:** ", "", "## Discuția de după predare", ""]
    for i, (intrebare, bifa) in enumerate(p.discutie, 1):
        r += [f"### {i}. {intrebare}", f"- D{i} [ ] Da, dacă: {bifa}", f"**Ce a răspuns ({i}):** ", ""]
    return "\n".join(r)


def pachetul_foii(text):
    """Pachetul pe care a fost scrisa foaia, din randul temei."""
    m = _TEMA.search(text)
    return pachet(m.group(1) if m else None)


def valori(text):
    """Campurile foii: bifele (C1-C4, D1-D3: "", "da", "nu") si textele (CAMPURI)."""
    v = {}
    for rand in text.splitlines():
        if m := _BIFA.match(rand):
            v[m.group(1)] = m.group(2).strip().lower()
        elif (m := _CAMP.match(rand)) and m.group(1) in _DUPA_ETICHETA:
            v[_DUPA_ETICHETA[m.group(1)]] = m.group(2)
    return v


def scrie(text, noi):
    """Foaia cu valorile din formular. O cheie necunoscuta sau o bifa alta decat da / nu / gol e refuzata."""
    if necunoscute := sorted(set(noi) - set(valori(text))):
        raise ValueError(f"câmpuri care nu sunt în foaia probei: {', '.join(necunoscute)}")
    rez = []
    for rand in text.splitlines():
        if (m := _BIFA.match(rand)) and m.group(1) in noi:
            val = noi[m.group(1)].strip().lower()
            if val not in ("", "da", "nu"):
                raise ValueError(f"{m.group(1)}: „{val}” nu e „da” sau „nu”")
            rand = f"- {m.group(1)} [{val or ' '}] {m.group(3)}"
        elif (m := _CAMP.match(rand)) and _DUPA_ETICHETA.get(m.group(1)) in noi:
            rand = f"**{m.group(1)}:** {' '.join(noi[_DUPA_ETICHETA[m.group(1)]].split())}"
        rez.append(rand)
    return "\n".join(rez) + ("\n" if text.endswith("\n") else "")


def bife(text):
    """(conversatiile, discutia), ca liste de True / False / None, pentru `nota`."""
    if f"bifele `{pachetul_foii(text).amprenta}`" not in text:
        raise ValueError("foaia probei a fost scrisă cu alte bife: nota s-ar face pe altele")
    v = valori(text)
    ca = {"da": True, "nu": False}
    return ([ca.get(v.get(f"C{i}", "")) for i in range(1, len(TIPAR_CONVERSATII) + 1)],
            [ca.get(v.get(f"D{i}", "")) for i in range(1, len(TIPAR_DISCUTIE) + 1)])


def inceputa(text, are_tabel):
    """Proba e inceputa daca s-a incarcat tabelul sau s-a bifat ceva: de aici pachetul nu se mai schimba."""
    return are_tabel or any(v for k, v in valori(text).items() if re.fullmatch(r"[CD]\d", k))


def schimba_pachetul(text, p):
    """Foaia scrisa din nou pe pachetul `p`, cu ce s-a scris deja in campurile text (linkurile, dosarul, notitele)."""
    nume = text.splitlines()[0].removeprefix("# Proba — ")
    pastrate = {k: v for k, v in valori(text).items() if k in CAMPURI and v}
    return scrie(foaie(nume, "**Autoevaluare, demonstrativ:**" in text, p), pastrate)
