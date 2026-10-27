"""Fisa: detectorii de harness pe depozite construite anume, apoi scara si punctele."""
import re
from pathlib import Path

from harnesscraft import fisa, termeni
from harnesscraft.harness import citate, comenzi, documente_arhitectura, harness, interdictii, organizarea

INSTR = """# Proiect
## Comenzi
Rulezi `npm test` inainte de commit.
```bash
pytest -q
```
## Reguli
Never edit `src/gen/` by hand. Vezi `src/app.py` si [doc](docs/arhitectura.md).
"""


def stare(teste=1, ci=True, ai=1):
    return {"teste": {"fisiere_test": teste}, "ci": {"fisiere_ci": [".github/workflows/ci.yml"] if ci else []},
            "licenta": {"fisier_licenta": "LICENSE", "tip": "MIT"},
            "chei": {"gasiri": 0, "inca_in_arbore": 0}, "transparenta_ai": {"commits_cu_urma_ai": ai}}


def test_comenzi_din_cod_si_din_blocuri_fara_blocul_luat_drept_cod():
    assert comenzi(INSTR) == ["npm test", "pytest -q"]


def test_cli_propriu_e_comanda_dar_un_nume_de_tip_nu():
    text = "Run `arhivar review --prepare`, then `graphify update .`; pass `std.mem.Allocator`, `-v`."
    assert comenzi(text) == ["arhivar review --prepare", "graphify update ."]


def test_comenzi_powershell_cmdlet_cu_verb_oficial_si_script_cu_backslash():
    text = ("Build: `.\\build.ps1`. Header `Content-Type`, id `X-Request-Id`, alias `iex (irm <url>)`.\n"
            "```powershell\nImport-Module ./M.psd1 -Force\nInvoke-Pester\nUpload-Thing -Path x\n```\n")
    assert comenzi(text) == [".\\build.ps1", "Import-Module ./M.psd1 -Force", "Invoke-Pester"]


def test_cai_citate_fara_text_liber_adrese_si_sabloane():
    text = INSTR + "\nde ex. e.g Node.js, `https://x.ro/a`, `~/.claude/x.md`, `src/*.py`, `<cale>/a.md`"
    assert citate(text) == ["docs/arhitectura.md", "src/app.py", "src/gen"]


def test_harness_gol_e_prompter(depozit):
    d = depozit()
    d.commit("start", {"README.md": "x", "app.py": "x"})
    f = fisa.fisa("d", stare(), harness(d.cale))
    assert f["nivel"] == 0 and f["nivel_nume"] == "prompter"
    assert "instrucțiuni cu secțiuni" in f["pentru_urmatorul"][0]


def test_instructiuni_substantiale_fara_structura_raman_configurator(depozit):
    d = depozit()
    d.commit("start", {"CLAUDE.md": INSTR, "src/app.py": "x", "src/gen/a.py": "x", "docs/arhitectura.md": "x"})
    h = harness(d.cale)
    assert h["instructiuni"]["cai_lipsa_numar"] == 0 and h["instructiuni"]["cai_citate"] == 3
    f = fisa.fisa("d", stare(), h)
    assert f["nivel"] == 1
    # trimite la `docs/arhitectura.md`, dar titlurile nu spun cum e organizat proiectul
    assert f["principii"]["arhitectura e exprimată și ținută la zi"]["puncte"] == 3.0


def test_structura_si_verificare_dau_constructor_iar_portile_metodolog(depozit):
    d = depozit()
    fis = {"CLAUDE.md": INSTR, "src/app.py": "x", "src/gen/a.py": "x", "docs/arhitectura.md": "x",
           ".claude/skills/rel/SKILL.md": "x"}
    d.commit("start", fis)
    assert fisa.fisa("d", stare(), harness(d.cale))["nivel"] == 2
    assert fisa.fisa("d", stare(ci=False), harness(d.cale))["nivel"] == 1
    d.commit("hooks", {".claude/settings.json": '{"hooks": {"PreToolUse": []}}'})
    f = fisa.fisa("d", stare(), harness(d.cale))
    assert f["nivel"] == 3 and f["pentru_urmatorul"] == []
    assert f["principii"]["verificarea există și e folosită"]["puncte"] == 3.0


