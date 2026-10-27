"""Pasul 3 din interfata, proba: tema se descarca (cheia nu), tabelul predat se incarca si se potriveste cu cheia,
bifele se salveaza in proba.md, iar nota probei ajunge in rezultat si in raport."""
import json
import re
import urllib.error
import urllib.request

import pytest

from harnesscraft import candidati, proba, proba_stat, termeni, xlsx
from tests.test_interfata import site  # noqa: F401 (fixture)

PA = proba.pachet()
CH = PA.cheia()


def _tabel(tmp_path, randuri, nume="Raspuns.xlsx"):
    cale = tmp_path / nume
    xlsx.scrie(cale, [PA.raspuns_cap] + randuri)
    return cale.read_bytes()


def _incarca(site, id_, octeti, nume="Raspuns.xlsx"):
    granita = "----harnesscraft-test"
    corp = (f"--{granita}\r\nContent-Disposition: form-data; name=\"fisier\"; filename=\"{nume}\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n").encode() + octeti + f"\r\n--{granita}--\r\n".encode()
    cerere = urllib.request.Request(f"{site.baza}/c/{id_}/proba/raspuns", corp,
                                    {"Content-Type": f"multipart/form-data; boundary={granita}"})
    with urllib.request.urlopen(cerere) as r:
        return r.geturl(), r.read().decode("utf-8")


def _erori(*coduri):
    return [[e["marca"], e["coloana"], e["valoare_in_stat"], e["valoare_corecta"], "de verificat"]
            for e in CH["erori"] if e["cod"] in coduri]


def _toate_bifele(site, id_, conv=("da",) * 4, disc=("da",) * 3):
    date = {f"C{i}": v for i, v in enumerate(conv, 1)} | {f"D{i}": v for i, v in enumerate(disc, 1)}
    return site.post(f"/c/{id_}/proba", date, {"X-Autosalvare": "1"})


def test_tema_se_descarca_iar_cheia_nu(site):
    for _, f in PA.tema:
        with urllib.request.urlopen(f"{site.baza}/proba/{PA.id}/{f}") as r:
            assert r.status == 200 and "attachment" in r.headers["Content-Disposition"]
            assert r.read() == (PA.dosar / f).read_bytes()
    for f in ("cheia.json", "cheia.sha256", "..%2Fcheia.json"):
        assert pytest.raises(urllib.error.HTTPError, site.get, f"/proba/{PA.id}/{f}").value.code == 404


def test_proba_cap_coada_tabelul_bifele_rezultatul_si_raportul(site, tmp_path):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    site.post("/c/ana/fisa")
    corp = site.get("/c/ana/proba")[1]
    assert "Încarcă tabelul de răspuns" in corp and 'enctype="multipart/form-data"' in corp
    assert all(f'href="/proba/{PA.id}/{f}"' in corp for _, f in PA.tema) and "cheia.json" not in corp
    assert (site.de("ana") / "proba.md").exists()
    # trei greseli gasite si cazul corect semnalat: cine lucreaza cu forma veche a regulii
    pc = CH["plantata_corecta"]
    unde, corp = _incarca(site, "ana", _tabel(tmp_path, _erori("E1", "E2", "E3") +
                                              [[pc["marca"], pc["coloana"], 200, 300, "trebuie 300"]]))
    assert unde.endswith("/c/ana/proba")
    assert "Găsite: <b>3 din 5</b>" in corp and "semnalări greșite: <b>1</b>" in corp and "<b>40%</b>" in corp
    assert corp.count("<b>ratată</b>") == 2 and "cazul pus intenționat, corect" in corp and "trebuie 300" in corp
    assert _toate_bifele(site, "ana", ("da", "da", "nu", "nu"))[2] == json.dumps({"salvat": True})
    site.post("/c/ana/proba", {"nota-D2": "a citit ordonanța", "linkuri": "https://claude.ai/share/x"},
              {"X-Autosalvare": "1"})
    f = (site.de("ana") / "proba.md").read_text(encoding="utf-8")
    assert "- C3 [nu]" in f and "**Ce a răspuns (2):** a citit ordonanța" in f
    corp = site.get("/c/ana/proba")[1]
    assert "2 „da” din 4" in corp and "3 „da” din 3" in corp and ">63%<" in corp  # (0,4 + 0,5 + 1) / 3
    site.post("/c/ana/interviu", {"S1.1": "da", "S1.2": "da", "S1.3": "nu"}, {"X-Autosalvare": "1"})
    corp = site.get("/c/ana/rezultat")[1]
    assert "lipsește proba" not in corp and "Proba, pe părți" in corp and "21,1 din 33,3" in corp
    raport = site.get("/c/ana/raport")[1]
    assert "<h2>Proba</h2>" in raport and "3 din 5 greșeli găsite, 1 semnalări greșite" in raport
    assert "a citit ordonanța" in raport and "63%" in raport


