"""Jurnalul si raportul de audit (decizia autorului, 15 octombrie: scris de program pe loc, nu la sfarsit), si sectiunea
„Rapoarte”: intai pe cine, apoi ce, un singur document."""
import json
import re
from urllib.parse import quote

import pytest

from harnesscraft import audit, termeni
from tests.test_interfata import site  # noqa: F401 (fixture)
from tests.test_interfata_proba import _erori, _incarca, _tabel, _toate_bifele


def _jurnal(site, id_):
    return audit.citeste(site.de(id_))


def _text(corp):
    corp = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", corp, flags=re.S)
    corp = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", corp))
    return " ".join(w for w in corp.split() if "/" not in w and ":" + chr(92) not in w)  # caile proiectului de test


def test_jurnalul_tine_fiecare_pas_cu_cine_l_a_facut(site, tmp_path):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    site.post("/c/ana/fisa")
    site.post("/c/ana/interviu", {"S1.1": "da", "nota-S1": "un scop clar"}, {"X-Autosalvare": "1"})
    site.post("/c/ana/interviu", {"S1.1": "da"}, {"X-Autosalvare": "1"})  # fara schimbare: nimic in jurnal
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    _toate_bifele(site, "ana", conv=("da", "nu", "nu", "nu"), disc=("",) * 3)
    site.post("/c/ana/finalizeaza")
    j = _jurnal(site, "ana")
    assert [(x["pas"], x["cine"]) for x in j] == [
        ("candidatul", "recrutorul"), ("portofoliul", "programul"), ("interviul", "programul"),
        ("interviul", "recrutorul"), ("proba", "recrutorul"), ("proba", "programul"), ("proba", "recrutorul"),
        ("candidatura", "recrutorul")]
    assert j[1]["commit"] and j[1]["ce"].startswith("a analizat proiectul de portofoliu la versiunea din istoric (cod ")
    assert j[3]["ce"] == "întrebarea 1, rândul 1: nepusă → da; notițele la întrebarea 1: text schimbat"
    assert j[3]["bife"]["S1.1"] == "da" and "un scop clar" not in json.dumps(j, ensure_ascii=False)
    assert "1 din 5 greșeli găsite, 0 semnalări greșite" in j[5]["ce"] and j[5]["gasite"] == ["E1"]
    assert j[4]["tabel"] == audit.amprenta(site.de("ana") / "Raspuns.xlsx")
    assert all(x["versiune"] == audit.VERSIUNE and x["ora"] for x in j)


def test_auditul_spune_cum_s_a_ajuns_si_reface_fisa(site, tmp_path):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    site.post("/c/ana/interviu", {f"S{i}.{r}": "da" for i in range(1, 8) for r in (1, 2, 3)}, {"X-Autosalvare": "1"})
    corp = site.get("/c/ana/audit")[1]
    for parte in ("Raport de audit", "Cum s-a ajuns la rezultat", "Cine a hotărât ce", "Intrările", "Refacerea",
                  "<h2>Jurnalul</h2>", "Ce nu acoperă"):
        assert parte in corp, parte
    assert "aceeași treaptă și același punctaj" in corp and "(4 − 1) / 3 × 33,3" in corp
    assert "Bifele interviului de acum sunt cele din ultima intrare a jurnalului." in corp
    assert "Cheia probei are amprenta păstrată la verificarea ei" in corp
    assert termeni.neexplicate(_text(corp.split("</aside>", 1)[1])) == []
    # o bifa schimbata direct in fisier, in afara aplicatiei: refacerea o arata
    g = site.de("ana") / "ghid.md"
    g.write_text(g.read_text(encoding="utf-8").replace("- S1.1 [da]", "- S1.1 [nu]", 1), encoding="utf-8")
    assert "Bifele interviului diferă de ultima intrare a jurnalului</b> (S1.1)" in site.get("/c/ana/audit")[1]
    scurt = site.get("/c/ana/audit_scurt")[1]
    assert "Raport de audit, pe scurt" in scurt and "<h2>Jurnalul, pe scurt</h2>" in scurt and "r-jurnal" not in scurt


def test_un_candidat_de_dinainte_de_jurnal_isi_arata_urmele_din_fisiere(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    (site.de("ana") / "jurnal.jsonl").unlink()
    corp = site.get("/c/ana/audit")[1]
    assert "Jurnalul e gol." in corp and "Dinainte de jurnal" in corp and "candidatul adăugat (candidat.json)" in corp
    assert "nescris: fișa e de dinainte de jurnal" in corp


def test_rapoartele_se_scot_pentru_cine_alegi(site):
    for nume in ("Ana", "Bogdan", "Cora"):
        site.post("/nou", {"nume": nume, "sursa": site.proiect})
    site.post("/c/ana/fisa")
    site.post("/c/bogdan/fisa")
    assert 'href="/rapoarte">Rapoarte</a>' in site.get("/")[1]
    rez = site.get("/c/ana/rezultat")[1]  # raportul lui, direct; „Rapoarte”, in plus (decizia autorului, 19 octombrie)
    assert 'href="/c/ana/raport">Raportul pentru dosar</a>' in rez and 'href="/rapoarte?id=ana">Alte rapoarte</a>' in rez
    corp = site.get("/rapoarte?id=ana")[1]
    assert 'value="ana" checked' in corp and 'value="bogdan">' in corp and "Toți cei găsiți (3)" in corp
    assert 'name="fel" value="audit"' in corp and "Scoate raportul" in corp
    corp = site.get("/rapoarte?treapta=" + quote("fără"))[1]
    assert 'value="cora"' in corp and 'value="ana"' not in corp
    doc = site.get("/rapoarte/document?fel=scurt&id=ana&id=bogdan")[1]
    assert doc.count('<section class="r-candidat">') == 2 and "Raport de evaluare, pe scurt" in doc
    doc = site.get("/rapoarte/document?fel=audit-scurt&toti=1&q=bog")[1]
    assert doc.count('<section class="r-candidat">') == 1 and "Bogdan" in doc and "Raport de audit, pe scurt" in doc
    doc = site.get("/rapoarte/document?fel=lista&toti=1")[1]
    assert "Lista candidaților aleși" in doc and doc.count("<tr><td><b>") == 3 and "Fără probă</h2>" in doc
    assert "Alegi cel puțin un candidat" in site.get("/rapoarte/document?fel=dosar")[1]
    assert "Felul raportului nu e unul din listă" in site.get("/rapoarte/document?fel=altceva&id=ana")[1]
    for corp in (site.get("/rapoarte")[1], doc):
        assert termeni.neexplicate(_text(corp.split("</aside>", 1)[1])) == []
