"""Candidatii din interfata: un dosar pe candidat, in `candidaturi/` (in afara git-ului: date despre oameni reali),
intr-unul din trei dosare de stare (`STARI`): `propuse` (abia adaugat), `in-analiza` (de la prima analiza sau proba),
`finalizate` (numai cand recrutorul apasa „Finalizează candidatura”; „Redeschide” il intoarce). Cu multi candidati,
se gasesc si in Explorer, nu numai pe ecran.

Ce sta in dosar:
  candidat.json - numele, proiectul (calea; o clona din dosar, relativ la el, ca sa nu se rupa la mutare), de unde
                  a venit, daca e autoevaluare demonstrativa; fara proiect cu cod: `fara_cod`, motivul recrutorului,
                  iar proiectul lipseste (null);
  proiect/      - numai daca proiectul a venit ca link git: clona, cu tot istoricul;
  fisa.json     - fisa si drumul, din `pasi.py`;
  ghid.md       - ghidul de interviu, completat din formular; acelasi format ca in terminal;
  proba.md      - foaia probei: linkurile predate, bifele, notitele (`proba.py`);
  Raspuns.xlsx  - tabelul de raspuns predat de candidat; unul inlocuit ramane, cu ora inlocuirii in nume;
  fisa-proba.json, proba-proiect/ - fisa programului predat la proba (informatie, fara nota) si clona lui, daca a
                  venit ca link;
  jurnal.jsonl  - urma fiecarui pas, scrisa pe loc (`audit.py`), din care se citeste raportul de audit;
Rezultatul nu se pastreaza: se calculeaza din ghid la fiecare deschidere, ca o bifa schimbata sa se vada pe loc.
Fiecare functie de pas e cea pe care o cheama un buton; calculul e in `pasi.py` si `interviu.py`.
"""
import json
import os
import re
import shutil
import subprocess
import threading
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from harnesscraft import audit, interviu, istoric, md, pasi, proba
from harnesscraft.fisa import NUME_TREPTE, randare as randare_fisa
from harnesscraft.manifest import RADACINA

DOSAR = RADACINA / "candidaturi"
STARI = [("propuse", "Propuse"), ("in-analiza", "În analiză"), ("finalizate", "Finalizate")]
PASI = [("fisa", "Portofoliul"), ("interviu", "Interviul"), ("proba", "Proba"), ("rezultat", "Rezultatul")]
LINK = re.compile(r"^(https?://|git@|ssh://)")
# Un depozit privat vine ca un singur fisier cu tot istoricul, facut de candidat cu comanda de mai jos: o arhiva .zip
# facuta cu Compress-Archive pierde dosarul ascuns .git (incercat pe 16 octombrie 2026), iar fara el nu e istoric.
BUNDLE = "git bundle create proiect.bundle --all"


def de_descarcat(sursa):
    """Se cloneaza: un link git sau un fisier .bundle de pe calculator; altfel e un dosar, folosit pe loc."""
    return bool(LINK.match(sursa)) or (sursa.lower().endswith(".bundle") and Path(sursa).is_file())


def scrie_text(cale, text):
    """Un fisier cu datele omului, scris intai alaturi (`tmp-«nume»`), apoi pus in locul celui vechi dintr-o mutare:
    o intrerupere la scriere lasa fisierul vechi intreg, nu unul pe jumatate."""
    cale = Path(cale)
    tmp = cale.with_name(f"tmp-{cale.name}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, cale)


def _scrie(cale, date):
    scrie_text(cale, json.dumps(date, indent=1, ensure_ascii=False))


# Un lacat pe candidat: doua salvari deodata (autosalvarea, in fire diferite ale serverului) citesc, schimba si scriu
# pe rand, nu una peste alta. Reintrant: analiza probei salveaza si ea foaia.
_LACATE, _LACAT_LACATE = {}, threading.Lock()


def _lacat(c):
    with _LACAT_LACATE:
        return _LACATE.setdefault((str(c["radacina"]), c["id"]), threading.RLock())


def _citeste(cale):
    return json.loads(cale.read_text(encoding="utf-8")) if cale.exists() else None


def identificator(nume, dosar):
    baza = unicodedata.normalize("NFKD", nume).encode("ascii", "ignore").decode().lower()
    baza = re.sub(r"[^a-z0-9]+", "-", baza).strip("-") or "candidat"
    id_, n = baza, 2
    while any((dosar / s / id_).exists() for s, _ in STARI):
        id_, n = f"{baza}-{n}", n + 1
    return id_


# Fara ferestre de autentificare: la un depozit privat fara acces, managerul de parole al Windows ar deschide una din
# server, iar adaugarea ar astepta-o (incercat pe 16 octombrie 2026). Asa, git refuza pe loc, iar motivul se spune.
FARA_INTREBARI = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env={**os.environ, **FARA_INTREBARI})


