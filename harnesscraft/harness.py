"""Detectorii de harness: ce a construit omul in jurul agentului, citit din arborele de la `rev`.

De ce: semnalele de stare din `stare.py` sunt saturate pe esantion (runda 1), iar istoricul cu regulile reparate e la
nivelul intamplarii. Elementele de harness variaza intre proiecte si sunt chiar treptele scarii
(principii/DECIZII_INCHISE.md, nivelul provizoriu). Fapte, fara puncte: punctele le da `fisa.py`.

Ce se citeste:
  instructiunile - substanta (sectiuni, comenzi, interdictii) si prospetimea (caile citate exista);
  structura      - skills, comenzi, subagenti, reguli scoped (instructiuni in subdosare, `.cursor/rules`,
                   `.github/instructions`);
  portile        - hooks de agent (`.claude/settings.json` cu „hooks”, `.claude/hooks/`) si hooks git
                   (pre-commit, husky, lefthook, `.githooks`);
  MCP            - numai fisierele de configurare, nu proiectele care sunt servere MCP.
"""
import json
import re
from pathlib import PurePosixPath

from harnesscraft import instructiuni
from harnesscraft.extractori import CITAT, FISIER
from harnesscraft.gardieni import cere_clasament
from harnesscraft.manifest import git
from harnesscraft.stare import fisiere_la

SECTIUNE = re.compile(r"^#{1,6}\s+\S", re.M)
# o comanda: primul cuvant dintr-un `cod` sau dintr-un rand de bloc de cod e o unealta de linie de comanda
UNELTE = (r"npm|pnpm|yarn|npx|bun|bunx|node|deno|tsc|python3?|py|pip|uv|uvx|poetry|pytest|ruff|mypy|go|cargo|"
          r"rustc|make|just|dotnet|mvn|gradle|\./gradlew|bash|sh|git|gh|docker|composer|php|ruby|bundle|rake|"
          r"rails|eslint|prettier|biome|swift|xcodebuild|flutter|dart|mix|lein|clojure|clj|zig|cmake|ctest|"
          r"\./[\w./-]+|vitest|jest|playwright|tox|nox|hatch|pdm|conda|terraform|kubectl|helm|wp|nix")
COMANDA = re.compile(rf"^\$?\s*({UNELTE})(\s|$)")
# CLI-ul propriu al proiectului (`arhivar review --prepare`, `graphify update .`): o unealta necunoscuta,
# urmata de un flag sau de „.”. Corectura de citire dupa prima rulare pe esantion, inaintea oricarei
# comparatii cu clasamentul (rapoarte/fisa-runda1.md); pragurile nu s-au schimbat.
COMANDA_PROPRIE = re.compile(r"^\$?\s*[a-z][\w.-]*(\s+[\w:./-]+)*\s+(-{1,2}\w[\w-]*|\.)(\s|=|$)")
# PowerShell: un cmdlet `Verb-Substantiv` cu verbul din lista oficiala (`Get-Verb`, Windows PowerShell 5.1, plus Build si
# Deploy din PowerShell 7), sau un script local scris cu backslash (`.\build.ps1`). Verbul din lista tine afara
# `Content-Type` sau `X-Request-Id`. Reparat pe grupa A a rundei pe comenzile PowerShell
# (rapoarte/propunere-comenzi-powershell.md); aliasurile (`iex`, `copy`) si atribuirile (`$X = …`) nu se citesc.
VERBE_PS = (r"Add|Approve|Assert|Backup|Block|Build|Checkpoint|Clear|Close|Compare|Complete|Compress|Confirm|Connect|"
            r"Convert|ConvertFrom|ConvertTo|Copy|Debug|Deny|Deploy|Disable|Disconnect|Dismount|Edit|Enable|Enter|Exit|"
            r"Expand|Export|Find|Format|Get|Grant|Group|Hide|Import|Initialize|Install|Invoke|Join|Limit|Lock|Measure|"
            r"Merge|Mount|Move|New|Open|Optimize|Out|Ping|Pop|Protect|Publish|Push|Read|Receive|Redo|Register|Remove|"
            r"Rename|Repair|Request|Reset|Resize|Resolve|Restart|Restore|Resume|Revoke|Save|Search|Select|Send|Set|Show|"
            r"Skip|Split|Start|Step|Stop|Submit|Suspend|Switch|Sync|Test|Trace|Unblock|Undo|Uninstall|Unlock|Unprotect|"
            r"Unpublish|Unregister|Update|Use|Wait|Watch|Write")