def test_scara_v2_un_hook_care_ruleaza_testele_tine_locul_ci(depozit):
    d = depozit()
    d.commit("start", {"CLAUDE.md": INSTR, "src/app.py": "x", ".claude/skills/rel/SKILL.md": "x",
                       ".githooks/pre-commit": "#!/bin/sh\necho gata\n"})
    assert fisa.fisa("d", stare(ci=False), harness(d.cale))["nivel"] == 1
    d.commit("teste in hook", {".githooks/pre-commit": "#!/bin/sh\npy -m unittest discover -s teste\n"})
    h = harness(d.cale)
    assert h["teste_in_hooks"] == [".githooks/pre-commit"]
    assert fisa.fisa("d", stare(ci=False), h)["nivel"] == 2


def test_cai_lipsa_opresc_metodologul(depozit):
    d = depozit()
    d.commit("start", {"CLAUDE.md": INSTR, "src/app.py": "x", ".claude/skills/rel/SKILL.md": "x",
                       ".husky/pre-commit": "npm test"})
    h = harness(d.cale)
    assert h["hooks_git"] == [".husky/pre-commit"]
    f = fisa.fisa("d", stare(), h)
    assert f["nivel"] == 2 and "ținute la zi" in f["pentru_urmatorul"][0]
    # 3 citate, 2 lipsă; trimiterea la `docs/arhitectura.md` se numără și când documentul lipsește (îl prinde al doilea)
    assert f["principii"]["arhitectura e exprimată și ținută la zi"]["puncte"] == 2.0


def test_instructiuni_in_subdosar_sunt_reguli_scoped_iar_mcp_numai_configurarea(depozit):
    d = depozit()
    d.commit("start", {"CLAUDE.md": INSTR, "web/CLAUDE.md": "# web", "server/mcp.json": "{}", ".mcp.json": "{}"})
    h = harness(d.cale)
    assert h["reguli_scoped"] == ["web/CLAUDE.md"] and h["mcp"] == [".mcp.json"]


def test_fisa_spune_golurile_si_ca_e_necalibrata(depozit):
    d = depozit()
    d.commit("start", {"CLAUDE.md": INSTR})
    text = fisa.randare(fisa.fisa("d", stare(), harness(d.cale)))
    assert "necalibrat" in text.lower() and "metoda se schimbă după eșecuri" in text


# ── cele doua redari: tehnica (neschimbata, la caracter) si pentru recrutor ──

def _h(skills=(), hooks_git=(), hooks_agent=(), teste_in_hooks=(), cai=17, lipsa=(), docs=(), titluri=(), arbore=False):
    return {"instructiuni": {"sectiuni": 8, "comenzi": ["pytest -q", "npm test"], "interdictii": 5,
                             "fisiere": ["CLAUDE.md"], "cai_citate": cai, "cai_lipsa_numar": len(lipsa),
                             "cai_lipsa": list(lipsa), "documente_arhitectura": list(docs),
                             "titluri_organizare": list(titluri), "arbore_dosare": arbore},
            "skills": list(skills), "comenzi": [], "subagenti": [], "reguli_scoped": [], "hooks_git": list(hooks_git),
            "hooks_agent": list(hooks_agent), "teste_in_hooks": list(teste_in_hooks), "mcp": []}


ISTORIC = {"cicatrice": {"acceptate": 1, "cazuri": 12}, "arhitectura": {"acceptate": 5, "cazuri": 5}}


