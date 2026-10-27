import random
import string

import pytest

from harnesscraft import istoric, stare
from harnesscraft.gardieni import ClasamentNecomis
from harnesscraft.manifest import DEPOZITE

MIT = "MIT License\n\nPermission is hereby granted, free of charge, to any person obtaining a copy"


def test_teste_doar_fisiere_sursa_de_test():
    cai = ["tests/test_a.py", "src/a.test.ts", "pkg/x_test.go", "src/FooTest.java",
           "contest.py", "latest_results.py", "tests/fixtures/data.json", "testing.md", "src/attest.rs"]
    r = stare.teste(cai)
    assert r["fisiere_test"] == 4
    assert "contest.py" not in r["exemple"]


def test_ci_doar_locurile_cunoscute():
    cai = [".github/workflows/ci.yml", ".github/workflow/ci.yml", "docs/.gitlab-ci.yml", ".gitlab-ci.yml"]
    assert stare.ci(cai)["fisiere_ci"] == [".github/workflows/ci.yml", ".gitlab-ci.yml"]


def test_licenta_mit_la_radacina(depozit):
    d = depozit()
    d.commit("init", {"LICENSE": MIT, "package.json": "{}"})
    r = stare.licenta(d.cale, stare.fisiere_la(d.cale))
    assert (r["fisier_licenta"], r["tip"]) == ("LICENSE", "MIT")
    assert r["manifeste_dependente"] == ["package.json"]
    assert r["licente_dependente"] == "neacoperit"


def test_licenta_doar_in_subdosar_nu_conteaza(depozit):
    d = depozit()
    d.commit("init", {"vendor/x/LICENSE": MIT})
    assert stare.licenta(d.cale, stare.fisiere_la(d.cale))["fisier_licenta"] is None


def test_transparenta_ai_numai_din_urme_ale_uneltelor(depozit):
    d = depozit()
    d.commit("a\n\nCo-Authored-By: Claude <noreply@anthropic.com>", {"a": "1"})
    d.commit("b\n\nCo-authored-by: Ion Pop <ion@x.ro>", {"a": "2"})
    d.commit("am intrebat claude despre asta", {"a": "3"})
    d.commit("c\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)", {"a": "4"})
    r = stare.transparenta_ai(istoric.citeste(d.cale))
    assert (r["commits_cu_urma_ai"], r["din"]) == (2, 4)


def test_chei_gasite_in_istoric_chiar_sterse(depozit):
    rnd = random.Random(7)
    token = "ghp_" + "".join(rnd.choice(string.ascii_letters + string.digits) for _ in range(36))
    d = depozit()
    d.commit("config", {"config.py": f'TOKEN = "{token}"\n'})
    d.commit("scoate cheia", {"config.py": "TOKEN = None\n"})
    r = stare.chei(d.cale)
    assert r["gasiri"] >= 1 and r["inca_in_arbore"] == 0
    d2 = depozit("curat")
    d2.commit("init", {"a.py": "x = 1\n"})
    assert stare.chei(d2.cale)["gasiri"] == 0
    d3 = depozit("ramasa")
    d3.commit("config", {"config.py": f'TOKEN = "{token}"\n'})
    assert stare.chei(d3.cale)["inca_in_arbore"] == 1


def test_stare_pe_esantion_refuza_fara_clasament(monkeypatch):
    monkeypatch.setattr("harnesscraft.gardieni.gardian_c2", lambda *a: "clasament lipsa")
    with pytest.raises(ClasamentNecomis):
        stare.stare(DEPOZITE / "orice__depozit", [])


def test_fisier_neurmarit_nu_e_cheie_urcata(depozit):
    rnd = random.Random(8)
    token = "ghp_" + "".join(rnd.choice(string.ascii_letters + string.digits) for _ in range(36))
    d = depozit()
    d.commit("init", {"a.py": "x = 1\n"})
    (d.cale / ".env").write_text(f"TOKEN={token}\n", encoding="utf-8")
    assert stare.chei(d.cale) == {"gasiri": 0, "reguli": [], "inca_in_arbore": 0,
                                  "de_proba": {"gasiri": 0, "inca_in_arbore": 0},
                                  "generica": {"gasiri": 0, "inca_in_arbore": 0}}


def test_cheile_din_teste_exemple_si_documentatie_si_valorile_model_nu_scad(depozit):
    rnd = random.Random(9)
    token = "ghp_" + "".join(rnd.choice(string.ascii_letters + string.digits) for _ in range(36))
    d = depozit()
    d.commit("init", {"tests/conftest.py": f'TOKEN = "{token}"\n', "docs/setup.md": f"TOKEN={token}\n",
                      "src/app.py": "x = 1\n"})
    r = stare.chei(d.cale)
    assert r["inca_in_arbore"] == 0 and r["gasiri"] == 0
    assert r["de_proba"]["inca_in_arbore"] == 2 and r["de_proba"]["gasiri"] == 2
    assert stare.cheie_de_proba("src/app.test.ts", "a1b2") and stare.cheie_de_proba(".env.example", "a1b2")
    assert stare.cheie_de_proba("config.py", "your_api_key_here") and stare.cheie_de_proba("config.py", "xxxxxxxx")
    assert not stare.cheie_de_proba("src/config.py", "q8Zr2LmP0aKs")
    assert not stare.cheie_de_proba("src/testimonials.py", "q8Zr2LmP0aKs")


