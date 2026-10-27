"""Fisa dinaintea interviului: scor 0-4 pe principiile schemei, nivelul provizoriu, dovezi, goluri.

NECALIBRAT. Regulile s-au scris si comis inaintea rularii pe esantion (principii/DECIZII_INCHISE.md,
nivelul provizoriu; rapoarte/plan-fisa-interviu.md). Calculeaza numai codul; un model nu da nivelul.

Nivelul e o scara cu porti, nu o suma (ideea din `harness-score`): fiecare treapta o cere pe cea
dinainte, iar fisa spune ce lipseste pentru urmatoarea. Principiile fara semnal mecanic raman goluri,
cu intrebarea de interviu care le acopera: o cifra inventata ar ascunde ca git-ul nu le vede.
Istoricul cu regulile reparate apare numai ca informatie, in afara scorului.
"""
from pathlib import Path

NIVELURI = ["prompter", "configurator", "constructor de sistem", "metodolog (provizoriu)"]
# scara cu teste automate: verificarea cere teste care ruleaza automat (CI sau un hook cu o comanda de test), nu CI anume.
# Decisa dupa prima rulare, cand proiectele autorului ieseau oprite numai de CI (DECIZII_INCHISE).
SCARA = 2
MIN_SECTIUNI = 2      # un fisier cu o singura sectiune e o notita, nu o structura
MIN_COMENZI = 1
MIN_INTERDICTII = 1
MIN_CAI = 3           # sub 3 cai citate, proportia celor existente nu spune nimic
MAX_LIPSA = 0.2       # „tinute la zi”: cel mult o cale din cinci nu mai exista

NOTA = ("Scor necalibrat, nivel provizoriu: calculate din reguli scrise, fără validare pe candidați reali. "
        "Arată ce se vede în git; interviul confirmă sau infirmă.")

GOLURI = {
    "metoda se schimbă după eșecuri": (
        "Din git nu se vede: semnalul de cicatrice a ieșit la nivelul întâmplării.",
        "Cum s-a schimbat felul în care lucrați cu AI-ul de când ați început? Ce v-a făcut să schimbați?"),
    "manual sau agent, cu cost": (
        "Din git nu se vede ce a ales omul să facă singur.",
        "Ce nu lăsați AI-ului să facă, deși ar putea? De ce?"),
}


def _porti(s, h):
    return {
        "substanta": (h["instructiuni"]["sectiuni"] >= MIN_SECTIUNI and len(h["instructiuni"]["comenzi"]) >= MIN_COMENZI
                      and h["instructiuni"]["interdictii"] >= MIN_INTERDICTII),
        "structura": bool(h["skills"] or h["comenzi"] or h["subagenti"] or h["reguli_scoped"]),
        "verificare": bool(s["teste"]["fisiere_test"] and (s["ci"]["fisiere_ci"] or h["teste_in_hooks"])),
        "porti": bool(h["hooks_agent"] or h["hooks_git"]),
        "la_zi": _la_zi(h["instructiuni"]),
    }


def _la_zi(i):
    return i["cai_citate"] >= MIN_CAI and i["cai_lipsa_numar"] / i["cai_citate"] <= MAX_LIPSA


TREPTE = [("substanta",), ("structura", "verificare"), ("porti", "la_zi")]
CE_LIPSESTE = {"substanta": "instrucțiuni cu secțiuni, comenzi și interdicții",
               "structura": "structură: skills, comenzi, subagenți sau reguli scoped",
               "verificare": "teste care rulează automat: CI, sau un hook care rulează testele",
               "porti": "porți automate: hooks de agent sau de git",
               "la_zi": f"instrucțiuni ținute la zi: cel puțin {MIN_CAI} căi citate, cel mult "
                        f"{MAX_LIPSA:.0%} lipsă"}


def nivel(porti):
    """Treapta atinsa si ce lipseste pentru urmatoarea."""
    n = 0
    for treapta in TREPTE:
        lipsa = [p for p in treapta if not porti[p]]
        if lipsa:
            return n, [CE_LIPSESTE[p] for p in lipsa]
        n += 1
    return n, []