def de_ce_nu_se_descarca(stderr):
    """Motivul, in cuvintele recrutorului: ce intoarce git e in engleza. Necunoscut, ramane raspunsul lui git."""
    s = stderr.lower()
    if "not found" in s or "does not exist" in s or "authentication" in s or "could not read username" in s:
        return ("la linkul acesta nu e un depozit public (nu există sau e privat). Cere candidatului un link public "
                "sau un singur fișier cu tot istoricul proiectului, pe care îl face în dosarul lui (comanda: "
                + BUNDLE + "); îl salvezi pe acest calculator și lipești calea lui.")
    if "could not resolve host" in s or "unable to access" in s:
        return "calculatorul nu ajunge la adresa asta: fără internet sau adresa e greșită."
    linii = [x.strip() for x in stderr.splitlines() if x.strip()]
    return f"git a răspuns „{linii[-1]}”." if linii else "git a refuzat, fără motiv."


def nume_sursei(sursa):
    """Numele proiectului: ultima parte a linkului (fara „.git”) sau a dosarului; nu „proiect”, numele clonei."""
    return re.split(r"[/\\:]", sursa.strip().rstrip("/\\").removesuffix(".git").removesuffix(".bundle"))[-1] or sursa


def _cu_git(proiect):
    """Istoric propriu: un dosar fara el, aflat in alt depozit (o arhiva dezarhivata acolo), ar da istoricul celuilalt."""
    sus = _git("-C", str(proiect), "rev-parse", "--show-toplevel").stdout.strip()
    return (bool(sus) and Path(sus).resolve() == Path(proiect).resolve() and
            not _git("-C", str(proiect), "rev-parse", "HEAD").returncode)


def nou(nume, sursa, demonstrativ=False, dosar=DOSAR, fara_cod=None):
    """Candidatul nou: dosarul lui si proiectul verificat (are istoric git). Intoarce identificatorul.
    `fara_cod`: motivul recrutorului cand omul nu are proiect cu cod; atunci `sursa` ramane goala."""
    nume, sursa = nume.strip(), sursa.strip().strip('"')
    if not nume:
        raise ValueError("Lipsește numele candidatului.")
    if fara_cod is not None:
        return _nou_fara_cod(nume, sursa, " ".join(fara_cod.split()), demonstrativ, dosar)
    if not sursa:
        raise ValueError("Lipsește proiectul: un dosar de pe calculator sau un link spre istoricul proiectului (git). Dacă omul nu are proiect "
                         "cu cod, bifezi „Candidatul nu are proiect cu cod”.")
    id_ = identificator(nume, dosar)
    d = dosar / STARI[0][0] / id_
    if de_descarcat(sursa):
        d.mkdir(parents=True)
        r = _git("clone", "--quiet", sursa, str(d / "proiect"))
        if r.returncode:
            shutil.rmtree(d, ignore_errors=True)  # dosarul abia creat, gol sau cu o clona pe jumatate
            raise ValueError(f"Proiectul nu s-a putut descărca de la {sursa}: {de_ce_nu_se_descarca(r.stderr)}")
        proiect = d / "proiect"
    else:
        proiect = Path(sursa)
        if not proiect.is_dir():
            raise ValueError(f"Dosarul {sursa} nu există pe acest calculator.")
        if not _cu_git(proiect):
            raise ValueError(f"Dosarul {sursa} nu are istoric git (commit-uri): fără istoric nu se vede drumul. O "
                             "arhivă îl pierde uneori; cere candidatului un singur fișier cu tot istoricul (comanda: "
                             f"{BUNDLE}).")
        d.mkdir(parents=True)
    cale = "proiect" if proiect == d / "proiect" else proiect.resolve().as_posix()  # clona: relativ la dosar
    _scrie(d / "candidat.json", {"nume": nume, "proiect": cale, "sursa": sursa,
                                 "demonstrativ": bool(demonstrativ), "creat": datetime.now().isoformat(timespec="seconds")})
    audit.scrie(d, "candidatul", audit.RECRUTOR, f"a adăugat candidatul, cu proiectul de portofoliu {sursa}"
                + (" (autoevaluare, demonstrativ)" if demonstrativ else ""), sursa=sursa)
    return id_


