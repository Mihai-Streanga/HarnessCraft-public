"""Intrebarile despre proiect: alese de program din ce lipseste in fisa, cu texte scrise dinainte, nepunctate.

Fiecare verificare a fisei are o intrebare, judecata de autor una cate una.
Programul ia primele doua verificari picate, in `ORDINE`: importanta raspunsului si usurinta evaluatorului, decisa
de autor pe 14 octombrie 2026. Nimic nu pleaca de pe calculator, iar acelasi
proiect da aceleasi intrebari. Textele sunt fixate la caracter de teste: o schimbare cere iar
acordul autorului.
"""
import re

from harnesscraft.fisa import _buc

IN_GHID = 2

# cheia verificarii din fisa -> intrebarea pentru candidat, apoi ce afla recrutorul (ghidul ii vorbeste cu „tu”)
INTREBARI = {
    "teste": (
        "Proiectul nu are programe care să verifice automat codul (teste). Cum vă dați seama că ce a scris AI-ul nu "
        "a stricat ceva ce mergea înainte?",
        "dacă omul verifică ce produce AI-ul, și cum."),
    "ci": (
        "Codul nu e verificat automat pe un server de fiecare dată când îl trimiteți: nimic nu rulează testele singur, "
        "fără să-și amintească cineva (integrare continuă, CI). Cine verifică codul înainte să ajungă la alții, și când?",
        "dacă verificarea depinde de memoria omului sau rulează singură."),
    "hooks_git": (
        "Când salvați o versiune a codului (commit), nu rulează nicio verificare automată (hooks git). Ce verificați "
        "de mână înainte să salvați?",
        "ce socotește omul că trebuie verificat de fiecare dată."),
    "hooks_agent": (
        "Cât lucrează AI-ul, nu rulează nicio verificare automată care să-l oprească dacă greșește (hooks de agent). "
        "Cum aflați că AI-ul a greșit, înainte ca greșeala să rămână în proiect?",
        "dacă omul supraveghează AI-ul pe parcurs sau doar la sfârșit."),
    "sectiuni": (
        "Regulile scrise pentru AI sunt doar câteva rânduri, fără părți, sau lipsesc. Cum îi spuneți AI-ului, la "
        "fiecare început de lucru, cum e făcut proiectul și ce așteptați de la el?",
        "dacă omul repetă contextul de fiecare dată sau l-a scris o dată pentru totdeauna."),
    "comenzi": (
        "Regulile scrise pentru AI nu spun cu ce comenzi se pornește și se verifică proiectul. De unde știe AI-ul cum "
        "să ruleze proiectul și cum să-și verifice munca?",
        "dacă AI-ul ghicește sau primește indicații precise."),
    "interdictii": (
        "Regulile scrise pentru AI nu spun ce nu are voie să facă, de pildă să șteargă fișiere sau să trimită codul "
        "fără să întrebe. A făcut vreodată AI-ul ceva ce nu trebuia? Cum l-ați oprit să repete?",
        "dacă omul a transformat greșelile AI-ului în reguli."),
    "sarcini": (
        "Proiectul nu are instrucțiuni separate pentru sarcinile care se repetă (skills, subagenți). Ce sarcină îi "
        "dați des AI-ului, și cum i-o explicați de fiecare dată?",
        "dacă omul și-a construit unelte pentru munca repetată sau o ia de fiecare dată de la capăt."),
    "cai_destule": (
        "Regulile scrise pentru AI pomenesc foarte puține fișiere ale proiectului ({n}). Ce citește AI-ul înainte să "
        "înceapă o sarcină, și de unde știe ce să citească?",
        "dacă omul îi arată AI-ului drumul prin proiect sau îl lasă să caute singur."),
    "cai_80": (
        "În regulile scrise pentru AI, programul a găsit nume de fișiere care nu se mai găsesc în proiect: {lista}. "
        "Sunt fișiere mutate sau șterse? Cum țineți regulile la zi când proiectul se schimbă?",
        "dacă regulile țin pasul cu proiectul, sau AI-ul caută lucruri care nu mai există."),
    "documente_arhitectura": (
        "Regulile scrise pentru AI nu trimit la niciun document care să explice cum e construit proiectul sau ce "
        "decizii s-au luat. Unde se vede de ce proiectul e făcut așa? Cum află AI-ul ce s-a hotărât deja?",
        "dacă AI-ul poate redeschide, fără să știe, decizii deja luate."),
    "organizare": (
        "Regulile scrise pentru AI nu descriu cum e împărțit proiectul. Cum știe AI-ul unde să lucreze?",
        "dacă omul i-a dat AI-ului o hartă a proiectului."),
    "chei_acum": (
        "Programul a găsit în cod ceva ce seamănă cu o parolă (în {n}). E una adevărată? Unde vă țineți parolele "
        "când lucrați cu AI-ul?",
        "dacă datele secrete stau departe de cod și de AI. Programul poate greși: de aceea întrebarea nu acuză."),
    "chei_istoric": (
        "Programul a găsit în istoricul codului ceva ce seamănă cu o parolă, deși acum nu mai e în cod. E una "
        "adevărată? Dacă da, ce ați făcut cu ea?",
        "dacă omul știe că o parolă ștearsă din cod rămâne în istoric și trebuie schimbată."),
    "licenta": (
        "Proiectul nu spune cine are voie să-i folosească codul (licență). V-ați gândit cui aparține codul scris cu "
        "AI-ul și cine are voie să-l folosească?",
        "dacă omul se gândește la drepturile asupra codului."),
    "ai": (
        "În istoricul proiectului nu scrie nicăieri ce a lucrat AI-ul și ce ați lucrat dumneavoastră. Când folosiți "
        "AI-ul la o lucrare, spuneți asta deschis? Cum?",
        "dacă omul e transparent cu privire la folosirea AI-ului: o chestiune de etică, pe care și regulile europene "
        "despre AI o pun în față."),
}
ORDINE = ["ai", "licenta", "teste", "interdictii", "ci", "comenzi", "sectiuni", "cai_80", "chei_acum", "hooks_agent",
          "chei_istoric", "hooks_git", "sarcini", "documente_arhitectura", "organizare", "cai_destule"]