def principii(s, h):
    i = h["instructiuni"]
    verif = [("teste", bool(s["teste"]["fisiere_test"]), f"{s['teste']['fisiere_test']} fișiere de test"),
             ("CI", bool(s["ci"]["fisiere_ci"]), ", ".join(s["ci"]["fisiere_ci"][:3])),
             ("hooks git", bool(h["hooks_git"]), ", ".join(h["hooks_git"][:3])),
             ("hooks de agent", bool(h["hooks_agent"]), ", ".join(h["hooks_agent"][:3]))]
    structura = h["skills"] + h["comenzi"] + h["subagenti"] + h["reguli_scoped"]
    spec = [("secțiuni", i["sectiuni"] >= MIN_SECTIUNI, f"{i['sectiuni']} secțiuni în {', '.join(i['fisiere'][:3])}"),
            ("comenzi", len(i["comenzi"]) >= MIN_COMENZI, "; ".join(f"`{c}`" for c in i["comenzi"][:3])),
            ("interdicții", i["interdictii"] >= MIN_INTERDICTII, f"{i['interdictii']} interdicții"),
            ("structură", bool(structura), f"{len(h['skills'])} skills, {len(h['comenzi'])} comenzi, "
                                           f"{len(h['subagenti'])} subagenți, {len(h['reguli_scoped'])} reguli scoped")]
    # punctajul B: patru verificari da / nu pe fiecare arie, cate un punct (DECIZII_INCHISE, 14 octombrie 2026)
    citate, lipsa = i["cai_citate"], i["cai_lipsa_numar"]
    destule = citate >= MIN_CAI
    parte = lipsa / citate if citate else 1.0
    lipsa_txt = f"; lipsă: {', '.join(f'`{c}`' for c in i['cai_lipsa'][:3])}" if i["cai_lipsa"] else ""
    # patru verificari diferite, nu trei praguri ale aceleiasi masuratori (DECIZII_INCHISE, aria „la zi”)
    docs, titluri, arbore = i["documente_arhitectura"], i["titluri_organizare"], i["arbore_dosare"]
    organizare = [f"„{t}”" for t in titluri[:3]] + (["arbore de dosare"] if arbore else [])
    arh = [("cel puțin 3 căi citate", destule, f"{citate} căi citate"),
           (f"cel mult {MAX_LIPSA:.0%} lipsă", destule and parte <= MAX_LIPSA,
            f"{citate - lipsa} din {citate} există{lipsa_txt}"),
           ("trimit la arhitectură sau decizii", bool(docs), ", ".join(f"`{c}`" for c in docs[:3])),
           ("spun cum e organizat proiectul", bool(organizare), "; ".join(organizare))]
    c, l, ai = s["chei"], s["licenta"], s["transparenta_ai"]
    licenta = "lipsă" if not l["fisier_licenta"] else "nerecunoscută" if l["tip"] == "necunoscut" else l["tip"]
    # gasirile din teste, exemple si documentatie si cele numai dupa forma generala nu scad; se spun langa (stare.fel_cheie)
    def langa(k):
        return "".join(f"; {c[fel][k]} {cum}" for fel, cum in (("de_proba", "de test sau exemplu"),
                                                                 ("generica", "numai după forma generală"))
                       if c.get(fel, {}).get(k))
    resp = [("nicio cheie în cod acum", not c["inca_in_arbore"], f"{c['inca_in_arbore']} în arbore{langa('inca_in_arbore')}"),
            ("nicio cheie în istoric", not c["gasiri"], f"{c['gasiri']} găsiri{langa('gasiri')}"),
            ("licență recunoscută", licenta not in ("lipsă", "nerecunoscută"), licenta),
            ("urma AI în commit-uri", bool(ai["commits_cu_urma_ai"]), f"{ai['commits_cu_urma_ai']} commit-uri o declară")]

    def arie(randuri, fapte):
        # `dovezi`: textul tehnic (terminal); `fapte`: aceleasi verificari, ca date, pentru recrutor
        return {"puncte": float(sum(ok for _, ok, _ in randuri)),
                "dovezi": [f"{'✓' if ok else '✗'} {n}: {d}" if d else f"{'✓' if ok else '✗'} {n}" for n, ok, d in randuri],
                "fapte": [[cheie, bool(ok), v] for (_, ok, _), (cheie, v) in zip(randuri, fapte)]}

    return {
        "verificarea există și e folosită": arie(
            [(n, ok, d if ok else "") for n, ok, d in verif],
            [("teste", s["teste"]["fisiere_test"]), ("ci", None), ("hooks_git", None), ("hooks_agent", None)]),
        "ce e de făcut e specificat dinainte": arie(
            spec, [("sectiuni", [i["sectiuni"], i["fisiere"][:3]]), ("comenzi", len(i["comenzi"])),
                   ("interdictii", i["interdictii"]), ("sarcini", len(structura))]),
        "arhitectura e exprimată și ținută la zi": arie(
            arh, [("cai_destule", citate), ("cai_80", lipsa), ("documente_arhitectura", docs[:3]),
                  ("organizare", organizare)]),
        "responsabilitatea": arie(
            resp, [("chei_acum", None), ("chei_istoric", None), ("licenta", licenta),
                   ("ai", ai["commits_cu_urma_ai"])]),
    }


