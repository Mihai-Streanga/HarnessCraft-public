"""Interviul structurat: ghidul pe proiect si punctajul din ghidul completat de recrutor.

NECALIBRAT. Recrutorul bifeaza da / nu ce aude in raspuns; nota o calculeaza codul: 1 + numarul de „da”.
Niciun model. Intrebarile sunt aceleasi pentru toti candidatii, in aceeasi ordine; se schimba numai fisa
de langa ele. Scrise pentru un recrutor care nu stie git: cuvinte obisnuite, raspuns scurt, cu un exemplu.

Ordinea e a interviului structurat clasic (OPM, „Structured Interviews: A Practical Guide”, 2008):
deschidere, motivatia, 4-6 arii de competenta, intrebarile recrutorului, incheierea („Mai e ceva ce ati
vrea sa stim?”), notarea imediat dupa. Ariile vin din metoda autorului (chat si cod) si din cadrul 4D:
de ce lucreaza cu AI, cum gandeste cu el, cum construieste, cum verifica, ce nu-i lasa, cum a invatat, cum
raspunde de date. Intrebarile 2-6 urmeaza treptele fisei, de la 1 la 4; etica, la sfarsit, le priveste pe toate (decizia autorului,
14 octombrie).
"""
import hashlib
import re
from pathlib import Path

from harnesscraft import tintite
from harnesscraft.fisa import GOLURI, NIVELURI
from harnesscraft.total import PLAFON_FARA_COD, randare as randare_total, total

STARE_INTREBARI = "confirmate de autor pe 13 octombrie 2026, neîncercate pe candidați"
LIBERE = 3            # locuri pentru intrebarile recrutorului: fara bife, nu intra in nota (decizia autorului, 14 oct.)

# id, principiile din fisa (gol: in afara lor), aria, pentru recrutor, 4D, intrebarea, bifele
INTREBARI = [
    ("S1", (), "motivația", "—",
     "De ce lucrați cu AI? Ce urmăriți când îl folosiți?",
     ["spune un scop concret, al lui (nu „toată lumea îl folosește”)",
      "dă un exemplu în care AI-ul l-a ajutat să ajungă acolo",
      "spune și unde AI-ul nu l-a ajutat sau nu merită folosit"]),
    ("S2", (), "gândirea cu AI-ul, în conversație", "Description, Discernment",
     "Povestiți o problemă pe care ați discutat-o cu AI-ul înainte să vă apucați de lucru. Cum ați folosit conversația?",
     ["a lămurit întâi problema, înainte să ceară o soluție",
      "i-a cerut AI-ului să-l contrazică, să dea surse sau alte variante",
      "decizia finală a fost a lui și spune pe ce s-a bazat"]),
    ("S3", ("ce e de făcut e specificat dinainte", "arhitectura e exprimată și ținută la zi"),
     "construirea cu AI-ul, în cod", "Description",
     "Povestiți o sarcină de programare pe care ați dat-o AI-ului. Ce i-ați pregătit dinainte?",
     ["a scris dinainte ce vrea și cum se vede că e gata",
      "a împărțit lucrul în pași mici",
      "regulile și structura proiectului sunt scrise într-un loc pe care AI-ul îl citește de fiecare dată "
      "(AI-ul nu ține minte de la o conversație la alta)"]),
    ("S4", ("verificarea există și e folosită",), "verificarea", "Discernment",
     "AI-ul vă dă un rezultat și spune că e corect: o informație într-o conversație, sau un cod care „merge”. "
     "Ce faceți înainte să-l folosiți?",
     ["nu acceptă pe cuvânt",
      "verifică pe altă cale: caută sursa, rulează codul sau testele",
      "dă un exemplu în care așa a prins o greșeală a AI-ului"]),
    ("S5", ("manual sau agent, cu cost",), "ce sarcini încredințează AI-ului și pe care le face personal", "Delegation",
     GOLURI["manual sau agent, cu cost"][1],
     ["numește ceva concret",
      "motivul e riscul, costul sau o decizie care trebuie să rămână a unui om, nu doar preferința",
      "spune de unde știe unde e granița (o întâmplare, o măsurătoare)"]),
    ("S6", ("metoda se schimbă după eșecuri",), "învățarea", "Diligence",
     GOLURI["metoda se schimbă după eșecuri"][1],
     ["spune o schimbare concretă",
      "a pornit de la o problemă reală (o greșeală, timp pierdut)",
      "schimbarea e scrisă sau automată (o regulă, o verificare), nu doar ținută minte"]),
    ("S7", ("responsabilitatea",), "responsabilitatea pentru date și etica", "Diligence",
     "Aveți de lucru cu date reale ale unor oameni (nume, salarii, date medicale) și vreți ajutorul AI-ului. Ce faceți?",
     ["nu pune datele reale în AI fără să știe unde ajung",
      "are o alternativă concretă: date false sau anonimizate, o unealtă aprobată de firmă",
      "întreabă sau anunță pe cine trebuie (șeful, clientul, regulile firmei)"]),
]