LEGARE = ("*Ultima o alege programul din istoricul proiectului, după aceeași regulă pentru toți: o versiune despre "
          "regulile scrise pentru AI.*")
CRESTERE = ("*Pe aceasta o alege programul când cel puțin jumătate din punctajul proiectului a apărut în ultimele "
            "două săptămâni ale istoricului.*")
FARA = "Proiectul trece toate verificările fișei: nu e nicio întrebare despre ce lipsește. Poți pune ale tale, mai jos."
_NUMAR = re.compile(r"\d+")
_LISTA = re.compile(r"lipsă: (.+)$")
_IN_GHID = re.compile(r"^\*\*(\d+)\.\*\* (.+)$", re.M)


def _picate(f):
    """Verificarile picate, cu ce a gasit fisa: {cheie: textul de dupa „:” din dovada}."""
    return {cheie: (dovada.split(": ", 1)[1] if ": " in dovada else "")
            for x in f["principii"].values() for (cheie, ok, _), dovada in zip(x["fapte"], x["dovezi"]) if not ok}


def _text(cheie, gasit):
    n = int(m.group(0)) if (m := _NUMAR.search(gasit)) else 0
    lista = m.group(1) if (m := _LISTA.search(gasit)) else ""
    return INTREBARI[cheie][0].format(n=_buc(n, "fișier", "fișiere") if cheie == "cai_destule" else _buc(n, "loc", "locuri"),
                                      lista=lista)