def _nou_fara_cod(nume, sursa, motivul, demonstrativ, dosar):
    """Fara proiect cu cod (datoria 12): hotararea recrutorului, cu motivul. Pasul 1 e gata pe loc, iar ghidul de
    interviu se scrie acum, fara fisa: portofoliul intra in total cu 0, etichetat. Daca omul aduce totusi un proiect,
    se adauga un candidat nou cu el, ca la orice alt proiect."""
    if sursa:
        raise ValueError("Alegi una: proiectul de portofoliu sau „Candidatul nu are proiect cu cod”.")
    if not motivul:
        raise ValueError("Scrii motivul pentru care candidatul nu are proiect cu cod.")
    id_ = identificator(nume, dosar)
    d = dosar / STARI[0][0] / id_
    d.mkdir(parents=True)
    _scrie(d / "candidat.json", {"nume": nume, "proiect": None, "sursa": "", "fara_cod": motivul,
                                 "demonstrativ": bool(demonstrativ), "creat": datetime.now().isoformat(timespec="seconds")})
    scrie_text(d / "ghid.md", interviu.ghid(None, demonstrativ=demonstrativ, nume=nume))
    audit.scrie(d, "candidatul", audit.RECRUTOR, "a adăugat candidatul, fără proiect cu cod"
                + (" (autoevaluare, demonstrativ)" if demonstrativ else ""))
    audit.scrie(d, "portofoliul", audit.RECRUTOR, "a hotărât: candidatul nu are proiect cu cod; portofoliul intră în "
                "total cu 0", fara_cod=True)
    audit.scrie(d, "interviul", audit.PROGRAM, f"a scris ghidul de interviu fără proiect cu cod (amprenta "
                f"întrebărilor, cod {interviu.AMPRENTA})")
    return id_


def fara_cod(c):
    """Motivul recrutorului, daca omul nu are proiect cu cod; altfel None."""
    return c.get("fara_cod")


def lista(dosar=DOSAR, cauta=""):
    """Toti candidatii, din cele trei dosare de stare, cel adaugat ultimul primul. Cu `cauta`, numai cei al caror nume
    sau proiect il contine; literele mari si diacriticele nu conteaza."""
    q = _fara_semne(cauta)
    cs = (c for s, _ in STARI if (dosar / s).is_dir() for d in (dosar / s).iterdir() if (c := citeste(d.name, dosar)))
    return sorted((c for c in cs if q in _fara_semne(f'{c["nume"]} {c["sursa"]}')), key=lambda c: c["creat"],
                  reverse=True)