# ce treapta a fisei verifica fiecare intrebare: aceeasi logica, de la 1 la 4 (fisa.NUME_TREPTE)
TREAPTA = {"S1": "Nu ține de o treaptă: deschiderea.", "S2": "Verifică treapta 1, prompter.",
           "S3": "Verifică treapta 2, configurator.", "S4": "Verifică treapta 3, constructor de sistem.",
           "S5": "Verifică treptele 3 și 4, constructor de sistem și metodolog.",
           "S6": "Verifică treapta 4, metodolog.", "S7": "Privește toate treptele."}

NOTA = ("Notele arată cum funcționează unealta, înainte de încercarea pe candidați reali; decizia de angajare rămâne "
        "a oamenilor. Totalul: o treime portofoliul, o treime interviul, o treime proba.")

DESCHIDERE = [
    "Mulțumești candidatului că a venit și spui pe scurt postul.",
    "Spui, cu cuvintele astea: „Vă pun aceleași întrebări pe care le pun tuturor candidaților. La fiecare vă rog "
    "un exemplu din munca dumneavoastră, în două-trei fraze. Îmi iau notițe.”",
    "Întrebi dacă are întrebări înainte să începeți.",
]
AJUTATOARE = "„Dați-mi un exemplu.” · „Ce ați făcut dumneavoastră?” · „Cum s-a terminat?”"
INCHEIERE = [
    "Întrebi: „Mai e ceva ce ați vrea să știm?”",
    "Îi dai ocazia să pună el întrebări, apoi îi mulțumești.",
    "Completezi bifele și concluzia imediat după, cât îți amintești răspunsurile.",
]
CUM = "## Cum folosești ghidul"   # interfata muta sectiunea asta in fereastra „Cum folosesc”
FARA_NOTA = ("*La ce folosesc: te ajută să vezi dacă proiectul e al candidatului. Cine și-a construit singur proiectul "
             "își explică ușor alegerile: ce a făcut, de ce, ce a schimbat după; așa se deosebește de un proiect preluat "
             "de la altcineva, de pildă copiat de pe GitHub. Pe cele despre proiect le alege programul: cel mult două din ce lipsește "
             "în fișa proiectului de portofoliu și una dintr-o versiune a proiectului despre regulile scrise pentru AI; celelalte le scrii tu, despre ce vrei să mai afli. Ce răspunde îți sprijină "
             "impresia despre el și recomandarea din concluzie.*",
             "*De ce stau în afara notei: nota vine din cele 7 întrebări din partea III, aceleași pentru toți, ca "
             "să se poată compara candidații între ei. Întrebările de aici diferă de la un om la altul: cele despre "
             "proiect pornesc de la proiectul lui, iar pe ale tale le scrii tu. Într-o evaluare a candidaților, nota o calculează programul, "
             "din reguli scrise de oameni: AI Act (Regulamentul UE 2024/1689, anexa III, punctul 4) încadrează la "
             "„risc ridicat” un sistem de IA folosit la evaluarea candidaților.*")

# Fara proiect cu cod (datoria 12): ce a adus in loc se citeste la interviu, fara nota; codul nu-l poate nota fara
# reguli verificate pe transcrieri, iar un model nu da verdict pe om. Aceleasi doua intrebari pentru toti cei fara cod;
# scrise de agent, aprobate de autor pe 16 octombrie 2026.
FARA_COD = "fara-cod"
FARA_COD_INTREBARI = [
    ("Ce ne-ați adus în loc de un proiect cu cod: o conversație cu AI-ul, instrucțiunile fixe pe care le-ați scris "
     "pentru el (prompt de sistem), un proiect făcut în chat? Arătați-mi-l și povestiți cum l-ați făcut.",
     "dacă e al lui: cine l-a făcut singur își explică alegerile, ce a cerut și de ce."),
    ("Ce ați schimbat la el după ce n-a mers prima dată, și de unde ați văzut că nu merge?",
     "dacă își îndreaptă felul de lucru după greșeli și dacă verifică ce primește de la AI."),
]
FARA_NOTA_FARA_COD = (
    "*La ce folosesc: candidatul nu are proiect cu cod, așa că aici afli ce face cu AI-ul în afara codului. Primele "
    "două sunt despre ce a adus în loc, aceleași pentru toți cei fără proiect cu cod; celelalte le scrii tu. Ce "
    "răspunde îți sprijină impresia despre el și recomandarea din concluzie.*",
    "*De ce stau în afara notei: nota vine din cele 7 întrebări din partea III, aceleași pentru toți, ca să se poată "
    "compara candidații între ei. Ce aduce omul în loc de cod diferă de la unul la altul, iar programul nu are încă "
    "reguli verificate după care să-l noteze; un program AI nu dă note oamenilor.*")


