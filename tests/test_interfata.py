"""Interfata: formularul scrie ghidul pe care `interviu-scor` il citeste ca pe unul scris de mana; contractul HTTP al
fiecarui buton, cu un server adevarat pe un port liber; nimic nu iese de pe calculator."""
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

import pytest

from harnesscraft import candidati, formular, interviu, md, tintite
from tests.test_fisa import INSTR
from tests.test_interviu import _bifeaza



def _proiect(depozit):
    d = depozit("proiect")
    d.commit("start", {"CLAUDE.md": INSTR, "README.md": "# Proiect\nCe face.", "src/app.py": "x"})
    d.commit("fix: reparatie", {"src/app.py": "y"})
    return d.cale


# ── formularul ──

def test_formularul_scrie_ce_ar_scrie_recrutorul_de_mana(depozit, tmp_path):
    c = candidati.citeste(candidati.nou("Ana Pop", str(_proiect(depozit)), dosar=tmp_path / "c"), tmp_path / "c")
    candidati.analizeaza(c)
    g = candidati.ghid(c)
    de_mana = _bifeaza(g, {"S1": "da nu da", "S4": "nu nu nu"})
    din_formular = formular.scrie(g, {"S1.1": "da", "S1.2": "nu", "S1.3": "da", "S4.1": "nu", "S4.2": "nu", "S4.3": "nu"})
    assert din_formular == de_mana and interviu.scor(din_formular) == interviu.scor(de_mana)


def test_formularul_notele_si_concluzia_pe_un_rand_fara_sa_atinga_bifele(depozit, tmp_path):
    c = candidati.citeste(candidati.nou("Ana", str(_proiect(depozit)), dosar=tmp_path / "c"), tmp_path / "c")
    candidati.analizeaza(c)
    g = formular.scrie(candidati.ghid(c), {"nota-S2": "a lămurit\nîntâi", "nota-parcurs": "inginer", "L1": "De ce?",
                                            "concluzia": "de discutat"})
    v = formular.valori(g)
    assert (v["nota-S2"], v["nota-parcurs"], v["L1"], v["concluzia"]) == ("a lămurit întâi", "inginer", "De ce?",
                                                                         "de discutat")
    assert interviu.citeste(g) == interviu.citeste(candidati.ghid(c))


def test_formularul_refuza_campuri_straine_si_valori_altele_decat_da_nu(depozit, tmp_path):
    c = candidati.citeste(candidati.nou("Ana", str(_proiect(depozit)), dosar=tmp_path / "c"), tmp_path / "c")
    candidati.analizeaza(c)
    with pytest.raises(ValueError, match="nu sunt în ghid"):
        formular.scrie(candidati.ghid(c), {"S9.1": "da"})
    with pytest.raises(ValueError, match="nu e „da” sau „nu”"):
        formular.scrie(candidati.ghid(c), {"S1.1": "poate"})


def test_markdown_escapeaza_textul_proiectului():
    assert "<script>" not in md.html_din("# Titlu <script>x</script>\n- **gros** `cod`")
    assert "<strong>gros</strong>" in md.html_din("- **gros**")


def test_cifrele_interfetei_in_scrierea_romaneasca():
    from harnesscraft.interfata import nr
    assert (nr(0.05, ".2f"), nr(60000, ","), nr(13.3), nr(16), nr(1234.5, ",.2f")) ==         ("0,05", "60.000", "13,3", "16", "1.234,50")


def test_drumul_in_paralel_iese_ca_zi_dupa_zi(depozit):
    from harnesscraft import istoric, pasi
    from harnesscraft.fisa import fisa
    from harnesscraft.harness import harness
    from harnesscraft.stare import stare
    d = depozit("proiect")
    d.commit("start", {"CLAUDE.md": INSTR, "README.md": "# Proiect", "src/app.py": "x"})
    for i in range(4):  # o zi pe commit
        d.commit(f"docs: pasul {i}", {f"docs/p{i}.md": "x"})
    p = d.cale
    commits = istoric.citeste(p)
    serial = [fisa(p, stare(p, commits[:i + 1], c.sha), harness(p, c.sha))["total"] for i, c in enumerate(commits)]
    drum = pasi.drumul(p, commits)
    assert [z["ziua"] for z in drum] == sorted(z["ziua"] for z in drum) and [z["total"] for z in drum] == serial


