"""Nota probei: textele bifelor aprobate de autor, potrivirea cu cheia pe angajat, cele trei parti, totalul."""
from pathlib import Path

import pytest

from harnesscraft import proba, proba_stat, termeni, total, xlsx

TEXTE = Path(__file__).parent / "date" / "bifele-probei.md"
DOSAR = Path(__file__).parent.parent / "proba" / "septembrie-2026"
PA = proba.pachet()
CH = PA.cheia()


def _randare():
    r = ["Conversațiile"] + [f"{n}. {b}" for n, b in enumerate(PA.conversatii, 1)] + ["", "Discuția"]
    for n, (intrebare, bifa) in enumerate(PA.discutie, 1):
        r += [f"{n}. {intrebare}", f"Da, dacă: {bifa}"]
    return "\n".join(r) + "\n"


def _erori(*coduri):
    return [(e["marca"], e["coloana"]) for e in CH["erori"] if e["cod"] in coduri]


def _predat(tmp_path, randuri):
    cale = tmp_path / "Raspuns.xlsx"
    xlsx.scrie(cale, [PA.raspuns_cap] + randuri)
    return cale


def test_textele_bifelor_sunt_cele_aprobate_de_autor_la_caracter():
    # o schimbare aici cere iar acordul autorului (rapoarte/plan-proba.md, sectiunea 2)
    assert _randare() == TEXTE.read_text(encoding="utf-8")


def test_textele_bifelor_n_au_termeni_tehnici_neexplicati():
    text = " ".join(PA.conversatii + [x for q in PA.discutie for x in q])
    assert termeni.neexplicate(text) == []


def test_cheia_din_dosar_e_cea_construita_si_amprenta_o_apara(tmp_path):
    assert proba.cheia(DOSAR) == proba_stat.cheia()
    (tmp_path / "cheia.json").write_bytes((DOSAR / "cheia.json").read_bytes().replace(b"816", b"817"))
    (tmp_path / "cheia.sha256").write_bytes((DOSAR / "cheia.sha256").read_bytes())
    with pytest.raises(ValueError, match="amprenta"):
        proba.cheia(tmp_path)


def test_toate_cele_cinci_gasite_si_nimic_gresit_da_nota_intreaga():
    n = proba.nota_cheie(_erori("E1", "E2", "E3", "E4", "E5"), CH)
    assert (n["gasite"], n["ratate"], n["gresite"], n["fractie"]) == (["E1", "E2", "E3", "E4", "E5"], [], [], 1)


def test_o_eroare_se_gaseste_pe_orice_coloana_in_care_se_vede_si_se_numara_o_data():
    # E1 (CASS fara tichete) se vede si in restul de plata; trei randuri pe acelasi om = o eroare gasita
    m = next(e["marca"] for e in CH["erori"] if e["cod"] == "E1")
    n = proba.nota_cheie([(m, "Rest plata"), (m, "CASS Angajat"), (m, "Impozit")], CH)
    assert (n["gasite"], n["gresite"], n["fractie"]) == (["E1"], [], 1 / 5)


def test_cazul_corect_semnalat_pe_patru_coloane_e_o_singura_semnalare_gresita():
    m = CH["plantata_corecta"]["marca"]
    semnalate = _erori("E1", "E2", "E3") + [(m, c) for c in ("Suma 300 lei netaxabila", "Baza CAS Angajat",
                                                              "CAS Angajat", "Rest plata")]
    n = proba.nota_cheie(semnalate, CH)
    assert (n["gresite"], n["fractie"]) == ([m], (3 - 1) / 5)


def test_cine_lucreaza_cu_forma_veche_semnaleaza_cazul_corect_si_rateaza_capcana():
    m = CH["plantata_corecta"]["marca"]
    n = proba.nota_cheie(_erori("E1", "E2", "E3", "E4") + [(m, "Suma 300 lei netaxabila")], CH)
    assert (n["ratate"], n["gresite"], n["fractie"]) == (["E5"], [m], 3 / 5)


def test_un_om_cu_eroare_semnalat_numai_pe_coloane_corecte_e_ratat_si_gresit():
    # E3 (avansul nescazut) se vede numai in restul de plata; CAS-ul aceluiasi om e corect
    m = next(e["marca"] for e in CH["erori"] if e["cod"] == "E3")
    n = proba.nota_cheie([(m, "CAS Angajat")], CH)
    assert (n["gasite"], n["ratate"].count("E3"), n["gresite"], n["fractie"]) == ([], 1, [m], 0)