def test_un_fisier_care_nu_e_tabel_nu_inlocuieste_tabelul_bun_iar_cel_inlocuit_ramane(site, tmp_path):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    _, corp = _incarca(site, "ana", b"nu e un tabel", "poza.png")
    assert "Nu s-a putut." in corp and "nu e un tabel Excel" in corp and "Găsite: <b>1 din 5</b>" in corp
    _, corp = _incarca(site, "ana", _tabel(tmp_path, [[9999, "Impozit", 1, 2, ""]]))
    assert "marca „9999” nu e în stat" in corp and "Găsite: <b>1 din 5</b>" in corp
    _, corp = _incarca(site, "ana", _tabel(tmp_path, _erori("E1", "E2")))
    assert "Găsite: <b>2 din 5</b>" in corp
    assert len(list(site.de("ana").glob("Raspuns-inlocuit-la-*.xlsx"))) == 1
    assert not list(site.de("ana").glob("tmp-*"))


def test_proba_bifata_pe_jumatate_se_spune_pe_ecran_si_la_rezultat(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    site.post("/c/ana/fisa")
    site.post("/c/ana/interviu", {"S1.1": "da", "S1.2": "da", "S1.3": "nu"}, {"X-Autosalvare": "1"})
    site.get("/c/ana/proba")
    site.post("/c/ana/proba", {"C1": "da"}, {"X-Autosalvare": "1"})
    assert "Conversațiile: completată pe jumătate" in site.get("/c/ana/proba")[1]
    corp = site.get("/c/ana/rezultat")[1]
    assert "Proba are o parte bifată pe jumătate" in corp and "/c/ana/raport" not in corp


def test_proba_deschisa_refuza_campuri_straine(site):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    assert "Încarcă tabelul de răspuns" in site.get("/c/ana/proba")[1]
    cod, _, corp = site.post("/c/ana/proba", {"C9": "da"}, {"X-Autosalvare": "1"})
    assert cod == 400 and "C9" in json.loads(corp)["eroare"]
    cod, unde, corp = site.post("/c/ana/proba", {"C1": "da", "C2": "nu", "C3": "da", "C4": "nu"})  # fara JavaScript
    assert "?salvat=" in unde and "Salvat la " in corp


def test_ecranul_probei_fara_termeni_tehnici_neexplicati(site, tmp_path):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    corp = site.get("/c/ana/proba")[1]
    # tabelele au datele statului (nume inventate, coloane ca „CASS Angajat”), nu text al programului: nu se verifica
    corp = re.sub(r"<table>.*?</table>", " ", corp.split("<main", 1)[-1], flags=re.S)  # ca la fisa: fara bara
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", corp, flags=re.S))
    text = text.replace(site.proiect, "")
    assert termeni.neexplicate(text) == []


def test_fisa_probei_se_face_din_programul_predat_ca_informatie_fara_nota(site, tmp_path):
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    cod, unde, corp = site.post("/c/ana/proba/fisa", {"cod": ""})
    assert "Scrii întâi linkul sau dosarul programului lui" in corp
    (tmp_path / "fara-git").mkdir()
    corp = site.post("/c/ana/proba/fisa", {"cod": str(tmp_path / "fara-git")})[2]
    assert "nu are istoric git" in corp and not (site.de("ana") / "fisa-proba.json").exists()
    cod, unde, corp = site.post("/c/ana/proba/fisa", {"cod": site.proiect})
    assert unde.endswith("/c/ana/proba") and "<h2>Fișa probei</h2>" in corp and "fără notă" in corp
    assert corp.index("<h2>Conversațiile</h2>") < corp.index("<h2>Fișa probei</h2>") < corp.index("Discuția de după")
    assert f'value="{site.proiect}"' in corp  # sursa ramane scrisa in foaia probei
    # trimiterile la interviu si la proba sunt ale portofoliului, nu ale fisei probei
    assert "Fișa proiectului probei" in corp and "Fișa proiectului de portofoliu" not in corp
    assert "Ce afli numai la interviu" not in corp and "Cum se citește fișa" not in corp
    # fisa nu intra in nota: proba ramane fara nicio parte facuta
    n = candidati.nota_probei(candidati.citeste("ana", site.dosar))["nota"]
    assert n["lipsa"] == ["cheia", "conversațiile", "discuția"] and n["nota"] is None


def test_ecranul_spune_de_unde_vin_linkurile_conversatiilor_si_ca_programul_nu_le_citeste(site):
    # observatia autorului, 15 octombrie: „ce incarc la conversatii? unde e linkul?”
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    corp = site.get("/c/ana/proba")[1]
    ce_a_predat = corp.split("<h2>Ce a mai predat</h2>", 1)[1].split("<h2>Conversațiile</h2>", 1)[0]
    assert "odată cu tabelul" in ce_a_predat and "„Share” / „Partajează”" in ce_a_predat
    assert "programul nu le deschide și nu le citește" in ce_a_predat


def test_fraza_de_inceput_a_interviului_spune_ce_vine_din_proiect_si_unde_sta(site):
    # observatia autorului, 15 octombrie: „care e fisa de mai jos?” — fisa e la pasul 1, nu in interviu
    from harnesscraft import interviu
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    site.post("/c/ana/fisa")
    corp = site.get("/c/ana/interviu")[1]
    assert "fișa de mai jos" not in corp
    text = interviu.FRAZA_DE_INCEPUT
    for loc in ("„Înainte de interviu”", "pasul 1", "„Ce arată proiectul”", "partea IV"):
        assert loc in text and loc in corp


def test_mesajul_pentru_candidat_e_text_simplu_care_se_deschide_oriunde(site):
    # observatia autorului, 15 octombrie: un evaluator fara VS Code nu deschide un .md; „scrisoare” suna vechi
    nume = [f for n, f in PA.tema if n == "mesajul pentru candidat"]
    assert nume == ["Mesaj_pentru_candidat.txt"]
    with urllib.request.urlopen(f"{site.baza}/proba/{PA.id}/{nume[0]}") as r:
        assert r.headers["Content-Type"] == "text/plain; charset=utf-8"
        text = r.read().decode("utf-8")
    assert not re.search(r"^#|\*\*|`", text, re.M)  # fara semnele Markdown, care in Notepad apar ca atare
    assert "Raspuns.xlsx" in text and "Ce predați".upper() in text
    # sporul firmei, spus fara cifra (aprobat de autor, 15 octombrie): altfel cine socoteste cu 100% e notat gresit
    assert "Orele suplimentare se plătesc cu sporul minim din lege." in text and "75" not in text


def test_fisa_probei_trimite_la_discutie_nu_la_interviu_si_poarta_numele_programului(site, tmp_path):
    # gasit la incercarea cu un program facut anume, 15 octombrie: „Cum o folosesti” trimitea la interviu, iar titlul
    # avea calea (la un link, calea clonei din dosarul candidatului)
    from pathlib import Path
    from harnesscraft import interfata
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    corp = site.post("/c/ana/proba/fisa", {"cod": site.proiect})[2]
    fisa = corp.split("<h2>Fișa probei</h2>", 1)[1].split("Discuția de după", 1)[0]
    assert "interviu" not in fisa and "la discuție" in fisa
    assert f"Fișa proiectului probei — „{Path(site.proiect).name}”" in fisa
    for sursa, nume in (("https://github.com/ana/stat-septembrie.git", "stat-septembrie"),
                        ("https://github.com/ana/stat-septembrie/", "stat-septembrie"),
                        (str(tmp_path / "stat"), "stat"), ((tmp_path / "stat").as_posix() + "/", "stat")):
        assert interfata._nume_sursei(sursa) == nume


def test_un_link_care_nu_se_descarca_se_explica_pe_romaneste(site):
    # gasit la incercarea cu un link inexistent, 15 octombrie: recrutorul vedea raspunsul lui git, in engleza
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    corp = site.post("/c/ana/proba/fisa", {"cod": "https://127.0.0.1:9/nu-exista.git"})[2]  # portul 9: nimeni nu raspunde
    assert "calculatorul nu ajunge la adresa asta" in corp and "fatal:" not in corp
    assert candidati.de_ce_nu_se_descarca("remote: Repository not found.\nfatal: repository 'x' not found").startswith(
        "la linkul acesta nu e un depozit public")
    assert candidati.de_ce_nu_se_descarca("fatal: altceva\n") == "git a răspuns „fatal: altceva”."


def test_tabelul_predat_se_descarca_cu_numele_candidatului(site, tmp_path):
    # observatia autorului, 15 octombrie: „daca maine vreau sa il mai vad, sau colegul meu de la HR?”
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    assert pytest.raises(urllib.error.HTTPError, site.get, "/c/ana/proba/Raspuns_ana.xlsx").value.code == 404
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    corp = site.get("/c/ana/proba")[1]
    assert 'href="/c/ana/proba/Raspuns_ana.xlsx" download>Descarcă tabelul predat' in corp
    with urllib.request.urlopen(f"{site.baza}/c/ana/proba/Raspuns_ana.xlsx") as r:
        assert 'filename="Raspuns_ana.xlsx"' in r.headers["Content-Disposition"]
        assert r.read() == (site.de("ana") / "Raspuns.xlsx").read_bytes()
    for gresit in ("/c/ana/proba/Raspuns_altcineva.xlsx", "/c/nimeni/proba/Raspuns_nimeni.xlsx"):
        assert pytest.raises(urllib.error.HTTPError, site.get, gresit).value.code == 404


def test_de_unde_vin_treptele_stau_in_ajutor_si_in_manual_nu_in_fisa(site):
    # observatia autorului, 15 octombrie: cele trei explicatii ingreunau citirea fisei
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    site.post("/c/ana/fisa")
    site.post("/c/ana/proba/fisa", {"cod": site.proiect})
    for pas in ("fisa", "proba"):
        corp = site.get(f"/c/ana/{pas}")[1]
        ajutor, rest = corp.split('class="fereastra"', 1)[1].split("Tot manualul", 1)
        assert "De unde vin:" in ajutor and "De ce o scară:" in ajutor and "Cum o folosești:" in ajutor
        assert "De unde vin:" not in rest
    assert "discuție" in site.get("/c/ana/proba")[1].split("Tot manualul", 1)[0].split("Cum o folosești:", 1)[1][:200]
    manual = re.sub(r"\s+", " ", site.get("/manual")[1])
    assert "De unde vin:" in manual and "Unde stau datele" in manual and "Descarcă tabelul predat" in manual


def test_meseria_probei_se_alege_pana_la_inceput_si_tema_vine_din_pachetul_ales(site, tmp_path, monkeypatch):
    from tests.test_proba import pachet_de_proba
    pachete = tmp_path / "pachete"
    pachete.mkdir()
    pachet_de_proba(pachete)
    site.post("/nou", {"nume": "Ana", "sursa": site.proiect})
    site.accepta_proba("ana")
    assert 'name="pachet"' not in site.get("/c/ana/proba")[1]  # un singur pachet: un rand, fara alegere
    monkeypatch.setattr(proba, "PACHETE", pachete)
    corp = site.get("/c/ana/proba")[1]
    assert 'action="/c/ana/proba/pachet"' in corp and "marketing · Textul campaniei" in corp
    site.post("/c/ana/proba/pachet", {"pachet": "text-campanie"})
    corp = site.get("/c/ana/proba")[1]
    assert 'href="/proba/text-campanie/Text.txt"' in corp and "Unde a greșit AI-ul în lucrul la text?" in corp
    assert "Nu-i spui câte greșeli are textul campaniei." in corp
    with urllib.request.urlopen(f"{site.baza}/proba/text-campanie/Text.txt") as r:
        assert r.read() == (pachete / "text-campanie" / "Text.txt").read_bytes()
    assert pytest.raises(urllib.error.HTTPError, site.get, "/proba/text-campanie/cheia.json").value.code == 404
    _toate_bifele(site, "ana", conv=("da", "", "", ""), disc=("",) * 3)
    corp = site.post("/c/ana/proba/pachet", {"pachet": proba.IMPLICIT})[2]
    assert "meseria nu se mai schimbă" in corp and "text-campanie" in (site.de("ana") / "proba.md").read_text(encoding="utf-8")
