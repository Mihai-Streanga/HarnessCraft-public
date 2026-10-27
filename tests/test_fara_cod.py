"""Candidatul fara proiect cu cod (datoria 12, decizia autorului, 16 octombrie): hotararea recrutorului, cu motivul.
Portofoliul intra cu 0, etichetat, nu „lipsa”; totalul e complet, pe aceeasi scara, cel mult doua treimi."""
import pytest

from harnesscraft import audit, candidati, interviu, termeni
from harnesscraft.total import PLAFON_FARA_COD, randare, total
from tests.test_audit import _text
from tests.test_interfata import site  # noqa: F401 (fixture)
from tests.test_interviu import _bifeaza

TOATE_DA = {f"S{i}": "da da da" for i in range(1, 8)}


def test_fara_cod_portofoliul_are_0_si_totalul_e_complet_cel_mult_doua_treimi():
    t = total(None, 4, 1, fara_cod=True)
    assert t["puncte"] == {"portofoliul": 0, "interviul": 33.3, "proba": 33.3}
    assert t["complet"] and t["total"] == PLAFON_FARA_COD == 66.7 and t["plafon"] == 66.7
    assert "fără proiect cu cod" in randare(t) and "cel mult 66.7 din 100" in randare(t)
    t = total(None, 4, None, fara_cod=True)  # proba lipsa ramane lipsa: fara cod nu umple alte goluri
    assert t["lipsa"] == ["proba"] and not t["complet"]
    with pytest.raises(ValueError, match="are fișă"):
        total((8, 16), 4, 1, fara_cod=True)


def test_ghidul_fara_cod_poarta_hotararea_iar_punctajul_o_citeste_din_el():
    g = interviu.ghid(None, nume="Ana")
    assert g.splitlines()[1] == "<!-- fisa fara-cod -->" and "# Interviul cu Ana · fără proiect cu cod" in g
    assert "Ce a adus în loc de proiect" in g and "Despre proiectul lui" not in g and "Treapta provizorie" not in g
    s = interviu.scor(_bifeaza(g, TOATE_DA), proba=1)
    assert s["total"]["fara_cod"] and s["total"]["puncte"]["portofoliul"] == 0 and s["total"]["total"] == 66.7
    assert s["nivel_fisa"] is None and "Nivelul din fișă: fără proiect cu cod" in interviu.randare_scor(s)


def test_candidatul_fara_cod_cere_motivul_si_nu_are_ce_analiza(tmp_path):
    d = tmp_path / "c"
    with pytest.raises(ValueError, match="motivul"):
        candidati.nou("Ana", "", dosar=d, fara_cod="  ")
    with pytest.raises(ValueError, match="Alegi una"):
        candidati.nou("Ana", str(tmp_path / "ceva"), dosar=d, fara_cod="lucrează în chat")
    with pytest.raises(ValueError, match="nu are proiect cu cod"):
        candidati.nou("Ana", "", dosar=d)  # fara proiect si fara bifa: eroarea spune de bifa
    c = candidati.citeste(candidati.nou("Ana", "", dosar=d, fara_cod="lucrează numai în chat"), d)
    assert candidati.fara_cod(c) == "lucrează numai în chat" and c["proiect"] is None
    assert candidati.stari(c)["fisa"] == ("gata", "") and candidati.stari(c)["interviu"][0] == "de făcut"
    with pytest.raises(ValueError, match="nimic de analizat"):
        candidati.analizeaza(c)
    j = audit.citeste(c["dosar"])
    assert [(x["pas"], x["cine"]) for x in j] == [("candidatul", audit.RECRUTOR), ("portofoliul", audit.RECRUTOR),
                                                 ("interviul", audit.PROGRAM)]
    assert j[1]["fara_cod"] is True and "nu are proiect cu cod" in j[1]["ce"]


def test_drumul_fara_cod_pe_ecrane_raport_si_audit(site):
    cod, unde, corp = site.post("/nou", {"nume": "Ana", "fara_cod": "1", "motiv_fara_cod": ""})
    assert "Scrii motivul" in corp and 'name="fara_cod" value="1" checked' in corp  # bifa ramane la eroare
    cod, unde, corp = site.post("/nou", {"nume": "Ana", "fara_cod": "1", "motiv_fara_cod": "lucrează numai în chat"})
    assert unde.endswith("/c/ana/fisa") and "Fără proiect cu cod." in corp and "lucrează numai în chat" in corp
    assert 'action="/c/ana/fisa"' not in corp and "cel mult la 66,7 din 100" in corp  # fara butonul de analiza
    assert site.post("/c/ana/fisa")[0] == 200  # butonul nu exista; o cerere directa e refuzata cu motiv
    corp = site.get("/c/ana/interviu")[1]
    assert "Ce a adus în loc de proiect" in corp and "fără proiect cu cod" in corp
    site.post("/c/ana/interviu", {f"S{i}.{n}": "da" for i in (1, 2) for n in "123"}, {"X-Autosalvare": "1"})
    rez = site.get("/c/ana/rezultat")[1]
    assert "0 din 33,3, fără proiect cu cod" in rez and "fără proiect cu cod: cel mult 66,7" in rez
    assert "lipsește proba" in rez and "lipsește portofoliul" not in rez
    raport = site.get("/c/ana/raport")[1]
    assert "Portofoliul: fără proiect cu cod" in raport and "lucrează numai în chat" in raport
    assert "Ce ne-ați adus în loc de un proiect cu cod" in raport  # ce a adus, la discutia fara nota
    scurt = site.get("/c/ana/rezumat")[1]
    assert "Portofoliul: fără proiect cu cod" in scurt
    aud = site.get("/c/ana/audit")[1]
    assert "fără proiect cu cod, hotărârea recrutorului → 0" in aud and "cu motivul: lucrează numai în chat" in aud
    assert "nimic de refăcut" in aud
    lista = site.get("/rapoarte/document?fel=lista&toti=1")[1].replace("&nbsp;", " ")
    assert "fără proiect cu cod" in lista
    acasa = site.get("/")[1]
    assert "fără proiect cu cod" in acasa
    for p in (site.get("/c/ana/fisa")[1], corp, rez, raport, scurt, aud, site.get("/nou")[1], site.get("/manual")[1]):
        assert termeni.neexplicate(_text(p.split("</aside>", 1)[1])) == []