def fisa(nume, s, h, istoric=None):
    p = principii(s, h)
    n, lipsa = nivel(_porti(s, h))
    return {"proiect": nume, "scara": SCARA, "nivel": n, "nivel_nume": NIVELURI[n], "pentru_urmatorul": lipsa,
            "principii": p, "total": round(sum(x["puncte"] for x in p.values()), 1), "maxim": 4.0 * len(p),
            "goluri": GOLURI, "istoric_informativ": istoric, "nota": NOTA}


def randare(f):
    r = [f"# Fișa dinaintea interviului — „{f['proiect']}”", "", f"*{f['nota']}*", "",
         f"## Nivel provizoriu: **{f['nivel_nume']}** ({f['nivel'] + 1} din {len(NIVELURI)})", ""]
    if f["pentru_urmatorul"]:
        r += [f"Pentru {NIVELURI[f['nivel'] + 1]} lipsește: " + "; ".join(f["pentru_urmatorul"]) + ".", ""]
    r += [f"## Scor pe principii: {f['total']:g} din {f['maxim']:g}", ""]
    for nume, x in f["principii"].items():
        r += [f"**{nume}: {x['puncte']:g} din 4**", ""] + [f"- {d}" for d in x["dovezi"]] + [""]
    r += ["## Goluri — de acoperit la interviu", ""]
    for nume, (motiv, intrebare) in f["goluri"].items():
        r += [f"**{nume}.** {motiv}", f"> {intrebare}", ""]
    if f["istoric_informativ"]:
        i = f["istoric_informativ"]
        r += ["## Istoricul (informație, în afara scorului)", "",
              f"- cicatrici: {i['cicatrice']['acceptate']} din {i['cicatrice']['cazuri']} modificări ale instrucțiunilor",
              f"- arhitectura ținută la zi: {i['arhitectura']['acceptate']} din {i['arhitectura']['cazuri']} "
              "schimbări de structură", ""]
    r += ["## Ce nu se vede din fișa asta", "",
          "- dacă testele sunt bune; calitatea codului; munca fără urme în git;",
          "- un harness bogat arată un proiect pregătit pentru agent, nu că omul e bun: se poate și copia;",
          "- licențele dependențelor; o cheie prinsă numai de forma generală (se spune lângă, nu scade).", ""]
    return "\n".join(r)


# ── Pentru recrutor: aceleasi cifre si reguli, alte cuvinte (rapoarte/plan-fisa-pentru-recrutor.md) ──
# Un termen tehnic apare numai in paranteza, dupa explicatia lui; istoricul (in afara scorului, picat la nivelul
# intamplarii) nu apare. Redarea tehnica de mai sus ramane cea din terminal.

