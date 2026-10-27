"""Reparatiile din sesiunea de decizii dupa auditul unic (rapoarte/decizii-audit-unic.md): decizia salvata la bifa,
numele bifei nedate, invitatia, proba nedata, „Cum folosesc” peste tot, lista dupa total, conversatiile numarate la
fel, datele in forma omului, alegerea proiectului, scrierea sigura si salvarile deodata."""
import json
import re
import threading
from datetime import datetime

import pytest

from harnesscraft import candidati, interfata, interviu, md
from tests.test_interfata import site  # noqa: F401 (fixture)
from tests.test_interfata_proba import _erori, _incarca, _tabel

TOATE = {f"S{i}.{j}": "da" for i in range(1, len(interviu.INTREBARI) + 1) for j in (1, 2, 3)}
AUTO = {"X-Autosalvare": "1"}


def _candidat(site, nume="Ana", bife=None, **extra):
    site.post("/nou", {"nume": nume, "sursa": site.proiect, **extra})
    id_ = next(c["id"] for c in candidati.lista(site.dosar) if c["nume"] == nume)
    site.post(f"/c/{id_}/fisa")
    site.post(f"/c/{id_}/interviu", bife if bife is not None else {"S1.1": "da"}, AUTO)
    return id_


def _vizibil(html):
    """Textul paginii, fara etichete, scripturi si valorile atributelor."""
    html = re.sub(r"(?s)<(script|style)\b.*?</\1>", " ", html)
    return re.sub(r"<[^>]+>", " ", html)


def test_decizia_se_salveaza_la_bifa(site):
    _candidat(site)
    assert 'data-autosalvare="decizie"' in site.get("/c/ana/interviu")[1]
    cod, _, corp = site.post("/c/ana/decizia", {"decizia": "da", "motivul": ""}, AUTO)
    assert (cod, json.loads(corp)) == (200, {"salvat": True})
    assert candidati.decizia_probei(candidati.citeste("ana", site.dosar))["decizia"] == "da"
    cod, _, corp = site.post("/c/ana/decizia", {"decizia": "nu", "motivul": ""}, AUTO)
    assert cod == 400 and "motivul" in json.loads(corp)["eroare"]


def test_al_treilea_buton_are_nume(site):
    _candidat(site)
    corp = site.get("/c/ana/interviu")[1]
    assert "<span>nepusă</span>" in corp and "<span>—</span>" not in corp
    site.accepta_proba("ana")
    corp = site.get("/c/ana/proba")[1]
    assert "<span>nebifat</span>" in corp and "<span>—</span>" not in corp


def test_invitatia_cere_data_in_forma_omului_si_vine_cu_pe_e_mail(site):
    _candidat(site)
    site.post("/c/ana/decizia", {"decizia": "da"})
    corp = site.get("/c/ana/proba")[1]
    assert f'name="data" value="{datetime.now():%d.%m.%Y}"' in corp and 'type="date"' not in corp
    assert 'name="cum" value="pe e-mail"' in corp and " required" not in corp.split("Răspunsul candidatului")[1]
    assert "ZZ.LL.AAAA" in site.post("/c/ana/proba/acord", {"raspuns": "da", "data": "31.02.2026", "cum": "pe e-mail"})[2]
    site.post("/c/ana/proba/acord", {"raspuns": "da", "data": "21.10.2026", "cum": "pe e-mail"})
    a = candidati.decizia_probei(candidati.citeste("ana", site.dosar))["acordul"]
    assert a["data"] == "2026-10-21"  # in fisier, forma datelor; pe ecran, a omului
    assert "acceptat proba pe 21.10.2026" in site.get("/c/ana/proba")[1]


def test_fara_proba_rezultatul_nu_trimite_la_pasul_3(site):
    _candidat(site, bife=TOATE)
    site.post("/c/ana/decizia", {"decizia": "nu", "motivul": "rolul nu cere probă"})
    corp = site.get("/c/ana/rezultat")[1]
    assert "Nu merge la probă: rolul nu cere probă." in corp and ">pasul 3</a>" not in corp