COMANDA_PS = re.compile(rf"^(?:(?:{VERBE_PS})-[A-Z]\w*|\.\\[\w.\\/-]+)(\s|$)")
BLOC = re.compile(r"^```[^\n]*\n(.*?)^```", re.M | re.S)
LEGATURA = re.compile(r"\]\(([^)#\s]+)")
INTERDICTIE =re.compile(r"\b(never|do not|don't|must not|should not|avoid|niciodat\w*|nu se|interzis\w*)\b", re.I)
# imperativul negat romanesc („Nu adăuga…”, „**NU** modifica…”): „nu” la inceput de propozitie sau de rand de lista,
# urmat de un cuvant; nu si „nu e”, „nu are”, „nu există”, care descriu. Reparat pe grupa A a rundei pe reguli in romana
# (rapoarte/propunere-runda-reguli-in-romana.md); „nu se” il numara deja INTERDICTIE.
NU_IMPERATIV = re.compile(r"(?:^[ \t>]*(?:[-*+]|\d+[.)])?[ \t]*|[.!?:;—][ \t]+)(?:\*\*|__|_)?nu(?:\*\*|__|_)?[ \t]+"
                          r"(?!(?:e|este|sunt|are|au|a|am|ai|era|există|exista|poate|pot|se|mai|doar|numai)\b)\w",
                          re.M | re.I)

SKILL = re.compile(r"(^|/)\.[\w-]+/skills/.+/SKILL\.md$|(^|/)skills/[^/]+/SKILL\.md$", re.I)
COMENZI = re.compile(r"(^|/)\.(claude|cursor|gemini|opencode)/commands/.+\.(md|toml)$")
SUBAGENTI = re.compile(r"(^|/)\.(claude|codex|opencode)/agents/.+\.(md|toml)$")
REGULI_SCOPED = re.compile(r"(^|/)\.cursor/rules/|(^|/)\.github/instructions/.+\.md$")
HOOKS_AGENT = re.compile(r"(^|/)\.claude/hooks/")
HOOKS_GIT = re.compile(r"^(\.pre-commit-config\.ya?ml|\.husky/[^_][^/]*|lefthook\.ya?ml|\.lefthook\.ya?ml|"
                       r"\.githooks/[^/]+)$")
# o comanda de test scrisa direct in hook (scara cu teste automate: „teste care ruleaza automat”); un hook care cheama
# un script care la randul lui ruleaza testele nu se vede
TEST = re.compile(r"\b(pytest|unittest|(npm|pnpm|yarn|bun)( run)? test|(go|cargo|dotnet|mvn|gradle|gradlew|mix|swift|deno)"
                  r" test|make test|just test|zig build test|vitest|jest|rspec|phpunit|ctest|tox|nox)\b")
MCP = re.compile(r"^(\.mcp\.json|\.cursor/mcp\.json|\.vscode/mcp\.json|\.gemini/settings\.json)$")
# aria „la zi” (rapoarte/propuneri-la-zi-si-numele-pasului-1.md, incercarea detectorilor): regulile trimit la un document
# despre arhitectura sau decizii - dupa numele lui, sau citat pe un rand care pomeneste arhitectura. Formele mai largi
# („structura”, „design” pe rand) prindeau paragrafe fara legatura.
DOC = re.compile(r"\.(md|mdx|rst|txt|adoc)$|^docs?/|/docs?/", re.I)
DOC_ARH = re.compile(r"architect|arhitect|design|structur|adr|decision|decizi", re.I)
DOSAR_ADR = re.compile(r"(^|/)docs?/(adr|adrs|decisions)(/|$)", re.I)
RAND_ARH = re.compile(r"architect|arhitectur", re.I)
# regulile spun cum e organizat proiectul: un titlu despre arhitectura sau structura, sau un arbore de dosare desenat
TITLU = re.compile(r"^#{1,6}\s+(.*?)\s*#*$", re.M)
TITLU_ARH = re.compile(r"architect\w*|arhitectur\w*|structure\b|structur[ăa]\b|layout|organi[sz]ation|"
                       r"directory (layout|structure|map)|folder structure|module map|code ?map|codebase map", re.I)
ARBORE = re.compile(r"[├└]──")


def _text(depozit, rev, cale):
    return git(depozit, "-c", "core.quotepath=false", "show", f"{rev}:{cale}")


def _in_rand(text):
    """`cod` pe un singur rand, din textul fara blocuri de cod (un bloc ``` nu e un `cod`)."""
    return [c for c in CITAT.findall(BLOC.sub("", text)) if "\n" not in c]


def comenzi(text):
    """Comenzile din instructiuni: `cod` pe un rand si randurile blocurilor de cod."""
    candidati = _in_rand(text) + [l for b in BLOC.findall(text) for l in b.splitlines()]
    return sorted({c.strip() for c in candidati
                   if COMANDA.match(c.strip()) or COMANDA_PROPRIE.match(c.strip()) or COMANDA_PS.match(c.strip())})


