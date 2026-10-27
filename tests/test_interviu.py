"""Interviul: aceleasi intrebari pentru toti, bifele citite din ghidul completat, nota = 1 + „da”, nepusa ramane nepusa."""
import re
from pathlib import Path

import pytest

from harnesscraft import fisa, formular, interviu
from harnesscraft.harness import harness
from tests.test_fisa import INSTR, stare


def _fisa(depozit, fisiere):
    d = depozit()
    d.commit("start", fisiere)
    return fisa.fisa("d", stare(), harness(d.cale))


def _ghid(depozit):
    return interviu.ghid(_fisa(depozit, {"README.md": "x"}))


def _bifeaza(ghid, bife):
    """{"S1": "da nu da"} -> scrie valorile pe cele trei randuri ale intrebarii."""
    for id_, valori in bife.items():
        for nr, v in enumerate(valori.split(), 1):
            ghid = ghid.replace(f"- {id_}.{nr} [ ] ", f"- {id_}.{nr} [{v}] ")
    return ghid


def _intrebari(ghid):
    return [r for r in ghid.splitlines() if r.startswith("### ") or re.match(r"- [SL]\d+\.[123] ", r)]


def test_aceleasi_intrebari_si_bife_la_proiecte_diferite_numai_fisa_difera(depozit):
    gol = _ghid(depozit)
    plin = interviu.ghid(_fisa(depozit, {"CLAUDE.md": INSTR, "src/app.py": "x", "src/gen/a.py": "x",
                                         "docs/arhitectura.md": "x"}))
    # 7 intrebari cu cate 3 bife, plus titlurile din partea 4; intrebarile recrutorului n-au bife
    assert _intrebari(gol) == _intrebari(plin) and len(_intrebari(gol)) == 7 + 3 * 7 + 2
    assert not re.search(r"^- L\d", gol, re.M) and gol.count("**Întrebarea ta ") == interviu.LIBERE
    assert "**prompter**" in gol and "**configurator**" in plin


def test_titlul_spune_candidatul_si_proiectul_nu_calea_si_poarta_amprenta_nu_versiune(depozit):
    f = _fisa(depozit, {"README.md": "x"})
    g = interviu.ghid(f, nume="Ana Pop")
    assert g.splitlines()[2] == f"# Interviul cu Ana Pop · proiectul „{Path(f['proiect']).name}”"
    assert interviu.ghid(f).splitlines()[2].startswith("# Interviul · proiectul ")
    assert f"<!-- ghid-interviu intrebari {interviu.AMPRENTA} -->" in g and not re.search(r"\bv\d+\b", g)
    assert not any(x in g for x in ("SPEC", "etapa", "piesa", "13 octombrie"))


def test_golurile_fisei_au_aceeasi_intrebare_ca_in_fisa_fara_cuvantul_agent(depozit):
    g = _ghid(depozit)
    for _, intrebare in fisa.GOLURI.values():
        assert f"### S5. {intrebare}" in g or f"### S6. {intrebare}" in g
    intrebari = [r for r in g.splitlines() if r.startswith("### ")]
    assert not any("agent" in r.lower() for r in intrebari)


def test_marcajul_demonstrativ_numai_la_cerere_si_fara_alta_diferenta(depozit):
    f = _fisa(depozit, {"README.md": "x"})
    normal, demo = interviu.ghid(f), interviu.ghid(f, demonstrativ=True)
    assert "Demonstrație, nu evaluare" in demo and "Demonstrație" not in normal
    assert demo.replace(interviu.DEMONSTRATIV + "\n\n", "") == normal


def test_partile_din_spec_in_ordinea_interviului_clasic(depozit):
    g = _ghid(depozit)
    parti = ["## Cum folosești ghidul", "## Înainte de interviu: ce arată proiectul", "## I. Deschiderea",
             "## II. Parcursul: CV, studii și cursuri", "## III. Întrebările cu notă: aceleași pentru toți",
             "## IV. Întrebările fără notă: pentru discuție", "*La ce folosesc:", "*De ce stau în afara notei:",
             "### Despre proiectul lui", "### Ale tale, dacă vrei", "## V. Încheierea", "**Concluzia recrutorului:**"]
    assert [g.index(x) for x in parti] == sorted(g.index(x) for x in parti)
    assert "Mai e ceva ce ați vrea să știm?" in g


def test_nota_e_unu_plus_da_nepusa_ramane_nepusa_si_numai_cele_7_intra_in_medie(depozit):
    g = _bifeaza(_ghid(depozit), {"S1": "da da nu", "S2": "da da da", "S6": "nu nu nu"})
    g = formular.scrie(g, {"L1": "Ce ați automatiza mâine?", "nota-L1": "un raport"})
    s = interviu.scor(g)
    assert s["standard"]["S1"] == 3 and s["standard"]["S2"] == 4 and s["standard"]["S6"] == 1
    assert s["standard"]["S3"] is None and "libere" not in s and s["amprenta"] == interviu.AMPRENTA
    assert s["medie"] == {"medie": 2.67, "punctate": 3, "din": 7}  # (3 + 4 + 1) / 3: nepusele nu scad
    assert s["pe_principii"]["metoda se schimbă după eșecuri"] == 1 and s["nivel_fisa"] == "prompter"
    assert s["pe_principii"]["arhitectura e exprimată și ținută la zi"] is None
    assert "S3 (construirea cu AI-ul, în cod): nepusă" in interviu.randare_scor(s)


@pytest.mark.parametrize("val", ["x", "poate", "1", "dap"])
def test_alta_valoare_decat_da_sau_nu_refuzata(depozit, val):
    with pytest.raises(ValueError, match="S1.2"):
        interviu.scor(_bifeaza(_ghid(depozit), {"S1": f"da {val} nu"}))


def test_intrebare_completata_pe_jumatate_refuzata(depozit):
    with pytest.raises(ValueError, match="S5: completată pe jumătate"):
        interviu.scor(_bifeaza(_ghid(depozit), {"S5": "da nu"}))


def test_ghid_scris_cu_alte_intrebari_sau_rand_sters_refuzate(depozit):
    g = _ghid(depozit)
    with pytest.raises(ValueError, match="alte întrebări"):
        interviu.scor(g.replace(f"ghid-interviu intrebari {interviu.AMPRENTA}", "ghid-interviu intrebari 000000000000"))
    with pytest.raises(ValueError, match="alte întrebări"):
        interviu.scor(g.replace(f"<!-- ghid-interviu intrebari {interviu.AMPRENTA} -->", "<!-- ghid-interviu v3 -->"))
    with pytest.raises(ValueError, match="S5.2"):
        interviu.scor(g.replace("- S5.2 [ ] ", ""))


def test_intrebarile_urmeaza_treptele_fisei_iar_etica_e_ultima(depozit):
    # decizia autorului, 14 octombrie: intrebarile 2-6 merg pe treptele 1-4; etica le priveste pe toate, la sfarsit
    assert [q[2] for q in interviu.INTREBARI][5:] == ["învățarea", "responsabilitatea pentru date și etica"]
    assert set(interviu.TREAPTA) == {q[0] for q in interviu.INTREBARI}
    g = _ghid(depozit)
    assert all(t in g for t in interviu.TREAPTA.values())
    # legatura cu interviul sta in „Cum folosesc” si in manual, nu in fisa (observatia autorului, 15 octombrie)
    assert "întrebările 5 și 6 îl confirmă" in " ".join(fisa.explicatii_scara())