def test_cum_folosesc_pe_toate_ecranele(site):
    assert 'popovertarget="ajutor-candidati"' in site.get("/candidati")[1]  # si fara niciun candidat
    _candidat(site, bife=TOATE)
    for cale, pas in (("/", "acasa"), ("/candidati", "candidati"), ("/c/ana/raport", "raport"),
                      ("/c/ana/rezumat", "raport"), ("/c/ana/audit", "raport"),
                      ("/rapoarte/document?id=ana&fel=lista", "raport")):
        assert f'popovertarget="ajutor-{pas}"' in site.get(cale)[1], cale
    assert "exemple" in interfata.AJUTOR  # pagina exemplelor cere setul; o acopera tests/test_exemple_in_aplicatie.py


def test_lista_celor_alesi_dupa_total_iar_un_rezultat_stricat_se_spune(site):
    _candidat(site, "Ana", bife={k: "nu" for k in TOATE})
    _candidat(site, "Bogdan", bife=TOATE)
    _candidat(site, "Cristi", bife={"S1.1": "da"})  # bifata pe jumatate: rezultatul nu se poate calcula
    corp = site.get("/rapoarte/document?toti=1&fel=lista")[1]
    assert corp.index("Bogdan") < corp.index("Ana") < corp.index("Cristi")
    assert "nu se poate calcula" in corp.split("Cristi", 1)[1]


def test_auditul_numara_conversatiile_ca_raportul(site):
    _candidat(site, bife=TOATE)
    site.accepta_proba("ana")
    site.post("/c/ana/proba", {"linkuri": "o conversație ChatGPT, trimisă ca PDF"}, AUTO)
    assert "o conversație ChatGPT" in site.get("/c/ana/raport")[1]
    corp = site.get("/c/ana/audit")[1]
    assert "conversațiile cu AI-ul: predate, fără link" in corp and "0 conversații" not in corp


def test_jurnalul_tine_bifele_una_sub_alta(site):
    _candidat(site, bife={"S1.1": "da", "S1.2": "nu", "S1.3": "da"})
    corp = site.get("/c/ana/audit")[1]
    assert "întrebarea 1, rândul 1: nepusă → da<br>întrebarea 1, rândul 2: nepusă → nu" in corp


def test_valorile_probei_au_unitatea(site, tmp_path):
    _candidat(site)
    site.accepta_proba("ana")
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    corp = site.get("/c/ana/proba")[1]
    assert re.search(r"\d lei în stat, [\d.,]+ lei corect", corp)


def test_semnul_demonstrativ_si_pe_rapoarte(site):
    _candidat(site, "Mihai", demonstrativ="1")
    assert "demonstrativ · " in site.get("/rapoarte")[1]
    assert "· demonstrativ" in site.get("/rapoarte/document?toti=1&fel=lista")[1].replace("&nbsp;", " ")


def test_alegerea_proiectului_din_fereastra_windows(site, monkeypatch):
    monkeypatch.setattr(interfata, "alege_pe_calculator", lambda bundle=False: "C:\\Proiecte\\x.bundle" if bundle else "C:\\Proiecte\\x")
    assert json.loads(site.post("/nou/alege", {"fel": "dosar"})[2]) == {"cale": "C:\\Proiecte\\x"}
    assert json.loads(site.post("/nou/alege", {"fel": "bundle"})[2]) == {"cale": "C:\\Proiecte\\x.bundle"}
    corp = site.get("/nou")[1]
    assert 'data-alege="dosar"' in corp and 'data-alege="bundle"' in corp and ".bundle" in corp
    corp = site.post("/nou", {"nume": "Ana", "sursa": "C:/nu-exista-deloc"})[2]
    assert 'name="sursa"' in corp and 'class="camp-gresit"' in corp


