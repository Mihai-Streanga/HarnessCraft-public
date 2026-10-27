import hashlib
import json

from harnesscraft import proba_stat as p
from harnesscraft import xlsx


def test_deducerea_urmeaza_tabelul_din_art_77():
    # fara persoane in intretinere: 20% la minim, 19,5% pana la minim + 50, 16% la minim + 351..400, 0 peste minim + 2.000
    assert p.deducere(p.SALARIU_MINIM) == 865
    assert p.deducere(p.SALARIU_MINIM - 500) == 865
    assert p.deducere(p.SALARIU_MINIM + 1) == p._r(19.5 * 4325 / 100)
    assert p.deducere(p.SALARIU_MINIM + 50) == p._r(19.5 * 4325 / 100)
    assert p.deducere(p.SALARIU_MINIM + 51) == p._r(19 * 4325 / 100)
    assert p.deducere(p.SALARIU_MINIM + 387) == 692
    assert p.deducere(p.SALARIU_MINIM + 1951) == 0
    assert p.deducere(p.SALARIU_MINIM + 2000) == 0
    assert p.deducere(p.SALARIU_MINIM + 2001) == 0


def test_randul_de_control_da_netul_oficial_la_salariul_minim():
    # Ministerul Muncii, despre HG 146/2026: la 4.325 lei brut, cu 200 lei netaxabili, netul e 2.699 lei
    r = next(r for r in p.stat(False) if r["Marca"] == 1001)
    assert (r["Venit brut realizat"], r["Suma 300 lei netaxabila"], r["Salariu net"]) == (4325, 200, 2699)


def test_fiecare_greseala_e_pe_alt_angajat_si_numai_pe_randul_ei():
    marci = [m for m, _, _ in p.GRESELI.values()]
    assert len(set(marci)) == len(marci) == 5
    assert p.PLANTATA_CORECTA[0] not in marci
    gresit, corect = p.stat(True), p.stat(False)
    diferite = {g["Marca"] for g, c in zip(gresit, corect) if g != c}
    assert diferite == set(marci)


def test_cheia_are_valoarea_gresita_si_pe_cea_corecta():
    k = {e["cod"]: e for e in p.cheia()["erori"]}
    assert (k["E5"]["valoare_in_stat"], k["E5"]["valoare_corecta"]) == (300, 200)
    assert (k["E4"]["valoare_in_stat"], k["E4"]["valoare_corecta"]) == (200, 0)
    assert k["E3"]["coloane_afectate"] == ["Rest plata"]
    assert all(e["valoare_in_stat"] != e["valoare_corecta"] for e in k.values())
    c = p.cheia()["plantata_corecta"]
    assert c["valoare_in_stat"] == p.NETAXABIL


def test_statul_ocoleste_regulile_necitite():
    # suma netaxabila numai la venit brut egal cu minimul; tichete numai peste minim + 2.000 (fara deducere)
    for r in p.stat(False):
        if r["Suma 300 lei netaxabila"]:
            assert r["Venit brut realizat"] == p.SALARIU_MINIM
        if r["Tichete de masa"]:
            assert r["Venit brut realizat"] > p.SALARIU_MINIM + 2000
        if r["Deducere personala"]:
            assert r["Deducere personala"] * 100 % p.SALARIU_MINIM == 0  # 20 / 16 / 12 / 8 / 4%, fara rotunjire


def test_statul_corect_respecta_regulile():
    for r in p.stat(False):
        assert r["CAS Angajat"] == p._r(r["Baza CAS Angajat"] * p.COTA_CAS)
        assert r["Baza CASS Angajat"] == r["Venit brut realizat"] + r["Tichete de masa"] - r["Suma 300 lei netaxabila"]
        assert r["Rest plata"] == r["Salariu net"] - r["Avans chenzinal suma"]
        if r["Venit brut realizat"] > p.PLAFON_NETAXABIL:
            assert r["Suma 300 lei netaxabila"] == 0


def test_xlsx_se_citeste_inapoi_la_fel(tmp_path):
    randuri = [["Marca", "Nume", "Suma"], [1001, "Adamescu", 4325], [1002, "Bărbulescu & fiii", 12.5]]
    assert xlsx.citeste(xlsx.scrie(tmp_path / "t.xlsx", randuri)) == randuri


def test_scrie_da_aceeasi_amprenta_de_fiecare_data(tmp_path):
    a = p.scrie(tmp_path / "a")
    b = p.scrie(tmp_path / "b")
    assert a == b
    text = (tmp_path / "a" / "cheia.json").read_bytes()
    assert hashlib.sha256(text).hexdigest() == a
    assert json.loads(text)["erori_de_gasit"] == 5
    stat = xlsx.citeste(next((tmp_path / "a").glob("Stat_*.xlsx")))
    assert stat[0] == p.COLOANE and len(stat) == 1 + len(p.ANGAJATI) + 1
    assert (tmp_path / "a" / next((tmp_path / "a").glob("Stat_*.xlsx")).name).read_bytes() == \
        (tmp_path / "b" / next((tmp_path / "b").glob("Stat_*.xlsx")).name).read_bytes()