NUME_TREPTE = ["prompter", "configurator", "constructor de sistem", "metodolog"]
TREPTE_RECRUTOR = [
    "Lucrează cu AI-ul prin cereri de la caz la caz; regulile scrise pentru AI, dacă există, sunt sumare.",
    "A scris pentru AI regulile proiectului: cum e organizat, ce comenzi folosește, ce nu are voie să facă.",
    "În plus, i-a dat AI-ului instrucțiuni pe sarcini și are teste care verifică singure codul.",
    "În plus, verificări care rulează singure, la fiecare salvare a codului sau cât lucrează AI-ul, iar regulile sunt "
    "ținute la zi. Din proiect se vede numai provizoriu; interviul confirmă."]
LIPSA_RECRUTOR = {
    "substanta": "reguli scrise pentru AI, pe părți, cu comenzile proiectului și cu ce nu are voie să facă",
    "structura": "instrucțiuni pentru AI pe sarcini anume (skills, subagenți)",
    "verificare": "programe care verifică automat codul (teste), pornite singure: pe server, la fiecare trimitere a "
                  "codului (CI), sau la fiecare salvare a codului",
    "porti": "verificări care rulează singure, la fiecare salvare a codului sau cât lucrează AI-ul (hooks)",
    "la_zi": f"reguli ținute la zi: cel puțin {MIN_CAI} fișiere enunțate în ele, iar dintre acestea cel mult unul din "
             f"{round(1 / MAX_LIPSA)} să lipsească"}
_POARTA = {text: poarta for poarta, text in CE_LIPSESTE.items()}
ARII_RECRUTOR = {"verificarea există și e folosită": "Își verifică munca",
                 "ce e de făcut e specificat dinainte": "Spune dinainte ce vrea",
                 "arhitectura e exprimată și ținută la zi": "Ține la zi descrierea proiectului",
                 "responsabilitatea": "Lucrează responsabil (date, licență, transparență)"}
# numarul intrebarii din interviu care acopera golul: aceeasi legatura ca in `interviu.INTREBARI` (testul o verifica)
GOLURI_RECRUTOR = {
    "metoda se schimbă după eșecuri": ("Dacă își schimbă felul de lucru după greșeli",
                                       "Din istoricul proiectului nu se vede sigur.", 6),
    "manual sau agent, cu cost": ("Ce sarcini încredințează AI-ului și pe care le face personal",
                                  "Din istoricul proiectului nu se vede ce a ales omul.", 5)}
NOTA_RECRUTOR = ("Punctaj necalibrat, treaptă provizorie: le calculează programul din reguli scrise, fără validare pe "
                 "candidați reali. Arată ce se vede în istoricul proiectului; interviul confirmă sau infirmă.")


def _nr(x):
    return f"{x:g}".replace(".", ",")


def _buc(n, sg, pl):
    """Numaratul romanesc: 1 fisier, 2 fisiere, 20 de fisiere."""
    return f"1 {sg}" if n == 1 else f"{n} de {pl}" if n % 100 >= 20 or (n and n % 100 == 0) else f"{n} {pl}"


def lipsa_pentru_recrutor(lipsa):
    """`pentru_urmatorul` (si `lipseste` din drum), in cuvintele recrutorului."""
    return [LIPSA_RECRUTOR[_POARTA[t]] for t in lipsa]


def _la_proba(text):
    """La fisa probei, ce confirma interviul confirma discutia de dupa proba: interviul e al portofoliului."""
    return text.replace("interviul confirmă", "discuția de după probă confirmă")


def explicatii_scara(proba=False):
    """De unde vin treptele, de ce o scara, cum o folosesti: in „Cum folosesc” si in manual, nu in fisa (observatia
    autorului, 15 octombrie: in fisa ingreunau citirea)."""
    return ["- **De unde vin:** din metoda autorului de lucru cu AI-ul și din ideea unei scări pe care se urcă numai "
            "pas cu pas, încercate pe 36 de proiecte open-source (24 în runda 1, 12 în runda 2).",
            "- **De ce o scară:** fiecare treaptă are condițiile ei, iar o treaptă se atinge numai dacă sunt "
            "îndeplinite și condițiile tuturor treptelor de dedesubt. Un proiect cu "
            "teste, dar fără reguli scrise pentru AI, rămâne la treapta 1.",
            ("- **Cum o folosești:** treapta arată cum și-a organizat lucrul cu AI-ul pe programul probei. O ai în "
             "față la discuție, lângă conversațiile predate." if proba else
             "- **Cum o folosești:** treapta îți spune la ce să fii atent la interviu. Întrebările 2–6 din interviu "
             "urmează aceleași trepte, de la 1 la 4; la metodolog, întrebările 5 și 6 îl confirmă.")]