def _fara_semne(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()


def citeste(id_, dosar=DOSAR):
    if not re.fullmatch(r"[a-z0-9-]+", id_ or ""):
        return None
    for stare, _ in STARI:
        d = dosar / stare / id_
        c = _citeste(d / "candidat.json")
        if c is not None:
            proiect = Path(c["proiect"] or "")
            c.update(id=id_, dosar=d, stare=stare, radacina=dosar,
                     proiect=None if not c["proiect"] else
                     (d / proiect).as_posix() if not proiect.is_absolute() else c["proiect"])
            return c
    return None


def muta(c, stare):
    """Dosarul candidatului, in alt dosar de stare. `c` se actualizeaza pe loc: cine il tine are calea noua."""
    if stare not in dict(STARI):
        raise ValueError(f"stare necunoscută: {stare}")
    if c["stare"] == stare:
        return c
    tinta = c["radacina"] / stare / c["id"]
    tinta.parent.mkdir(parents=True, exist_ok=True)
    c["dosar"].rename(tinta)
    c.update(citeste(c["id"], c["radacina"]))
    return c


def _in_analiza(c):
    """Primul lucru facut pe candidat (analiza portofoliului sau a probei, tabelul predat) il scoate din „propuse”."""
    if c["stare"] == "propuse":
        muta(c, "in-analiza")


def finalizeaza(c):
    muta(c, "finalizate")
    audit.scrie(c["dosar"], "candidatura", audit.RECRUTOR, "a finalizat candidatura")
    return c


def redeschide(c):
    muta(c, "in-analiza")
    audit.scrie(c["dosar"], "candidatura", audit.RECRUTOR, "a redeschis candidatura")
    return c


SCOASE = "tmp-de-sters"  # langa dosarele de stare, nu printre ele: `lista` nu-l vede


def sterge(c, nume):
    """Stergerea definitiva a candidaturii, la cererea recrutorului (GDPR: datele unui candidat se sterg cand nu mai
    folosesc; decizia autorului, 19 octombrie): tot dosarul, de pe disc, fara copie si fara Cosul de reciclare. Ce nu e
    in dosar (proiectul dat ca dosar de pe calculator, un .bundle primit) e al candidatului si ramane. `nume` e
    confirmarea: numele candidatului, scris din nou."""
    if _fara_semne(nume) != _fara_semne(c["nume"]):
        raise ValueError(f"Numele scris nu e „{c['nume']}”. Ca să ștergi, îl scrii întocmai.")
    tinta = c["radacina"] / SCOASE / f"{c['id']}-{datetime.now():%Y%m%d-%H%M%S-%f}"
    tinta.parent.mkdir(exist_ok=True)
    try:  # o singura mutare: dosarul iese intreg din lista sau ramane intreg; Windows o refuza cu un fisier deschis
        c["dosar"].rename(tinta)
    except PermissionError:
        raise ValueError("Dosarul nu se poate șterge acum: un fișier din el e deschis în alt program (de pildă tabelul "
                         "predat, în Excel). Îl închizi și apeși din nou.") from None
    if tinta in goleste_scoasele(c["radacina"]):
        raise ValueError(f"Candidatul a ieșit din listă, dar câteva fișiere au rămas în {tinta}: se șterg la "
                         "următoarea pornire.")


def goleste_scoasele(dosar=DOSAR):
    """Sterge de pe disc dosarele scoase din lista (si ce a ramas de la o stergere oprita); intoarce ce a ramas."""
    scoase = dosar / SCOASE
    for d in list(scoase.iterdir()) if scoase.is_dir() else []:
        try:
            shutil.rmtree(d, onexc=_fa_scriibil)
        except OSError:
            pass
    ramase = list(scoase.iterdir()) if scoase.is_dir() else []
    if scoase.is_dir() and not ramase:
        scoase.rmdir()
    return ramase


def _fa_scriibil(functia, cale, ex):
    """Fisierele din .git sunt numai de citit pe Windows, iar `rmtree` se opreste la ele: le face scriibile si reia."""
    if not isinstance(ex, PermissionError):
        raise ex
    os.chmod(cale, 0o700)
    functia(cale)


def ghid(c):
    g = c["dosar"] / "ghid.md"
    return g.read_text(encoding="utf-8") if g.exists() else None


def stari(c):
    """Starea fiecarui pas: „gata”, „în lucru”, „de făcut”, „blocat” sau, la proba, „fără probă”, cu motivul."""
    f = (c["dosar"] / "fisa.json").exists() or bool(fara_cod(c))  # fara cod: pasul 1 s-a incheiat cu hotararea
    g = ghid(c) or ""
    bife = re.findall(r"^- S\d+\.[123] \[(da|nu)\]", g, re.M)
    lipsa_fisa = "Întâi portofoliul (pasul 1)."
    decis = decizia_probei(c) is not None  # interviul se incheie cu decizia de proba
    intv = (("blocat", lipsa_fisa) if not f else
            ("gata", "") if len(bife) == 3 * len(interviu.INTREBARI) and decis else
            ("în lucru", "") if bife or decis else ("de făcut", ""))
    deschisa, de_ce = proba_deschisa(c)
    if not deschisa:
        prb = (("fără probă", de_ce) if fara_proba(c) else ("de făcut", de_ce) if decis else ("blocat", de_ce))
    else:
        try:
            n = nota_probei(c)["nota"]
        except ValueError:  # cheia schimbata: o spune ecranul probei
            n = None
        prb = (("în lucru", "") if n is None else ("gata", "") if n["complet"] else
               ("de făcut", "") if len(n["lipsa"]) == 3 else ("în lucru", ""))
    return {
        "fisa": ("gata", "") if f else ("de făcut", ""),
        "interviu": intv,
        "proba": prb,
        "rezultat": intv,  # se calculeaza singur din interviu: e atat de gata cat e interviul
    }


def pasul_curent(c):
    s = stari(c)
    return next((p for p, _ in PASI if s[p][0] in ("de făcut", "în lucru")), "rezultat")


def analizeaza(c):
    """Pasul 1: fisa si drumul. Ghidul de interviu se scrie o singura data: o reanalizare nu sterge raspunsurile, dar
    aduce in el scorul si nivelul fisei noi (`interviu.din_fisa_actuala`), cu copia ghidului de dinainte."""
    if fara_cod(c):
        raise ValueError("candidatul nu are proiect cu cod: nu e nimic de analizat. Un proiect adus după se adaugă "
                         "ca un candidat nou")
    p = c["proiect"]
    commits = istoric.citeste(p)
    f, drum = pasi.fisa_proiect(p, commits), pasi.drumul(p, commits)
    f["crestere"] = pasi.crestere(drum)
    if de_descarcat(c["sursa"]):  # clona se cheama „proiect”: in fisa si in interviu, numele din link
        f["proiect"] = nume_sursei(c["sursa"])
    _scrie(c["dosar"] / "fisa.json", {"fisa": f, "drumul": drum, "commit": commits[-1].sha,
                                     "calculat": datetime.now().isoformat(timespec="seconds")})
    g = c["dosar"] / "ghid.md"
    ghidul = None
    if not g.exists():
        scrie_text(g, interviu.ghid(f, demonstrativ=c["demonstrativ"], nume=c["nume"]))
        ghidul = f"a scris ghidul de interviu (amprenta întrebărilor, cod {interviu.AMPRENTA})"
    elif (nou := interviu.din_fisa_actuala(vechi := g.read_text(encoding="utf-8"), f)) != vechi:
        copie = f"ghid.inainte-de-reanalizare-{datetime.now():%Y-%m-%d-%H%M%S}.md"
        scrie_text(c["dosar"] / copie, vechi)
        scrie_text(g, nou)
        ghidul = f"a adus în ghidul de interviu punctajul și treapta fișei noi; ghidul de dinainte: {copie}"
    _in_analiza(c)
    audit.scrie(c["dosar"], "portofoliul", audit.PROGRAM,
                f"a analizat proiectul de portofoliu la versiunea din istoric (cod {commits[-1].sha[:7]}): {NUME_TREPTE[f['nivel']]}, "
                f"{f['total']:g} din {f['maxim']:g}", commit=commits[-1].sha, nivel=f["nivel"], total=f["total"],
                maxim=f["maxim"])
    if ghidul:
        audit.scrie(c["dosar"], "interviul", audit.PROGRAM, ghidul)


def fisa(c):
    return _citeste(c["dosar"] / "fisa.json")


def refa_fisa(c):
    """Fisa portofoliului calculata din nou, acum, pe commitul salvat: pentru raportul de audit. Aceeasi treapta si
    acelasi scor arata ca rezultatul se reface din intrari; o diferenta arata ca regulile s-au schimbat de atunci."""
    f = fisa(c)
    if not f:
        return None
    try:
        commits = istoric.citeste(c["proiect"], f["commit"])
    except Exception:  # dosarul mutat sau sters, commitul disparut: se spune, nu se ghiceste
        return {"eroare": f"proiectul nu se mai poate citi la versiunea {f['commit'][:7]} ({c['proiect']})"}
    nou, vechi = pasi.fisa_proiect(c["proiect"], commits), f["fisa"]
    return {"nivel": nou["nivel"], "total": nou["total"], "maxim": nou["maxim"],
            "la_fel": (nou["nivel"], nou["total"], nou["maxim"]) == (vechi["nivel"], vechi["total"], vechi["maxim"])}


def fisa_md(c):
    return randare_fisa(fisa(c)["fisa"])


def _eticheta_interviu(k):
    if m := re.fullmatch(r"S(\d+)\.([123])", k):
        return f"întrebarea {m.group(1)}, rândul {m.group(2)}"
    if m := re.fullmatch(r"nota-S(\d+)", k):
        return f"notițele la întrebarea {m.group(1)}"
    if m := re.fullmatch(r"(nota-)?([LT])(\d)", k):
        ce = "întrebarea ta" if m.group(2) == "L" else "întrebarea despre proiect"
        return f"{'notițele la ' if m.group(1) else ''}{ce} {m.group(3)}"
    return {"concluzia": "concluzia", "nota-parcurs": "notițele despre parcurs"}.get(k, f"câmpul {k}")


def _bife_interviu(text):
    from harnesscraft import formular
    return {k: v for k, v in formular.valori(text).items() if re.fullmatch(r"S\d+\.[123]", k)}


def salveaza_interviu(c, valori):
    """Ghidul cu valorile din formular; in jurnal, ce s-a schimbat si starea bifelor dupa. O salvare fara schimbare
    (autosalvarea la iesirea dintr-un camp) nu scrie nimic in jurnal."""
    from harnesscraft import formular
    with _lacat(c):
        vechi = ghid(c)
        nou = formular.scrie(vechi, valori)
        scrie_text(c["dosar"] / "ghid.md", nou)
        if ce := audit.schimbari(formular.valori(vechi), formular.valori(nou), _eticheta_interviu,
                                 lambda k: bool(re.fullmatch(r"S\d+\.[123]", k)), "nepusă"):
            audit.scrie(c["dosar"], "interviul", audit.RECRUTOR, "; ".join(ce), bife=_bife_interviu(nou))


def foaie_probei(c):
    """Foaia probei; scrisa la prima deschidere a pasului 3 cu proba deschisa, goala. Cat proba e inchisa (decizia
    „nu”, refuzul, fara raspuns), o deschidere nu scrie nimic: se citeste foaia goala (B12)."""
    f = c["dosar"] / "proba.md"
    if not f.exists():
        gol = proba.foaie(c["nume"], c["demonstrativ"])
        if not proba_deschisa(c)[0]:
            return gol
        scrie_text(f, gol)
    return f.read_text(encoding="utf-8")


def _eticheta_probei(k):
    if m := re.fullmatch(r"([CD])(\d)", k):
        return f"{'conversațiile' if m.group(1) == 'C' else 'discuția'}, rândul {m.group(2)}"
    return proba.CAMPURI.get(k, k).lower()


def _bife_probei(text):
    return {k: v for k, v in proba.valori(text).items() if re.fullmatch(r"[CD]\d", k)}


def salveaza_proba(c, valori):
    _cere_proba_deschisa(c)
    with _lacat(c):
        vechi = foaie_probei(c)
        nou = proba.scrie(vechi, valori)
        scrie_text(c["dosar"] / "proba.md", nou)
        if ce := audit.schimbari(proba.valori(vechi), proba.valori(nou), _eticheta_probei,
                                 lambda k: bool(re.fullmatch(r"[CD]\d", k)), "nebifat"):
            audit.scrie(c["dosar"], "proba", audit.RECRUTOR, "; ".join(ce), bife=_bife_probei(nou))


def pachetul_probei(c):
    """Pachetul meseriei pe care da candidatul proba: cel din foaia lui; fara foaie, primul. Nu scrie foaia: rezultatul
    si raportul il cer si inainte de pasul 3."""
    f = c["dosar"] / "proba.md"
    return proba.pachetul_foii(f.read_text(encoding="utf-8")) if f.exists() else proba.pachet()


def alege_pachetul(c, id_):
    """Proba pe alta meserie; numai inainte de inceput: un tabel incarcat sau o bifa s-ar nota pe alta cheie."""
    p, text = proba.pachet(id_), foaie_probei(c)
    if proba.inceputa(text, (c["dosar"] / "Raspuns.xlsx").exists()):
        raise ValueError("proba e începută (tabelul încărcat sau o bifă dată): meseria nu se mai schimbă")
    scrie_text(c["dosar"] / "proba.md", proba.schimba_pachetul(text, p))
    audit.scrie(c["dosar"], "proba", audit.RECRUTOR, f"a ales proba pe meseria {p.meseria} ({p.titlu})", pachet=p.id,
                bife_amprenta=p.amprenta)


def incarca_raspuns(c, octeti):
    """Tabelul de raspuns predat. Se citeste intai: unul care nu se poate nota nu-l inlocuieste pe cel bun. Cel vechi
    ramane, cu ora inlocuirii in nume."""
    _cere_proba_deschisa(c)
    nou, tinta = c["dosar"] / "tmp-raspuns.xlsx", c["dosar"] / "Raspuns.xlsx"
    nou.write_bytes(octeti)
    try:
        pachetul_probei(c).raspuns(nou)
    except (zipfile.BadZipFile, KeyError, IndexError, ET.ParseError):
        nou.unlink()
        raise ValueError("fișierul nu e un tabel Excel (.xlsx): candidatul completează tabelul de răspuns din temă") from None
    except ValueError:
        nou.unlink()
        raise
    inlocuit = None
    if tinta.exists():
        inlocuit = f"Raspuns-inlocuit-la-{datetime.now():%Y-%m-%d-%H%M%S}.xlsx"
        tinta.rename(c["dosar"] / inlocuit)
    nou.rename(tinta)
    _in_analiza(c)
    pa = pachetul_probei(c)
    ch = pa.cheia()
    n = proba.nota_cheie(pa.raspuns(c["dosar"] / "Raspuns.xlsx"), ch)
    amp = audit.amprenta(c["dosar"] / "Raspuns.xlsx")
    audit.scrie(c["dosar"], "proba", audit.RECRUTOR, f"a încărcat tabelul de răspuns predat (amprenta, cod {amp})"
                + (f"; cel de dinainte rămâne: {inlocuit}" if inlocuit else ""), tabel=amp)
    audit.scrie(c["dosar"], "proba", audit.PROGRAM,
                f"a potrivit tabelul cu cheia (cod {_amprenta_cheii(pa)}): {len(n['gasite'])} din {ch['erori_de_gasit']} "
                f"greșeli găsite, {len(n['gresite'])} semnalări greșite", cheia=_amprenta_cheii(pa), pachet=pa.id,
                gasite=n["gasite"], gresite=[str(x) for x in n["gresite"]])


def _amprenta_cheii(pa):
    return (pa.dosar / "cheia.sha256").read_text(encoding="utf-8")[:12]


def analizeaza_proba(c, sursa):
    """Fisa probei: programul predat (link sau dosar), analizat cu acelasi cod ca portofoliul, ca informatie, fara
    nota. O clona veche ramane, cu ora inlocuirii in nume: candidatul poate sterge intre timp depozitul."""
    sursa = (sursa or "").strip().strip('"')
    salveaza_proba(c, {"cod": sursa})
    if not sursa:
        raise ValueError("scrii întâi linkul sau dosarul programului lui")
    if de_descarcat(sursa):
        tinta, nou_ = c["dosar"] / "proba-proiect", c["dosar"] / "tmp-proba-proiect"
        shutil.rmtree(nou_, ignore_errors=True)  # o clona pe jumatate, de la o incercare intrerupta
        r = _git("clone", "--quiet", sursa, str(nou_))
        if r.returncode:
            shutil.rmtree(nou_, ignore_errors=True)
            raise ValueError(f"Programul nu s-a putut descărca de la {sursa}: {de_ce_nu_se_descarca(r.stderr)}")
        if tinta.exists():
            tinta.rename(c["dosar"] / f"proba-proiect-inlocuit-la-{datetime.now():%Y-%m-%d-%H%M%S}")
        nou_.rename(tinta)
        proiect = tinta
    else:
        proiect = Path(sursa)
        if not proiect.is_dir():
            raise ValueError(f"dosarul {sursa} nu există pe acest calculator")
        if not _cu_git(proiect):
            raise ValueError(f"dosarul {sursa} nu are istoric git (commit-uri): fără istoric nu se vede cum a lucrat")
    commits = istoric.citeste(str(proiect))
    fp = pasi.fisa_proiect(str(proiect), commits)
    _scrie(c["dosar"] / "fisa-proba.json", {"fisa": fp, "sursa": sursa,
                                           "commit": commits[-1].sha,
                                           "calculat": datetime.now().isoformat(timespec="seconds")})
    _in_analiza(c)
    audit.scrie(c["dosar"], "proba", audit.PROGRAM,
                f"a analizat programul probei {sursa} la versiunea din istoric (cod {commits[-1].sha[:7]}): {NUME_TREPTE[fp['nivel']]}, "
                f"{fp['total']:g} din {fp['maxim']:g}, fără notă", commit=commits[-1].sha, sursa=sursa)


def fisa_probei(c):
    return _citeste(c["dosar"] / "fisa-proba.json")


# Decizia de proba: la sfarsitul interviului, recrutorul spune daca candidatul merge la proba, cu motivul; daca da, ii
# trimite invitatia (`proba.invitatie`) si consemneaza raspunsul lui. Proba se deschide numai dupa acord. Acordul e
# acordul de a da proba, nu temeiul prelucrarii datelor.
DECIZIA = "decizia-probei.json"


def decizia_probei(c):
    f = c["dosar"] / DECIZIA
    return _citeste(f) if f.exists() else None


def _interviu_inceput(c):
    return bool(re.search(r"^- S\d+\.[123] \[(da|nu)\]", ghid(c) or "", re.M))


def _proba_inceputa(c):
    f = c["dosar"] / "proba.md"
    return proba.inceputa(f.read_text(encoding="utf-8") if f.exists() else "", (c["dosar"] / "Raspuns.xlsx").exists())


def hotaraste_proba(c, decizia, motivul=""):
    with _lacat(c):
        _hotaraste_proba(c, decizia, motivul)


def _hotaraste_proba(c, decizia, motivul):
    motivul = " ".join((motivul or "").split())
    if decizia not in ("da", "nu"):
        raise ValueError("alegi „da” sau „nu”: merge sau nu la probă")
    if not _interviu_inceput(c):
        raise ValueError("decizia de probă se ia după interviu: întâi bifezi răspunsurile lui")
    if decizia == "nu" and not motivul:
        raise ValueError("scrii motivul pentru care nu merge la probă")
    vechi = decizia_probei(c)
    if decizia == "nu" and _proba_inceputa(c):
        raise ValueError("proba e începută (tabelul încărcat sau o bifă dată): decizia nu se mai schimbă în „nu”")
    if vechi and (vechi["decizia"], vechi["motivul"]) == (decizia, motivul):
        return
    acordul = vechi.get("acordul") if vechi and vechi["decizia"] == decizia else None
    _scrie(c["dosar"] / DECIZIA, {"decizia": decizia, "motivul": motivul, "acordul": acordul,
                                 "ora": datetime.now().isoformat(timespec="seconds")})
    _in_analiza(c)
    ce = "merge la probă" if decizia == "da" else "fără probă"
    schimbat = f", în locul deciziei de dinainte („{'merge la probă' if vechi['decizia'] == 'da' else 'fără probă'}”)" \
        if vechi and vechi["decizia"] != decizia else ", cu motivul schimbat" if vechi else ""
    audit.scrie(c["dosar"], "interviul", audit.RECRUTOR, f"a hotărât, după interviu: {ce}{schimbat}", decizia=decizia)


def consemneaza_acordul(c, raspuns, data, cum):
    with _lacat(c):
        _consemneaza_acordul(c, raspuns, data, cum)


def _data_iso(data):
    """Data scrisa de recrutor, `ZZ.LL.AAAA` (sau `AAAA-LL-ZZ`, din fisierele vechi), ca `AAAA-LL-ZZ`; altfel None."""
    for forma in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(data, forma).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _consemneaza_acordul(c, raspuns, data, cum):
    d = decizia_probei(c)
    if not d or d["decizia"] != "da":
        raise ValueError("întâi decizia de probă, la sfârșitul interviului")
    if raspuns not in ("da", "nu"):
        raise ValueError("alegi ce a răspuns candidatul: a acceptat sau a refuzat proba")
    data, cum = (data or "").strip(), " ".join((cum or "").split())
    if not (data := _data_iso(data)):
        raise ValueError("scrii data răspunsului candidatului în forma ZZ.LL.AAAA, de pildă 21.10.2026")
    if not cum:
        raise ValueError("scrii cum a răspuns candidatul (de exemplu: pe e-mail)")
    if raspuns == "nu" and _proba_inceputa(c):
        raise ValueError("proba e începută (tabelul încărcat sau o bifă dată): refuzul nu se mai poate consemna")
    d["acordul"] = {"raspuns": raspuns, "data": data, "cum": cum, "ora": datetime.now().isoformat(timespec="seconds")}
    _scrie(c["dosar"] / DECIZIA, d)
    audit.scrie(c["dosar"], "proba", audit.RECRUTOR,
                f"a consemnat că candidatul {'a acceptat' if raspuns == 'da' else 'a refuzat'} proba, pe {md.data(data)} ({cum})",
                acordul=raspuns)


def proba_deschisa(c):
    """(deschisa, de ce). Un candidat cu proba incepută inainte de regula aceasta nu se blocheaza."""
    d = decizia_probei(c)
    if d is None:
        return (True, "decizia de probă neconsemnată: proba e de dinainte de regulă") if _proba_inceputa(c) else \
            (False, "Întâi decizia de probă, la sfârșitul interviului.")
    if d["decizia"] == "nu":
        return False, f"Fără probă: {d['motivul']}"
    a = d.get("acordul")
    if a is None:
        return False, "Așteaptă răspunsul candidatului la invitația la probă."
    if a["raspuns"] == "nu":
        return False, f"Fără probă: candidatul a refuzat-o, pe {md.data(a['data'])} ({a['cum']})."
    return True, ""


def fara_proba(c):
    """Motivul, cand proba nu se mai da (decizia „nu” sau refuzul candidatului); altfel None."""
    d = decizia_probei(c)
    if d and (d["decizia"] == "nu" or (d.get("acordul") or {}).get("raspuns") == "nu"):
        return proba_deschisa(c)[1]
    return None


def _cere_proba_deschisa(c):
    deschisa, motiv = proba_deschisa(c)
    if not deschisa:
        raise ValueError(motiv[0].lower() + motiv[1:].rstrip("."))


def nota_probei(c):
    """Nota probei, din foaia de acum si din tabelul predat, cu regula din `proba.py`. Ca rezultatul: calculata la
    fiecare deschidere, fara fisier. O parte bifata pe jumatate da `nota` None si motivul in `eroare`; o cheie
    schimbata ridica ValueError."""
    p = pachetul_probei(c)
    ch = p.cheia()
    f, r = c["dosar"] / "proba.md", c["dosar"] / "Raspuns.xlsx"
    semnalate = p.raspuns(r) if r.exists() else None
    din_cheie = proba.nota_cheie(semnalate, ch) if semnalate is not None else None
    try:
        conv, disc = proba.bife(f.read_text(encoding="utf-8")) if f.exists() else (None, None)
        n, eroare = proba.nota(din_cheie, conv, disc), None
    except ValueError as ex:
        n, eroare = None, str(ex)
    return {"pachet": p, "cheia": ch, "semnalate": semnalate, "din_cheie": din_cheie, "nota": n, "eroare": eroare}


def rezultat(c):
    """Pasul 4: punctajul, din ghidul de acum, cu regula din `interviu.py`, si nota probei. Fara buton si fara
    fisier: o bifa schimbata dupa o zi se vede la urmatoarea deschidere. Un ghid sau o proba completata pe jumatate
    ridica ValueError; cea a probei incepe cu „proba”."""
    g = ghid(c)
    if not g:
        return None
    try:
        p = nota_probei(c)
    except ValueError as ex:
        raise ValueError(f"proba: {ex}") from None
    if p["eroare"]:
        raise ValueError(f"proba: {p['eroare']}")
    s = interviu.scor(g, proba=p["nota"]["nota"])
    s["proba"] = p
    return s
