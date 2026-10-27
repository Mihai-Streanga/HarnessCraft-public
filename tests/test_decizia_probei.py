"""Decizia de proba, la sfarsitul interviului (punctul 18): recrutorul spune da / nu, cu motivul; la „da”, invitatia si
acordul candidatului; proba se deschide numai dupa acord. Un candidat cu proba inceputa inainte de regula nu se
blocheaza."""
import re
from pathlib import Path

from harnesscraft import audit, candidati, interviu, proba, termeni
from tests.test_interfata import site  # noqa: F401 (fixture)
from tests.test_interfata_proba import _erori, _incarca, _tabel


def _interviu(site, toate=False):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    bife = {f"S{i}.{j}": "da" for i in range(1, len(interviu.INTREBARI) + 1) for j in (1, 2, 3)} if toate else {"S1.1": "da"}
    site.post("/c/ana/interviu", bife, {"X-Autosalvare": "1"})


def _c(site):
    return candidati.citeste("ana", site.dosar)


def test_fara_decizie_proba_e_inchisa_si_trimite_la_sfarsitul_interviului(site, tmp_path):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    corp = site.post("/c/ana/decizia", {"decizia": "da"})[2]
    assert "Decizia de probă se ia după interviu" in corp and candidati.decizia_probei(_c(site)) is None
    corp = site.get("/c/ana/proba")[1]
    assert "Întâi decizia de probă" in corp and 'href="/c/ana/interviu#decizia"' in corp
    assert "Încarcă tabelul de răspuns" not in corp
    corp = _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))[1]
    assert "Întâi decizia de probă" in corp and not (site.de("ana") / "Raspuns.xlsx").exists()
    assert candidati.stari(_c(site))["proba"][0] == "blocat"


def test_interviul_e_gata_numai_cu_decizia_luata(site):
    _interviu(site, toate=True)
    assert candidati.stari(_c(site))["interviu"][0] == "în lucru"
    assert 'action="/c/ana/decizia"' in site.get("/c/ana/interviu")[1]
    site.post("/c/ana/decizia", {"decizia": "da"})
    assert candidati.stari(_c(site))["interviu"][0] == "gata"


def test_nu_cere_motivul_si_lasa_totalul_fara_proba_cu_motivul(site):
    _interviu(site)
    assert "Scrii motivul" in site.post("/c/ana/decizia", {"decizia": "nu"})[2]
    cod, unde, corp = site.post("/c/ana/decizia", {"decizia": "nu", "motivul": "  nu are   experiență de salarizare "})
    assert unde.endswith("/c/ana/rezultat")
    d = candidati.decizia_probei(_c(site))
    assert d["decizia"] == "nu" and d["motivul"] == "nu are experiență de salarizare"
    assert candidati.stari(_c(site))["proba"] == ("fără probă", "Fără probă: nu are experiență de salarizare")
    assert "Fără probă: nu are experiență de salarizare" in site.get("/c/ana/proba")[1]
    j = audit.citeste(site.de("ana"))[-1]
    assert (j["pas"], j["cine"], j["decizia"]) == ("interviul", "recrutorul", "nu") and "motiv" not in j["ce"]


