"""Intrebarea de legare: regula care alege commit-ul (rapoarte/plan-legare-si-crestere.md, verdictele autorului pe
trei cazuri) si locul ei in partea IV a ghidului, citit si de raport."""
from pathlib import Path

from harnesscraft import fisa, formular, interviu, legare, tintite
from harnesscraft.harness import harness
from tests.test_fisa import stare

REGULI = "# Reguli\n\n## Comenzi\n\n- `pytest -q` inainte de fiecare salvare\n"


def test_ultimul_commit_mai_ales_despre_reguli_nu_cel_atins_in_treacat(depozit):
    d = depozit()
    d.commit("start", {"CLAUDE.md": "# Reguli\n", "src/a.py": "x = 1\n", "src/b.py": "y = 2\n"})
    d.commit("regula de teste", {"CLAUDE.md": REGULI})
    d.commit("cod si o virgula", {"CLAUDE.md": REGULI + "- un rand\n", **{f"src/c{i}.py": "z\n" for i in range(4)}})
    d.commit("corectura", {"CLAUDE.md": REGULI + "- un rand.\n"})
    x = legare.alege(d.cale)
    assert (x["mesaj"], x["fel"], x["fisier"]) == ("regula de teste", "schimbare", "CLAUDE.md")


def test_fara_commit_despre_reguli_ia_commit_ul_care_le_a_creat(depozit):
    d = depozit()
    d.commit("cod", {"src/a.py": "x = 1\n"})
    d.commit("totul deodata", {"AGENTS.md": REGULI, "src/b.py": "y\n", "src/c.py": "z\n"})
    x = legare.alege(d.cale)
    assert (x["mesaj"], x["fel"], x["fisiere"]) == ("totul deodata", "creare", 3)


def test_fara_reguli_pentru_ai_nu_e_intrebare_de_legare(depozit):
    d = depozit()
    d.commit("cod", {"src/a.py": "x = 1\n"})
    assert legare.alege(d.cale) is None


def test_ghidul_o_pune_ultima_in_partea_IV_iar_raportul_o_citeste(depozit):
    d = depozit()
    d.commit("start", {"CLAUDE.md": "# Reguli\n", "src/app.py": "x"})
    d.commit("regula de teste", {"CLAUDE.md": REGULI})
    f = {**fisa.fisa("d", stare(), harness(d.cale)), "legare": legare.alege(d.cale)}
    g = interviu.ghid(f)
    parte4 = g[g.index("### Despre proiectul lui"):g.index("### Ale tale")]
    q = tintite.legare(f["legare"])[0]
    assert len(tintite.alege(f)) == 2 and f"**3.** {q}" in parte4 and tintite.LEGARE in parte4
    assert "Pe 2 ianuarie 2026 ați salvat" in q and "„regula de teste”" in q and "Ana Pop" in parte4
    assert "nota-T3" in formular.valori(g)
    assert tintite.din_ghid(g)[-1] == (3, q)
    assert interviu.citeste(g) is not None


def test_proiect_fara_goluri_primeste_tot_intrebarea_de_legare():
    x = {"commit": "abc1234", "data": "2026-10-12", "autor": "Ana Pop", "mesaj": "regula", "fisier": "CLAUDE.md",
         "fel": "creare", "fisiere": 1}
    f = {"principii": {"o arie": {"puncte": 4.0, "dovezi": [], "fapte": []}}, "legare": x}
    r = tintite.parte(f)
    assert tintite.FARA in r and any(y.startswith("**1.** Regulile scrise pentru AI") for y in r)
    assert "împreună cu 1 fișier" in tintite.legare(x)[0]


TEXTE_NOI = Path(__file__).parent / "date" / "intrebari-legare-crestere.md"


def _randare_noi():
    x = {"commit": "{commit}", "data": "2026-01-02", "autor": "{autor}", "mesaj": "{mesaj}", "fisier": "{fisier}",
         "fisiere": 5}
    schimbare = tintite.legare({**x, "fel": "schimbare"})
    creare = tintite.legare({**x, "fel": "creare"})
    crestere = tintite.crestere({"zile": 14, "inainte": 3.0, "acum": 9.0}, 16.0)
    return "\n".join([tintite.CRESTERE, crestere[0], f"Ce afli: {crestere[1]}", "", tintite.LEGARE, schimbare[0],
                      creare[0], schimbare[2], f"Ce afli: {schimbare[1]}", ""])


def test_textele_noi_sunt_cele_aprobate_de_autor_la_caracter():
    # aprobate de autor pe 22 octombrie 2026; o schimbare cere iar acordul lui, apoi se rescrie fisierul
    assert _randare_noi() == TEXTE_NOI.read_text(encoding="utf-8")