def test_nota_din_cheie_nu_scade_sub_zero():
    corecti = sorted({a[0] for a in proba_stat.ANGAJATI} - {e["marca"] for e in CH["erori"]})
    n = proba.nota_cheie(_erori("E1") + [(m, "Impozit") for m in corecti[:4]], CH)
    assert (len(n["gresite"]), n["fractie"]) == (4, 0)


def test_tabelul_predat_se_citeste_fara_diacritice_litere_mari_si_randuri_goale(tmp_path):
    cale = _predat(tmp_path, [[1014, "  rest   PLATĂ ", 5000, 4800, "avansul"], [None, None, None, None, None],
                              ["1011", "CASS angajat", 750, 816, None]])
    assert PA.raspuns(cale) == [(1014, "Rest plata", 4800, "avansul"), (1011, "CASS Angajat", 816, "")]


def test_marca_sau_coloana_necunoscuta_opreste_citirea_cu_randul_ei(tmp_path):
    cale = _predat(tmp_path, [["Ionescu", "Impozit"], [9999, "Impozit"], [1001, "Salariul de bază"]])
    with pytest.raises(ValueError) as e:
        PA.raspuns(cale)
    assert str(e.value) == ("rândul 2: marca „Ionescu” nu e în stat; rândul 3: marca „9999” nu e în stat; "
                            "rândul 4: coloana „Salariul de bază” nu e în stat")


def test_alt_tabel_decat_cel_de_raspuns_e_refuzat(tmp_path):
    cale = tmp_path / "x.xlsx"
    xlsx.scrie(cale, [["Nume", "Ce"], ["Ionescu", "impozit"]])
    with pytest.raises(ValueError, match="capul tabelului"):
        PA.raspuns(cale)


def test_tabelul_gol_din_dosarul_probei_da_zero_nu_eroare():
    assert proba.nota_cheie(PA.raspuns(DOSAR / "Raspuns.xlsx"), CH)["fractie"] == 0


def test_nota_e_media_celor_trei_parti():
    ch = proba.nota_cheie(_erori("E1", "E2", "E3", "E4"), CH)
    n = proba.nota(ch, [True, True, False, False], [True, True, True])
    assert n["parti"] == {"cheia": 4 / 5, "conversațiile": 2 / 4, "discuția": 1}
    assert n["complet"] and n["nota"] == pytest.approx((4 / 5 + 1 / 2 + 1) / 3)


def test_o_parte_lipsa_face_proba_incompleta_nu_zero():
    n = proba.nota(None, [True] * 4, [None] * 3)
    assert (n["lipsa"], n["complet"], n["nota"]) == (["cheia", "discuția"], False, None)
    assert "incompletă, lipsește: cheia, discuția" in proba.randare(n)


def test_bifele_pe_jumatate_sau_numarate_gresit_sunt_refuzate():
    with pytest.raises(ValueError, match="pe jumătate"):
        proba.nota(None, [True, None, None, None], None)
    with pytest.raises(ValueError, match="3 bife, nu 4"):
        proba.nota(None, [True, True, True], None)


def test_nota_intra_in_total_ca_fractie():
    n = proba.nota(proba.nota_cheie(_erori("E1", "E2", "E3", "E4", "E5"), CH), [True] * 4, [True] * 3)
    assert total.total((16, 16), 4, n["nota"])["total"] == 100


# ── Cadrul si pachetul meseriei (rapoarte/propunere-proba-alte-meserii.md, aprobata de autor pe 15 octombrie) ──