def _fise():
    """Patru fise, cate una pe treapta, cu dovezi de toate felurile: are, lipseste, chei, licenta, cai lipsa."""
    chei = stare(teste=0, ci=False, ai=0)
    chei["chei"], chei["licenta"] = {"gasiri": 2, "inca_in_arbore": 1}, {"fisier_licenta": None, "tip": None}
    neliceniat = stare(ci=False)
    neliceniat["licenta"], neliceniat["chei"] = {"fisier_licenta": "LICENSE", "tip": "necunoscut"}, {"gasiri": 1, "inca_in_arbore": 0}
    return [fisa.fisa("prompter", chei, {**_h(cai=2), "instructiuni": {**_h(cai=2)["instructiuni"], "interdictii": 0}}),
            fisa.fisa("configurator", neliceniat, _h(docs=["ARCHITECTURE.md", "docs/adr/0001.md"],
                                                     titluri=["Project Structure", "Arhitectura"])),
            fisa.fisa("constructor", stare(teste=45), _h(skills=["a", "b"], hooks_git=[".githooks/pre-commit"],
                                                     cai=17, lipsa=["docs/vechi.md", "src/x.py", "a/b.md", "c.md"],
                                                     arbore=True)),
            fisa.fisa("metodolog", stare(teste=45, ai=34), _h(skills=["a"], hooks_agent=[".claude/hooks/x.py"],
                                                              lipsa=["docs/vechi.md"], docs=["docs/DECISIONS.md"]),
                      ISTORIC)]


DATE = Path(__file__).parent / "date"
def test_redarea_tehnica_ramane_neschimbata_la_caracter():
    # textul din terminal; fisierul s-a scris cu `randare` dinaintea redarii pentru recrutor,
    # refacut o data, la aria „la zi” in patru verificari: diff-ul a atins numai randurile ei si totalurile
    asteptat = (DATE / "fisa-randare-tehnica.md").read_text(encoding="utf-8")
    assert "\n\n=====\n\n".join(fisa.randare(f) for f in _fise()) == asteptat


def test_pentru_recrutor_termenii_numai_in_paranteza_dupa_explicatie_si_cifrele_cu_virgula():
    for f in _fise():
        text = fisa.pentru_recrutor(f)
        assert termeni.neexplicate(text) == [], (f["proiect"], termeni.neexplicate(text))
        assert not re.search(r"\d\.\d", text) and "✓" not in text and "✗" not in text


def test_pentru_recrutor_toate_treptele_cu_a_candidatului_marcata_fara_istoric():
    for f in _fise():
        text = fisa.pentru_recrutor(f)
        assert all(f"{i + 1}. {n[0].upper() + n[1:]}" in text for i, n in enumerate(fisa.NUME_TREPTE))
        marcat = [r for r in text.splitlines() if r.startswith("| ▶")]
        assert len(marcat) == 1 and f"{f['nivel'] + 1}. " in marcat[0]
    # istoricul: in afara scorului, picat la nivelul intamplarii; ramane numai in redarea tehnica
    assert "1 din 12" in fisa.randare(_fise()[3])
    assert "1 din 12" not in fisa.pentru_recrutor(_fise()[3]) and "schimbări de structură" not in fisa.pentru_recrutor(_fise()[3])


def test_pentru_recrutor_aceleasi_cifre_ca_redarea_tehnica():
    for f in _fise():
        text = fisa.pentru_recrutor(f)
        assert f"Punctajul proiectului: {f['total']:g} puncte din 16 posibile".replace(".", ",") in text
        for nume, x in f["principii"].items():
            assert f"{fisa.ARII_RECRUTOR[nume]}: {x['puncte']:g} din 4".replace(".", ",") in text