def scara_recrutor(nivel=None, proba=False, explicatii=True):
    """Cele patru trepte, cu a candidatului marcata; tot aici, legatura cu cele patru arii. Cu `explicatii`, si de
    unde vin (manualul); fisa le lasa ajutorului. Cu `proba`, folosirea e la discutia de dupa proba, nu la interviu."""
    r = ["| | Treapta | Ce arată proiectul |", "|---|---|---|"]
    for i, (n, t) in enumerate(zip(NUME_TREPTE, TREPTE_RECRUTOR)):
        t = _la_proba(t) if proba else t
        g = "**" if i == nivel else ""
        r.append(f"| {'▶' if i == nivel else ''} | {g}{i + 1}. {n[0].upper() + n[1:]}{g} | {t} |")
    return r + [""] + (explicatii_scara(proba) + [""] if explicatii else []) + [
                "**Treapta** spune *ce fel* de lucru cu AI-ul arată proiectul: da sau nu, condiție cu condiție, de jos în "
                "sus. **Punctajul** (cel mult 16 puncte: câte 4 pentru fiecare din cele patru arii) spune *cât de bine*, "
                "cu puncte și parțial. Nu se înlocuiesc: două proiecte pe aceeași treaptă pot avea punctaje diferite."]


def _enunt(cheie, ok, v):
    """Ce se verifica, ca enunt, si ce s-a gasit (cand ajuta)."""
    if cheie == "teste":
        return "Are programe care verifică automat codul (teste)" + (f": {_buc(v, 'fișier', 'fișiere')}" if ok else "")
    if cheie == "ci":
        return "Are verificarea automată pe server la fiecare trimitere a codului (CI)"
    if cheie == "hooks_git":
        return "Are verificări care rulează singure la fiecare salvare a codului (hooks git)"
    if cheie == "hooks_agent":
        return "Are verificări care rulează singure cât lucrează AI-ul (hooks de agent)"
    if cheie == "sectiuni":
        return (f"Regulile scrise pentru AI au cel puțin {MIN_SECTIUNI} părți"
                + (f": {_buc(v[0], 'parte', 'părți')}, în {', '.join(v[1])}" if v[0] else ""))
    if cheie == "comenzi":
        return "Regulile conțin comenzile proiectului" + (f": {_buc(v, 'comandă', 'comenzi')}" if ok else "")
    if cheie == "interdictii":
        return "Regulile spun ce nu are voie AI-ul să facă" + (f": {_buc(v, 'regulă', 'reguli')}" if ok else "")
    if cheie == "sarcini":
        return "Are instrucțiuni pentru AI pe sarcini anume (skills, subagenți)" + (f": {v} în total" if ok else "")
    if cheie == "cai_destule":
        return f"Regulile enunță cel puțin {MIN_CAI} fișiere ale proiectului: {v}"
    if cheie == "cai_80":
        return f"Cel puțin {round((1 - MAX_LIPSA) * 5)} din 5 fișiere enunțate există" + \
            (f": {_buc(v, 'fișier lipsește', 'fișiere lipsesc')}" if v else "")
    if cheie == "documente_arhitectura":
        return "Regulile trimit la un document despre arhitectura proiectului sau despre deciziile luate" + \
            (f": {', '.join(v)}" if v else "")
    if cheie == "organizare":
        return "Regulile spun cum e organizat proiectul, pe părți și dosare" + (f": {', '.join(v)}" if v else "")
    if cheie == "chei_acum":
        return "Nicio parolă sau cheie de acces scrisă acum în cod"
    if cheie == "chei_istoric":
        return "Nicio parolă sau cheie de acces nici în istoricul codului"
    if cheie == "licenta":
        return "Are o licență recunoscută, adică spune cine are voie să folosească proiectul" + \
            {"lipsă": ": lipsește", "nerecunoscută": ": nerecunoscută"}.get(v, f": {v}")
    return "A declarat în istoric unde a lucrat cu AI-ul" + \
        (f": în {_buc(v, 'salvare de cod', 'salvări de cod')}" if v else "")


