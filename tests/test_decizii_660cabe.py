"""Reparatiile din a doua sesiune de decizii dupa auditul unic (rapoarte/decizii-audit-unic-660cabe.md, B5–B36): textele
pentru recrutor, formularul probei dupa o eroare, proba inchisa care nu scrie nimic, refuzul spus ca refuz, aspectul."""
import re

import pytest

from harnesscraft import candidati, fisa, interfata, termeni
from tests.test_decizii_audit_unic import AUTO, TOATE, _candidat, _vizibil
from tests.test_interfata import site  # noqa: F401 (fixture)
from tests.test_interfata_proba import _erori, _incarca, _tabel


def _refuzata(site, nume="Ana"):
    id_ = _candidat(site, nume, bife=TOATE)
    site.post(f"/c/{id_}/decizia", {"decizia": "da"})
    site.post(f"/c/{id_}/proba/acord", {"raspuns": "nu", "data": "09.10.2026", "cum": "pe e-mail"})
    return id_


def test_nota_fisei_pentru_recrutor_spune_treapta(site):
    assert "treaptă provizorie" in fisa.NOTA_RECRUTOR and "nivel" not in fisa.NOTA_RECRUTOR  # B5
    _candidat(site)
    assert "nivel provizoriu" not in site.get("/c/ana/fisa")[1]


def test_git_in_paranteza_pe_acasa_lista_goala_si_eroare(site):
    for cale in ("/", "/candidati"):  # B6: „Acasă” si lista goala, primul ecran al unei instalari noi
        text = _vizibil(site.get(cale)[1].split("</aside>", 1)[1])
        assert termeni.neexplicate(text) == [], (cale, termeni.neexplicate(text))
    corp = site.post("/nou", {"nume": "Ana", "sursa": ""})[2]
    assert termeni.neexplicate(_vizibil(corp.split("</aside>", 1)[1])) == []


def test_codurile_auditului_stau_in_paranteza(site, tmp_path):
    _candidat(site, bife=TOATE)
    site.accepta_proba("ana")
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    for cale in ("/c/ana/audit", "/c/ana/audit_scurt"):  # B7: un cod hexazecimal numai dupa „(cod ”
        text = _vizibil(site.get(cale)[1])
        afara = [text[max(0, m.start() - 60):m.end()] for m in re.finditer(r"\b[0-9a-f]{7,64}\b", text)
                 if not re.search(r"\([^()]*cod\s*$", text[max(0, m.start() - 80):m.start()])]
        assert afara == [], (cale, afara)


def test_formularul_probei_pastreaza_ce_s_a_scris_dupa_o_eroare(site):
    _candidat(site)
    site.post("/c/ana/decizia", {"decizia": "da"})
    corp = site.post("/c/ana/proba/acord", {"raspuns": "da", "data": "31.02.2026", "cum": "la telefon"})[2]
    assert 'value="da" checked' in corp and 'value="la telefon"' in corp  # B11
    assert re.search(r'name="data" value="31\.02\.2026"[^>]*class="camp-gresit"', corp)


def test_o_privire_pe_proba_inchisa_nu_scrie_nimic(site):
    _refuzata(site)
    assert site.get("/c/ana/proba")[0] == 200
    assert not (site.de("ana") / "proba.md").exists()  # B12
    assert "a refuzat proba" in site.get("/rapoarte")[1]  # B13
    lista = site.get("/rapoarte/document?toti=1&fel=lista")[1].replace("&nbsp;", " ")
    assert "Fără probă</h2>" in lista and "a refuzat proba" in lista and "fără probă încă" not in lista


def test_proba_refuzata_are_pasul_urmator_si_refuzul_spus_o_data(site):
    _refuzata(site)
    assert 'href="/c/ana/rezultat">4. Rezultatul →</a>' in site.get("/c/ana/proba")[1]  # B20
    corp = _vizibil(site.get("/c/ana/rezultat")[1])
    assert corp.count("a refuzat") == 1 and "Candidatul a refuzat proba pe" in corp  # B25, B18
    assert "Totalul e incomplet: fără probă." in corp  # B2: textul dintre ghilimele, întocmai (B1)


def test_mesajele_de_eroare_incep_cu_litera_mare(site):
    _candidat(site)
    site.post("/c/ana/decizia", {"decizia": "da"})
    corp = site.post("/c/ana/proba/acord", {"data": "21.10.2026", "cum": "pe e-mail"})[2]
    assert "<strong>Nu s-a putut.</strong> Alegi ce a răspuns" in corp  # B15


