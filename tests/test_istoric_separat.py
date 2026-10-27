from harnesscraft.istoric_separat import agrega


def caz(zona, regula):
    return {"zona": zona, "regula": regula}


def test_proportia_pe_zona_si_totalul_suma():
    r = agrega([caz("cicatrice", True), caz("cicatrice", False), caz("arhitectura", True)])
    assert r["cicatrice"] == {"acceptate": 1, "cazuri": 2, "puncte": 0.5}
    assert r["arhitectura"]["puncte"] == 1.0
    assert r["total"] == 1.5 and r["maxim"] == 2.0


def test_numarul_de_cazuri_nu_conteaza():
    mic = agrega([caz("cicatrice", True), caz("cicatrice", False)])
    mare = agrega([caz("cicatrice", True)] * 10 + [caz("cicatrice", False)] * 10)
    assert mic["cicatrice"]["puncte"] == mare["cicatrice"]["puncte"]


def test_fara_cazuri_da_zero():
    r = agrega([])
    assert r["cicatrice"]["puncte"] == r["arhitectura"]["puncte"] == r["total"] == 0.0