def test_golurile_trimit_la_intrebarea_care_le_acopera_si_orice_lipsa_are_cuvinte_de_recrutor():
    from harnesscraft.interviu import INTREBARI
    for gol, (_, _, q) in fisa.GOLURI_RECRUTOR.items():
        assert gol in dict((x[0], x[1]) for x in INTREBARI)[f"S{q}"]
    assert set(fisa.GOLURI_RECRUTOR) == set(fisa.GOLURI) and set(fisa.ARII_RECRUTOR) == set(_fise()[0]["principii"])
    assert len(fisa.lipsa_pentru_recrutor(list(fisa.CE_LIPSESTE.values()))) == len(fisa.CE_LIPSESTE)
    assert [fisa._buc(n, "fișier", "fișiere") for n in (1, 2, 19, 20, 45, 100, 101)] == \
        ["1 fișier", "2 fișiere", "19 fișiere", "20 de fișiere", "45 de fișiere", "100 de fișiere", "101 fișiere"]


def test_punctajul_b_patru_verificari_da_nu_pe_fiecare_arie():
    for f in _fise():
        for nume, x in f["principii"].items():
            assert len(x["fapte"]) == 4 and len(x["dovezi"]) == 4, nume
            assert x["puncte"] == sum(ok for _, ok, _ in x["fapte"])
    # o cheie scoasa din cod ramane in istoric: 1 din 2 pe chei; licenta nerecunoscuta: 0
    resp = _fise()[1]["principii"]["responsabilitatea"]["fapte"]
    assert [ok for _, ok, _ in resp] == [True, False, False, True]
    # la zi, patru verificari diferite: destule cai, cel mult una din cinci lipsa, trimitere, organizare
    la_zi = [[ok for _, ok, _ in f["principii"]["arhitectura e exprimată și ținută la zi"]["fapte"]] for f in _fise()]
    assert la_zi == [[False, False, False, False], [True, True, True, True], [True, False, False, True],
                     [True, True, True, False]]


def test_interdictiile_in_romana_imperativul_negat_nu_si_descrierea():
    interzic = """- Nu sterge datele de test.
- **NU** publica fara cerere.
1. Nu folosiți `eval`. Rulezi testele; nu modifica schema.
"""
    descriu = """Proiectul nu are backend. Nu e o aplicatie, nu există server.
Ce nu se vede: nimic. Nu doar un link, nu mai există.
"""
    assert interdictii(interzic) == 4
    # „nu se” il numara INTERDICTIE, o singura data; restul descriu
    assert interdictii(descriu) == 1


def test_la_zi_trimiterea_la_arhitectura_si_organizarea_fara_zgomotul_din_proba():
    # formele largi prindeau aceste randuri in proba pe esantion
    zgomot = """This version has breaking changes: file structure may differ, read `node_modules/next/dist/docs/`.
Keep the structural type in `src/types.ts`; design notes live in `NOTES.md`.
## Structured output
"""
    assert documente_arhitectura(zgomot) == [] and organizarea(zgomot) == ([], False)
    bun = """For internal architecture, see [the doc](docs/intern.md).
| când se discută arhitectura | `ghid/P.md` |
Decizii: `ghid/DECIZII.md`, `docs/adr/0001-db.md`, `ARCHITECTURE.md`.
## Project Structure ##
```
src/
├── app.py
└── db.py
```
"""
    assert documente_arhitectura(bun) == ["ARCHITECTURE.md", "docs/adr/0001-db.md", "docs/intern.md",
                                          "ghid/DECIZII.md", "ghid/P.md"]
    assert organizarea(bun) == (["Project Structure"], True)


def test_o_fisa_cu_verificarile_vechi_pe_la_zi_cere_analiza_din_nou():
    f = _fise()[1]
    assert fisa.actuala(f)
    assert {d[0] for x in f["principii"].values() for d in x["fapte"]} == fisa.CHEI
    veche = {**f, "principii": {**f["principii"], "arhitectura e exprimată și ținută la zi": {
        **f["principii"]["arhitectura e exprimată și ținută la zi"],
        "fapte": [["cai_destule", True, 17], ["cai_80", True, None], ["cai_90", True, None], ["cai_toate", True, 0]]}}}
    assert not fisa.actuala(veche)
