"""Dosarele candidaturilor pe stare: propuse, in-analiza, finalizate (cererea autorului, 15 octombrie: „cu multi
candidati e complicat”). Fiecare test verifica si ca, dupa mutare, datele candidatului se gasesc tot la el."""
import json
import shutil
import urllib.request
from pathlib import Path

from harnesscraft import candidati
from tests.test_interfata import _proiect, site  # noqa: F401 (fixture)
from tests.test_interfata_proba import _erori, _incarca, _tabel


def _unde(site, id_):
    c = candidati.citeste(id_, site.dosar)
    return c["stare"], c["dosar"].relative_to(site.dosar).as_posix()


def test_candidatul_merge_din_propuse_in_analiza_si_in_finalizate_cu_tot_ce_are(site):
    site.post("/nou", {"nume": "Ana Pop", "sursa": site.proiect})
    assert _unde(site, "ana-pop") == ("propuse", "propuse/ana-pop")
    site.post("/c/ana-pop/fisa")  # prima analiza il scoate din „propuse”
    assert _unde(site, "ana-pop") == ("in-analiza", "in-analiza/ana-pop")
    assert not (site.dosar / "propuse" / "ana-pop").exists()
    site.post("/c/ana-pop/interviu", {"concluzia": "bun"})
    corp = site.get("/c/ana-pop/rezultat")[1]
    assert "Finalizează candidatura" in corp and "Redeschide" not in corp
    cod, unde, corp = site.post("/c/ana-pop/finalizeaza")
    assert unde.endswith("/c/ana-pop/rezultat?candidatura=finalizat") and "Redeschide" in corp
    assert corp.index("Candidatura e finalizată") < corp.index("<h2>Totalul pe treimi</h2>")
    assert _unde(site, "ana-pop") == ("finalizate", "finalizate/ana-pop")
    # dupa mutare: fisa, interviul si concluzia se citesc tot ale lui, de pe ecran
    assert "Treapta provizorie" in site.get("/c/ana-pop/fisa")[1]
    assert "bun" in candidati.ghid(candidati.citeste("ana-pop", site.dosar))
    site.post("/c/ana-pop/redeschide")
    assert _unde(site, "ana-pop") == ("in-analiza", "in-analiza/ana-pop")


def test_tabelul_predat_scoate_candidatul_din_propuse_si_ramane_descarcabil(site, tmp_path):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    assert _unde(site, "ana")[0] == "in-analiza"
    with urllib.request.urlopen(f"{site.baza}/c/ana/proba/Raspuns_ana.xlsx") as r:
        assert r.read() == (site.dosar / "in-analiza" / "ana" / "Raspuns.xlsx").read_bytes()


def test_o_clona_din_dosar_se_tine_relativ_si_nu_se_rupe_la_mutare(site):
    # un proiect dat prin link se cloneaza in dosarul candidatului: o cale intreaga s-ar rupe cand dosarul se muta
    d = site.dosar / "propuse" / "bob"
    d.mkdir(parents=True)
    shutil.copytree(site.proiect, d / "proiect")
    (d / "candidat.json").write_text(json.dumps({"nume": "Bob", "proiect": "proiect", "sursa":
                                                 "https://github.com/bob/stat-septembrie.git", "demonstrativ": False,
                                                 "creat": "2026-10-15T10:00:00"}), encoding="utf-8")
    assert candidati.citeste("bob", site.dosar)["proiect"] == (d / "proiect").as_posix()
    site.post("/c/bob/fisa")
    c = candidati.citeste("bob", site.dosar)
    assert c["stare"] == "in-analiza" and c["proiect"] == (c["dosar"] / "proiect").as_posix()
    assert candidati.fisa(c)["fisa"]["proiect"] == "stat-septembrie"  # numele din link, nu „proiect”
    assert "proiectul „stat-septembrie”" in site.get("/")[1]


