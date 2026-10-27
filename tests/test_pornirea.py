"""Pornirea: o pornire noua inchide ce a ramas de la cele vechi (serverul, fereastra lui, taburile), dar nu pe ea
insasi si nici ce doar pomeneste programul (cerut de autor)."""
import re
from pathlib import Path

from harnesscraft import interfata

BAT = r'C:\Windows\system32\cmd.exe /c ""C:\HarnessCraft\Porneste_HarnessCraft.bat" "'
SRV = '".venv\\Scripts\\python.exe"  -m harnesscraft.interfata'


def test_pornirea_inchide_serverele_si_ferestrele_vechi_dar_nu_pe_ea_insasi():
    procese = [
        (100, 1, "cmd.exe", BAT), (101, 100, "python.exe", SRV), (102, 101, "python.exe", SRV),  # pornirea veche
        (110, 1, "cmd.exe", BAT),                                    # fereastra unei porniri cazute, ramasa la „pause”
        (200, 1, "cmd.exe", BAT), (201, 200, "python.exe", SRV), (202, 201, "python.exe", SRV),  # eu, cu stramosii
        (300, 1, "bash.exe", "bash -c Start-Process Porneste_HarnessCraft.bat"),  # doar pomeneste fisierul
        (301, 1, "python.exe", "python -m pytest"),
    ]
    assert interfata.de_oprit(procese, 202) == [100, 101, 102, 110]
    assert interfata.de_oprit(procese, 102) == [110, 200, 201, 202]


def test_taburile_inchise_sunt_numai_ale_paginilor_programului():
    ps1 = (Path(interfata.__file__).parent / "inchide_taburi.ps1").read_text(encoding="utf-8")
    tipar = re.compile(re.search(r"-match '([^']+)'", ps1).group(1))
    titlu = re.search(r"<title>(.*?)</title>", interfata.pagina("Candidați", "")).group(1)
    assert titlu == "Candidați — HarnessCraft" and tipar.search(titlu)
    assert tipar.search("Rezultatul - HarnessCraft - Memory usage - 37.2 MB")
    for altul in ("GitHub - mihaistreanga/HarnessCraft: privat", "HarnessCraft-portofoliu-GitHub.md - Visual Studio Code",
                  "Conversațiile SkyRoll, de citit"):
        assert not tipar.search(altul), altul


def test_taburile_se_inchid_numai_in_browsere_nu_in_vs_code():
    ps1 = (Path(interfata.__file__).parent / "inchide_taburi.ps1").read_text(encoding="utf-8")
    # VS Code are aceeasi clasa de fereastra ca Chrome; un tab al lui nu se inchide
    assert '-notin @("chrome", "msedge")' in ps1 and ps1.index("-notin") < ps1.index("Invoke()")


def test_al_doilea_server_nu_poate_lua_un_port_ocupat():
    # pe Windows, SO_REUSEADDR lasa doua servere pe acelasi port; cererile ajungeau la cel vechi
    import pytest
    s = interfata.server(port=0)
    try:
        with pytest.raises(OSError):
            interfata.server(port=s.server_address[1])
    finally:
        s.server_close()


def test_tabul_nou_se_deschide_inainte_sa_se_inchida_cele_vechi():
    # inchise intai, fereastra ramanea goala, iar Chrome isi refacea sesiunea: doua „Acasa” (observat de autor)
    ps1 = (Path(interfata.__file__).parent / "inchide_taburi.ps1").read_text(encoding="utf-8")
    assert ps1.index('"pregatit"') < ps1.index("$nou = @(Taburi") < ps1.index("Invoke()")
    deschise = []
    if interfata.os.name != "nt":
        assert interfata.deschide_in_browser("http://x", deschise.append) == 0 and deschise == ["http://x"]


def test_pornirea_nu_inchide_copiii_serverului_vechi_cum_e_browserul():
    # Chrome pornit de un server vechi e copilul lui; „taskkill /T” inchidea tot browserul autorului
    import inspect
    sursa = inspect.getsource(interfata.opreste_vechi)
    assert '"taskkill", "/F", "/PID"' in sursa and '"/T"' not in sursa
    procese = [(100, 1, "cmd.exe", BAT), (101, 100, "python.exe", SRV), (102, 101, "python.exe", SRV),
               (103, 102, "chrome.exe", "chrome.exe http://127.0.0.1:8765"), (200, 1, "python.exe", "eu")]
    assert interfata.de_oprit(procese, 200) == [100, 101, 102]  # browserul nu e in lista


def test_fereastra_serverului_porneste_micsorata_si_un_motiv_de_oprire_se_vede_pe_ecran(capsys):
    # cerut de autor: fereastra serverului jos, in bara; ce n-o lasa sa porneasca nu ramane ascuns in ea
    bat = (Path(interfata.__file__).parent.parent / "Porneste_HarnessCraft.bat").read_text(encoding="utf-8")
    assert 'start "HarnessCraft - server" /min "%~f0" min' in bat
    # .venv lipsa se spune in fereastra intreaga, inaintea micsorarii; serverul porneste in cea micsorata
    assert bat.index('python.exe" (') < bat.index("/min") < bat.index("-m harnesscraft.interfata")
    vazute = []
    assert interfata.nu_porneste("lipsește git", caseta=vazute.append) == 1
    assert vazute == ["lipsește git"] and "lipsește git" in capsys.readouterr().out


def test_fara_gitleaks_programul_nu_porneste_si_spune_de_ce(monkeypatch):
    # ca la git lipsa: o caseta cu motivul, inainte sa inchida ceva sau sa porneasca serverul
    monkeypatch.setattr(interfata.shutil, "which", lambda p: None if p == "gitleaks" else "C:/unelte/" + p)
    motive = []
    monkeypatch.setattr(interfata, "nu_porneste", lambda text: motive.append(text) or 1)
    monkeypatch.setattr(interfata, "opreste_vechi", lambda: (_ for _ in ()).throw(AssertionError("a inchis")))
    assert interfata.main() == 1
    assert len(motive) == 1 and "caută cheile de acces în proiecte (gitleaks)" in motive[0]


def test_fara_gitleaks_analiza_spune_motivul_nu_cade(monkeypatch, tmp_path):
    from harnesscraft import stare
    monkeypatch.setenv("PATH", str(tmp_path))  # niciun gitleaks pe drum
    try:
        stare._gitleaks("dir", str(tmp_path))
    except RuntimeError as ex:  # prinsa de ecranul portofoliului si spusa acolo
        assert str(ex) == stare.GITLEAKS_LIPSA
    else:
        raise AssertionError("fara gitleaks, analiza a mers")