CHEI = {"teste", "ci", "hooks_git", "hooks_agent", "sectiuni", "comenzi", "interdictii", "sarcini", "cai_destule",
        "cai_80", "documente_arhitectura", "organizare", "chei_acum", "chei_istoric", "licenta", "ai"}


def actuala(f):
    """O fisa.json veche (fara `fapte`, sau cu verificarile de dinaintea ariei „la zi” in patru) nu se reda: cere
    „Analizează din nou”, altfel `_enunt` ar scrie alt enunt."""
    return all("fapte" in x and all(d[0] in CHEI for d in x["fapte"]) for x in f["principii"].values())


def _dovada(cheie, ok, v):
    """Un rand al ariei, la fel peste tot: enuntul, apoi da / nu si punctul."""
    return _enunt(cheie, ok, v) + (" — **da**, 1 punct" if ok else " — **nu**, 0 puncte")


def pentru_recrutor(f, proba=False, nume=None):
    """Fisa, pentru recrutor: pe ecranul pasului 1 si in raport. Aceleasi cifre ca `randare`. Cu `proba`, fisa
    programului predat la proba: alt titlu, fara trimiterile la interviu si la proba, care sunt ale portofoliului.
    In titlu, numele proiectului (`nume`, altfel dosarul), nu calea: la un link, calea e a clonei."""
    n = f["nivel"]
    nume = nume or Path(f["proiect"]).name or f["proiect"]
    r = [f"# Fișa {'proiectului probei' if proba else 'proiectului de portofoliu'} — „{nume}”", "", f"*{_la_proba(NOTA_RECRUTOR) if proba else NOTA_RECRUTOR}*", "",
         f"## Treapta: **{NUME_TREPTE[n]}** ({n + 1} din {len(NUME_TREPTE)})"
         + ((" · provizoriu, de confirmat la discuție" if proba else " · provizoriu, de confirmat la interviu")
            if n == len(NUME_TREPTE) - 1 else ""), ""]
    if f["pentru_urmatorul"]:
        r += [f"Pentru treapta următoare, {NUME_TREPTE[n + 1]}, lipsește: "
              + "; ".join(lipsa_pentru_recrutor(f["pentru_urmatorul"])) + ".", ""]
    else:
        r += ["E treapta cea mai înaltă.", ""]
    r += scara_recrutor(n, proba, explicatii=False) + ["", f"## Punctajul proiectului: {_nr(f['total'])} puncte din {_nr(f['maxim'])} posibile", ""]
    for nume, x in f["principii"].items():
        r += [f"**{ARII_RECRUTOR[nume]}: {_nr(x['puncte'])} din 4**", ""] + [f"- {_dovada(*d)}" for d in x["fapte"]] + [""]
    if proba:
        return "\n".join(r)
    r += ["## Ce afli numai la interviu", ""]
    r += [f"- **{t}.** {m} Întrebarea {q} din interviu." for t, m, q in (GOLURI_RECRUTOR[g] for g in f["goluri"])]
    r += ["", "## Cum se citește fișa", "",
          "- Fișa proiectului de portofoliu arată cum e organizat proiectul pentru lucrul cu AI-ul, așa cum se vede în istoricul lui.",
          "- Cum lucrează omul efectiv, pe o sarcină dată de tine, se vede la probă (pasul 3).",
          "- Ce a lucrat omul cu AI-ul în afara acestui proiect, de exemplu numai în chat sau la serviciu, afli la "
          "interviu.",
          "- O organizare bogată se poate și copia de la alții: de aceea, în partea IV a interviului, întrebările "
          "despre proiect.", ""]
    return "\n".join(r)
