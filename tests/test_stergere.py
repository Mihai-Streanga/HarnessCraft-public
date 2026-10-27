"""Stergerea unui candidat (cererea autorului, 19 octombrie: GDPR, datele nu se tin cand nu mai folosesc): butonul din
aplicatie sterge de pe disc tot dosarul, definitiv. Testele cauta urma omului dupa stergere in tot ce a scris
aplicatia, nu numai in lista."""
import re
import subprocess
import sys

import pytest

from harnesscraft import candidati
from tests.test_interfata import _proiect, site  # noqa: F401 (fixture)


def _urme(radacina, *cuvinte):
    """Orice cale sau fisier de sub `radacina` care pomeneste unul din cuvinte (in nume sau in continut)."""
    gasite = []
    for f in radacina.rglob("*"):
        nume = f.relative_to(radacina).as_posix().lower()
        text = f.read_bytes().decode("utf-8", "ignore").lower() if f.is_file() else ""
        gasite += [f for x in cuvinte if x.lower() in nume or x.lower() in text]
    return gasite


def test_stergerea_din_aplicatie_scoate_tot_dosarul_de_pe_disc_si_lasa_proiectul_candidatului(site):
    site.post("/nou", {"nume": "Ioana Stoica", "sursa": site.proiect})
    site.post("/c/ioana-stoica/fisa")
    site.post("/c/ioana-stoica/interviu", {"concluzia": "o notita despre Ioana"})
    rezultat = site.get("/c/ioana-stoica/rezultat")[1]
    # langa „Finalizeaza”, de aceeasi latime, cu ce face spus sub ele (observatia autorului)
    assert re.search(r'class="actiune pereche">.*class="buton secundar lat">Finalizează candidatura<.*'
                     r'class="buton secundar lat" href="/c/ioana-stoica/sterge">Șterge candidatul<', rezultat)
    assert "definitiv tot dosarul de pe discul acestui calculator" in rezultat
    assert "scrii numele candidatului: Ioana Stoica" in site.get("/c/ioana-stoica/sterge")[1]
    assert _urme(site.dosar, "ioana")
    cod, unde, corp = site.post("/c/ioana-stoica/sterge", {"nume": "ioana stoica"})  # literele mari nu conteaza
    assert unde.endswith("/candidati?sters=1") and "șters definitiv" in corp and "Ioana" not in corp
    assert _urme(site.dosar, "ioana", "stoica") == []
    assert candidati.citeste("ioana-stoica", site.dosar) is None
    assert site.post("/c/ioana-stoica/sterge", {"nume": "Ioana Stoica"})[0] == 404
    # proiectul dat ca dosar de pe calculator e al candidatului: ramane, cu istoricul lui
    istoricul = subprocess.run(["git", "-C", site.proiect, "log", "--oneline"], capture_output=True, text=True).stdout
    assert istoricul.count("\n") == 2


def test_numele_gresit_nu_sterge_nimic(site):
    site.post("/nou", {"nume": "Ana Pop", "sursa": site.proiect})
    cod, _, corp = site.post("/c/ana-pop/sterge", {"nume": "Ana"})
    assert cod == 200 and "Numele scris nu e „Ana Pop”" in corp
    assert candidati.citeste("ana-pop", site.dosar)["dosar"].is_dir()


def test_clona_cu_fisierele_git_numai_de_citit_se_sterge_si_ea(depozit, tmp_path):
    d = depozit("privat")
    d.commit("start", {"CLAUDE.md": "reguli", "src/app.py": "x"})
    fisier = tmp_path / "privat.bundle"
    subprocess.run(["git", "-C", str(d.cale), "bundle", "create", str(fisier), "--all"], check=True, capture_output=True)
    c = candidati.citeste(candidati.nou("Ana", str(fisier), dosar=tmp_path / "c"), tmp_path / "c")
    obiecte = [f for f in (c["dosar"] / "proiect" / ".git" / "objects").rglob("*") if f.is_file()]
    assert obiecte
    for f in obiecte:
        f.chmod(0o444)
    candidati.sterge(c, "Ana")
    assert not c["dosar"].exists() and list((tmp_path / "c").rglob("*.pack")) == []
    assert not (tmp_path / "c" / candidati.SCOASE).exists() or not any((tmp_path / "c" / candidati.SCOASE).iterdir())
    assert fisier.is_file()  # fisierul primit de la candidat nu e al aplicatiei


@pytest.mark.skipif(sys.platform != "win32", reason="numai Windows tine dosarul cu un fisier deschis in el")
def test_un_fisier_deschis_opreste_stergerea_si_lasa_dosarul_intreg(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    c = candidati.citeste("ana", site.dosar)
    with open(c["dosar"] / "candidat.json", "rb"):  # ca Excel, care tine tabelul predat deschis
        cod, _, corp = site.post("/c/ana/sterge", {"nume": "Ana"})
    assert cod == 200 and "un fișier din el e deschis" in corp
    assert (c["dosar"] / "candidat.json").is_file() and candidati.citeste("ana", site.dosar)["dosar"] == c["dosar"]
    site.post("/c/ana/sterge", {"nume": "Ana"})  # inchis: merge
    assert not c["dosar"].exists()


def test_ce_a_ramas_de_la_o_stergere_oprita_se_sterge_la_pornire(tmp_path):
    from harnesscraft import interfata
    ramas = tmp_path / "c" / candidati.SCOASE / "ana-20261019"
    (ramas / "proiect").mkdir(parents=True)
    (ramas / "ghid.md").write_text("notite", encoding="utf-8")
    interfata.aplicatie(tmp_path / "c")
    assert not ramas.exists()