def _amprenta():
    """Amprenta intrebarilor cu nota: un ghid se puncteaza numai cu intrebarile cu care a fost scris. Nu e un numar
    de versiune (decizia autorului: fara versiuni pana la sfarsitul prototipului)."""
    text = "\n".join(f"{q[0]} {q[4]} | " + " | ".join(q[5]) for q in INTREBARI)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


AMPRENTA = _amprenta()
_BIFA = re.compile(r"^- (S\d+)\.([123]) \[(.*?)\] ", re.M)
_AMPRENTA = re.compile(r"^<!-- ghid-interviu intrebari ([0-9a-f]+) -->$", re.M)
# „Nivelul … Scorul”: ghidurile scrise inainte de „treapta” si „punctajul” (decizia autorului, „Termenii”)
_NIVEL = re.compile(r"^(?:Nivelul provizoriu|Treapta provizorie) din fișă: \*\*(.+?)\*\*", re.M)
_FISA = re.compile(r"^<!-- fisa ([\d.]+) din ([\d.]+) -->$", re.M)
_FARA_COD = re.compile(rf"^<!-- fisa {FARA_COD} -->$", re.M)


def _bife(id_, bife):
    return [f"- {id_}.{i} [ ] {b}" for i, b in enumerate(bife, 1)]


def _cifra(x):
    return f"{x:g}".replace(".", ",")


def _din_fisa(f, principii):
    if f is None:
        return "Ce arată proiectul: nimic, candidatul nu are proiect cu cod; afli numai din interviu."
    vazute = [p for p in principii if p not in f["goluri"]]
    if not vazute:
        return "Ce arată proiectul: nimic, istoricul proiectului (git) nu poate arăta asta; afli numai din interviu."
    puncte = round(sum(f["principii"][p]["puncte"] for p in vazute) / len(vazute), 1)
    return f"Ce arată proiectul: {_cifra(puncte)} din 4. Cere un exemplu care se potrivește."


def din_fisa_actuala(text, f):
    """Ghidul cu fisa de acum: scorul (din care se face treimea portofoliului), nivelul si „Ce arata proiectul” la
    fiecare intrebare. Bifele, notitele si intrebarile despre proiect raman: o reanalizare nu sterge raspunsurile, dar
    nici nu lasa in ghid scorul fisei vechi (un ghid vechi pastra alt scor decat fisa refacuta, iar totalul se calcula din cel din ghid)."""
    text = _FISA.sub(f"<!-- fisa {f['total']:g} din {f['maxim']:g} -->", text, count=1)
    text = re.sub(r"^(?:Nivelul provizoriu|Treapta provizorie) din fișă: \*\*.+?\*\* \(\d+ din \d+\)",
                  lambda m: f"Treapta provizorie din fișă: **{f['nivel_nume']}** ({f['nivel'] + 1} din {len(NIVELURI)})",
                  text, count=1, flags=re.M)
    text = re.sub(r"^(?:Scorul|Punctajul) proiectului: [\d,]+ din [\d,]+\.",
                  f"Punctajul proiectului: {_cifra(f['total'])} din {_cifra(f['maxim'])}.", text, count=1, flags=re.M)
    for id_, principii, *_ in INTREBARI:
        text = re.sub(rf"^(### {id_}\. .*\n\n\*Aria: .*?\* )Ce arată proiectul: .*$",
                      lambda m, p=principii: m.group(1) + _din_fisa(f, p), text, count=1, flags=re.M)
    return text


# fisa nu e in interviu, e la pasul 1: aici vin din ea numai trei lucruri, fiecare cu locul lui (observatia 18)
FRAZA_DE_INCEPUT = ("*Întrebările 1–7 sunt aceleași pentru toți candidații. Din proiectul lui de portofoliu vin numai "
                    "trei lucruri: treapta și punctajul de sub „Înainte de interviu”, luate din fișa proiectului (pasul 1, "
                    "„Portofoliul”); rândul „Ce arată proiectul” de la fiecare întrebare; întrebările despre "
                    "proiect, din partea IV.*")