# ── candidatii ──

def test_candidat_nou_refuza_dosar_fara_git_si_dosar_inexistent(tmp_path):
    (tmp_path / "gol").mkdir()
    with pytest.raises(ValueError, match="nu are istoric git"):
        candidati.nou("Ana", str(tmp_path / "gol"), dosar=tmp_path / "c")
    with pytest.raises(ValueError, match="nu există"):
        candidati.nou("Ana", str(tmp_path / "nu-e"), dosar=tmp_path / "c")
    assert not (tmp_path / "c").exists() or not any((tmp_path / "c").iterdir())


def test_acelasi_nume_doi_candidati(depozit, tmp_path):
    p = str(_proiect(depozit))
    assert [candidati.nou("Ana Pop", p, dosar=tmp_path), candidati.nou("Ana Pop", p, dosar=tmp_path)] == \
        ["ana-pop", "ana-pop-2"]


def test_reanaliza_nu_sterge_raspunsurile(depozit, tmp_path):
    c = candidati.citeste(candidati.nou("Ana", str(_proiect(depozit)), dosar=tmp_path), tmp_path)
    candidati.analizeaza(c)
    candidati.salveaza_interviu(c, {"S1.1": "da"})
    candidati.analizeaza(c)
    assert formular.valori(candidati.ghid(c))["S1.1"] == "da"


# ── serverul ──

@pytest.fixture
def site(depozit, tmp_path):
    from harnesscraft import interfata
    s = interfata.server(port=0, dosar=tmp_path / "c")
    threading.Thread(target=s.serve_forever, daemon=True).start()
    baza = f"http://127.0.0.1:{s.server_port}"

    class Site:
        def get(self, cale):
            with urllib.request.urlopen(baza + cale) as r:
                return r.status, r.read().decode("utf-8")

        def post(self, cale, date=None, antete=None):
            cerere = urllib.request.Request(baza + cale, urlencode(date or {}).encode(), antete or {})
            try:
                with urllib.request.urlopen(cerere) as r:
                    return r.status, r.geturl(), r.read().decode("utf-8")
            except urllib.error.HTTPError as ex:
                return ex.code, None, ex.read().decode("utf-8")

        def accepta_proba(self, id_):
            """Decizia „da” si acordul candidatului, scrise direct: testele probei nu trec prin interviu. Drumul
            adevarat (interviul, decizia, invitatia, acordul): tests/test_decizia_probei.py."""
            (self.de(id_) / candidati.DECIZIA).write_text(json.dumps(
                {"decizia": "da", "motivul": "", "ora": "2026-10-15T10:00:00",
                 "acordul": {"raspuns": "da", "data": "2026-10-15", "cum": "pe e-mail", "ora": "2026-10-15T10:00:00"}}),
                encoding="utf-8")

        def de(self, id_):
            """Dosarul candidatului, oriunde l-a mutat starea (propuse, in-analiza, finalizate)."""
            return candidati.citeste(id_, tmp_path / "c")["dosar"]

    site = Site()
    site.proiect = str(_proiect(depozit))
    site.dosar = tmp_path / "c"
    site.baza = baza
    yield site
    s.shutdown()