def test_da_arata_invitatia_iar_proba_se_deschide_dupa_acord(site, tmp_path):
    _interviu(site)
    unde = site.post("/c/ana/decizia", {"decizia": "da"})[1]
    assert unde.endswith("/c/ana/proba")
    corp = site.get("/c/ana/proba")[1]
    pa = proba.pachet()
    assert "Invitația la probă" in corp and "Bună ziua, Ana," in corp and pa.durata in corp and pa.termen in corp
    assert proba.FIRMA_COMPLETEAZA in corp and "Încarcă tabelul de răspuns" not in corp
    assert candidati.stari(_c(site))["proba"][0] == "de făcut"
    assert "Scrii data" in site.post("/c/ana/proba/acord", {"raspuns": "da", "data": "ieri", "cum": "pe e-mail"})[2]
    assert "cum a răspuns" in site.post("/c/ana/proba/acord", {"raspuns": "da", "data": "2026-10-16", "cum": " "})[2]
    site.post("/c/ana/proba/acord", {"raspuns": "da", "data": "16.10.2026", "cum": "pe e-mail"})
    corp = site.get("/c/ana/proba")[1]
    assert "Încarcă tabelul de răspuns" in corp and "Candidatul a acceptat proba pe 16.10.2026 (pe e-mail)." in corp
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    assert (site.de("ana") / "Raspuns.xlsx").exists()
    j = [x for x in audit.citeste(site.de("ana")) if "acordul" in x]
    assert j[0]["ce"] == "a consemnat că candidatul a acceptat proba, pe 16.10.2026 (pe e-mail)"
    corp = site.get("/c/ana/audit")[1]
    assert "decizia de probă: merge la probă" in corp
    assert "răspunsul la invitația la probă: a acceptat, pe 16.10.2026 (pe e-mail), consemnat de recrutor" in corp
    # proba inceputa: decizia nu se mai intoarce in „nu”, nici refuzul nu se mai consemneaza
    assert "decizia nu se mai schimbă" in site.post("/c/ana/decizia", {"decizia": "nu", "motivul": "x"})[2]
    assert "refuzul nu se mai poate" in site.post("/c/ana/proba/acord", {"raspuns": "nu", "data": "2026-10-16",
                                                                           "cum": "telefon"})[2]


def test_refuzul_candidatului_inchide_proba_cu_motivul(site):
    _interviu(site)
    site.post("/c/ana/decizia", {"decizia": "da"})
    site.post("/c/ana/proba/acord", {"raspuns": "nu", "data": "16.10.2026", "cum": "la telefon"})
    assert candidati.fara_proba(_c(site)) == "Fără probă: candidatul a refuzat-o, pe 16.10.2026 (la telefon)."
    assert candidati.stari(_c(site))["proba"][0] == "fără probă"
    # decizia schimbata (din „da” in „nu” si inapoi) cere iar acordul
    site.post("/c/ana/decizia", {"decizia": "nu", "motivul": "a refuzat"})
    site.post("/c/ana/decizia", {"decizia": "da"})
    assert candidati.decizia_probei(_c(site))["acordul"] is None
    ce = [x["ce"] for x in audit.citeste(site.de("ana")) if "decizia" in x]
    assert ce[-1] == "a hotărât, după interviu: merge la probă, în locul deciziei de dinainte („fără probă”)"


def test_proba_inceputa_inainte_de_regula_nu_se_blocheaza(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    c = _c(site)
    text = candidati.foaie_probei(c)
    (c["dosar"] / "proba.md").write_text(proba.scrie(text, {"C1": "da"}), encoding="utf-8")
    assert candidati.proba_deschisa(_c(site)) == (True, "decizia de probă neconsemnată: proba e de dinainte de regulă")
    assert "Decizia de probă neconsemnată" in site.get("/c/ana/proba")[1]


def test_invitatia_e_textul_aprobat_de_autor():
    """Aprobat de autor pe 15 octombrie 2026: o schimbare cere iar aprobarea lui, apoi fisierul nou."""
    aprobat = (Path(__file__).parent / "date" / "invitatia-probei.md").read_text(encoding="utf-8")
    assert proba.invitatie("«numele»") + "\n" == aprobat


def test_invitatia_si_ecranele_fara_termeni_tehnici_neexplicati(site):
    _interviu(site)
    assert not termeni.neexplicate(proba.invitatie("Ana"))
    site.post("/c/ana/decizia", {"decizia": "da"})
    corp = site.get("/c/ana/proba")[1].split("<main", 1)[-1]
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", corp, flags=re.S))
    assert termeni.neexplicate(text.replace(site.proiect, "")) == []