def test_lista_celor_alesi_si_cifrele_probei(site, tmp_path):
    _candidat(site, bife=TOATE)
    assert ".;" not in site.get("/rapoarte/document?toti=1&fel=lista")[1]  # B16
    site.accepta_proba("ana")
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    assert not re.search(r"\b\d{4,} lei", site.get("/c/ana/proba")[1])  # B17: 4.847, nu 4847


def test_candidat_nou_pe_randul_actiunii_si_pasul_urmator_ca_buton(site):
    _candidat(site)
    for cale in ("/", "/candidati"):  # B18
        corp = site.get(cale)[1]
        titlu = re.search(r'<div class="rand-titlu">.*?</div>', corp, re.S).group(0)
        assert "Candidat nou" not in titlu and '<div class="actiune"><a class="buton" href="/nou">Candidat nou' in corp
    assert '<div class="urmator">Pasul următor: <a class="buton"' in site.get("/c/ana/fisa")[1]  # B28


def test_interviul_fara_nume_in_titlu_si_fara_a_doua_cale(site):
    _candidat(site)
    corp = site.get("/c/ana/interviu")[1]
    assert "Interviul cu Ana" not in corp and "Salvează decizia și mergi mai departe" not in corp  # B24
    assert "<noscript><button" in corp


def test_media_interviului_si_datele_scurte(site):
    _candidat(site, bife=TOATE)
    corp = site.get("/c/ana/rezultat")[1]
    assert "puse, din" not in corp and "media celor 7 întrebări</i>" in corp  # B26
    assert interfata.nerupt("constructor de sistem") == "constructor&nbsp;de&nbsp;sistem"  # B22


def test_alegerea_programului_probei_si_copierea_invitatiei(site):
    _candidat(site)
    site.post("/c/ana/decizia", {"decizia": "da"})
    assert 'data-copiaza="#invitatia"' in site.get("/c/ana/proba")[1]  # B36
    site.accepta_proba("ana")
    corp = site.get("/c/ana/proba")[1]
    assert re.search(r'name="cod".*?data-alege="dosar"', corp, re.S)  # B19


def test_manualul_un_singur_nume_pentru_istoric_si_dosarele_in_paranteza(site):
    corp = site.get("/manual")[1]
    assert "istoricul schimbărilor" not in corp  # B27
    assert "în analiză (<code>in-analiza</code>)" in corp  # B32
    assert "(<code>propuse</code>)" not in corp and "(<code>finalizate</code>)" not in corp  # B21


def test_exemplele_numai_de_citit_peste_tot():
    pagina = ('<a class="nav" href="/exemple">Exemple</a><main><a class="buton secundar lat" href="/c/ana/sterge">'
              'Șterge candidatul</a><h2>Concluzia ta</h2><p><i>Încă nescrisă: o scrii la sfârșitul interviului.</i></p>'
              '<div class="urmator">Ultimul pas. <a class="buton" href="/">Înapoi acasă</a></div>'
              '<a class="buton secundar" href="/rapoarte?id=ana">Alte rapoarte</a></main>')
    html = interfata.doar_de_citit(pagina)
    assert '<a class="nav" href="/exemple">' in html  # B30: selectia, numai pe pas
    assert '<button class="buton secundar lat" disabled>Șterge candidatul</button>' in html  # B21
    assert "<h2>Concluzia: nescrisă în acest exemplu</h2>" in html and "Concluzia ta" not in html  # B31, B3
    assert '<a class="buton" href="/exemple">Înapoi la exemple</a>' in html  # B10
    assert '<button class="buton secundar" disabled>Alte rapoarte</button>' in html  # B10


def test_cheia_schimbata_nu_spune_comisa(tmp_path):
    (tmp_path / "cheia.json").write_text("{}", encoding="utf-8")
    (tmp_path / "cheia.sha256").write_text("0" * 64, encoding="utf-8")
    from harnesscraft import proba
    try:
        proba.cheia(tmp_path)
    except ValueError as ex:
        assert "comis" not in str(ex)  # B35
    else:
        raise AssertionError("cheia schimbată trebuia refuzată")


@pytest.mark.privat
def test_contract_module_spus_in_principii():
    from pathlib import Path
    text = Path("principii/Principii.md").read_text(encoding="utf-8")
    assert "`candidati` (dosarele candidaților) îl importă numai `interfata`, `set_exemple` și `capturi`" in text  # B1
    assert candidati  # importul, pentru linter
    assert AUTO
