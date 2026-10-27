"""Capturile din manual: fiecare ecran din „Ecranele și butoanele” are figura lui, iar
fiecare imagine din manual e pe disc si se trimite. Daca o captura e veche (codul ecranelor schimbat de atunci) nu se
verifica aici, ar cadea la orice schimbare de ecran: `py -m harnesscraft.capturi --verifica`, inaintea copiei publice."""
import re
import threading
import urllib.request

import pytest

from harnesscraft import capturi, interfata


@pytest.fixture
def baza(tmp_path):
    s = interfata.server(port=0, dosar=tmp_path / "c")
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_port}"
    s.shutdown()
    s.server_close()


def _ecranele(manual):
    return manual.split("<h2>Ecranele și butoanele</h2>", 1)[1].split("<h2>", 1)[0]


def test_fiecare_ecran_din_manual_are_captura_lui_sub_titlu(baza):
    with urllib.request.urlopen(baza + "/manual") as r:
        sectiune = _ecranele(r.read().decode("utf-8"))
    titluri = re.findall(r"<h3>([^<]+)</h3>", sectiune)
    assert titluri and set(titluri) == set(interfata.CAPTURI_MANUAL)
    for t in titluri:
        assert re.search(rf'<h3>{re.escape(t)}</h3><figure class="captura"><img src="/static/manual/[\w-]+\.png" alt="[^"]+"',
                         sectiune), t
    assert "persoane inventate" in sectiune.split("<h3>", 1)[0]  # nota, deasupra primei capturi


def test_imaginile_din_manual_sunt_pe_disc_si_se_trimit(baza):
    with urllib.request.urlopen(baza + "/manual") as r:
        surse = re.findall(r'<img src="(/static/manual/[\w-]+\.png)"', r.read().decode("utf-8"))
    assert len(surse) == len(interfata.CAPTURI_MANUAL)
    for s in surse:
        with urllib.request.urlopen(baza + s) as r:
            assert r.headers["Content-Type"] == "image/png" and r.read(8) == b"\x89PNG\r\n\x1a\n", s
    assert sum(f.stat().st_size for f in capturi.DOSAR.glob("*.png")) < 3e6  # tinta din plan: sub 3 MB toate


def test_scriptul_face_exact_capturile_din_manual():
    assert set(capturi.PAGINI) == {f for f, _ in interfata.CAPTURI_MANUAL.values()}
    assert capturi.PORT != interfata.PORT  # instanta deschisa a recrutorului nu se inchide
