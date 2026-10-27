"""Reparatiile din a treia sesiune de decizii dupa auditul unic (rapoarte/decizii-audit-unic-88a6d30.md, B2–B25): textele
dintre ghilimele, puse intocmai (B1), refuzul spus o data, jurnalul cu termenii recrutorului, campul gresit cu cursorul,
exemplele care nu scot omul din ele, lista celor alesi, caile in forma din Explorer, ajutorul si la stergere. B2, B3, B10,
B17, B18, B21: in testele mai vechi, aduse la textul nou; B6: tests/test_aspect.py; B26: tests/test_plasa_ecrane.py.
Ce nu acopera: aspectul pe ecran (B11, B14, B19, B20, B25) se vede numai in browser; aici, markupul si stilul."""
from pathlib import Path

from harnesscraft import interfata
from tests.test_decizii_audit_unic import TOATE, _candidat, _vizibil
from tests.test_interfata import site  # noqa: F401 (fixture)
from tests.test_interfata_proba import _erori, _incarca, _tabel, _toate_bifele

BS = chr(92)


def test_eroarea_de_la_candidat_nou_spune_istoricul_proiectului(site):
    corp = site.post("/nou", {"nume": "Ana", "sursa": ""})[2]
    assert "un link spre istoricul proiectului (git)" in corp  # B4


def test_jurnalul_spune_punctajul_si_treapta():
    sursa = Path("harnesscraft/candidati.py").read_text(encoding="utf-8")
    assert "punctajul și treapta fișei noi" in sursa and "scorul și nivelul" not in sursa  # B7, randul nou
    assert "punctajul și treapta" in interfata._ce_jurnal("a adus în ghidul de interviu scorul și nivelul fișei noi")


def test_campul_gresit_primeste_cursorul(site):
    _candidat(site)
    site.post("/c/ana/decizia", {"decizia": "da"})
    corp = site.post("/c/ana/proba/acord", {"raspuns": "da", "data": "31.02.2026", "cum": "pe e-mail"})[2]
    assert 'class="camp-gresit" aria-invalid="true" autofocus' in corp and corp.count(" autofocus") == 1  # B8
    corp = site.post("/c/ana/proba/acord", {"data": "21.10.2026", "cum": "pe e-mail"})[2]
    assert 'name="raspuns" value="da" autofocus' in corp and corp.count(" autofocus") == 1  # fara alegere: prima


def test_decizia_refuzata_revine_si_spune_eroarea():
    js = Path("harnesscraft/static/app.js").read_text(encoding="utf-8")
    assert '"Nu s-a salvat. "' in js and "Nu s-a salvat: " not in js  # B9: un punct, litera mare
    assert "if (decizie) inapoi();" in js and 'stare.classList.add("eroare")' in js
    assert ".stare-salvare.eroare" in Path("harnesscraft/static/stil.css").read_text(encoding="utf-8")


def test_lista_celor_alesi(site):
    site.post("/nou", {"nume": "Bogdan", "fara_cod": "1", "motiv_fara_cod": "lucrează numai în chat"})
    lista = site.get("/rapoarte/document?toti=1&fel=lista")[1]
    assert "fără&nbsp;fișă" in lista  # B11: ca pe „Rapoarte”, nu „—”
    assert '<colgroup><col><col class="c-stare"><col class="c-treapta">' in lista
    unelte = lista.split('<div class="r-unelte">', 1)[1].split("</div>", 1)[0]
    assert 'class="motiv' not in unelte and 'popovertarget="ajutor-raport"' in unelte  # B14
    assert '<p class="motiv r-ales">Lista celor aleși: 1 candidat.</p>' in lista


def test_auditul_spune_media_si_proba_ca_pe_rezultat(site, tmp_path):
    _candidat(site, bife=TOATE)
    site.accepta_proba("ana")
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    _toate_bifele(site, "ana")
    text = _vizibil(site.get("/c/ana/audit")[1])
    assert "Media celor 7 întrebări: " in text and "întrebări puse din" not in text  # B12
    assert ", adică " in text and " din 33,3" in text and "→ × 33,3" not in text


def test_caile_in_forma_din_explorer(site):
    assert interfata.cale("C:/a/b") == f"C:{BS}a{BS}b"  # B13
    assert interfata.cale("https://github.com/x/y.git") == "https://github.com/x/y.git"
    _candidat(site, bife=TOATE)
    win = site.proiect.replace("/", BS)
    assert win in site.get("/c/ana/audit")[1] and win in site.get("/c/ana/raport")[1]


def test_stergerea_are_ajutorul_ei(site):
    _candidat(site)
    corp = site.get("/c/ana/sterge")[1]
    assert 'popovertarget="ajutor-sterge"' in corp and 'href="/manual#stergerea"' in corp  # B15
    assert '<h3 id="stergerea">' in site.get("/manual")[1]


def test_textele_mici(site):
    _candidat(site, bife=TOATE)
    assert "nu mai sunt de folos" in site.get("/c/ana/rezultat")[1]  # B16
    manual = site.get("/manual")[1]
    assert "verificată de teste automate" in manual and "190" not in manual  # B22
    assert "lipsește programul care citește istoricul proiectelor (git)" in manual  # B23
    assert "propuse și în analiză</span></h2>" in site.get("/")[1]  # B24


def test_stilul_filtrelor_casutelor_si_cardurilor():
    stil = Path("harnesscraft/static/stil.css").read_text(encoding="utf-8")
    assert ".filtre input, .filtre select { height: 2.4rem;" in stil  # B19
    assert "input[type=checkbox] { width: 1.1rem; height: 1.1rem;" in stil  # B20
    sursa = Path("harnesscraft/interfata.py").read_text(encoding="utf-8")
    assert '<div class="card"><h3>' not in sursa  # B25: cardul exemplelor, ca pe „Acasă”
