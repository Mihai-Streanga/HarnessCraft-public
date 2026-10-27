from harnesscraft import istoric, instructiuni


def _gaseste(d):
    return {f.cale: f for f in instructiuni.gaseste(d.cale, istoric.citeste(d.cale))}


def test_conventiile_se_recunosc_si_doar_numele_exact():
    assert instructiuni.conventia("CLAUDE.md") == "claude"
    assert instructiuni.conventia("pachete/x/claude.md") == "claude"
    assert instructiuni.conventia("AGENTS.md") == "agents"
    assert instructiuni.conventia(".cursor/rules/stil.mdc") == "cursor"
    assert instructiuni.conventia(".cursorrules") == "cursor"
    for fals in ("rlm-claude.md", "CLAUDE.md.template", "agents.md.txt", "docs/cursor/rules.md"):
        assert instructiuni.conventia(fals) is None, fals


def test_istoricul_fisierului_si_modificarile(depozit):
    d = depozit()
    d.commit("init", {"CLAUDE.md": "v1", "a.py": "1"})
    d.commit("cod", {"a.py": "2"})
    d.commit("regula noua", {"CLAUDE.md": "v2"})
    d.commit("alta regula", {"CLAUDE.md": "v3"})
    f = _gaseste(d)["CLAUDE.md"]
    assert f.conventie == "claude"
    assert [c.titlu for c in f.commits] == ["init", "regula noua", "alta regula"]
    assert len(f.modificari) == 2


def test_istoricul_trece_peste_redenumire(depozit):
    d = depozit()
    text = "regula foarte lunga\n" * 30
    d.commit("init", {"docs/CLAUDE.md": text})
    d.commit("muta", {"docs/CLAUDE.md": None, "CLAUDE.md": text})
    d.commit("schimba", {"CLAUDE.md": text + "inca una\n"})
    f = _gaseste(d)["CLAUDE.md"]
    assert [c.titlu for c in f.commits] == ["init", "muta", "schimba"]


def test_fisier_sters_nu_apare_si_recreat_porneste_de_la_zero(depozit):
    d = depozit()
    d.commit("unu", {"AGENTS.md": "a", "x": "1"})
    d.commit("sterge", {"AGENTS.md": None})
    d.commit("recreeaza", {"AGENTS.md": "complet altceva"})
    f = _gaseste(d)["AGENTS.md"]
    assert [c.titlu for c in f.commits] == ["recreeaza"]


def test_fara_fisier_de_instructiuni(depozit):
    d = depozit()
    d.commit("init", {"README.md": "x"})
    assert _gaseste(d) == {}


def test_cursor_mai_multe_reguli(depozit):
    d = depozit()
    d.commit("init", {".cursor/rules/a.mdc": "a", ".cursor/rules/b.mdc": "b"})
    d.commit("b", {".cursor/rules/b.mdc": "b2"})
    g = _gaseste(d)
    assert set(g) == {".cursor/rules/a.mdc", ".cursor/rules/b.mdc"}
    assert len(g[".cursor/rules/b.mdc"].modificari) == 1
