import pytest

from harnesscraft import manifest
from harnesscraft.gardieni import CLASAMENT, ClasamentNecomis, cere_clasament, clasament, gardian_c2

COMPLET = "### Jumătatea de sus\n\n- a/x\n- a/y\n\n### Jumătatea de jos\n\n- b/x\n- b/y\n"
MANIFEST = "nr,depozit\n1,a/x\n2,a/y\n3,b/x\n4,b/y\n"


def test_c2_refuza_fara_clasament(depozit):
    d = depozit("harness")
    d.commit("init", {"README.md": "x"})
    assert "nu e comis" in gardian_c2(d.cale)


def test_c2_refuza_clasament_modificat_necomis(depozit):
    d = depozit("harness")
    d.commit("clasament", {"esantion/clasament-orb.md": "1. a\n"})
    (d.cale / "esantion/clasament-orb.md").write_text("1. b\n", encoding="utf-8")
    assert "necomise" in gardian_c2(d.cale)


def test_c2_trece_cu_clasament_comis(depozit):
    d = depozit("harness")
    d.commit("clasament", {"esantion/clasament-orb.md": COMPLET, "esantion/manifest.csv": MANIFEST})
    assert gardian_c2(d.cale) is None


def test_c2_refuza_clasament_comis_pe_jumatate(depozit):
    d = depozit("harness")
    d.commit("clasament", {"esantion/clasament-orb.md": "### 1. a/x — nota 9\n\n> bun\n"})
    assert "nu e complet" in gardian_c2(d.cale)


def test_c2_refuza_jumatati_suprapuse(depozit):
    d = depozit("harness")
    d.commit("clasament", {"esantion/clasament-orb.md": COMPLET.replace("- b/y", "- a/x")})
    assert "in amandoua" in gardian_c2(d.cale)


def test_c2_refuza_clasament_care_nu_acopera_manifestul(depozit):
    d = depozit("harness")
    d.commit("clasament", {"esantion/clasament-orb.md": COMPLET,
                           "esantion/manifest.csv": MANIFEST.replace("b/y", "c/z")})
    assert "nu acopera manifestul" in gardian_c2(d.cale)


@pytest.mark.privat
def test_c2_trece_pe_clasamentul_real():
    assert gardian_c2() is None


def test_semnal_pe_esantion_cere_clasament(depozit, tmp_path):
    d = depozit("harness")
    d.commit("init", {"README.md": "x"})
    clona = tmp_path / "harness" / "depozite" / "a__b"
    clona.mkdir(parents=True)
    with pytest.raises(ClasamentNecomis):
        cere_clasament(clona, radacina=d.cale, gardate=[(tmp_path / "harness" / "depozite", CLASAMENT)])


def test_semnal_in_afara_esantionului_nu_cere(depozit, tmp_path):
    d = depozit("harness")
    d.commit("init", {"README.md": "x"})
    cere_clasament(tmp_path / "alt", radacina=d.cale, gardate=[(tmp_path / "harness" / "depozite", CLASAMENT)])


def test_runda_noua_nu_trece_pe_clasamentul_celei_vechi(depozit, tmp_path):
    d = depozit("harness")
    d.commit("clasament", {"esantion/clasament-orb.md": COMPLET, "esantion/manifest.csv": MANIFEST})
    gardate = [(tmp_path / "harness" / "depozite", CLASAMENT),
               (tmp_path / "harness" / "depozite-runda2", clasament(2))]
    cere_clasament(tmp_path / "harness" / "depozite" / "a__x", radacina=d.cale, gardate=gardate)
    with pytest.raises(ClasamentNecomis):
        cere_clasament(tmp_path / "harness" / "depozite-runda2" / "c__z", radacina=d.cale, gardate=gardate)


def test_c2_runda2_cere_manifestul_ei(depozit):
    d = depozit("harness")
    d.commit("clasament", {"esantion-runda2/clasament-orb.md": COMPLET,
                           "esantion-runda2/manifest.csv": MANIFEST.replace("b/y", "c/z")})
    assert "nu acopera manifestul" in gardian_c2(d.cale, clasament(2))


def test_harness_pe_esantion_cere_clasament(monkeypatch):
    from harnesscraft.harness import harness
    from harnesscraft.manifest import RADACINA
    monkeypatch.setattr("harnesscraft.gardieni.gardian_c2", lambda *a: "clasament lipsa")
    with pytest.raises(ClasamentNecomis):
        harness(RADACINA / "depozite-runda2" / "orice__depozit")


def test_c1_vede_abaterea_de_la_manifest(depozit, tmp_path):
    sursa = depozit("sursa")
    primul = sursa.commit("unu", {"a.txt": "1"})
    sursa.commit("doi", {"a.txt": "2"})
    rand = {"depozit": "x/y", "commit": primul}
    clona = manifest.cale_clona(rand, tmp_path / "dep")
    manifest.subprocess.run(["git", "clone", "--quiet", str(sursa.cale), str(clona)], check=True)
    assert "manifestul cere" in manifest.gardian_c1(rand, tmp_path / "dep")
    manifest.git(clona, "checkout", "--quiet", "--detach", primul)
    assert manifest.gardian_c1(rand, tmp_path / "dep") is None


def test_c1_vede_clona_lipsa(tmp_path):
    assert "lipseste" in manifest.gardian_c1({"depozit": "x/y", "commit": "0"}, tmp_path)