FRAZA_FARA_COD = ("*Întrebările 1–7 sunt aceleași pentru toți candidații. Candidatul nu are proiect cu cod, deci nu are "
                  "fișă: „Înainte de interviu” spune ce înseamnă asta pentru total, iar partea IV întreabă despre ce a "
                  "adus în loc.*")
FARA_COD_INAINTE = [
    "Candidatul nu are proiect cu cod: a hotărât recrutorul, la adăugarea lui. Portofoliul intră în total cu 0, deci "
    f"totalul ajunge cel mult la {_cifra(PLAFON_FARA_COD)} din 100: codul e un plus, nu o cerință.",
    "Întrebarea 3 (construirea, în cod) o poți lăsa nepusă: o întrebare nepusă nu scade nota."]


def _parte_fara_cod():
    r = ["*Aceleași pentru toți candidații fără proiect cu cod.*", ""]
    for n, (intrebare, afli) in enumerate(FARA_COD_INTREBARI, 1):
        r += [f"**{n}.** {intrebare}", "", f"*Ce afli: {afli}*", "", "Note: ", ""]
    return r


DEMONSTRATIV = ("**Demonstrație, nu evaluare.** Candidatul răspunde și bifează singur, ca să se vadă cum funcționează "
                "interviul. Nu e o judecată despre el.")


def ghid(f, demonstrativ=False, nume=None):
    """Ghidul de interviu pentru un candidat: intrebarile, aceleasi pentru toti, langa fisa proiectului lui. `f` None:
    candidatul fara proiect cu cod; ghidul o spune in semnul de la inceput, iar punctajul il citeste de acolo."""
    if f is None:
        semn, despre, fraza = f"<!-- fisa {FARA_COD} -->", "fără proiect cu cod", FRAZA_FARA_COD
        inainte = ["## Înainte de interviu: fără proiect cu cod", ""] + FARA_COD_INAINTE
        parte_iv = (FARA_NOTA_FARA_COD, "### Ce a adus în loc de proiect", _parte_fara_cod())
    else:
        proiect = Path(f["proiect"]).name or f["proiect"]
        semn, despre, fraza = f"<!-- fisa {f['total']:g} din {f['maxim']:g} -->", f"proiectul „{proiect}”", FRAZA_DE_INCEPUT
        inainte = ["## Înainte de interviu: ce arată proiectul", "",
                   f"Treapta provizorie din fișă: **{f['nivel_nume']}** ({f['nivel'] + 1} din {len(NIVELURI)}); se "
                   "confirmă la interviu.",
                   f"Punctajul proiectului: {_cifra(f['total'])} din {_cifra(f['maxim'])}. Dovezile sunt în fișa proiectului "
                   "de portofoliu."]
        parte_iv = (FARA_NOTA, "### Despre proiectul lui", tintite.parte(f))
    r = [f"<!-- ghid-interviu intrebari {AMPRENTA} -->", semn,
         f"# Interviul cu {nume} · {despre}" if nume else f"# Interviul · {despre}", "",
         fraza, ""] + ([DEMONSTRATIV, ""] if demonstrativ else []) + [
         CUM, "",
         "- **AI-ul** e programul cu care lucrează candidatul: un asistent de conversație (ChatGPT, Claude) sau unul "
         "care scrie cod (Claude Code, Cursor, Copilot).",
         "- **Cum se completează.** La fiecare rând al întrebărilor 1–7 scrii `[da]` sau `[nu]`; nota o calculează "
         "programul. Dacă n-ai pus o întrebare, lași toate trei rândurile `[ ]`. O întrebare pe care n-o pui nu scade "
         "nota: nota interviului e media numai a întrebărilor puse. E alegerea ta, de pildă când nu ai timp de toate.",
         f"- **Dacă răspunsul rămâne general**, aceleași întrebări ajutătoare pentru toți: {AJUTATOARE}",
         "- **Întrebările fără notă** (partea IV) sunt pentru discuție: te ajută să vezi dacă proiectul e al lui. Le pui "
         "dacă ai timp și notezi ce răspunde.",
         f"- {NOTA}", ""] + inainte + ["",
         "## I. Deschiderea", ""] + [f"- {x}" for x in DESCHIDERE] + \
        ["", "## II. Parcursul: CV, studii și cursuri", "",
         "„Povestiți-mi pe scurt parcursul dumneavoastră.” Cântărit liber; nu intră în notă.", "", "Note: ", "",
         "## III. Întrebările cu notă: aceleași pentru toți", "",
         "De ce lucrează cu AI, cum gândește cu el, cum construiește, cum verifică, ce nu-i lasă, cum a învățat, cum "
         "răspunde de date. Întrebările 2–6 urmează treptele fișei, de la 1 la 4; ultima le privește pe toate. O "
         "întrebare pe care n-o pui nu scade nota.", "",
         f"Dacă răspunsul rămâne general: {AJUTATOARE}", ""]
    for id_, principii, aria, _, intrebare, bife in INTREBARI:
        r += [f"### {id_}. {intrebare}", "", f"*Aria: {aria}. {TREAPTA[id_]}* {_din_fisa(f, principii)}", ""] + \
             _bife(id_, bife) + ["", "Note: ", ""]
    r += ["## IV. Întrebările fără notă: pentru discuție", "", parte_iv[0][0], "", parte_iv[0][1], "",
          parte_iv[1], ""] + parte_iv[2] + [
          "### Ale tale, dacă vrei", "",
          "Scrii întrebarea, apoi ce a răspuns.", ""]
    for i in range(1, LIBERE + 1):
        r += [f"**Întrebarea ta {i}:** ", "", "Note: ", ""]
    r += ["## V. Încheierea", ""] + [f"- {x}" for x in INCHEIERE] + ["", "**Concluzia recrutorului:** ", ""]
    return "\n".join(r)