def test_datele_pe_ecrane_sunt_in_forma_omului(site, tmp_path):
    _candidat(site, bife=TOATE)
    site.accepta_proba("ana")
    _incarca(site, "ana", _tabel(tmp_path, _erori("E1")))
    for cale in ("/c/ana/fisa", "/c/ana/interviu", "/c/ana/proba", "/c/ana/rezultat", "/c/ana/raport",
                 "/c/ana/audit", "/c/ana/audit_scurt", "/rapoarte", "/rapoarte/document?toti=1&fel=lista"):
        text = _vizibil(site.get(cale)[1]).replace(site.proiect, "")
        assert not re.search(r"\b\d{4}-\d{2}-\d{2}\b", text), (cale, re.findall(r".{30}\d{4}-\d{2}-\d{2}.{10}", text))
    assert md.data("2026-10-19T14:47:17") == "19.10.2026, 14:47" and md.data("2026-10-19") == "19.10.2026"


def test_scrierea_lasa_fisierul_vechi_intreg_la_o_intrerupere(tmp_path, monkeypatch):
    f = tmp_path / "ghid.md"
    candidati.scrie_text(f, "vechi")
    def pica(*a):
        raise OSError("discul s-a umplut")
    monkeypatch.setattr(candidati.os, "replace", pica)
    with pytest.raises(OSError):
        candidati.scrie_text(f, "nou")
    assert f.read_text(encoding="utf-8") == "vechi"


def test_salvarile_deodata_nu_se_calca(site):
    _candidat(site, bife={})
    c = candidati.citeste("ana", site.dosar)
    fire = [threading.Thread(target=candidati.salveaza_interviu, args=(c, {f"S{i}.1": "da"}))
            for i in range(1, len(interviu.INTREBARI) + 1)]
    for x in fire:
        x.start()
    for x in fire:
        x.join()
    bife = candidati._bife_interviu(candidati.ghid(c))
    assert all(bife[f"S{i}.1"] == "da" for i in range(1, len(interviu.INTREBARI) + 1))
    assert not list(c["dosar"].glob("tmp-*"))


def test_o_refacere_picata_a_exemplelor_lasa_setul_de_dinainte(tmp_path, monkeypatch):
    from harnesscraft import set_exemple
    setul = tmp_path / "tmp-set"
    (setul / "candidaturi").mkdir(parents=True)
    (setul / set_exemple.GATA).write_text("", encoding="utf-8")
    def pica(radacina, cu_autorul=True):
        radacina.mkdir()
        raise RuntimeError("commitul nu se gaseste")
    monkeypatch.setattr(set_exemple, "construieste", pica)
    with pytest.raises(RuntimeError):
        set_exemple.reface(setul)
    assert set_exemple.gata(setul) and not (tmp_path / "tmp-set-inainte-de-refacere").exists()


def test_cazul_autorului_se_reconstruieste_pe_commitul_de_azi(tmp_path, monkeypatch):
    import subprocess
    from harnesscraft import set_exemple
    metoda, autorul = tmp_path / "Metoda", tmp_path / "autorul"
    metoda.mkdir()
    autorul.mkdir()
    git = [*set_exemple.GIT, "-C", str(metoda)]
    subprocess.run([*git, "init", "-q"], check=True)
    (metoda / "CLAUDE.md").write_text("# reguli\n", encoding="utf-8")
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "azi"], check=True)
    (autorul / "fisa.json").write_text(json.dumps({"commit": "8a2258ae" + "0" * 32}), encoding="utf-8")
    monkeypatch.setattr(set_exemple, "METODA", metoda)
    monkeypatch.setattr(set_exemple, "AUTORUL", autorul)
    d = set_exemple.metoda(tmp_path / "proiecte")
    azi = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    assert subprocess.run([*set_exemple.GIT, "-C", str(d), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip() == azi


def test_interviul_si_proba_n_au_termeni_neexplicati(site):
    from harnesscraft import termeni
    _candidat(site)
    site.accepta_proba("ana")
    for cale in ("/c/ana/interviu", "/c/ana/proba", "/c/ana/rezultat", "/c/ana/audit"):
        text = _vizibil(site.get(cale)[1].split("</aside>", 1)[1]).replace(site.proiect, "")
        assert termeni.neexplicate(text) == [], (cale, termeni.neexplicate(text))