def test_cautarea_gaseste_dupa_nume_sau_proiect_in_toate_starile(site):
    for nume in ("Ana Pop", "Ștefan Ionescu", "Maria Pop"):
        site.post("/nou", {"nume": nume, "sursa": site.proiect})
    site.post("/c/stefan-ionescu/fisa")
    site.post("/c/maria-pop/fisa")
    site.post("/c/maria-pop/finalizeaza")
    acasa = site.get("/")[1]  # acasa: toti cei in lucru, fara limita; finalizatii, numai in istoric
    assert "<h1>Acasă</h1>" in acasa and "Ana Pop" in acasa and "Ștefan Ionescu" in acasa and "Maria Pop" not in acasa
    assert '<h2>În lucru <span class="estompat">(2): propuse și în analiză</span></h2>' in acasa and 'href="/candidati"' in acasa
    corp = site.get("/candidati")[1]
    assert "<h1>Istoricul candidaților</h1>" in corp and "Candidații" not in corp
    assert all(f"<h2>{n} <span class=\"estompat\">(1)</span></h2>" in corp for _, n in candidati.STARI)
    pop = site.get("/?q=POP")[1]  # adresa veche a cautarii duce in istoric; literele mari nu conteaza
    assert "Ana Pop" in pop and "Maria Pop" in pop and "Ștefan Ionescu" not in pop
    assert "Ștefan Ionescu" in site.get("/candidati?q=stefan")[1]  # fara diacritice il gaseste
    assert len(candidati.lista(site.dosar, Path(site.proiect).name)) == 3  # dupa proiect: toti au acelasi
    gol = site.get("/candidati?q=nimeni")[1]
    assert "Niciun candidat cu „nimeni”" in gol and 'class="buton secundar" href="/candidati">Toate candidaturile</a>' in gol
    assert 'class="buton secundar">Caută</button>' in gol  # acelasi fel de buton, unul langa altul


def test_reanalizarea_aduce_in_ghid_scorul_fisei_noi_si_pastreaza_raspunsurile(depozit, tmp_path):
    from harnesscraft import interviu
    d = depozit("proiect")
    d.commit("start", {"CLAUDE.md": "# Reguli\n", "src/app.py": "x"})
    c = candidati.citeste(candidati.nou("Ana", str(d.cale), dosar=tmp_path / "c"), tmp_path / "c")
    candidati.analizeaza(c)
    candidati.salveaza_interviu(c, {"S1.1": "da", "S1.2": "da", "S1.3": "nu", "nota-S1": "un scop clar"})
    vechi, scor_vechi = candidati.ghid(c), candidati.fisa(c)["fisa"]["total"]
    # proiectul creste: teste, licenta, reguli cu comenzi; fisa noua are alt scor
    from tests.test_fisa import INSTR
    d.commit("feat: teste", {"CLAUDE.md": INSTR, "LICENSE": "MIT License\n", "tests/test_app.py": "def test_x(): pass"})
    candidati.analizeaza(c)
    f = candidati.fisa(c)["fisa"]
    assert f["total"] != scor_vechi
    g = candidati.ghid(c)
    assert f"<!-- fisa {f['total']:g} din {f['maxim']:g} -->" in g
    assert f"Punctajul proiectului: {interviu._cifra(f['total'])} din" in g
    # raspunsurile raman; totalul se face din scorul fisei noi
    assert interviu.scor(g)["standard"]["S1"] == interviu.scor(vechi)["standard"]["S1"] == 3 and "un scop clar" in g
    assert interviu.scor(g)["total"]["puncte"]["portofoliul"] == round(f["total"] / f["maxim"] * 100 / 3, 1)
    copii = list(c["dosar"].glob("ghid.inainte-de-reanalizare-*.md"))
    assert len(copii) == 1 and copii[0].read_text(encoding="utf-8") == vechi
    # o reanalizare fara schimbari nu mai face copii
    candidati.analizeaza(c)
    assert len(list(c["dosar"].glob("ghid.inainte-de-reanalizare-*.md"))) == 1
