"""Setul de date al exemplelor: proiectele inventate ies pe treapta tipului lor si
sunt aceleasi la fiecare rulare, deci cifrele capitolului se pot reface oriunde. Cifrele capitolului din manual vin
din exemple-candidati/rezultate.json; testele cad cand setul refacut nu mai da fisierul, sau cand capitolul are o
cifra care nu e acolo. Cazul autorului se verifica numai pe masina lui."""
import json
import re

import pytest

from harnesscraft import candidati, interfata, set_exemple

# commitul ultim al fiecarui proiect inventat: se schimba numai cand se schimba ISTORII, si atunci cu intentie
COMMITURI = {"Andrei Costache": "5fef1e8", "Ioana Vlădescu": "4403e70", "Victor Matei": "37052d9",
             "Cristina Pavel": "498f222"}
AUTORUL_AICI = set_exemple.autorul_aici()


def _din_fisier():
    return json.loads(set_exemple.REZULTATE.read_text(encoding="utf-8"))


def _cifre(x):
    """Toate numerele din rezultate.json, scrise ca in capitol (virgula zecimala)."""
    if isinstance(x, dict):
        return set().union(*map(_cifre, x.values())) if x else set()
    if isinstance(x, list):
        return set().union(*map(_cifre, x)) if x else set()
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return {interfata._nr(x)}
    return set()


def test_setul_iese_pe_treptele_tipurilor_cu_aceleasi_commituri(tmp_path):
    rez = {r["nume"]: r for r in set_exemple.construieste(tmp_path / "set", cu_autorul=False)}
    assert rez["Mihai Streanga"]["sarit"] == "cerut"
    assert {n: r["commit"][:7] for n, r in rez.items() if "commit" in r} == COMMITURI
    assert {n: (r["treapta"], r["total"]) for n, r in rez.items() if "treapta" in r} == {
        "Andrei Costache": (1, 8.0), "Ioana Vlădescu": (0, 3.0), "Victor Matei": (3, 16.0), "Cristina Pavel": (2, 10.0)}
    dosar = tmp_path / "set" / "candidaturi"
    elena = candidati.citeste(rez["Elena Dobrescu"]["id"], dosar)
    assert candidati.fara_cod(elena) and candidati.ghid(elena)
    for n in COMMITURI:  # pasul 1 facut prin functia butonului: ghidul de interviu e scris, candidatul e in analiza
        c = candidati.citeste(rez[n]["id"], dosar)
        assert candidati.ghid(c) and c["dosar"].parent.name == "in-analiza"
    # pasii 2-4, din exemple-candidati/: exact cifrele pe care le citeaza capitolul din manual
    rez = set_exemple.completeaza(list(rez.values()), tmp_path / "set")
    refacute = set_exemple.rezultate(rez)
    fisier = _din_fisier()
    assert {k: v for k, v in refacute.items() if k != "candidati"} == {k: v for k, v in fisier.items() if k != "candidati"}
    assert refacute["candidati"] == [c for c in fisier["candidati"] if c["tip"] != 1]
    rez = {r["nume"]: r for r in rez}
    assert not rez["Andrei Costache"]["fisa_probei"]  # tipul 3: numai conversatii, fara program
    assert rez["Cristina Pavel"]["fara_proba"].startswith("Fără probă: candidatul a refuzat-o")


@pytest.mark.skipif(not AUTORUL_AICI, reason="cazul autorului: fără proiectul sau fără dosarul lui, nu se reface")
def test_cazul_autorului_da_cifrele_din_fisier(tmp_path):
    rez = set_exemple.completeaza(set_exemple.construieste(tmp_path / "set"), tmp_path / "set")
    autorul = [c for c in set_exemple.rezultate(rez)["candidati"] if c["tip"] == 1]
    assert autorul == [c for c in _din_fisier()["candidati"] if c["tip"] == 1]


def test_capitolul_are_numai_cifrele_calculate_si_cei_sase():
    fisier = _din_fisier()
    assert [c["tip"] for c in fisier["candidati"]] == [1, 2, 3, 4, 5, 6]
    capitol = interfata.capitol_exemple()
    assert capitol in interfata.MANUAL
    text = re.sub(r"<[^>]+>", " ", capitol)
    straine = set(re.findall(r"\d+(?:,\d+)?", text)) - _cifre(fisier)
    assert not straine, f"cifre din capitol care nu vin din rezultate.json: {sorted(straine)}"
    assert "inventate" in text and "orice potrivire cu o persoană reală e întâmplătoare" in text
    assert "Bifele la interviu și la probă le-a dat tot asistentul, la cererea autorului" in text


def test_textul_spune_ce_arata_cifrele():
    """Constatarea din capitol: Victor (tipul 5) iese peste Ioana (tipul 4); Cristina e incompleta; Elena, sub plafon."""
    d = {c["tip"]: c for c in _din_fisier()["candidati"]}
    assert d[5]["total"] > d[4]["total"]
    assert not d[6]["complet"] and all(d[t]["complet"] for t in (1, 2, 3, 4, 5))
    assert d[2]["treapta"] is None and d[2]["total"] <= _din_fisier()["plafon_fara_cod"]


def test_exemplele_spun_ce_lipseste_autorului(tmp_path, monkeypatch):
    """Intr-o clona noua, cu proiectul autorului pe calculator, lipseste numai dosarul lui (`candidaturi/` nu vine cu
    git): ecranul nu da vina pe proiect (instalarea urmata, 21 octombrie)."""
    proiect, dosar = tmp_path / "Metoda", tmp_path / "mihai-streanga"
    (proiect / ".git").mkdir(parents=True)
    monkeypatch.setattr(set_exemple, "PROIECT_AUTOR", proiect)
    monkeypatch.setattr(set_exemple, "AUTORUL", dosar)
    motiv = set_exemple.ce_lipseste_autorului()
    assert "dosarul lui nu e printre candidați" in motiv and "proiectul" not in motiv
    assert not set_exemple.autorul_aici()
    assert "copia de siguranță a candidaturilor" in interfata.exemple_lista(tmp_path)
    dosar.mkdir()
    (dosar / "fisa.json").write_text("{}", encoding="utf-8")
    assert set_exemple.ce_lipseste_autorului() == "" and set_exemple.autorul_aici()
    (proiect / ".git").rmdir()
    assert set_exemple.ce_lipseste_autorului() == "proiectul lui nu e pe acest calculator"