def test_patru_pasi_si_fereastra_cum_folosesc_pe_fiecare_ecran(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    for pas in ("fisa", "interviu", "proba", "rezultat"):
        corp = site.get(f"/c/ana/{pas}")[1]
        assert f'popovertarget="ajutor-{pas}"' in corp and 'class="ajutor"' not in corp and "Tot manualul" in corp
    assert corp.count('class="pas') == 4 and "Întrebările despre proiect</a>" not in corp
    assert site.get("/c/ana/intrebari")[0] == 200  # legatura veche duce la interviu
    assert 'popovertarget="ajutor-nou"' in site.get("/nou")[1]


def test_raportul_pentru_dosar_are_tot_ce_ramane_la_dosar(site):
    site.post("/nou", {"nume": "Ana Pop", "sursa": site.proiect})
    site.post("/c/ana-pop/fisa")
    site.post("/c/ana-pop/interviu", {"S1.1": "da", "S1.2": "da", "S1.3": "nu", "nota-S1": "un scop clar",
                                      "nota-T1": "a explicat regula", "L1": "Ce ați automatiza?", "nota-L1": "rapoartele",
                                      "concluzia": "de chemat la a doua discuție"}, {"X-Autosalvare": "1"})
    corp = site.get("/c/ana-pop/rezultat")[1]
    assert 'href="/rapoarte?id=ana-pop"' in corp
    corp = site.get("/c/ana-pop/raport")[1]
    assert "Raport de evaluare" in corp and "Ana Pop" in corp and "Evaluatorul" in corp and "window.print()" in corp
    # 7 note la interviu, 4 + 3 bife la proba
    assert corp.count('class="r-nota"') == 7 + 7 and "un scop clar" in corp and "incomplet: lipsește proba" in corp
    assert "a explicat regula" in corp and "Ce ați automatiza?" in corp and "rapoartele" in corp
    assert "de chemat la a doua discuție" in corp and "decizia o iau oamenii care îl citesc" in corp
    assert "Ce nu arată" not in corp and "Proiectul</th><td>„" in corp
    # bara laterala ramane pe ecran (acasa, alt candidat); la tipar o ascunde stilul
    assert 'class="bara"' in corp and 'body class="raport"' in corp
    assert "body.raport .bara { display: none; }" in site.get("/static/stil.css")[1]


def test_ruta_de_viata_si_paginile_fara_candidat(site):
    assert site.get("/viata") == (200, "viu")
    assert "Adaugă primul candidat" in site.get("/candidati")[1] and "Candidat nou" in site.get("/")[1]
    manual = site.get("/manual")[1]
    assert "alege programul din ce lipsește în fișa proiectului de portofoliu" in manual and "Formulează" not in manual
    assert site.get("/static/stil.css")[0] == 200


def test_drumul_unui_candidat_cap_coada(site):
    cod, unde, corp = site.post("/nou", {"nume": "Ana Pop", "sursa": site.proiect})
    assert unde.endswith("/c/ana-pop/fisa") and "Analizează proiectul de portofoliu" in corp
    cod, unde, corp = site.post("/c/ana-pop/fisa")
    assert "Treapta provizorie" in corp and "Drumul, zi cu zi" in corp
    corp = site.get("/c/ana-pop/interviu")[1]  # intrebarile despre proiect sunt deja in partea IV
    g = candidati.ghid(candidati.citeste("ana-pop", site.dosar))
    assert tintite.din_ghid(g) and "Ce afli:" in corp
    cod, unde, corp = site.post("/c/ana-pop/interviu", {"S1.1": "da", "S1.2": "da", "S1.3": "nu", "nota-S1": "clar"},
                                {"X-Autosalvare": "1"})
    assert json.loads(corp) == {"salvat": True}
    corp = site.get("/c/ana-pop/rezultat")[1]  # se calculeaza singur, fara buton
    assert "Incomplet." in corp and "proba" in corp and "<td>1</td><td>motivația</td><td>3</td>" in corp
    assert "necalibrat, incomplet: lipsește proba" in corp  # langa cifra totalului, nu numai in cutia de sub ea
    assert "media celor 1 întrebări puse (din 7)" in corp and "<td>7</td>" in corp and "<td>8</td>" not in corp
    assert "Concluzia ta" in corp


def test_interviul_fara_cheile_ghidului_si_salvarea_spune_ora(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    corp = site.get("/c/ana/interviu")[1]
    assert '<span class="id">' not in corp and "<h4>S1." not in corp and "<h4>1. " in corp
    assert "Ce a răspuns" in corp and ">Întrebarea ta 1<" in corp and 'name="L1.1"' not in corp
    assert "apeși „da” sau „nu”" in corp and "<code>[da]</code>" not in corp
    # instructiunile stau in fereastra „Cum folosesc”, inaintea formularului, nu pe ecran intre intrebari
    assert corp.index('popover class="fereastra"') < corp.index("Cum se completează") < corp.index('class="interviu"')
    cod, unde, corp = site.post("/c/ana/interviu", {"S1.1": "da"})  # butonul, fara JavaScript
    assert "?salvat=" in unde and "Salvat la " in corp


def test_bifa_pe_jumatate_se_spune_la_rezultat(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    site.post("/c/ana/interviu", {"S2.1": "da"})
    corp = site.get("/c/ana/rezultat")[1]
    assert "Nu s-a putut." in corp and "S2: completată pe jumătate" in corp and "/c/ana/raport" not in corp


def test_pasii_blocati_fara_fisa_si_proiect_fara_git_refuzat(site, tmp_path):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    corp = site.get("/c/ana/interviu")[1]
    assert "Întâi portofoliul (pasul 1)." in corp
    assert site.post("/c/ana/interviu", {"S1.1": "da"})[1].endswith("/c/ana/fisa")
    (tmp_path / "fara-git").mkdir()
    cod, unde, corp = site.post("/nou", {"nume": "Ion", "sursa": str(tmp_path / "fara-git")})
    assert "nu are istoric git" in corp


def test_post_din_alta_pagina_refuzat(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    cod, _, _ = site.post("/c/ana/fisa", antete={"Origin": "https://alt-site.ro"})
    assert cod == 403


def test_candidat_inexistent_si_cale_straina(site):
    assert pytest.raises(urllib.error.HTTPError, site.get, "/c/nimeni/fisa").value.code == 404
    assert pytest.raises(urllib.error.HTTPError, site.get, "/static/../interfata.py").value.code == 404


def test_rezultatul_urmeaza_interviul_fara_buton_de_recalculat(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    site.post("/c/ana/interviu", {"S1.1": "da", "S1.2": "da", "S1.3": "da"}, {"X-Autosalvare": "1"})
    corp = site.get("/c/ana/rezultat")[1]
    assert "<td>1</td><td>motivația</td><td>4</td>" in corp and "Recalculează" not in corp
    # a doua zi recrutorul schimba o bifa: rezultatul o arata la urmatoarea deschidere
    site.post("/c/ana/interviu", {"S1.3": "nu"}, {"X-Autosalvare": "1"})
    assert "<td>1</td><td>motivația</td><td>3</td>" in site.get("/c/ana/rezultat")[1]
    assert site.post("/c/ana/rezultat")[0] == 404  # nu mai e nimic de apasat
    assert not (site.de("ana") / "rezultat.json").exists()


def test_numele_proiectului_in_ghilimele_si_partile_interviului_cu_cifre_romane(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    nume = Path(site.proiect).name
    assert f"proiectul „{nume}”" in site.get("/")[1] and f"proiectul „{nume}”" in site.get("/c/ana/fisa")[1]
    g = site.de("ana") / "ghid.md"
    g.write_text(g.read_text(encoding="utf-8").replace("## I. ", "## 1. ").replace("## II. ", "## 2. "),
                 encoding="utf-8")  # un ghid scris inainte de cifrele romane
    corp = site.get("/c/ana/interviu")[1]
    assert ">I. Deschiderea<" in corp and ">II. Parcursul" in corp and ">IV. Întrebările fără notă" in corp
    assert ">2. Parcursul" not in corp and "<h4>1. " in corp  # intrebarile raman cu cifre arabe
    site.post("/c/ana/interviu", {"nota-parcurs": "inginer"}, {"X-Autosalvare": "1"})
    assert formular.valori(g.read_text(encoding="utf-8"))["nota-parcurs"] == "inginer"


def test_drumul_pe_treapta_de_sus_spune_ca_nu_lipseste_nimic(site):
    from harnesscraft import interfata
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    f = site.de("ana") / "fisa.json"
    date = json.loads(f.read_text(encoding="utf-8"))
    date["drumul"][-1]["lipseste"] = []
    f.write_text(json.dumps(date), encoding="utf-8")
    corp = site.get("/c/ana/fisa")[1]
    assert interfata._VARF in corp and "<td>—</td></tr>" not in corp


def test_bara_laterala_ramane_pe_loc_la_derulare(site):
    css = site.get("/static/stil.css")[1]
    # cu body fixat la inaltimea ferestrei, bara sticky urca odata cu el
    assert "html, body { margin: 0; }" in css and "min-height: 100vh" in css and "position: sticky; top: 0" in css


def test_fisa_pe_ecran_si_in_raport_e_cea_pentru_recrutor_iar_terminalul_primeste_redarea_tehnica(site):
    import re
    from harnesscraft import fisa
    import html
    from harnesscraft import interfata, termeni
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    fi = json.loads((site.de("ana") / "fisa.json").read_text(encoding="utf-8"))["fisa"]
    corp = site.get("/c/ana/fisa")[1]
    assert md.html_din(fisa.pentru_recrutor(fi)) in corp and "Ce afli numai la interviu" in corp
    assert all(f"{i + 1}. {n[0].upper() + n[1:]}" in corp for i, n in enumerate(fisa.NUME_TREPTE))
    def text(h):
        # datele candidatului (calea si numele proiectului) nu sunt textul nostru: un proiect se poate numi oricum
        t = html.unescape(re.sub(r"<[^>]+>", " ", h.split("<main", 1)[-1]))
        return t.replace(fi["proiect"], "").replace(site.proiect, "")
    assert termeni.neexplicate(text(corp)) == []
    raport = site.get("/c/ana/raport")[1]
    assert fisa.TREPTE_RECRUTOR[fi["nivel"]] in raport and fisa.ARII_RECRUTOR["responsabilitatea"] in raport
    assert termeni.neexplicate(text(raport)) == []
    manual = site.get("/manual")[1]
    assert termeni.neexplicate(text(manual)) == []
    assert all(termeni.neexplicate(a + " " + " ".join(p)) == [] for a, p in interfata.AJUTOR.values())
    assert "<h2>Treptele</h2>" in manual and all(t in manual for t in fisa.TREPTE_RECRUTOR)
    c = candidati.citeste("ana", site.dosar)
    assert candidati.fisa_md(c) == fisa.randare(fi)


def test_fisa_veche_fara_dovezi_ca_date_cere_reanalizarea(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.post("/c/ana/fisa")
    f = site.de("ana") / "fisa.json"
    date = json.loads(f.read_text(encoding="utf-8"))
    for x in date["fisa"]["principii"].values():
        del x["fapte"]
    f.write_text(json.dumps(date), encoding="utf-8")
    corp = site.get("/c/ana/fisa")[1]
    assert "versiune mai veche" in corp and "Analizează din nou" in corp


def test_pasul_1_e_portofoliul_iar_fisa_si_butonul_spun_al_cui_proiect(site):
    # proba (pasul 3) va avea si ea un proiect analizat: „fișa” si „Analizează proiectul” fara precizare s-ar confunda
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    corp = site.get("/c/ana/fisa")[1]
    assert "<h1>1. Portofoliul</h1>" in corp and "Analizează proiectul de portofoliu" in corp
    site.post("/c/ana/fisa")
    corp = site.get("/c/ana/fisa")[1]
    assert "Fișa proiectului de portofoliu" in corp and "Analizează din nou proiectul de portofoliu" in corp
    assert "</span>Portofoliul</a>" in site.get("/c/ana/interviu")[1]  # bara laterala
    manual = site.get("/manual")[1]
    assert "<h3>1. Portofoliul</h3>" in manual and "<h3>1. Fișa</h3>" not in manual
    for text in (corp, manual):
        assert "Analizează proiectul”" not in text and "<b>Analizează proiectul</b>" not in text