def citate(text):
    """Caile citate: `cod` cu „/” sau nume de fisier si legaturile markdown relative. Textul liber nu:
    acolo „e.g” sau „Node.js” ar arata ca fisiere lipsa. Fara adrese web si fara sabloane."""
    termeni = [t for t in _in_rand(text) if "/" in t or FISIER.fullmatch(t.strip())] + LEGATURA.findall(text)
    rez = set()
    for t in termeni:
        t = t.strip().strip("'\"").removeprefix("./").rstrip("/")
        # in afara depozitului (`~/…`, `/usr/…`) sau sablon: nu se poate verifica in arbore
        if not t or " " in t or "www." in t or t.startswith(("/", "~", "..")) or \
                any(c in t for c in "*{}<>$[]()@:=~"):
            continue
        rez.add(t)
    return sorted(rez)


def exista(cale, cai, dosare):
    """O cale citata exista daca e un fisier sau un dosar din arbore, intreaga sau ca sfarsit de cale
    (instructiunile citeaza des relativ la un subdosar)."""
    return cale in cai or cale in dosare or any(c.endswith("/" + cale) for c in cai) or \
        any(d.endswith("/" + cale) for d in dosare)


def interdictii(text):
    """Cate limite pune regulile agentului: formele din INTERDICTIE si imperativul negat romanesc."""
    return len(INTERDICTIE.findall(text)) + len(NU_IMPERATIV.findall(text))


def documente_arhitectura(text):
    """Documentele despre arhitectura sau decizii la care trimit regulile."""
    def doc(c):
        return DOC.search(c) and (DOC_ARH.search(PurePosixPath(c).name) or DOSAR_ADR.search(c))
    pe_rand = {c for r in text.splitlines() if RAND_ARH.search(r) for c in citate(r) if DOC.search(c)}
    return sorted({c for c in citate(text) if doc(c)} | pe_rand)


def organizarea(text):
    """Cum spun regulile ca e organizat proiectul: titlurile despre structura si, daca e, arborele de dosare."""
    return [t for t in TITLU.findall(text) if TITLU_ARH.search(t)], bool(ARBORE.search(text))


def instructiunile(depozit, rev, cai):
    fisiere = sorted(c for c in cai if instructiuni.conventia(c))
    text = "\n".join(_text(depozit, rev, f) for f in fisiere)
    dosare = {str(p) for c in cai for p in PurePosixPath(c).parents if str(p) != "."}
    numite = citate(text)
    lipsa = [c for c in numite if not exista(c, set(cai), dosare)]
    titluri, arbore = organizarea(text)
    return {"documente_arhitectura": documente_arhitectura(text)[:20], "titluri_organizare": titluri[:20],
            "arbore_dosare": arbore,"fisiere": fisiere, "randuri": len(text.splitlines()),
            "sectiuni": len(SECTIUNE.findall(text)), "comenzi": comenzi(text)[:20],
            "interdictii": interdictii(text),
            "cai_citate": len(numite), "cai_lipsa": lipsa[:20], "cai_lipsa_numar": len(lipsa)}


def _hooks_in_setari(depozit, rev, cai):
    for c in cai:
        if c == ".claude/settings.json" or c.endswith("/.claude/settings.json"):
            try:
                if json.loads(_text(depozit, rev, c)).get("hooks"):
                    return c
            except ValueError:
                continue
    return None


def harness(depozit, rev="HEAD"):
    cere_clasament(depozit)
    cai = fisiere_la(depozit, rev)
    scoped = [c for c in cai if REGULI_SCOPED.search(c) or (instructiuni.conventia(c) and "/" in c
                                                          and not instructiuni.cursor(c))]
    setari = _hooks_in_setari(depozit, rev, cai)
    hooks_agent = sorted(c for c in cai if HOOKS_AGENT.search(c)) + ([setari] if setari else [])
    hooks_git = sorted(c for c in cai if HOOKS_GIT.match(c))
    return {"instructiuni": instructiunile(depozit, rev, cai),
            "skills": sorted(c for c in cai if SKILL.search(c)),
            "comenzi": sorted(c for c in cai if COMENZI.search(c)),
            "subagenti": sorted(c for c in cai if SUBAGENTI.search(c)),
            "reguli_scoped": sorted(scoped),
            "hooks_agent": hooks_agent, "hooks_git": hooks_git,
            "teste_in_hooks": [c for c in hooks_agent + hooks_git if TEST.search(_text(depozit, rev, c))],
            "mcp": sorted(c for c in cai if MCP.match(c))}