def alege(f):
    """Primele `IN_GHID` verificari picate, in `ORDINE`: [(cheie, intrebarea, ce afli)]. Fisierele lipsa intra numai
    daca lipseste ceva: verificarea pica si cand regulile pomenesc prea putine fisiere."""
    picate = _picate(f)
    if "cai_80" in picate and not _LISTA.search(picate["cai_80"]):
        del picate["cai_80"]
    return [(k, _text(k, picate[k]), INTREBARI[k][1]) for k in ORDINE if k in picate][:IN_GHID]


LUNI = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie",
        "noiembrie", "decembrie"]


def _data(iso):
    an, luna, zi = iso.split("-")
    return f"{int(zi)} {LUNI[int(luna) - 1]} {an}"


def legare(x):
    """Intrebarea de legare (`legare.alege`): (intrebarea, ce afli, autorul din istoric)."""
    if x["fel"] == "schimbare":
        q = (f"Pe {_data(x['data'])} ați salvat o versiune a codului (commit) care schimbă regulile scrise pentru AI din "
             f"`{x['fisier']}`, cu mesajul „{x['mesaj']}”. Ce s-a întâmplat înainte, de ați schimbat regula, și ce s-a "
             "schimbat după în lucrul cu AI-ul?")
    else:
        q = (f"Regulile scrise pentru AI din `{x['fisier']}` au apărut pe {_data(x['data'])}, într-o versiune a codului "
             f"(commit) cu mesajul „{x['mesaj']}”, împreună cu {_buc(x['fisiere'], 'fișier', 'fișiere')}. Cum ați "
             "ajuns la regulile acestea și ce ați schimbat la ele de atunci?")
    afli = ("dacă proiectul e al lui: cine a scris regula știe ce a pățit înainte și de ce a pus-o; cine n-a scris-o "
            "povestește doar ce scrie în ea.")
    autor = f"*Autorul versiunii, în istoric: {x['autor']}; dacă nu e candidatul, întrebați-l ce a făcut el în proiect.*"
    return q, afli, autor


def crestere(x, maxim):
    """Intrebarea despre cresterea proiectului (`pasi.crestere`): (intrebarea, ce afli)."""
    q = (f"În ultimele {x['zile']} zile ale istoricului, punctajul proiectului a urcat de la {x['inainte']:g} la "
         f"{x['acum']:g} din {maxim:g}. Cum a crescut proiectul până acolo, și ce ați lucrat în zilele acelea?")
    afli = ("dacă proiectul a crescut din lucrul lui sau a fost pregătit pentru evaluare: cine l-a construit povestește "
            "pașii și de ce i-a făcut; cine l-a pregătit pentru fișă povestește ce a adăugat.")
    return q, afli


def parte(f):
    """Randurile partii IV, „Despre proiectul lui”: fiecare intrebare cu ce afli si locul de notite; la urma, intrebarea
    despre cresterea proiectului, cand a aparut brusc, si cea de legare, pentru orice proiect cu reguli pentru AI."""
    r = ["*Le alege programul din ce lipsește în fișa proiectului de portofoliu, în aceeași ordine pentru toți.*", ""]
    alese = alege(f)
    for n, (_, intrebare, afli) in enumerate(alese, 1):
        r += [f"**{n}.** {intrebare}", "", f"*Ce afli: {afli}*", "", "Note: ", ""]
    if not alese:
        r += [FARA, ""]
    n = len(alese)
    if f.get("crestere"):
        n += 1
        q, afli = crestere(f["crestere"], f["maxim"])
        r += [CRESTERE, "", f"**{n}.** {q}", "", f"*Ce afli: {afli}*", "", "Note: ", ""]
    if f.get("legare"):
        q, afli, autor = legare(f["legare"])
        r += [LEGARE, "", f"**{n + 1}.** {q}", "", autor, "", f"*Ce afli: {afli}*", "", "Note: ", ""]
    return r


def din_ghid(ghid):
    """Intrebarile despre proiect, asa cum stau in ghid: [(numarul, textul)]; raportul le ia de aici."""
    return [(int(n), t) for n, t in _IN_GHID.findall(ghid or "")]
