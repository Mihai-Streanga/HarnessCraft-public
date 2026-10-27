"""Totalul pe treimi: fiecare componenta adusa la 0-1, lipsa ramane lipsa, nu zero ascuns."""
import pytest

from harnesscraft import interviu
from harnesscraft.total import randare, total
from tests.test_interviu import _bifeaza, _ghid


def test_toate_trei_la_maxim_dau_100_si_la_minim_0():
    assert total((16, 16), 4, 1)["total"] == 100
    assert total((0, 16), 1, 0) == {"puncte": {"portofoliul": 0, "interviul": 0, "proba": 0}, "total": 0,
                                    "lipsa": [], "complet": True, "fara_cod": False, "plafon": 100}


def test_proba_lipsa_face_totalul_incomplet_nu_zero_ascuns():
    t = total((8, 16), 2.5)
    assert t["puncte"] == {"portofoliul": 16.7, "interviul": 16.7, "proba": None}
    assert t["total"] == 33.3 and not t["complet"] and t["lipsa"] == ["proba"]
    assert "incomplet, lipsește: proba" in randare(t)


def test_valoare_in_afara_scalei_refuzata():
    with pytest.raises(ValueError, match="proba"):
        total((8, 16), 2, 1.5)


def test_ghidul_completat_duce_fisa_si_interviul_in_total(depozit):
    g = _bifeaza(_ghid(depozit), {"S1": "da da da", "S2": "nu nu nu"})
    t = interviu.scor(g)["total"]
    assert t["puncte"]["interviul"] == round((2.5 - 1) / 3 * 100 / 3, 1)
    assert t["puncte"]["portofoliul"] is not None and t["lipsa"] == ["proba"]
