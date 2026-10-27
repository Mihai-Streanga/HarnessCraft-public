"""Intrebarile despre proiect: textele aprobate de autor, ordinea, alegerea din fisa, partea IV a ghidului. Fara
model si fara retea: le alege programul din verificarile picate."""
from pathlib import Path

from harnesscraft import fisa, formular, interviu, tintite
from harnesscraft.harness import harness
from tests.test_fisa import stare

TEXTE = Path(__file__).parent / "date" / "intrebari-despre-proiect.md"


def _fisa(picate):
    """O fisa cu verificarile din `picate` picate ({cheie: ce a gasit}); restul trec."""
    fapte = [[k, k not in picate, None] for k in tintite.ORDINE]
    dovezi = [f"{'✗' if k in picate else '✓'} {k}" + (f": {picate[k]}" if picate.get(k) else "") for k in tintite.ORDINE]
    return {"principii": {"o arie": {"puncte": 0.0, "dovezi": dovezi, "fapte": fapte}}}


def _randare():
    return "\n".join(f"{n}. {k}\n{tintite.INTREBARI[k][0]}\nCe afli: {tintite.INTREBARI[k][1]}\n"
                     for n, k in enumerate(tintite.ORDINE, 1))


def test_textele_si_ordinea_sunt_cele_aprobate_de_autor_la_caracter():
    # o schimbare aici cere iar acordul autorului; apoi se rescrie fisierul
    assert _randare() == TEXTE.read_text(encoding="utf-8")


def test_fiecare_verificare_a_fisei_are_o_intrebare_si_un_loc_in_ordine():
    assert set(tintite.INTREBARI) == set(tintite.ORDINE) == fisa.CHEI and len(tintite.ORDINE) == len(fisa.CHEI)
    assert all(q.endswith("?") for q, _ in tintite.INTREBARI.values())


def test_primele_doua_picate_in_ordine_nu_in_ordinea_fisei():
    f = _fisa({"cai_destule": "2 căi citate", "hooks_agent": "", "teste": "", "ai": "0 commit-uri o declară"})
    assert [k for k, _, _ in tintite.alege(f)] == ["ai", "teste"]


def test_o_fisa_ca_a_metodei_da_licenta_si_ci():
    f = _fisa({"ci": "", "organizare": "", "licenta": "lipsă"})
    assert [k for k, _, _ in tintite.alege(f)] == ["licenta", "ci"]


def test_fisierele_lipsa_numai_cand_lipseste_ceva():
    # verificarea pica si cand regulile pomenesc prea putine fisiere: atunci nu e nicio lista de intrebat
    assert tintite.alege(_fisa({"cai_80": "2 din 2 există", "organizare": ""}))[0][0] == "organizare"
    (k, q, _), = tintite.alege(_fisa({"cai_80": "7 din 9 există; lipsă: `a.json`, `b.db`"}))
    assert k == "cai_80" and "nu se mai găsesc în proiect: `a.json`, `b.db`. Sunt" in q


def test_cifrele_se_numara_romaneste():
    assert "(în 1 loc)" in tintite.alege(_fisa({"chei_acum": "1 în arbore"}))[0][1]
    assert "(în 165 de locuri)" in tintite.alege(_fisa({"chei_acum": "165 în arbore"}))[0][1]
    assert "(2 fișiere)" in tintite.alege(_fisa({"cai_destule": "2 căi citate"}))[0][1]


def test_proiect_fara_goluri_spune_ca_nu_e_nicio_intrebare():
    r = tintite.parte(_fisa({}))
    assert tintite.FARA in r and not any(x.startswith("**1.**") for x in r)


def test_ghidul_le_are_in_partea_IV_cu_notite_iar_raportul_le_citeste_din_ghid(depozit):
    d = depozit()
    d.commit("start", {"CLAUDE.md": "# Reguli\n", "src/app.py": "x"})
    f = fisa.fisa("d", stare(), harness(d.cale))
    g = interviu.ghid(f)
    alese = tintite.alege(f)
    assert len(alese) == 2
    parte4 = g[g.index("### Despre proiectul lui"):g.index("### Ale tale")]
    assert f"**1.** {alese[0][1]}" in parte4 and f"*Ce afli: {alese[1][2]}*" in parte4
    assert "model" not in parte4
    assert {"nota-T1", "nota-T2"} <= set(formular.valori(g))
    assert tintite.din_ghid(g) == [(1, alese[0][1]), (2, alese[1][1])]
    assert interviu.citeste(g) is not None  # bifele si amprenta nu se schimba
