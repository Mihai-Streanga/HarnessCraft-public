"""Plasa pe ecrane (B38, rapoarte/decizii-audit-unic-660cabe.md): porneste de la `/`, urmeaza legaturile de pe aceeasi
gazda si trece textul vizibil al fiecarei pagini prin plasele textului pentru recrutor. O pagina noua sau o stare noua
intra singura, fara sa-i aleaga cineva adresa. Ce nu acopera: textul candidatilor nu se desparte de al programului decat
pe datele de proba cunoscute de aici; erorile intra numai prin POST-urile scrise mai jos."""
import re
from urllib.parse import urljoin, urlparse

from harnesscraft import audit, termeni
from tests.test_decizii_audit_unic import TOATE, _candidat, _vizibil
from tests.test_interfata import site  # noqa: F401 (fixture)
from tests.test_interfata_proba import _erori, _incarca, _tabel

LEGATURA = re.compile(r'<a\b(?![^>]*\bdownload\b)[^>]*\bhref="([^"#]+)')
PLASE = {
    "o dată în forma fișierelor (AAAA-LL-ZZ)": re.compile(r"\b20\d\d-\d\d-\d\d\b"),
    "o valoare a programului (True / False / None)": re.compile(r"\b(True|False|None)\b"),
    "numele unei stări scris ca atare": re.compile(r"(?<![(\w-])in-analiza\b(?!\))"),
    "punct urmat de punct și virgulă": re.compile(r"\.;"),
    # B26 (rapoarte/decizii-audit-unic-88a6d30.md): ce cauta `/utilizare` inca de mana
    "un cod în afara parantezei „(cod …)”": re.compile(r"(?<!cod )\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,64}\b"),
    "o cheie a programului (S1.1, C1)": re.compile(r"\b[SC]\d+(?:\.\d+)?\b"),
    "numele bifei „fără proiect cu cod” scris ca atare": re.compile(r"\bfara-cod\b"),
    "„nivel” sau „scor”, nu „treapta” și „punctajul”": re.compile(r"\b(?:nivel|scor)\w*", re.I),
}


def _text(html, proiect):
    """Textul vizibil din `<main>`, fara calea proiectului de proba si fara ce sta in <code> (nume de fisiere, puse
    in paranteza dupa explicatie: regula termenilor le cauta separat)."""
    html = html.split("<main>", 1)[-1]
    html = re.sub(r"(?s)<code>.*?</code>", "(cod)", html)
    return _vizibil(html).replace(proiect, " ").replace(proiect.replace("/", chr(92)), " ")


# din materialul probei de salarizare (statul de plata): nume de oameni inventati si o abreviere din lege, nu termeni
DIN_MATERIAL = {"CASS", "Katalin", "Kovacs"}


def _plase(text):
    gasite = [f"{nume}: {m.group(0)!r}" for nume, t in PLASE.items() for m in t.finditer(text)]
    return gasite + [f"termen neexplicat: {x}" for x in termeni.neexplicate(text) if x not in DIN_MATERIAL]


def _umbla(site, de_la="/"):
    vazute, coada, pagini = set(), [de_la], {}
    while coada:
        cale = coada.pop(0)
        if cale in vazute:
            continue
        vazute.add(cale)
        cod, html = site.get(cale)
        assert cod == 200, cale
        pagini[cale] = html
        for href in LEGATURA.findall(html):
            u = urlparse(urljoin("http://x" + cale, href.replace("&amp;", "&")))
            # paginile candidatilor din „Exemple” au aceleasi sabloane, cu textul proiectelor reale (al candidatilor)
            if (u.netloc == "x" and not u.path.startswith(("/static/", "/exemple/c/"))
                    and not re.search(r"\.\w{2,5}$", u.path)):
                coada.append(u.path + (f"?{u.query}" if u.query else ""))
    return pagini


def test_lista_goala_fara_semne(site):
    for cale, html in _umbla(site).items():
        assert _plase(_text(html, site.proiect)) == [], cale


def test_toate_ecranele_unui_candidat_fara_semne(site, tmp_path):
    _candidat(site, "Ana", bife=TOATE)
    site.accepta_proba("ana")
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    _candidat(site, "Bogdan", bife=TOATE)
    site.post("/c/bogdan/decizia", {"decizia": "da"})
    site.post("/c/bogdan/proba/acord", {"raspuns": "nu", "data": "09.10.2026", "cum": "pe e-mail"})
    # un rand vechi din jurnal, de dinainte de „Termenii”: se citeste cu termenii recrutorului (B7)
    audit.scrie(site.de("ana"), "interviul", audit.PROGRAM,
                "a adus în ghidul de interviu scorul și nivelul fișei noi; ghidul de dinainte: ghid-vechi.md")
    pagini = _umbla(site)
    # la rapoarte duce un formular, nu o legatura: adresele lor, scrise aici
    for id_ in ("ana", "bogdan"):
        for fel in ("raport", "rezumat", "audit", "audit_scurt"):
            pagini[f"/c/{id_}/{fel}"] = site.get(f"/c/{id_}/{fel}")[1]
    pagini["lista"] = site.get("/rapoarte/document?toti=1&fel=lista")[1]
    assert {"/c/ana/proba", "/c/bogdan/rezultat", "/c/ana/audit", "/manual"} <= set(pagini)
    gasite = {cale: g for cale, html in pagini.items() if (g := _plase(_text(html, site.proiect)))}
    assert gasite == {}


def test_erorile_fara_semne(site):
    _candidat(site)
    site.post("/c/ana/decizia", {"decizia": "da"})
    erori = [site.post("/nou", {"nume": "Ion", "sursa": ""})[2],
             site.post("/nou", {"nume": "Ion", "sursa": "C:/nu-exista-deloc"})[2],
             site.post("/c/ana/proba/acord", {"raspuns": "da", "data": "31.02.2026", "cum": "pe e-mail"})[2],
             site.post("/c/ana/proba/acord", {"data": "21.10.2026", "cum": "pe e-mail"})[2],
             site.post("/c/ana/sterge", {"nume": "Altcineva"})[2]]
    for html in erori:
        assert "Nu s-a putut." in html
        assert _plase(_text(html, site.proiect).replace("C:/nu-exista-deloc", " ")) == []
