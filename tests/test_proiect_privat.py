"""Proiectul privat al unui candidat (incercat pe 16 octombrie 2026): git nu deschide ferestre de autentificare din
server; un depozit privat vine ca un singur fisier cu tot istoricul (.bundle); un dosar fara istoric propriu, aflat in
alt depozit, e refuzat, nu citit cu istoricul celuilalt."""
import subprocess

import pytest

from harnesscraft import candidati


def test_git_ruleaza_fara_ferestre_de_autentificare(monkeypatch):
    vazut = {}

    def run(args, **kw):
        vazut.update(kw["env"])
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(candidati.subprocess, "run", run)
    candidati._git("clone", "https://exemplu.ro/privat.git", "x")
    assert vazut["GIT_TERMINAL_PROMPT"] == "0" and vazut["GCM_INTERACTIVE"] == "never"


def test_un_link_privat_trimite_la_fisierul_cu_tot_istoricul():
    motiv = candidati.de_ce_nu_se_descarca("fatal: could not read Username for 'https://gitlab.com': terminal prompts disabled")
    assert "nu e un depozit public" in motiv and candidati.BUNDLE in motiv


def test_proiectul_din_fisierul_cu_tot_istoricul_se_analizeaza(depozit, tmp_path):
    d = depozit("privat")
    d.commit("start", {"CLAUDE.md": "reguli", "src/app.py": "x"})
    d.commit("fix: reparatie", {"src/app.py": "y"})
    fisier = tmp_path / "privat.bundle"
    subprocess.run(["git", "-C", str(d.cale), "bundle", "create", str(fisier), "--all"], check=True, capture_output=True)
    c = candidati.citeste(candidati.nou("Ana", str(fisier), dosar=tmp_path / "c"), tmp_path / "c")
    assert c["proiect"].endswith("/proiect") and candidati.nume_sursei(c["sursa"]) == "privat"
    candidati.analizeaza(c)
    assert candidati.fisa(c)["fisa"]["proiect"] == "privat" and len(candidati.fisa(c)["drumul"]) >= 1


def test_dosarul_fara_istoric_propriu_din_alt_depozit_e_refuzat(depozit, tmp_path):
    d = depozit("gazda")
    d.commit("start", {"README.md": "x"})
    dezarhivat = d.cale / "arhiva" / "proiect"
    dezarhivat.mkdir(parents=True)
    (dezarhivat / "app.py").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="nu are istoric git") as ex:
        candidati.nou("Ana", str(dezarhivat), dosar=tmp_path / "c")
    assert candidati.BUNDLE in str(ex.value)
