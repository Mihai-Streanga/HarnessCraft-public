"""Exemplele, in aceeasi aplicatie, numai de citit (rapoarte/propunere-exemple-in-aplicatie.md, „Refăcut”): „Exemple” in
bara din stanga si pe „Acasă”, lista, paginile fiecarui candidat cu legaturile ramase in exemple, campurile blocate,
rapoartele de tiparit. Setul adevarat (20 de secunde, C:/Metoda) nu se face aici: `set_exemple.reface` e inlocuit cu un
candidat scris direct; setul insusi il verifica tests/test_set_exemple.py."""
import re
import threading
import time
import urllib.error
import urllib.request

import pytest

from harnesscraft import candidati, interfata, set_exemple

NUME = "Elena Dobrescu"  # un nume din exemple-candidati/rezultate.json: lista arata numai candidatii capitolului
ID = "elena-dobrescu"


@pytest.fixture
def lumea(tmp_path, monkeypatch):
    refaceri = []

    def reface(radacina):
        refaceri.append(radacina)
        if getattr(reface, "pica", False):
            raise RuntimeError("git lipsește")
        candidati.nou(NUME, "", dosar=radacina / "candidaturi", fara_cod="Lucrează numai în conversații.")
        (radacina / set_exemple.GATA).write_text("", encoding="utf-8")

    monkeypatch.setattr(set_exemple, "reface", reface)
    monkeypatch.setattr(interfata, "EXEMPLE_STARE", {"se_reface": False, "eroare": None})
    s = interfata.server(port=0, dosar=tmp_path / "c", radacina_exemple=tmp_path / "set")
    threading.Thread(target=s.serve_forever, daemon=True).start()
    baza = f"http://127.0.0.1:{s.server_port}"

    class Lumea:
        dosar = tmp_path / "c"

        def __init__(self):
            self.refaceri, self.reface = refaceri, reface

        @staticmethod
        def get(cale):
            with urllib.request.urlopen(baza + cale) as r:
                return r.geturl().removeprefix(baza), r.read().decode("utf-8")

        @staticmethod
        def post(cale):
            cerere = urllib.request.Request(baza + cale, b"", {"Origin": baza})
            try:
                with urllib.request.urlopen(cerere) as r:
                    return r.status, r.geturl().removeprefix(baza)
            except urllib.error.HTTPError as ex:
                return ex.code, None

        @staticmethod
        def asteapta():
            for _ in range(100):
                if not interfata.EXEMPLE_STARE["se_reface"]:
                    return
                time.sleep(0.05)
            raise AssertionError("refacerea n-a mai terminat")

        def deschide(self):
            """Primul clic pe „Exemple”: intai pagina de asteptare, apoi lista."""
            _, corp = self.get("/exemple")
            assert "Se pregătesc exemplele" in corp and 'http-equiv="refresh"' in corp
            self.asteapta()
            return self.get("/exemple")[1]

    yield Lumea()
    s.shutdown()
    s.server_close()


def test_exemple_sta_in_bara_si_pe_acasa_si_in_manual(lumea):
    _, acasa = lumea.get("/")
    assert 'href="/exemple">Exemple</a>' in acasa and 'href="/exemple">Vezi exemplele</a>' in acasa
    _, manual = lumea.get("/manual")
    assert 'href="/exemple">Vezi exemplele în aplicație</a>' in manual and 'id="exemple"' in manual
    lista = lumea.deschide()
    assert NUME in lista and f'href="/exemple/c/{ID}/raport"' in lista and "numai de citit" in lista
    assert 'class="nav activ" href="/exemple"' in lista


def test_paginile_candidatului_raman_in_exemple_si_sunt_numai_de_citit(lumea):
    lumea.deschide()
    for pas in ("fisa", "interviu", "proba", "rezultat", "sterge"):
        _, corp = lumea.get(f"/exemple/c/{ID}/{pas}")
        assert corp.count("nota-exemplu") == 1, pas
        campuri = re.findall(r"<(?:input|textarea|select|button)\b[^>]*>", corp)
        blocate = [c for c in campuri if "popovertarget" not in c and "window.print" not in c]
        assert all(" disabled" in c for c in blocate), pas  # nimic nu se bifeaza, nimic nu se trimite
        if pas in ("interviu", "sterge"):  # au campuri si la candidatul fara proiect cu cod
            assert blocate, pas
        assert all(" disabled" not in c for c in campuri if "popovertarget" in c), pas  # ajutorul se deschide
        assert not re.search(r'(href|action)="/c/', corp), pas  # legaturile candidatului raman in exemple
        assert 'href="/">Acasă</a>' in corp  # „Acasă” duce mereu la candidatii recrutorului
    for pas in ("raport", "rezumat", "audit", "audit_scurt"):  # rapoartele se tiparesc: fara campuri blocate
        _, corp = lumea.get(f"/exemple/c/{ID}/{pas}")
        assert "nota-exemplu" in corp and "window.print()" in corp, pas
        assert not re.search(r'<button[^>]*window\.print\(\)[^>]*disabled', corp), pas
    assert lumea.get(f"/exemple/c/{ID}")[0].startswith(f"/exemple/c/{ID}/")  # pasul curent, tot in exemple
    assert candidati.lista(lumea.dosar) == []  # candidatii adevarati: neatinsi


def test_nimic_nu_se_trimite_din_exemple_iar_reface_le_face_din_nou(lumea):
    lumea.deschide()
    assert lumea.post(f"/exemple/c/{ID}/interviu")[0] == 403
    assert lumea.post(f"/exemple/c/{ID}/sterge")[0] == 403
    assert candidati.citeste(ID, lumea.refaceri[0] / "candidaturi")
    assert lumea.post("/exemple/reface") == (200, "/exemple")
    lumea.asteapta()
    assert len(lumea.refaceri) == 2 and NUME in lumea.get("/exemple")[1]


def test_o_refacere_picata_se_spune_si_se_reia(lumea):
    lumea.reface.pica = True
    lumea.get("/exemple")
    lumea.asteapta()
    _, corp = lumea.get("/exemple")
    assert "nu s-au putut pregăti" in corp and "git lipsește" in corp and "Încearcă din nou" in corp
    lumea.reface.pica = False
    _, corp = lumea.get("/exemple?din-nou=1")
    assert "Se pregătesc exemplele" in corp
    lumea.asteapta()
    assert NUME in lumea.get("/exemple")[1]
