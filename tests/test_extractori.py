"""Fisierele de proba din SPEC, „Zonele”: cicatrice reala, cicatrice falsa, fara fisier de instructiuni."""
import pytest

from harnesscraft import extractori, istoric, instructiuni
from harnesscraft.gardieni import ClasamentNecomis
from harnesscraft.manifest import DEPOZITE


def _cicatrici(d):
    c = istoric.citeste(d.cale)
    return extractori.cicatrici(c, instructiuni.gaseste(d.cale, c), d.cale)


def test_cicatrice_reala(depozit):
    d = depozit()
    d.commit("init", {"CLAUDE.md": "reguli", "a.py": "1"})
    d.commit("fix: parserul pierdea ultimul rand", {"a.py": "2"})
    d.commit("docs: regula despre ultimul rand", {"CLAUDE.md": "reguli\n`a.py` verifica ultimul rand"})
    [caz] = _cicatrici(d)
    assert caz["regula"] and caz["reparatie"].titlu.startswith("fix:")


def test_cicatrice_falsa_modificare_fara_reparatie(depozit):
    d = depozit()
    d.commit("init", {"CLAUDE.md": "reguli", "a.py": "1"})
    d.commit("feat: functie noua", {"a.py": "2"})
    d.commit("docs: stil", {"CLAUDE.md": "reguli\nstil `a.py`"})
    [caz] = _cicatrici(d)
    assert not caz["regula"]


def test_reparatie_fara_legatura_cu_regula_nu_e_cicatrice(depozit):
    """prima formă se aprindea la orice „fix” din apropiere (C4, C6 in runda 1)."""
    d = depozit()
    d.commit("init", {"CLAUDE.md": "reguli", "a.py": "1", "b.py": "1"})
    d.commit("fix: parserul pierdea ultimul rand", {"a.py": "2"})
    d.commit("docs: regula de push", {"CLAUDE.md": "reguli\n`git push` dupa fiecare commit, in `b.py`"})
    [caz] = _cicatrici(d)
    assert not caz["regula"]


def test_regula_care_numeste_termenul_din_titlul_reparatiei(depozit):
    d = depozit()
    d.commit("init", {"CLAUDE.md": "reguli", "a.py": "1"})
    d.commit("fix: filtrul de salariu bloca anunturile", {"a.py": "2"})
    d.commit("docs: regula", {"CLAUDE.md": "reguli\n`filtrul` nu blocheaza fara motiv"})
    assert _cicatrici(d)[0]["regula"]


def test_reparatia_prea_veche_nu_conteaza(depozit):
    d = depozit()
    d.commit("init", {"CLAUDE.md": "r", "a.py": "1"}, data="2026-01-01T12:00:00+00:00")
    d.commit("fix: ceva", {"a.py": "2"}, data="2026-01-02T12:00:00+00:00")
    d.commit("docs", {"CLAUDE.md": "r2 `a.py`"}, data="2026-01-10T12:00:00+00:00")
    assert not _cicatrici(d)[0]["regula"]


def test_crearea_fisierului_nu_e_cicatrice(depozit):
    d = depozit()
    d.commit("fix: ceva", {"a.py": "1"})
    d.commit("adauga CLAUDE.md", {"CLAUDE.md": "r"})
    assert _cicatrici(d) == []


def test_fara_fisier_de_instructiuni(depozit):
    d = depozit()
    d.commit("init", {"a.py": "1"})
    d.commit("fix: x", {"a.py": "2"})
    assert _cicatrici(d) == []


def test_cuvantul_prefix_nu_e_reparatie():
    class C:
        def __init__(self, t):
            self.titlu = t
    assert extractori.este_reparatie(C("fix(parser): x"))
    assert extractori.este_reparatie(C("Repară calculul"))
    assert not extractori.este_reparatie(C("prefix nou pentru rute"))
    assert not extractori.este_reparatie(C("debugger integrat"))


def test_termenii_numiti_de_regula():
    linii = ["Push-ul il face `hook-ul post-commit`; vezi `scripts/verifica.py` si docs/INSTALARE.md.",
             "`rm` nu"]
    assert extractori.termeni(linii) == {"hook-ul post-commit", "verifica.py", "instalare.md"}


def test_arhitectura_tinuta_la_zi_si_nu(depozit):
    d = depozit()
    d.commit("init", {"src/a.py": "1", "docs/ARCHITECTURE.md": "v1"})
    d.commit("modul nou", {"src/plata/b.py": "1"})
    d.commit("arhitectura: modulul plata", {"docs/ARCHITECTURE.md": "v1\n- `src/plata/`: platile"})
    d.commit("alt modul", {"src/raport/c.py": "1"})
    for i in range(6):
        d.commit(f"cod {i}", {"src/a.py": str(i)})
    cazuri = extractori.arhitectura(istoric.citeste(d.cale), d.cale)
    assert [(x["commit"].titlu, x["regula"]) for x in cazuri] == [("modul nou", True), ("alt modul", False)]


def test_documentul_de_arhitectura_se_recunoaste_dupa_continut_nu_dupa_nume(depozit):
    """prima formă cerea un nume ca ARCHITECTURE; un document de arhitectura poate avea alt nume (A1, A2, A5 in runda 1)."""
    d = depozit()
    d.commit("init", {"src/a.py": "1", "Ghid.md": "v1"})
    d.commit("unealta noua", {"unelte/export.py": "1"})
    d.commit("ghid: unealta", {"Ghid.md": "v1\n`unelte/export.py` scrie exportul"})
    [caz] = extractori.arhitectura(istoric.citeste(d.cale), d.cale)
    assert caz["regula"]


def test_jurnalul_nu_tine_arhitectura_la_zi(depozit):
    d = depozit()
    d.commit("init", {"src/a.py": "1", "docs/ARCHITECTURE.md": "v1"})
    d.commit("modul nou", {"src/plata/b.py": "1"})
    d.commit("jurnal", {"CHANGELOG.md": "am adaugat src/plata/"})
    d.commit("arhitectura, fara modul", {"docs/ARCHITECTURE.md": "v2 stil"})
    [caz] = extractori.arhitectura(istoric.citeste(d.cale), d.cale)
    assert not caz["regula"]


def test_extractorii_pe_esantion_refuza_fara_clasament(monkeypatch):
    monkeypatch.setattr("harnesscraft.gardieni.gardian_c2", lambda *a: "clasament lipsa")
    with pytest.raises(ClasamentNecomis):
        extractori.toate(DEPOZITE / "orice__depozit", [], [])
