"""Aspectul, in tot proiectul (observatia 26 a autorului): un singur fel de buton pe rol, actiunile ca butoane,
niciun control al browserului lasat ca atare, marginile aliniate, „pasul urmator” la sfarsit. Testele prind
markupul si stilul; ce se vede cu ochii s-a verificat pe capturi (rapoarte/observatii-autor-interfata.md)."""
import re

from tests.test_interfata import site  # noqa: F401 (fixture)


def _ecranele(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    site.post("/c/ana/fisa")
    return {p: site.get(p)[1] for p in ("/", "/candidati", "/candidati?q=zzz", "/nou", "/manual", "/c/ana/fisa", "/c/ana/interviu",
                                        "/c/ana/proba", "/c/ana/rezultat", "/c/ana/raport")}


def test_fiecare_buton_e_de_un_fel_si_fiecare_actiune_e_buton(site):
    for cale, corp in _ecranele(site).items():
        for b in re.findall(r"<button[^>]*>", corp):
            assert re.search(r'class="(buton( lat)?|buton secundar( lat)?|buton secundar buton-info|inchide)"', b), (cale, b)
        for a in re.findall(r"<a [^>]*\bdownload\b[^>]*>", corp):  # o descarcare e o actiune: buton, nu legatura
            assert re.search(r'class="buton secundar( lat)?"', a), (cale, a)
        # semnul ℹ nu e in fontul paginii; selectorul de fisier al browserului vorbeste limba browserului
        assert "ℹ" not in corp, cale
        assert all("alege-fisier" in corp[max(0, corp.find(i) - 80):corp.find(i)]
                   for i in re.findall(r'<input type="file"[^>]*>', corp)), cale
    ecrane = _ecranele(site)
    assert 'Alege fișierul</label><button class="buton lat">Încarcă tabelul de răspuns</button>' in ecrane["/c/ana/proba"]
    assert 'class="buton secundar" href="/c/ana/rezultat">← Înapoi la rezultat' in ecrane["/c/ana/raport"]
    # la sfarsitul paginii Acasa, secundar nu se distingea: plin, ca „Candidat nou” (autorul)
    assert '<a class="buton" href="/candidati">Vezi toți candidații</a>' in ecrane["/"]


def test_fereastra_cum_folosesc_poarta_numele_ecranului(site):
    ecrane = _ecranele(site)
    assert "<h2>Cum folosesc: Candidat nou</h2>" in ecrane["/nou"]
    for p, nume in (("fisa", "Portofoliul"), ("interviu", "Interviul"), ("proba", "Proba"), ("rezultat", "Rezultatul")):
        assert f"<h2>Cum folosesc: {nume}</h2>" in ecrane[f"/c/ana/{p}"]


def test_pasul_urmator_sta_la_sfarsit_si_nivelul_se_spune_o_data(site):
    corp = _ecranele(site)["/c/ana/rezultat"]
    assert corp.index("<h2>Candidatura</h2>") < corp.index('class="urmator"')
    assert "(provizoriu)</b>" not in corp


def test_stilul_aliniaza_marginile_si_tine_datele_scurte_pe_un_rand(site):
    css = site.get("/static/stil.css")[1]
    assert ".formular .buton { justify-self: start; }" in css  # un buton e cat textul lui
    assert re.search(r"\.cautare \{[^}]*\}", css) and "max-width" not in re.search(r"\.cautare \{[^}]*\}", css)[0]
    assert ".cifre { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));" in css
    assert "table.drumul td:not(:last-child) { white-space: nowrap; }" in css
    assert "table.note th:last-child, table.note td:last-child { width: 8rem; text-align: center; }" in css
    assert "background" not in re.search(r"\.sectiune \{[^}]*\}", css)[0]  # numele nu arata ca pasul activ
    assert "body.raport main { max-width: 56rem; margin: 0 auto;" in css
    assert ".rand-titlu { gap: 1rem; margin-bottom: 1rem; } .rand-titlu h1 { margin: 0; }" in css
    assert "html { scrollbar-gutter: stable; }" in css  # marginea dreapta, aceeasi pe pagini scurte si lungi


def test_mai_putin_pe_ecran_deodata_dovezile_si_partile_se_deschid_la_un_clic(site):
    ecrane = _ecranele(site)
    fisa = ecrane["/c/ana/fisa"]
    assert '<details class="pliat"><summary>Vezi dovezile' in fisa and "<summary>Drumul, zi cu zi:" in fisa
    assert fisa.index("<h3>Ce afli numai la interviu</h3>") < fisa.index("<summary>Vezi dovezile")  # ramane sus
    assert "Își verifică munca</span>" in fisa  # ariile, ca cifre, deasupra
    interviu = ecrane["/c/ana/interviu"]
    deschise = re.findall(r'<details class="pliat parte-ghid"( open)?><summary>([IV]+)\.', interviu)
    assert [p for d, p in deschise if d] == ["III", "V"] and {"I", "II", "IV"} <= {p for d, p in deschise if not d}
    proba = ecrane["/c/ana/proba"]
    assert proba.count('<p class="estompat">') <= 3  # erau 6 paragrafe gri, plus explicatiile de langa butoane
    assert "body.raport th { background: none;" in site.get("/static/stil.css")[1]


def test_conversatiile_si_programul_predate_raman_si_se_deschid_pe_ecran_si_in_raport(site):
    _ecranele(site)
    link = "https://claude.ai/share/abc-123"
    site.post("/c/ana/proba", {"linkuri": f"{link}\nnu e link"}, {"X-Autosalvare": "1"})
    proba = site.get("/c/ana/proba")[1]
    assert f'<li><a href="{link}" target="_blank" rel="noopener noreferrer">{link}</a></li>' in proba
    assert "<h3>Cum a gândit: conversațiile cu AI-ul</h3>" in proba and "<h3>Ce a făcut: programul</h3>" in proba
    raport = site.get("/c/ana/raport")[1]
    assert f'<th>Conversațiile predate</th><td><a href="{link}">{link}</a> nu e link</td>' in raport


def test_clasele_noi_nu_se_bat_cu_cele_vechi_din_stil(site):
    # „parte” era a barelor de la totalul pe treimi (o grila cu trei coloane): partile interviului se rupeau pe cuvinte
    css = site.get("/static/stil.css")[1]
    assert ".parte-ghid" not in css or "grid-template-columns" not in re.search(r"\.parte-ghid[^{]*\{[^}]*\}", css)[0]
    assert '<details class="pliat parte-ghid"' in _ecranele(site)["/c/ana/interviu"]


def test_manualul_spune_cum_e_facut_si_ce_reguli_respecta(site):
    # cerut de autor: „acolo oamenii deschid si vreau sa vada”, chiar daca e scris si in alt loc
    manual = site.get("/manual")[1]
    sectiune = manual.split("<h2>Cum e făcut și ce reguli respectă</h2>", 1)[1].split("<h2>", 1)[0]
    for x in ("Claude Code", "Programul nu folosește AI", "2024/1689", "anexa III, punctul 4", "considerentul 12",
              "2016/679", "articolul 22", "decizia de angajare o iau oamenii", "nu un aviz juridic"):
        assert x in sectiune, x
    assert manual.index("Cum e făcut și ce reguli respectă") < manual.index("Pornirea și oprirea")  # se vede primul


def test_raportul_pe_scurt_are_esentialul_fara_notite(site):
    from tests.test_interviu import _bifeaza  # noqa: F401
    _ecranele(site)
    site.post("/c/ana/interviu", {"S1.1": "da", "S1.2": "da", "S1.3": "da", "nota-S1": "NOTITA LUNGA", "concluzia": "de chemat"},
              {"X-Autosalvare": "1"})
    scurt = site.get("/c/ana/rezumat")[1]
    assert "Raport de evaluare, pe scurt" in scurt and "de chemat" in scurt and "<th>Totalul</th>" in scurt
    assert "NOTITA LUNGA" not in scurt and "Discuția, fără notă" not in scurt  # notitele raman in raportul intreg
    assert "NOTITA LUNGA" in site.get("/c/ana/raport")[1]
    assert 'href="/c/ana/rezumat">Raportul pe scurt</a>' in site.get("/c/ana/raport")[1]


def test_textele_de_citit_sunt_aliniate_ca_un_document(site):
    css = site.get("/static/stil.css")[1]
    assert "text-align: justify; hyphens: auto;" in css and "text-indent: 1.5em;" in css
    assert '<body class="document">' in site.get("/manual")[1]


def test_casetele_de_stare_sunt_doua_si_fiecare_la_locul_ei(site):
    """Regula din DECIZII_INCHISE (B29, 660cabe; B6, 88a6d30): galbena („avert”), cand lipseste ceva sau nu se poate
    schimba; cu chenar, simpla, pentru o stare hotarata; rosie numai pentru eroare. A treia caseta nu trece."""
    from pathlib import Path
    sursa = Path("harnesscraft/interfata.py").read_text(encoding="utf-8")
    assert set(re.findall(r'class="(cutie[^"]*)"', sursa)) == {"cutie", "cutie avert", "cutie eroare",
                                                                "cutie avert nota-exemplu"}
    stil = Path("harnesscraft/static/stil.css").read_text(encoding="utf-8")
    assert set(re.findall(r"^\.cutie[\w.]*", stil, re.M)) == {".cutie", ".cutie.eroare", ".cutie.avert"}
    from tests.test_decizii_660cabe import _refuzata
    _refuzata(site)
    assert '<div class="cutie"><strong>Fără probă: candidatul a refuzat-o' in site.get("/c/ana/proba")[1]
    rez = site.get("/c/ana/rezultat")[1]
    assert '<div class="cutie avert"><strong>Totalul e incomplet: fără probă.</strong></div>' in rez  # lipseste ceva
    site.post("/c/ana/finalizeaza")
    assert '<div class="cutie">Candidatura e finalizată' in site.get("/c/ana/rezultat?candidatura=finalizat")[1]
    site.post("/nou", {"nume": "Bogdan", "fara_cod": "1", "motiv_fara_cod": "lucrează numai în chat"})
    assert re.search(r'<div class="cutie"><strong>Fără proiect cu cod\.</strong>', site.get("/c/bogdan/fisa")[1])