def pachet_de_proba(dosar):
    """Un al doilea pachet, inventat pentru test (un text de campanie): cadrul trebuie sa mearga si pe el. Copiaza si
    pachetul payroll, ca sa fie doua."""
    import hashlib
    import json
    import shutil
    shutil.copytree(DOSAR, dosar / DOSAR.name)
    p = dosar / "text-campanie"
    p.mkdir()
    (p / "Text.txt").write_text("P1 ... P2 100% ecologic ... P3 49 lei", encoding="utf-8")
    xlsx.scrie(p / "Raspuns.xlsx", [["Paragraful", "Câmpul", "Ce scrie în text", "Ce ar trebui", "De ce"]])
    cuvinte = {"materialul": "textul campaniei", "regulile": "regulile de publicitate", "e_corect": "textul e corect",
               "sursa": "o regulă de publicitate", "sursa_unde": "legea, articolul",
               "unealta": "o listă de verificare pe care o refolosește", "la_material": "la text",
               "in_material": "în text", "locul": "Paragraful", "tema_pe_scurt": "un text de campanie de verificat"}
    (p / "pachet.json").write_text(json.dumps({
        "meseria": "marketing", "titlu": "Textul campaniei", "stare_bife": "inventate pentru test",
        "durata": "o oră", "termen": "2 zile",
        "tema": [["textul campaniei", "Text.txt"], ["tabelul de răspuns, gol", "Raspuns.xlsx"]],
        "raspuns": ["Paragraful", "Câmpul", "Ce scrie în text", "Ce ar trebui", "De ce"], "cheia": {"loc": "paragraf"},
        "locuri": [["P1", "Paragraful 1"], ["P2", "Paragraful 2"], ["P3", "Paragraful 3"]],
        "campuri": ["Afirmația", "Prețul"], "cuvinte": cuvinte,
        "discutia_2": ["Cum ai aflat ce cere acum legea despre afirmația „ecologic”?", "numește o sursă oficială"]},
        ensure_ascii=False), encoding="utf-8")
    cheie = json.dumps({"erori_de_gasit": 1, "erori": [
        {"cod": "E1", "paragraf": "P2", "coloana": "Afirmația", "coloane_afectate": ["Afirmația"],
         "valoare_in_stat": "100% ecologic", "valoare_corecta": "fără afirmație", "ce": "afirmație fără dovadă"}],
        "plantata_corecta": {"paragraf": "P3", "coloana": "Prețul", "valoare_in_stat": "49 lei",
                             "ce": "prețul redus e corect"}}, ensure_ascii=False).encode("utf-8")
    (p / "cheia.json").write_bytes(cheie)
    (p / "cheia.sha256").write_text(f"{hashlib.sha256(cheie).hexdigest()}  cheia.json\n", encoding="utf-8")
    return p


def test_pachetul_payroll_pastreaza_amprenta_foilor_scrise_inainte_de_pachete():
    # foile Metodei si ale candidatului de incercare au fost scrise cu aceasta amprenta: raman bune
    assert PA.amprenta == "c71fa7985f41" and PA.id == proba.IMPLICIT and PA.meseria == "salarizare"


def test_cadrul_nu_are_cuvinte_de_payroll():
    text = " ".join(proba.TIPAR_CONVERSATII + [x for q in proba.TIPAR_DISCUTIE if q for x in q]).lower()
    assert not [c for c in ("stat", "cotă", "plafon", "salari", "angajat", "marca") if c in text]


def test_un_al_doilea_pachet_merge_pe_acelasi_cadru(tmp_path, monkeypatch):
    pachet_de_proba(tmp_path)
    monkeypatch.setattr(proba, "PACHETE", tmp_path)
    assert [p.id for p in proba.pachete()] == [proba.IMPLICIT, "text-campanie"]
    m = proba.pachet("text-campanie")
    assert m.conversatii[0].startswith("i-a dat AI-ului textul campaniei și regulile de publicitate")
    assert m.discutie[0][0] == "Unde a greșit AI-ul în lucrul la text?"
    assert m.discutie[1][0].startswith("Cum ai aflat ce cere acum legea") and m.amprenta != PA.amprenta
    cale = tmp_path / "r.xlsx"
    xlsx.scrie(cale, [m.raspuns_cap, ["p2", "afirmatia", "100% ecologic", "fără", "nedovedit"], ["P3", "Prețul"]])
    n = proba.nota_cheie(m.raspuns(cale), m.cheia())
    assert n["gasite"] == ["E1"] and n["gresite"] == ["P3"] and n["fractie"] == 0
    xlsx.scrie(cale, [m.raspuns_cap, ["P9", "Prețul"]])
    with pytest.raises(ValueError, match="paragraful „P9” nu e în text"):
        m.raspuns(cale)


def test_foaia_isi_tine_pachetul_iar_schimbarea_pastreaza_linkurile(tmp_path, monkeypatch):
    pachet_de_proba(tmp_path)
    monkeypatch.setattr(proba, "PACHETE", tmp_path)
    f = proba.scrie(proba.foaie("Ana"), {"linkuri": "https://claude.ai/share/x"})
    assert proba.pachetul_foii(f).id == proba.IMPLICIT and not proba.inceputa(f, False)
    g = proba.schimba_pachetul(f, proba.pachet("text-campanie"))
    assert proba.pachetul_foii(g).id == "text-campanie" and proba.valori(g)["linkuri"] == "https://claude.ai/share/x"
    assert proba.bife(proba.scrie(g, {"C1": "da"}))[0] == [True, None, None, None]
    assert proba.inceputa(proba.scrie(g, {"C1": "da"}), False) and proba.inceputa(g, True)
    with pytest.raises(ValueError, match="nu există"):
        proba.pachet("../cheia")