def citeste(text):
    """Bifele din ghidul completat: {id: [True/False/None] * 3}. Refuza un ghid scris cu alte intrebari."""
    v = _AMPRENTA.search(text)
    if not v or v.group(1) != AMPRENTA:
        raise ValueError("ghidul a fost scris cu alte întrebări: punctajul s-ar face pe altele")
    b = {}
    for id_, nr, val in _BIFA.findall(text):
        val = val.strip().lower()
        if val not in ("", "da", "nu"):
            raise ValueError(f"{id_}.{nr}: „{val}” nu e „da” sau „nu”")
        b.setdefault(id_, {})[nr] = {"da": True, "nu": False}.get(val)
    asteptate = [q[0] for q in INTREBARI]
    lipsa = [f"{i}.{n}" for i in asteptate for n in "123" if n not in b.get(i, {})]
    if lipsa or sorted(b) != sorted(asteptate):
        raise ValueError(f"rândurile de bifat nu se potrivesc cu ghidul: {lipsa or sorted(set(b) ^ set(asteptate))}")
    return {i: [b[i][n] for n in "123"] for i in asteptate}


def nota(bife):
    """1 + numarul de „da”; None daca intrebarea nu s-a pus. Pe jumatate completata: refuzata."""
    if all(x is None for x in bife):
        return None
    if any(x is None for x in bife):
        raise ValueError("completată pe jumătate")
    return 1 + sum(bife)


def _medie(valori):
    date = [v for v in valori if v is not None]
    return {"medie": round(sum(date) / len(date), 2) if date else None, "punctate": len(date), "din": len(valori)}


def scor(text, proba=None):
    note = {}
    for id_, bife in citeste(text).items():
        try:
            note[id_] = nota(bife)
        except ValueError as e:
            raise ValueError(f"{id_}: {e}") from None
    nivel, f = _NIVEL.search(text), _FISA.search(text)
    # Se noteaza numai intrebarile aceleasi pentru toti; o intrebare nepusa nu intra in medie.
    medie = _medie([note[q[0]] for q in INTREBARI])
    return {"standard": {q[0]: note[q[0]] for q in INTREBARI}, "amprenta": AMPRENTA,
            "total": total((float(f.group(1)), float(f.group(2))) if f else None, medie["medie"], proba,
                           fara_cod=bool(_FARA_COD.search(text))),
            "pe_principii": {p: note[q[0]] for q in INTREBARI for p in q[1]},
            "medie": medie,
            "nivel_fisa": nivel.group(1) if nivel else None, "nota": NOTA}


def randare_scor(s):
    m = s["medie"]
    r = [f"Nivelul din fișă: {s['nivel_fisa'] or ('fără proiect cu cod' if s['total']['fara_cod'] else '—')}",
         "Interviul: " + (f"{m['medie']:g} din 4" if m["medie"] is not None else "nepunctat") +
         f", {m['punctate']} întrebări puse din {m['din']}"]
    r += [f"  {q[0]} ({q[2]}): {s['standard'][q[0]] or 'nepusă'}" for q in INTREBARI]
    r += [randare_total(s["total"]), s["nota"]]
    return "\n".join(r)
