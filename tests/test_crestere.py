"""Intrebarea despre cresterea proiectului: regula pe drumul in timp (fereastra de 14 zile, nu fractie din istoric) si
locul ei in partea IV, intre intrebarile din goluri si cea de legare."""
from harnesscraft import candidati, formular, pasi, tintite

REGULI = "# Reguli\n\n## Comenzi\n\n- `pytest -q` inainte de fiecare salvare\n"


def _drum(*zile):
    return [{"ziua": z, "total": t} for z, t in zile]


def test_jumatate_din_punctaj_in_ultimele_14_zile_aduce_intrebarea():
    x = pasi.crestere(_drum(("2026-01-01", 2.0), ("2026-05-01", 3.0), ("2026-05-20", 9.0), ("2026-05-31", 9.0)))
    assert x == {"zile": 14, "inainte": 3.0, "acum": 9.0}


def test_proiectul_vechi_care_a_crescut_in_saptamani_nu_o_primeste():
    # ca un proiect din esantion: ani la 2 puncte, apoi regulile pentru AI pe parcursul a doua luni
    drum = _drum(("2021-11-15", 2.0), ("2026-08-08", 8.0), ("2026-08-20", 11.0), ("2026-09-07", 14.0),
                 ("2026-09-14", 13.0))
    assert pasi.crestere(drum) is None


def test_proiect_fara_punctaj_sau_fara_drum_nu_o_primeste():
    assert pasi.crestere([]) is None and pasi.crestere(_drum(("2026-05-01", 0.0))) is None


def test_ghidul_o_pune_intre_goluri_si_legare_iar_raportul_o_citeste(depozit, tmp_path):
    d = depozit("proiect")
    d.commit("cod", {"src/app.py": "x"}, data="2026-01-01T12:00:00+00:00")
    d.commit("reguli si teste", {"CLAUDE.md": REGULI, "tests/test_app.py": "def test_a():\n    assert 1\n"},
             data="2026-03-01T12:00:00+00:00")
    c = candidati.citeste(candidati.nou("Ana Pop", str(d.cale), dosar=tmp_path / "c"), tmp_path / "c")
    candidati.analizeaza(c)
    g = candidati.ghid(c)
    f = candidati.fisa(c)["fisa"]
    q = tintite.crestere(f["crestere"], f["maxim"])[0]
    n = len(tintite.alege(f)) + 1
    assert f"**{n}.** {q}" in g and tintite.CRESTERE in g and f"**{n + 1}.**" in g.split(tintite.LEGARE)[1]
    assert f"nota-T{n + 1}" in formular.valori(g)
    assert (n, q) in tintite.din_ghid(g)