def test_regula_generica_nu_scade_cele_pe_furnizor_da():
    assert stare.fel_cheie({"File": "src/app.ts", "RuleID": "generic-api-key", "Secret": "q8Zr2LmP0aKs"}) == "generica"
    assert stare.fel_cheie({"File": "src/app.ts", "RuleID": "github-pat", "Secret": "q8Zr2LmP0aKs"}) == "scade"
    assert stare.fel_cheie({"File": "tests/a.ts", "RuleID": "github-pat", "Secret": "q8Zr2LmP0aKs"}) == "de_proba"


def _arbore(depozit, rev, tmp):
    """Fisierele extrase de `stare.extrage`, ca lista: ce ajunge la analiza."""
    from pathlib import Path
    stare.extrage(depozit, rev, tmp)
    return sorted(p.relative_to(tmp).as_posix() for p in Path(tmp).rglob("*") if p.is_file())


def test_legatura_simbolica_din_arbore_nu_opreste_analiza(depozit):
    """Pe Windows, o legatura din arhiva devine copie, iar filtrul „data” o refuza (un proiect din esantion, `venv/bin/python`)."""
    import tempfile
    d = depozit()
    d.commit("cod", {"a.py": "x = 1\n"})
    for cale, tinta in (("venv/bin/python3", "/usr/bin/python3"), ("venv/bin/python", "python3")):
        (d.cale / "tinta").write_text(tinta, encoding="utf-8")
        blob = d._git("hash-object", "-w", "tinta").strip()
        (d.cale / "tinta").unlink()
        d._git("update-index", "--add", "--cacheinfo", f"120000,{blob},{cale}")
    d.commit("venv", {})
    assert stare.chei(d.cale)["gasiri"] == 0
    with tempfile.TemporaryDirectory() as tmp:
        assert "a.py" in _arbore(d.cale, "HEAD", tmp)


def test_commit_fara_fisiere_nu_opreste_analiza(depozit):
    """`git archive` pe un arbore gol da numai antetul, pe care `tarfile` nu-l deschide (un proiect din esantion)."""
    import tempfile
    d = depozit()
    d.commit("cod", {"a.py": "x = 1\n"})
    d.commit("sterge tot", {"a.py": None})
    assert stare.chei(d.cale)["inca_in_arbore"] == 0
    with tempfile.TemporaryDirectory() as tmp:
        assert _arbore(d.cale, "HEAD", tmp) == []


def test_cheile_pe_drum_dau_ce_da_chei_la_fiecare_commit(depozit):
    """`CheiPeDrum` citeste istoricul o data si fiecare versiune de fisier o data; rezultatul ramane al lui `chei`."""
    rnd = random.Random(10)
    token = "ghp_" + "".join(rnd.choice(string.ascii_letters + string.digits) for _ in range(36))
    d = depozit()
    d.commit("cod", {"a.py": "x = 1\n"})
    d.commit("cheie", {"config.py": f'TOKEN = "{token}"\n'})
    d.commit("de proba", {"tests/conftest.py": f'TOKEN = "{token}"\n'})
    d.commit("scoate", {"config.py": "TOKEN = None\n"})
    d.commit("reguli", {".gitleaks.toml": '[extend]\nuseDefault = true\n[allowlist]\npaths = ["tests/"]\n'})
    d.commit("din nou", {"src/x.py": f'TOKEN = "{token}"\n'})
    d.commit("sterge tot", {c: None for c in ("a.py", "config.py", "tests/conftest.py", ".gitleaks.toml", "src/x.py")})
    shas = d._git("rev-list", "--reverse", "HEAD").split()
    pe_drum = stare.CheiPeDrum(d.cale, shas)
    vazute = set()
    for sha in reversed(shas):  # in alta ordine decat zilele: versiunile vazute deja se refolosesc
        r = stare.chei(d.cale, sha)
        assert pe_drum(sha) == r, sha[:7]
        vazute.add(repr(r))
    assert len(vazute) >= 4  # comparatia prinde ceva: rezultatul se schimba de la un commit la altul


def test_nume_interzis_pe_windows_nu_opreste_analiza(depozit):
    """Un `x.pdf:Zone.Identifier` comis (un proiect din esantion): git pe Windows refuza arhiva intreaga."""
    import tempfile
    d = depozit()
    d.commit("cod", {"a.py": "x = 1\n"})
    (d.cale / "tinta").write_text("[ZoneTransfer]\n", encoding="utf-8")
    blob = d._git("hash-object", "-w", "tinta").strip()
    (d.cale / "tinta").unlink()
    d._git("-c", "core.protectNTFS=false", "update-index", "--add", "--cacheinfo",
           f"100644,{blob},doc.pdf:Zone.Identifier")
    d._git("-c", "core.protectNTFS=false", "commit", "--quiet", "-m", "pdf")
    assert stare.chei(d.cale)["inca_in_arbore"] == 0
    with tempfile.TemporaryDirectory() as tmp:
        assert "a.py" in _arbore(d.cale, "HEAD", tmp)
