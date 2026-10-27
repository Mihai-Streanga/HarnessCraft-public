"""Interfata prototipului: o pagina web locala, servita din biblioteca standard Python.
Pornire: `Porneste_HarnessCraft.bat`, sau `python -m harnesscraft.interfata`.

Raspunde numai pe acest calculator (127.0.0.1) si nu cheama nimic din afara. Nu calculeaza nimic al ei: fiecare buton cheama
o functie din `candidati.py`, care cheama aceleasi functii ca terminalul. Aspectul e cel din SkyRoll.

Un POST se primeste numai de pe pagina proprie (Host si Origin verificate): altfel orice site deschis in browser
ar putea apasa, de la distanta, butoanele care scriu in dosarul candidatului.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from email.parser import BytesParser
from email.policy import default as POLITICA_EMAIL

from harnesscraft import audit, candidati, formular, interviu, md, proba, set_exemple, tintite
from harnesscraft.fisa import (ARII_RECRUTOR, NUME_TREPTE, TREPTE_RECRUTOR, actuala, explicatii_scara,
                               lipsa_pentru_recrutor, pentru_recrutor, scara_recrutor)
from harnesscraft.interviu import INTREBARI, NOTA as NOTA_INTERVIU
from harnesscraft.total import PLAFON_FARA_COD

PORT = 8765
STATIC = Path(__file__).with_name("static")
MAX_INCARCARE = 5 * 1024 * 1024  # un tabel de raspuns are cativa kilooctet
TEMA = {"xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "txt": "text/plain; charset=utf-8"}
TIPURI = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".woff2": "font/woff2",
          ".txt": "text/plain; charset=utf-8", ".png": "image/png"}
e = html.escape
ROMANE = ["", "I", "II", "III", "IV", "V"]  # partile interviului; intrebarile 1-7 raman cu cifre arabe


def nerupt(s):
    """Un text scurt care nu se rupe pe doua randuri (o treapta, un total): spatii nerupte (B22)."""
    return e(s).replace(" ", "&nbsp;")


def nr(x, f="g"):
    """O cifra in scrierea romaneasca: virgula zecimala, punct la mii."""
    return format(x, f).replace(",", " ").replace(".", ",").replace(" ", ".")

AJUTOR = {
    "acasa": ("Ecranul de început: ce face programul, cei patru pași și candidații în lucru.",
              ["„Candidat nou” adaugă un om și proiectul lui; de acolo începe pasul 1, portofoliul.",
               "Un clic pe un candidat în lucru te duce la pasul la care a rămas.",
               "„Vezi exemplele” deschide candidați inventați, cu toți pașii făcuți, numai de citit: așa înveți aplicația.",
               "„Vezi toți candidații” deschide istoricul, cu cei finalizați și cu căutarea."]),
    "candidati": ("Toți candidații, pe trei grupuri, după unde au ajuns: propuse, în analiză, finalizate.",
                  ["Cauți un om după nume sau proiect și apeși „Caută”; „Toate candidaturile” golește căutarea.",
                   "Un clic pe candidat te duce la pasul lui.",
                   "Un candidat trece singur în „În analiză” la prima analiză și în „Finalizate” când apeși „Finalizează "
                   "candidatura”, la pasul 4."]),
    "exemple": ("Candidații din capitolul de exemple al manualului, persoane inventate, cu toți pașii făcuți. Numai de "
                "citit: câmpurile și butoanele nu se apasă, iar candidații tăi rămân neatinși.",
                ["Alegi un candidat și un pas, ca la un candidat al tău.",
                 "Scoți raportul pentru dosar, pe scurt sau auditul, de tipărit sau ca PDF.",
                 "„Reface exemplele” le face din nou, după o actualizare a programului: cam 20 de secunde."]),
    "raport": ("Raportul unui candidat, de tipărit sau de salvat ca PDF, pentru dosarul lui. Bara din stânga și butoanele "
               "de sus rămân pe ecran; pe hârtie nu apar.",
               ["„Tipărește sau salvează ca PDF” deschide tipărirea browserului; acolo alegi imprimanta sau „Salvează ca PDF”.",
                "Raportul pe scurt încape în cel mult două pagini, pentru un manager; raportul de audit spune cum s-a "
                "ajuns la rezultat, pas cu pas.",
                "Cifrele sunt ale unui prototip, necalibrat: decizia o iau oamenii care citesc raportul."]),
    "rapoarte": ("Scoți rapoartele numai pentru cine alegi: întâi pe cine, apoi ce raport. Iese un singur document de "
                 "tipărit sau de salvat ca PDF, fiecare candidat pe pagină nouă.",
                 ["Cauți după nume sau proiect și alegi, dacă vrei, starea, meseria probei sau treapta; apeși „Caută”.",
                  "Bifezi candidații pe care îi vrei, sau „Toți cei găsiți”.",
                  "Alegi raportul: pentru dosar (întreg, cu notițele), pe scurt (cel mult două pagini, pentru un manager), "
                  "de audit (cum s-a ajuns la rezultat, pas cu pas), auditul pe scurt, sau lista celor aleși (un tabel cu "
                  "notele, câte unul pe meserie).",
                  "Apeși „Scoate raportul”, apoi „Tipărește sau salvează ca PDF”."]),
    "nou": ("Creează dosarul candidatului și verifică dacă proiectul are istoricul proiectului (git): istoricul arată "
            "cum a lucrat omul, pas cu pas.",
            ["Ceri candidatului proiectul de portofoliu, unul pe care l-a făcut deja: de obicei un link GitHub (din CV sau trimis pe e-mail), uneori un dosar "
             "copiat pe acest calculator.",
             "Scrii numele candidatului.",
             "Lipești proiectul în câmpul „Proiectul de portofoliu”: linkul (GitHub, GitLab), sau alegi dosarul cu „Alege "
             "dosarul…”. Un link se descarcă cu tot istoricul, în cel mult un minut.",
             "Dacă proiectul e privat, candidatul îți trimite un singur fișier cu tot istoricul, pe care îl face în "
             f"dosarul lui (comanda: {candidati.BUNDLE}). Îl salvezi pe acest calculator și îl alegi cu „Alege fișierul "
             ".bundle…”.",
             "Dacă omul nu are proiect cu cod (lucrează cu AI-ul numai în conversație), bifezi „Candidatul nu are "
             "proiect cu cod” și scrii motivul. Portofoliul intră atunci în total cu 0: totalul ajunge cel mult la "
             f"{nr(PLAFON_FARA_COD)} din 100, iar ce aduce în loc citești la interviu, fără notă.",
             "Bifezi „Autoevaluare” numai dacă omul se evaluează singur, ca demonstrație.",
             "Apeși „Adaugă”. Pasul următor e portofoliul."]),
    "fisa": ("Citește istoricul proiectului de portofoliu (git) și calculează fișa proiectului de portofoliu: treapta provizorie, punctajul proiectului și "
             "dovezile, plus drumul zi cu zi. O calculează programul, din reguli scrise; totul rămâne pe acest calculator.",
             ["Proiectul e cel dat la „Candidat nou”. Pentru alt proiect, adaugi un candidat nou.",
              "Apeși „Analizează proiectul de portofoliu”. Durează de la câteva secunde la un minut.",
              "Citești treapta și ce lipsește pentru treapta următoare: de acolo vin întrebările la care ești atent.",
              "Treci la interviu: întrebările s-au pregătit odată cu fișa proiectului de portofoliu.",
              "La un candidat fără proiect cu cod, pasul e deja încheiat: ecranul arată hotărârea ta și motivul."]),
    "interviu": ("Pagina interviului: o ții deschisă cât vorbești cu candidatul. Întrebările din partea III sunt "
                 "aceleași pentru toți și au notă; cele din partea IV sunt pentru discuție.",
                 ["Pagina s-a pregătit singură, după fișa proiectului de portofoliu (pasul 1).",
                  "Înainte de interviu, citești în partea IV întrebările despre proiect: le-a ales programul, cel mult două "
                  "din ce lipsește în fișă și cel mult două din istoricul proiectului (cum a crescut proiectul și o schimbare "
                  "a regulilor pentru AI, pe care candidatul o explică), fiecare cu ce afli din răspuns.",
                  "La fiecare întrebare 1–7 asculți răspunsul și apeși „da” sau „nu” pe cele trei rânduri; „nepusă”, "
                  "dacă n-ai pus-o. Nota e media întrebărilor puse.",
                  "Scrii notițe unde vrei. Totul se salvează singur; „Salvează” salvează pe loc și îți arată ora.",
                  "Poți reveni oricând: schimbi o bifă sau o notiță, iar rezultatul se actualizează singur.",
                  "La sfârșit scrii concluzia ta și hotărăști dacă merge la probă: „da” sau „nu”, cu motivul. Interviul e "
                  "gata numai cu decizia luată."]),
    "proba": ("Proba practică: aceeași temă pentru toți cei de pe aceeași meserie (la salarizare, un stat de plată de "
              "verificat cu AI-ul). Nota probei o "
              "calculează programul, din trei părți egale: tabelul de răspuns, conversațiile și discuția de după predare.",
              ["Întâi invitația: dacă la sfârșitul interviului ai hotărât că merge la probă, aici găsești mesajul "
               "pentru candidat (ce face, cât durează, ce predă, ce se întâmplă cu datele lui). Completezi partea firmei, "
               "i-l trimiți și salvezi ce a răspuns: a acceptat sau a refuzat, data și cum. Tema apare numai după ce acceptă.",
               "Descarci cele trei fișiere ale temei și i le trimiți candidatului pe e-mail. Munca e gândită pentru cel "
               "mult două ore; o predă în trei zile. Nu-i spui câte greșeli are tema. Dacă programul are probe pe mai multe "
               "meserii, o alegi întâi pe a lui, sus, la „Meseria probei”.",
               "Când îl primești înapoi, încarci tabelul de răspuns completat. Programul îl potrivește cu răspunsurile "
               "corecte (cheia) și arată, pe fiecare greșeală, dacă a găsit-o, plus ce a semnalat greșit. Nota din tabel: "
               "greșelile găsite minus semnalările greșite, împărțit la numărul greșelilor, cel puțin 0. Ce a scris "
               "candidatul pe fiecare angajat (la altă meserie, pe fiecare loc din temă) se deschide la un clic.",
               "Lipești linkurile conversațiilor cu AI-ul, primite de la candidat odată cu tabelul (butonul „Share” / "
               "„Partajează” din Claude sau ChatGPT), în caseta „Cum a gândit”. Programul doar le păstrează; le deschizi tu "
               "și le citești. Dacă a lucrat și cu un program, scrii unde e în caseta „Ce a făcut” (poate da amândouă) și apeși "
               "„Analizează proiectul probei”: fișa probei apare deasupra discuției, ca informație, fără notă.",
               "Citești conversațiile și apeși „da” sau „nu” pe cele patru rânduri; „nebifat”, până te hotărăști.",
               "La discuția cu candidatul pui cele trei întrebări, bifezi și notezi ce a răspuns.",
               "Totul se salvează singur. O parte lipsă face proba „incompletă”, nu zero."]),
    "rezultat": ("Nota interviului (1 + numărul de „da” la fiecare întrebare, apoi media celor puse) și totalul pe "
                 "treimi: portofoliul, interviul, proba. Se calculează singur, din ce e bifat acum în interviu și în probă.",
                 ["Deschizi pagina: notele și totalul sunt la zi, de fiecare dată.",
                  "Cu proba neterminată, totalul se arată „incomplet”, cu partea lipsă numită.",
                  "Ai schimbat ceva în interviu? Revii aici și vezi deja noul rezultat.",
                  "„Raportul pentru dosar” îl deschide direct, de tipărit sau PDF. „Alte rapoarte” deschide „Rapoarte” "
                  "cu el ales: cel pe scurt (cel mult două pagini, pentru un manager, lângă CV), auditul (cum s-a ajuns "
                  "la rezultat).",
                  "„Șterge candidatul” scoate tot dosarul lui de pe discul acestui calculator, definitiv, după ce îi scrii numele."]),
    # ecranul fara intoarcere are si el ajutorul lui (B15)
    "sterge": ("Ștergerea definitivă a unui candidat: tot dosarul lui, de pe discul acestui calculator. Nu se poate reface.",
               ["Citești ce dispare și ce rămâne în afara aplicației (PDF-urile salvate de tine, fișierele primite).",
                "Scrii numele candidatului întocmai, apoi „Șterge definitiv”.",
                "Te-ai răzgândit? „← Înapoi la rezultat”: nu se șterge nimic."]),
}


# ── Pagina ────────────────────────────────────────────────────────────────────

def _bara(c=None, activ=None):
    r = ['<a class="logo" href="/">Harness<span>Craft</span></a>',
         '<span class="subtitlu">prototip · necalibrat</span>',
         # „Candidat nou” al doilea, la indemana; istoricul dupa el (observatia autorului)
         f'<a class="nav{" activ" if activ == "acasa" else ""}" href="/">Acasă</a>',
         f'<a class="nav{" activ" if activ == "nou" else ""}" href="/nou">Candidat nou</a>',
         f'<a class="nav{" activ" if activ == "istoric" else ""}" href="/candidati">Istoricul candidaților</a>',
         f'<a class="nav{" activ" if activ == "rapoarte" else ""}" href="/rapoarte">Rapoarte</a>',
         f'<a class="nav{" activ" if activ == "manual" else ""}" href="/manual">Manualul</a>',
         f'<a class="nav{" activ" if activ == "exemple" else ""}" href="/exemple">Exemple</a>']
    if c:
        s = candidati.stari(c)
        r.append(f'<div class="sectiune">{e(c["nume"])}</div>')
        for i, (p, nume) in enumerate(candidati.PASI, 1):
            stare = s[p][0]
            semn = {"gata": "✓", "în lucru": "…", "de făcut": str(i), "blocat": "–", "fără probă": "–"}[stare]
            clasa = "pas" + (" activ" if p == activ else "") + (" blocat" if stare == "blocat" else "")
            r.append(f'<a class="{clasa}" href="/c/{c["id"]}/{p}"><span class="semn {stare.replace(" ", "-").replace("ă", "a")}">'
                     f'{semn}</span>{e(nume)}</a>')
    r.append('<div class="spatiu"></div><div class="subsol">HarnessCraft · prototip</div>')
    return "\n".join(r)


def _media_puse(m):
    """„media celor 7 întrebări”; cu întrebări nepuse, „media celor 5 întrebări puse (din 7)” (B26)."""
    return (f'media celor {m["punctate"]} întrebări' if m["punctate"] == m["din"] else
            f'media celor {m["punctate"]} întrebări puse (din {m["din"]})')


def pagina(titlu, corp, c=None, activ=None, eroare=None, clasa=""):
    cutie = f'<div class="cutie eroare"><strong>Nu s-a putut.</strong> {e(eroare[:1].upper() + eroare[1:])}</div>' if eroare else ""
    return f"""<!doctype html>
<html lang="ro"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titlu)} — HarnessCraft</title><link rel="stylesheet" href="/static/stil.css"></head>
<body{f' class="{clasa}"' if clasa else ""}><aside class="bara">{_bara(c, activ)}</aside>
<main>{cutie}{corp}</main><script src="/static/app.js"></script></body></html>"""


def _ajutor(pas, extra=""):
    """Butonul „Cum folosesc” si fereastra lui (atributul HTML popover: fara JavaScript, fara dependente)."""
    ce, pasi = AJUTOR[pas]
    lista = f'<ol>{"".join(f"<li>{e(x)}</li>" for x in pasi)}</ol>' if pasi else ""
    ecran = dict(candidati.PASI).get(pas) or {"rapoarte": "Rapoarte", "acasa": "Acasă", "candidati": "Istoricul candidaților",
                                              "exemple": "Exemple", "raport": "Rapoartele",
                                              "sterge": "Ștergerea"}.get(pas, "Candidat nou")
    # „i”-ul e o litera din fontul paginii, intr-un cerc: semnul ℹ nu e in Public Sans si iesea dintr-alt font
    return (f'<button type="button" class="buton secundar buton-info" popovertarget="ajutor-{pas}">'
            f'<span class="semn-info" aria-hidden="true">i</span>Cum folosesc</button>'
            f'<div id="ajutor-{pas}" popover class="fereastra"><div class="fereastra-cap"><h2>Cum folosesc: {e(ecran)}</h2>'
            f'<button type="button" class="inchide" popovertarget="ajutor-{pas}" popovertargetaction="hide" '
            f'aria-label="Închide">×</button></div>'
            f'<p>{e(ce)}</p>{lista}{extra}<p class="la-manual"><a href="/manual">Tot manualul →</a></p></div>')


def _urmator(c, pas):
    nume = dict(candidati.PASI)
    ordine = [p for p, _ in candidati.PASI]
    i = ordine.index(pas)
    if i + 1 == len(ordine):
        return '<div class="urmator">Ultimul pas. <a class="buton" href="/">Înapoi acasă</a></div>'
    p = ordine[i + 1]
    return f'<div class="urmator">Pasul următor: <a class="buton" href="/c/{c["id"]}/{p}">{i + 2}. {e(nume[p])} →</a></div>'


def _buton(eticheta, actiune, activ=True, motiv="", lung=False, clasa="buton"):
    dezactivat = "" if activ else " disabled"
    lucru = ' data-lung="1"' if lung else ""
    return (f'<form method="post" action="{actiune}" class="actiune"{lucru}><button class="{clasa}"{dezactivat}>'
            f'{e(eticheta)}</button>' + (f'<span class="motiv">{e(motiv)}</span>' if motiv else "") + "</form>")


def cale(s):
    """O cale de pe calculator, in forma din Explorer (bare inverse), la fel in raport si in audit (B13); un link ramane
    cum e."""
    return s if candidati.LINK.match(s or "") else (s or "").replace("/", chr(92))


def proiect(c):
    """Numele proiectului, in ghilimele: pe ecran se vede ca un nume, nu ca un pas sau o parte a interviului."""
    if candidati.fara_cod(c):
        return "fără proiect cu cod"
    return f'„{e(candidati.nume_sursei(c["sursa"]))}”'  # nu din cale: o clona se cheama „proiect”


def _despre(c):
    """Sub numele candidatului: „proiectul „X”” sau „fără proiect cu cod”, cu calea la trecerea mouse-ului."""
    if candidati.fara_cod(c):
        return '<span>fără proiect cu cod</span>'
    return f'<span title="{e(c["proiect"])}">proiectul {proiect(c)}</span>'


def _treptele(proba=False):
    """De unde vin treptele fisei: in „Cum folosesc”, nu in fisa, unde ingreunau citirea (observatia autorului)."""
    return f'<h3>Treptele fișei</h3><div class="text-ghid">{md.html_din(chr(10).join(explicatii_scara(proba)))}</div>'


def _ce_e_treapta(n):
    """Treapta candidatului, explicata pe ecran, sub cifra ei: recrutorul o vede inainte de „Vezi dovezile”."""
    return (f'<p class="estompat ce-e-treapta"><b>Treapta {n + 1}, {e(NUME_TREPTE[n])}:</b> '
            f'{e(TREPTE_RECRUTOR[n])}</p>')


def _antet(c, pas, extra=""):
    i = [p for p, _ in candidati.PASI].index(pas) + 1
    demo = '<span class="eticheta demo">autoevaluare · demonstrativ</span>' if c["demonstrativ"] else ""
    return (f'<div class="antet"><div class="supratitlu">{e(c["nume"])} · {_despre(c)} {demo}</div>'
            f'<div class="rand-titlu"><h1>{i}. {e(dict(candidati.PASI)[pas])}</h1>{_ajutor(pas, extra)}</div></div>')


# ── Ecranele ──────────────────────────────────────────────────────────────────

def _card(c):
    p = candidati.pasul_curent(c)
    i = [x for x, _ in candidati.PASI].index(p) + 1
    demo = '<span class="eticheta demo">demonstrativ</span>' if c["demonstrativ"] else ""
    gata = candidati.stari(c)["rezultat"][0] == "gata"
    return (f'<a class="card" href="/c/{c["id"]}/{p}"><div class="card-nume">{e(c["nume"])} {demo}</div>'
            f'<div class="card-cale">{_despre(c)}</div>'
            f'<div class="card-pas">{"Rezultatul e calculat" if gata else f"Urmează: {i}. "}'
            f'{"" if gata else e(dict(candidati.PASI)[p])}</div></a>')


PASII_PE_SCURT = [  # ecranul de inceput: ce face fiecare pas, intr-un rand
    ("Portofoliul", "Programul citește proiectul lui, cu istoricul proiectului (git), și face fișa: treapta și punctajul."),
    ("Interviul", "Șapte întrebări, aceleași pentru toți. Asculți și apeși „da” sau „nu”."),
    ("Proba", "O temă practică de cel mult două ore: un stat de plată de verificat cu AI-ul."),
    ("Rezultatul", "Totalul din cele trei și raportul pentru dosar, de tipărit sau PDF."),
]


def acasa(dosar):
    """Ecranul de inceput: ce face aplicatia, cei patru pasi, „Candidat nou” la indemana si toti candidatii in lucru,
    fara limita (o firma mare evalueaza multi deodata). Istoricul intreg, cu cautarea, are ecranul lui. Si intrarea
    spre exemple, ca sa le gaseasca oricine invata aplicatia (ideea autorului)."""
    pasi = "".join(f'<div class="pas-acasa"><span class="semn de-facut">{i}</span><b>{e(n)}</b><p>{e(t)}</p></div>'
                   for i, (n, t) in enumerate(PASII_PE_SCURT, 1))
    corp = [f'<div class="rand-titlu"><h1>Acasă</h1>{_ajutor("acasa")}</div>'
            '<div class="actiune"><a class="buton" href="/nou">Candidat nou</a></div>',
            '<p class="intro">HarnessCraft te ajută să vezi cum lucrează un om cu AI-ul: din proiectul lui, la interviu și '
            'la o probă practică. Patru pași, pentru fiecare candidat:</p>', f'<div class="pasi-acasa">{pasi}</div>']
    corp.append('<h2>Învață aplicația pe exemple</h2><p>Candidații din capitolul de exemple al manualului, persoane '
                'inventate, de feluri diferite: fiecare cu toți pașii făcuți și cu rapoartele lui. Te uiți, treci de la un '
                'pas la altul și scoți raportul, ca să vezi aplicația înainte s-o folosești; numai de citit.</p>'
                '<div class="actiune"><a class="buton" href="/exemple">Vezi exemplele</a></div>')
    toti = candidati.lista(dosar)
    in_lucru = [c for c in toti if c["stare"] != "finalizate"]
    # „în lucru” aduna doua stari: spus, nu ghicit fata de „În analiză” din istoric (B24)
    corp.append(f'<h2>În lucru <span class="estompat">({len(in_lucru)}): propuse și în analiză</span></h2>')
    if in_lucru:
        corp.append(f'<div class="carduri">{"".join(_card(c) for c in in_lucru)}</div>')
    else:
        corp.append('<p class="estompat">Niciun candidat în lucru. Începi cu „Candidat nou”.</p>')
    if toti:
        # un buton, ca restul; „toti 1, si cei finalizati, cu cautare” nu arata si nu suna bine; plin, ca „Candidat nou”:
        # secundar, la sfarsitul paginii, nu se distingea (autorul)
        corp.append('<div class="actiune"><a class="buton" href="/candidati">Vezi toți candidații</a></div>')
    return pagina("Acasă", "".join(corp), activ="acasa")


def istoric(dosar, cauta="", sters=False, eroare=None):
    """Candidatii, pe cele trei stari, ca dosarele de pe disc; cautarea, dupa nume sau proiect, in toate trei. `sters`:
    vine de la o stergere, care se confirma aici."""
    gata = '<div class="cutie avert">Candidatul a fost șters definitiv, cu tot dosarul lui.</div>' if sters else ""
    if not candidati.lista(dosar):
        corp = (f'<div class="rand-titlu"><h1>Istoricul candidaților</h1>{_ajutor("candidati")}</div>'
                '<div class="gol"><p>Niciun candidat încă.</p>'
                '<p>Un candidat e un om și proiectul lui, cu istoricul proiectului (git). Începi de aici:</p>'
                '<a class="buton" href="/nou">Adaugă primul candidat</a></div>')
        return pagina("Istoricul candidaților", gata + corp, activ="istoric", eroare=eroare)
    cs = candidati.lista(dosar, cauta)
    corp = [f'<div class="rand-titlu"><h1>Istoricul candidaților</h1>{_ajutor("candidati")}</div>'
            '<div class="actiune"><a class="buton" href="/nou">Candidat nou</a></div>',
            f'<form method="get" action="/candidati" class="cautare"><input type="search" name="q" value="{e(cauta)}" '
            'placeholder="Caută după nume sau proiect" aria-label="Caută un candidat"><button class="buton secundar">'
            'Caută</button>' + ('<a class="buton secundar" href="/candidati">Toate candidaturile</a>' if cauta else '') +
            '</form>', gata]
    if cauta and not cs:
        corp.append(f'<p class="estompat">Niciun candidat cu „{e(cauta)}” în nume sau în proiect.</p>')
    for stare, nume in candidati.STARI:
        grup = [c for c in cs if c["stare"] == stare]
        if grup or not cauta:
            corp.append(f'<h2>{nume} <span class="estompat">({len(grup)})</span></h2>' +
                        (f'<div class="carduri">{"".join(_card(c) for c in grup)}</div>' if grup else
                         '<p class="estompat">Niciunul.</p>'))
    return pagina("Istoricul candidaților", "".join(corp), activ="istoric", eroare=eroare)


def nou_formular(valori=None, eroare=None):
    v = valori or {}
    # la o eroare despre proiect, campul lui se marcheaza; numele lipsa are mesajul lui
    rau = ' class="camp-gresit" aria-invalid="true"' if eroare and not eroare.startswith("Lipsește numele") else ""
    bifat = " checked" if v.get("demonstrativ") else ""
    fara = " checked" if v.get("fara_cod") else ""
    corp = f"""<div class="rand-titlu"><h1>Candidat nou</h1>{_ajutor("nou")}</div>
<form method="post" action="/nou" class="formular" data-lung="1">
<label>Numele candidatului<input name="nume" value="{e(v.get('nume', ''))}" required autofocus></label>
<label>Proiectul de portofoliu<input name="sursa" value="{e(v.get('sursa', ''))}"{rau}
 placeholder="C:\\Proiecte\\nume-proiect   sau   https://github.com/cineva/proiect">
<span class="indiciu">Un link se descarcă cu tot istoricul; poate dura un minut. Un proiect privat vine ca un singur
fișier, cu numele terminat în <b>.bundle</b>.</span></label>
<div class="actiune alege-proiect"><button type="button" class="buton secundar" data-alege="dosar">Alege dosarul…</button>
<button type="button" class="buton secundar" data-alege="bundle">Alege fișierul .bundle…</button>
<span class="motiv">Se deschide fereastra Windows; calea ajunge singură în câmp.</span></div>
<label class="bifa"><input type="checkbox" name="fara_cod" value="1"{fara}> Candidatul nu are proiect cu cod: lucrează
cu AI-ul numai în conversație. Portofoliul intră în total cu 0, deci totalul ajunge cel mult la {nr(PLAFON_FARA_COD)} din
100; ce aduce în loc citești la interviu, fără notă.</label>
<label>Motivul (obligatoriu când bifezi că nu are proiect cu cod)<textarea name="motiv_fara_cod" rows="2">{e(v.get('motiv_fara_cod', ''))}</textarea></label>
<label class="bifa"><input type="checkbox" name="demonstrativ" value="1"{bifat}> Autoevaluare, demonstrativ:
candidatul răspunde și bifează singur, ca să se vadă cum funcționează. Nu e o evaluare.</label>
<button class="buton">Adaugă</button></form>"""
    return pagina("Candidat nou", corp, activ="nou", eroare=eroare)


def pas_fisa(c, eroare=None):
    f = candidati.fisa(c)
    corp = [_antet(c, "fisa", _treptele())]
    if motivul := candidati.fara_cod(c):
        corp.append(_fara_cod(motivul))
        corp.append('<p class="estompat">Nu e nimic de analizat. Dacă aduce totuși un proiect cu cod, îl adaugi ca '
                    '<a href="/nou">candidat nou</a>, cu proiectul.</p>')
        corp.append(_urmator(c, "fisa"))
    elif f:
        corp.append(_buton("Analizează din nou proiectul de portofoliu", f"/c/{c['id']}/fisa", lung=True, clasa="buton secundar",
                           motiv=f"Calculată la {md.data(f['calculat'])}. Răspunsurile din interviu rămân."))
        fi = f["fisa"]
        # sus numai ce conteaza: treapta, punctajul si cele patru arii; dovezile si drumul se deschid la un clic
        arii = "".join(f'<div class="cifra"><span>{e(ARII_RECRUTOR[n])}</span><b>{nr(x["puncte"])}</b><i>din 4</i></div>'
                       for n, x in fi["principii"].items() if n not in fi["goluri"])
        corp.append(f'<div class="cifre aliniate"><div class="cifra"><span>Treapta provizorie</span>'
                    f'<b class="treapta">{nerupt(NUME_TREPTE[fi["nivel"]])}</b><i>{fi["nivel"] + 1} din {len(NUME_TREPTE)}</i></div>'
                    f'<div class="cifra"><span>Punctajul proiectului</span>'
                    f'<b>{nr(fi["total"])}</b><i>din {nr(fi["maxim"])}, necalibrat</i></div>{arii}</div>'
                    + _ce_e_treapta(fi["nivel"]))
        if actuala(fi):
            text = md.html_din(pentru_recrutor(fi))
            if (i := text.find("<h3>Ce afli numai la interviu</h3>")) >= 0:  # md coboara titlurile: ## -> h3
                j = text.find("<h3>", i + 4)
                corp.append(text[i:j if j >= 0 else len(text)])
            corp.append(f'<details class="pliat"><summary>Vezi dovezile: fiecare verificare, treptele și cum se citește '
                        f'fișa</summary><div class="card-text">{text}</div></details>')
        else:  # fisa.json dinaintea redarii pentru recrutor, sau cu verificarile vechi pe „la zi”
            corp.append('<div class="cutie avert">Fișa proiectului de portofoliu a fost calculată de o versiune mai veche a programului. Apasă '
                        '<b>Analizează din nou proiectul de portofoliu</b> ca s-o vezi explicată; răspunsurile din interviu rămân.</div>')
        randuri = "".join(f'<tr><td>{md.data(z["ziua"])}</td><td>{z["commituri"]}</td>'
                          f'<td>{z["nivel"] + 1}. {e(NUME_TREPTE[z["nivel"]])}</td><td>{nr(z["total"])}</td>'
                          f'<td>{e("; ".join(lipsa_pentru_recrutor(z["lipseste"]))) or _VARF}</td></tr>'
                          for z in f["drumul"])
        corp.append(f'<details class="pliat"><summary>Drumul, zi cu zi: {len(f["drumul"])} zile de lucru</summary>'
                    '<p class="estompat">Fișa proiectului de portofoliu la ultima salvare de cod din fiecare zi de '
                    'lucru.</p><table class="drumul"><thead><tr><th>Ziua</th><th>Salvări de cod</th><th>Treapta</th>'
                    f'<th>Din 16</th><th>Ce lipsește pentru treapta următoare</th></tr></thead><tbody>{randuri}'
                    '</tbody></table></details>')
        corp.append(_urmator(c, "fisa"))
    else:
        corp.append(_buton("Analizează proiectul de portofoliu", f"/c/{c['id']}/fisa", lung=True,
                           motiv="La un proiect mare durează cam un minut."))
    return pagina("Portofoliul", "\n".join(corp), c, "fisa", eroare)


def _fara_cod(motivul):
    """Hotararea recrutorului, aceeasi la pasul 1 si la rezultat: portofoliul cu 0, etichetat, si plafonul."""
    return (f'<div class="cutie"><strong>Fără proiect cu cod.</strong> Ai hotărât la adăugare, cu motivul: {e(motivul)} '
            f'Portofoliul intră în total cu 0, deci totalul ajunge cel mult la {nr(PLAFON_FARA_COD)} din 100, din interviu '
            'și probă: codul e un plus, nu o cerință. Judeci totalul față de cifra asta. Ce a adus în loc (o conversație '
            'cu AI-ul, instrucțiunile scrise pentru el) citești la interviu, în partea IV, fără notă.</div>')


_VARF = "Nimic: proiectul e pe treapta cea mai înaltă."  # altfel randul gol pare o analiza neterminata


def _eticheta(cheie):
    """Ce spune campul, in cuvintele recrutorului; cheia din ghid (S1, T2, L3) ramane numai in formular."""
    if cheie.startswith(("nota-T", "nota-L")):
        return "Ce a răspuns"
    if m := re.fullmatch(r"L(\d)", cheie):
        return f"Întrebarea ta {m.group(1)}"
    return {"concluzia": "Concluzia ta"}.get(cheie, "Notițe")


def pas_interviu(c, eroare=None, salvat=None):
    stare, motiv = candidati.stari(c)["interviu"]
    if stare == "blocat":
        corp = [_antet(c, "interviu"), f'<p class="motiv">{e(motiv)}</p>']
        return pagina("Interviul", "\n".join(corp), c, "interviu", eroare)
    corp = [f'<form method="post" action="/c/{c["id"]}/interviu" class="interviu" data-autosalvare="1">']
    text, cum, in_cum, parte = [], [], False, False

    def goleste():
        if text:
            corp.append(f'<div class="text-ghid">{md.html_din(chr(10).join(text))}</div>')
            text.clear()

    for b in formular.blocuri(candidati.ghid(c)):
        if b[0] == "text":
            rand = b[1]
            if rand.startswith(f"# Interviul cu {c['nume']} · "):  # pe ecran, numele stă sus și în bară (B24)
                rand = "# Interviul · " + rand.split(" · ", 1)[1]
            if rand == interviu.CUM or (in_cum and not rand.startswith("## ")):
                in_cum = True  # sectiunea „Cum folosesti ghidul” sta in fereastra „Cum folosesc”, nu pe ecran
                if rand.startswith("- **Cum se completează.**"):  # in fisier: [da] / [nu]; aici, butoanele
                    rand = ("- **Cum se completează.** La fiecare rând al întrebărilor 1–7 apeși „da” sau „nu”; nota "
                            "o calculează programul. Dacă n-ai pus o întrebare, lași „nepusă”. O întrebare pe care n-o pui "
                            "nu scade nota: nota interviului e media numai a întrebărilor puse.")
                if rand != interviu.CUM:
                    cum.append(rand)
                continue
            in_cum = False
            if rand == "### Despre proiectul lui":
                goleste()
                corp.append('<a id="proiect"></a>')
            rand = re.sub(r"^## ([1-5])\. ", lambda m: f"## {ROMANE[int(m.group(1))]}. ", rand)  # ghidurile mai vechi
            if rand.startswith("## "):  # fiecare parte se deschide la un clic; intrebarile cu nota si concluzia, deschise
                goleste()
                corp.append(("</details>" if parte else "") + f'<details class="pliat parte-ghid"'
                            f'{" open" if rand.startswith(("## III.", "## V.")) else ""}><summary>{md.inline(rand[3:])}</summary>')
                parte = True
                continue
            text.append(re.sub(r"^### S(\d+)\. ", r"### \1. ", rand))
            continue
        goleste()
        tip, cheie, valoare, eticheta = b
        if tip == "bifa":
            corp.append(_bifa(cheie, valoare, md.inline(eticheta)))
        elif tip in ("nota", "concluzia"):
            corp.append(f'<label class="camp">{e(_eticheta(cheie))}<textarea name="{cheie}" rows="2">{e(valoare)}'
                        '</textarea></label>')
        else:
            corp.append(f'<label class="camp">{e(_eticheta(cheie))}<input name="{cheie}" value="{e(valoare)}"></label>')
    goleste()
    if parte:
        corp.append("</details>")
    stare_salvare = f"Salvat la {salvat}." if salvat else "Se salvează singur, la fiecare bifă și la ieșirea din notițe."
    corp.append(f'<div class="salvare"><button class="buton">Salvează</button><span class="stare-salvare">{e(stare_salvare)}'
                '</span></div></form>')
    corp.append(_decizia(c))
    corp.append(_urmator(c, "interviu"))
    corp.insert(0, _antet(c, "interviu", f'<div class="text-ghid">{md.html_din(chr(10).join(cum))}</div>'))
    return pagina("Interviul", "\n".join(corp), c, "interviu", eroare)


def _decizia(c):
    """Sfarsitul interviului: recrutorul spune daca merge la proba. Formular separat: decizia nu sta in ghid."""
    d = candidati.decizia_probei(c) or {}
    ales = d.get("decizia", "")
    optiuni = "".join(f'<label class="opt"><input type="radio" name="decizia" value="{v}"{" checked" if ales == v else ""}'
                      f'><span>{n}</span></label>' for v, n in (("da", "da"), ("nu", "nu")))
    stare = (f'Hotărât: {"merge la probă" if ales == "da" else "fără probă"}, la {md.data(d["ora"])}. Se salvează '
             'singur, la bifă.' if d else "Încă nehotărât. Se salvează singur, la bifă.")
    return ('<a id="decizia"></a><h2>Decizia: merge la probă?</h2>'
            '<p class="estompat">O iei tu, la sfârșitul interviului. Dacă da, pe ecranul probei găsești invitația pentru '
            'candidat, iar proba începe numai după ce o acceptă. Dacă nu, totalul rămâne fără probă, cu motivul tău.</p>'
            f'<form method="post" action="/c/{c["id"]}/decizia" class="interviu" data-autosalvare="decizie">'
            f'<div class="rand-bifa"><span class="eticheta-bifa">Merge la probă?</span><span class="optiuni">{optiuni}'
            '</span></div><label class="camp">Motivul (obligatoriu la „nu”)'
            f'<textarea name="motivul" rows="2">{e(d.get("motivul", ""))}</textarea></label>'
            # fara buton: se salveaza singura, iar mai departe duce „Pasul următor” (B24); butonul, numai fara JavaScript
            '<div class="salvare"><noscript><button class="buton">Salvează decizia</button></noscript>'
            f'<span class="stare-salvare">{e(stare)}</span></div></form>')


def _proba_inchisa(c, pa, text, de_ce, eroare=None, scris=None):
    """Ecranul probei inainte de acord: trimiterea la decizie, invitatia si raspunsul candidatului, sau motivul. Dupa o
    eroare, formularul pastreaza ce s-a scris (`scris`) si marcheaza campul gresit (B11)."""
    d = candidati.decizia_probei(c)
    r = [_antet(c, "proba", _treptele(proba=True))]
    if d is None:
        return r + [f'<div class="cutie avert">{e(de_ce)}</div><div class="actiune"><a class="buton" '
                    f'href="/c/{c["id"]}/interviu#decizia">Mergi la decizie</a></div>']
    if candidati.fara_proba(c):
        return r + [f'<div class="cutie"><strong>{e(de_ce)}</strong></div><p class="estompat">Totalul se face fără '
                    'probă și spune de ce. Decizia o schimbi la sfârșitul '
                    f'<a href="/c/{c["id"]}/interviu#decizia">interviului</a>.</p>', _urmator(c, "proba")]
    s = scris or {}
    raspuns, data, cum = s.get("raspuns", ""), s.get("data", datetime.now().strftime("%d.%m.%Y")), s.get("cum", "pe e-mail")
    eroare = eroare or ""
    # campul gresit primeste cursorul, iar pagina coboara la el (B8)
    rau = lambda cuvant: ' class="camp-gresit" aria-invalid="true" autofocus' if cuvant in eroare else ""
    alege = lambda v: " checked" if raspuns == v else ""
    return r + [
        '<h2>Invitația la probă</h2>', _alege_meseria(c, pa, text),
        f'<p>I-o trimiți candidatului pe e-mail. Completezi întâi locul marcat {e(proba.FIRMA_COMPLETEAZA)}: cine '
        'prelucrează datele, temeiul, cât le păstrați. Aplicația nu le știe; le știe firma. Tema i-o trimiți numai după '
        'ce acceptă.</p>',
        f'<textarea class="invitatie" id="invitatia" readonly rows="30">{e(proba.invitatie(c["nume"], pa))}</textarea>',
        '<div class="actiune"><button type="button" class="buton secundar" data-copiaza="#invitatia">Copiază invitația'
        '</button><span class="motiv"></span></div>',
        '<h2>Răspunsul candidatului</h2>',
        f'<form method="post" action="/c/{c["id"]}/proba/acord" class="interviu">'
        '<div class="rand-bifa"><span class="eticheta-bifa">Candidatul</span><span class="optiuni">'
        f'<label class="opt"><input type="radio" name="raspuns" value="da"{alege("da")}'
        f'{" autofocus" if "alegi ce a răspuns" in eroare else ""}><span>a acceptat</span></label>'
        f'<label class="opt"><input type="radio" name="raspuns" value="nu"{alege("nu")}><span>a refuzat</span></label>'
        '</span></div>'
        f'<label class="camp">Data răspunsului (ZZ.LL.AAAA)<input name="data" value="{e(data)}" inputmode="numeric" '
        f'autocomplete="off"{rau("data")}></label>'
        f'<label class="camp">Cum a răspuns (de schimbat, dacă a fost altfel)<input name="cum" value="{e(cum)}"'
        f'{rau("cum a răspuns")}></label>'
        '<div class="salvare"><button class="buton">Salvează răspunsul</button>'
        f'<span class="stare-salvare">{e(de_ce)}</span></div></form>']


def _optiuni(cheie, valoare, gol):
    return "".join(f'<label class="opt"><input type="radio" name="{cheie}" value="{v}"'
                   f'{" checked" if valoare == v else ""}><span>{n}</span></label>'
                   for v, n in (("da", "da"), ("nu", "nu"), ("", gol)))


def _bifa(cheie, valoare, eticheta, gol="nepusă"):
    """Un rand de bife: „da”, „nu” si al treilea buton, cu numele lui: „nepusă” la interviu (intrebarea n-a fost pusa),
    „nebifat” la proba."""
    return (f'<div class="rand-bifa"><span class="eticheta-bifa">{eticheta}</span>'
            f'<span class="optiuni">{_optiuni(cheie, valoare, gol)}</span></div>')


def _val(v):
    return "—" if v in (None, "") else nr(v) if isinstance(v, (int, float)) else e(str(v))


def _om(pa, loc):
    return f"{e(pa.locuri[loc])} <span class=\"estompat\">({e(str(loc))})</span>"


def _la_clic(randuri):
    """Ce a scris candidatul pe un angajat: ascuns sub numarul de randuri, ca tabelul sa ramana scurt."""
    if not randuri:
        return "—"
    return (f'<details><summary>{len(randuri)} {"rând" if len(randuri) == 1 else "rânduri"}</summary>'
            f'{"<br>".join(randuri)}</details>')


def _linkuri(text):
    """Linkurile lipite, ca legaturi care se deschid intr-un tab nou; un dosar ramane text. Cautate oriunde in text:
    foaia probei tine un camp pe un rand, deci randurile lipite ajung despartite de spatii."""
    return "".join(f'<li><a href="{e(x)}" target="_blank" rel="noopener noreferrer">{e(x)}</a></li>'
                   for x in _LINK.findall(text or ""))


_LINK = re.compile(r"https?://[^\s<>\"']+")


def _din_cheie(p):
    """Tabelul predat, potrivit cu cheia: fiecare eroare, gasita sau ratata, si semnalarile gresite, pe loc."""
    ch, d, pa = p["cheia"], p["din_cheie"], p["pachet"]
    unde = pa.cuvinte["in_material"]
    lei = f' {e(pa.cuvinte["unitate"])}' if pa.cuvinte.get("unitate") else ""  # unitatea valorilor, a meseriei
    scris = {}
    for marca, coloana, corecta, de_ce in p["semnalate"]:
        scris.setdefault(marca, []).append(f"{e(coloana)}: {_val(corecta)}" + (f" <i>({e(de_ce)})</i>" if de_ce else ""))
    erori = "".join(
        f'<tr><td>{"găsită" if x["cod"] in d["gasite"] else "<b>ratată</b>"}</td><td>{_om(pa, x["loc"])}</td>'
        f'<td>{e(x["ce"])}</td><td>{e(x["coloana"])}: {nr(x["valoare_in_stat"], ",g")}{lei} {unde}, '
        f'{nr(x["valoare_corecta"], ",g")}{lei} corect</td><td>{_la_clic(scris.get(x["loc"], []))}</td></tr>'
        for x in ch["erori"])
    r = [f'<p>Găsite: <b>{len(d["gasite"])} din {ch["erori_de_gasit"]}</b> · semnalări greșite: '
         f'<b>{len(d["gresite"])}</b> · din tabel: <b>{d["fractie"] * 100:.0f}%</b></p>',
         f'<table><thead><tr><th></th><th>{e(pa.cuvinte["locul"])}</th><th>Ce e greșit {unde}</th><th>Valoarea</th>'
         f'<th>Ce a scris candidatul</th></tr></thead><tbody>{erori}</tbody></table>']
    if d["gresite"]:
        pc, cu_eroare = ch["plantata_corecta"], {x["loc"] for x in ch["erori"]}
        motiv = {m: (f"cazul pus intenționat, corect: {pc['ce']}" if m == pc["loc"] else
                     "are o eroare, dar semnalată pe coloane corecte" if m in cu_eroare else "rândul e corect")
                 for m in d["gresite"]}
        r.append('<h3>Semnalări greșite</h3><table><thead><tr><th>' + e(pa.cuvinte["locul"]) + '</th><th>Ce a scris candidatul</th>'
                 '<th>De ce e greșit</th></tr></thead><tbody>' +
                 "".join(f'<tr><td>{_om(pa, m)}</td><td>{_la_clic(scris[m])}</td><td>{e(motiv[m])}</td></tr>'
                         for m in d["gresite"]) + '</tbody></table>')
    return "".join(r)


def _parti_probei(n):
    """Partile probei, pe scurt: pe ecranul probei, la rezultat si in raport."""
    cate = {"cheia": None, "conversațiile": len(proba.TIPAR_CONVERSATII), "discuția": len(proba.TIPAR_DISCUTIE)}
    nume = {"cheia": "Tabelul de răspuns", "conversațiile": "Conversațiile", "discuția": "Discuția"}
    return "".join(f'<div class="cifra"><span>{nume[k]}</span><b>{"—" if x is None else f"{x * 100:.0f}%"}</b><i>'
                   + ("lipsă" if x is None else "din cheie" if cate[k] is None else f"{round(x * cate[k])} „da” din {cate[k]}")
                   + '</i></div>' for k, x in n["parti"].items())


_nume_sursei = candidati.nume_sursei  # numele programului predat, din link sau dosar


def _fisa_probei(c):
    """Fisa programului predat la proba: aceeasi redare ca la portofoliu, ca informatie, fara nota."""
    fp = candidati.fisa_probei(c)
    if not fp:
        return ""
    fi = fp["fisa"]
    corp = ('<h2>Fișa probei</h2><p class="estompat">Ca informație, fără notă: o ai în față la discuție. Pe două ore, '
            'multe verificări nu au sens (licența, verificarea automată pe server), iar cine a lucrat numai în '
            f'conversații nu are program. Programul: {e(cale(fp["sursa"]))}, analizat la {e(fp["calculat"].replace("T", " "))}.</p>')
    if not actuala(fi):
        return corp + ('<div class="cutie avert">Fișa probei a fost calculată de o versiune mai veche a programului. '
                       'Apasă <b>Analizează proiectul probei</b> ca s-o vezi explicată.</div>')
    return corp + (f'<details class="pliat"><summary>Vezi fișa probei</summary><div class="card-text">'
                   f'{md.html_din(pentru_recrutor(fi, proba=True, nume=_nume_sursei(fp["sursa"])))}</div></details>')


def _tabel_predat(c):
    """Numele tabelului predat, la descarcare: cu al cui e, ca sa nu se incurce intre candidati."""
    return f"Raspuns_{c['id']}.xlsx"


def _alege_meseria(c, pa, text):
    """Meseria probei: o alegere numai cand sunt mai multe pachete si proba nu e inceputa; altfel, un rand."""
    toate = proba.pachete()
    rand = f'<p>Proba: <b>{e(pa.meseria)}</b> · {e(pa.titlu)}.</p>'
    if len(toate) < 2:
        return rand
    if proba.inceputa(text, (c["dosar"] / "Raspuns.xlsx").exists()):
        return rand[:-4] + ' <span class="estompat">Proba e începută: meseria nu se mai schimbă.</span></p>'
    optiuni = "".join(f'<option value="{e(x.id)}"{" selected" if x.id == pa.id else ""}>{e(x.meseria)} · {e(x.titlu)}'
                      '</option>' for x in toate)
    return (f'<form method="post" action="/c/{c["id"]}/proba/pachet" class="actiune"><label class="camp">Meseria '
            f'probei<select name="pachet">{optiuni}</select></label><button class="buton secundar">Alege proba</button>'
            '</form>')


def pas_proba(c, eroare=None, salvat=None, scris=None):
    text = candidati.foaie_probei(c)
    v, pa = proba.valori(text), candidati.pachetul_probei(c)
    deschisa, de_ce = candidati.proba_deschisa(c)
    if not deschisa:
        return pagina("Proba", "\n".join(_proba_inchisa(c, pa, text, de_ce, eroare, scris)), c, "proba", eroare)
    try:
        p = candidati.nota_probei(c)
    except ValueError as ex:
        p, eroare = None, eroare or f"Proba nu se poate nota: {ex}."
    a = (candidati.decizia_probei(c) or {}).get("acordul")
    acord = (f'<p class="estompat">Candidatul a acceptat proba pe {e(md.data(a["data"]))} ({e(a["cum"])}).</p>' if a else
             f'<p class="estompat">{e(de_ce[0].upper() + de_ce[1:])}.</p>')
    corp = [_antet(c, "proba", _treptele(proba=True)), acord, '<h2>Tema</h2>', _alege_meseria(c, pa, text),
            '<p>Aceeași pentru toți cei care dau proba pe această meserie: i le trimiți candidatului pe e-mail. Nu-i spui '
            f'câte greșeli are {e(pa.cuvinte["materialul"])}.</p><div class="actiune">' +
            "".join(f'<a class="buton secundar lat" href="/proba/{quote(pa.id)}/{quote(f)}" download>'
                    f'{e(n[0].upper() + n[1:])}</a>' for n, f in pa.tema) + '</div>', '<h2>Tabelul de răspuns predat</h2>',
            # selectorul de fisier al browserului vorbeste limba browserului: in locul lui, un buton al paginii
            f'<form method="post" action="/c/{c["id"]}/proba/raspuns" enctype="multipart/form-data" class="actiune">'
            '<label class="buton secundar lat alege-fisier"><input type="file" name="fisier" accept=".xlsx" required>'
            'Alege fișierul</label><button class="buton lat">Încarcă tabelul de răspuns</button>'
            '<span class="nume-fisier estompat">niciun fișier ales</span></form>']
    if p and p["din_cheie"]:
        corp.append(f'<div class="actiune"><a class="buton secundar lat" href="/c/{c["id"]}/proba/{_tabel_predat(c)}" '
                    'download>Descarcă tabelul predat</a></div>')
        corp.append(_din_cheie(p))
    if p and p["eroare"]:
        corp.append(f'<div class="cutie avert">{e(p["eroare"][0].upper() + p["eroare"][1:])}. Nota probei se face '
                    'când fiecare parte e bifată întreagă sau lăsată toată „nebifat”.</div>')
    elif p:
        n = p["nota"]
        corp.append(f'<div class="cifre">{_parti_probei(n)}<div class="cifra"><span>Proba</span><b>'
                    f'{f"{n["nota"] * 100:.0f}%" if n["complet"] else "—"}</b><i>'
                    f'{"media celor trei părți, necalibrat" if n["complet"] else "incompletă"}</i></div></div>')
    # doua casete, date amandoua daca vrea candidatul: cum a gandit (conversatiile) si ce a facut (programul)
    corp += [f'<h2>Ce a mai predat</h2><p class="estompat">Le trimite candidatul odată cu tabelul, una sau amândouă. '
             'Programul le păstrează la dosar: programul nu le deschide și nu le citește; le deschizi tu.</p>'
             '<div class="predate">'
             f'<form method="post" action="/c/{c["id"]}/proba" class="caseta-predata" data-autosalvare="1">'
             '<h3>Cum a gândit: conversațiile cu AI-ul</h3><label class="camp">Linkurile de partajare (butonul „Share” / '
             f'„Partajează” din Claude sau ChatGPT), câte unul pe rând<textarea name="linkuri" rows="3">{e(v["linkuri"])}'
             f'</textarea></label><ul class="linkuri">{_linkuri(v["linkuri"])}</ul>'
             '<span class="stare-salvare estompat"></span></form>'
             f'<form method="post" action="/c/{c["id"]}/proba/fisa" class="caseta-predata" data-lung="1">'
             '<h3>Ce a făcut: programul</h3><label class="camp">Linkul sau dosarul codului'
             f'<input name="cod" value="{e(v["cod"])}"></label><ul class="linkuri">{_linkuri(v["cod"])}</ul>'
             '<div class="actiune alege-proiect"><button type="button" class="buton secundar" data-alege="dosar">'
             'Alege dosarul…</button><span class="motiv">Se deschide fereastra Windows; calea ajunge singură în câmp.'
             '</span></div>'
             '<div class="actiune"><button class="buton secundar">Analizează proiectul probei</button>'
             '<span class="motiv">Fișa probei, fără notă.</span></div></form></div>']
    f = [f'<form method="post" action="/c/{c["id"]}/proba" class="interviu" data-autosalvare="1">',
         '<h2>Conversațiile</h2>']
    f += [_bifa(f"C{i}", v[f"C{i}"], e(b), "nebifat") for i, b in enumerate(pa.conversatii, 1)]
    f.append(f'<label class="camp">Notițe<textarea name="nota-C" rows="2">{e(v["nota-C"])}</textarea></label>')
    f.append(_fisa_probei(c))
    f.append('<h2>Discuția de după predare</h2><p class="estompat">Aceleași trei întrebări pentru toți.</p>')
    for i, (intrebare, bifa) in enumerate(pa.discutie, 1):
        f += [f'<h3>{i}. {e(intrebare)}</h3>', _bifa(f"D{i}", v[f"D{i}"], f"<b>Da, dacă:</b> {e(bifa)}", "nebifat"),
              f'<label class="camp">Ce a răspuns<textarea name="nota-D{i}" rows="2">{e(v[f"nota-D{i}"])}</textarea>'
              '</label>']
    stare_salvare = f"Salvat la {salvat}." if salvat else "Se salvează singur, la fiecare bifă și la ieșirea din notițe."
    f.append(f'<div class="salvare"><button class="buton">Salvează</button><span class="stare-salvare">'
             f'{e(stare_salvare)}</span></div></form>')
    corp += f + [_urmator(c, "proba")]
    return pagina("Proba", "\n".join(corp), c, "proba", eroare)


def _eroare_probei(text):
    return (f"Proba are o parte bifată pe jumătate ({text.removeprefix('proba: ')}). Bifezi toată partea sau o lași "
            "toată „nebifat”, apoi revii aici.") if "pe jumătate" in text else f"Proba nu se poate nota: {text.removeprefix('proba: ')}."


def _finalizare(c):
    """Finalizarea e decizia recrutorului, nu a programului: un total complet nu inseamna ca a terminat cu omul. Cele
    doua butoane stau unul langa altul, de aceeasi latime; ce face fiecare, sub ele (observatia autorului)."""
    gata = c["stare"] == "finalizate"
    eticheta, actiune, ce_face = (
        ("Redeschide", "redeschide", "„Redeschide” o întoarce în „În analiză”, cu tot ce are.") if gata else
        ("Finalizează candidatura", "finalizeaza", "„Finalizează candidatura”: când ai terminat cu omul. Dosarul trece "
         "în „Finalizate”; îl poți redeschide oricând."))
    return ('<h2>Candidatura</h2>' + ('<p>Finalizată: dosarul e în „Finalizate”.</p>' if gata else "") +
            f'<div class="actiune pereche"><form method="post" action="/c/{c["id"]}/{actiune}">'
            f'<button class="buton secundar lat">{e(eticheta)}</button></form>'
            f'<a class="buton secundar lat" href="/c/{c["id"]}/sterge">Șterge candidatul</a></div>'
            f'<ul class="motiv ce-face"><li>{e(ce_face)}</li><li>„Șterge candidatul”: când datele lui nu mai sunt de folos. '
            'Îi șterge definitiv tot dosarul de pe discul acestui calculator, fără Coșul de reciclare; ștergerea nu se '
            'poate reface.</li></ul>')


def pas_sterge(c, eroare=None):
    """Confirmarea stergerii: ce dispare, ce ramane in afara aplicatiei, numele scris din nou."""
    manual = '<p class="la-manual"><a href="/manual#stergerea">În manual: ștergerea unui candidat →</a></p>'
    corp = [f'<div class="rand-titlu"><h1>Ștergi candidatul „{e(c["nume"])}”</h1>{_ajutor("sterge", manual)}</div>',
            '<p>Ștergi definitiv, de pe discul acestui calculator, tot ce are aplicația despre el: proiectul descărcat, fișa, '
            'interviul cu notițele, proba cu tabelul predat, jurnalul. Rapoartele lui nu se mai pot scoate, iar '
            'ștergerea nu se poate reface.</p>',
            '<p>Rămâne ce stă în afara aplicației: rapoartele salvate de tine ca PDF, fișierele primite de la candidat, '
            'acolo unde le-ai pus (de pildă dosarul proiectului, dacă l-ai dat de pe calculator), și copiile de siguranță '
            'ale calculatorului.</p>',
            f'<form method="post" action="/c/{c["id"]}/sterge" class="formular">'
            f'<label class="camp">Ca să confirmi, scrii numele candidatului: {e(c["nume"])}'
            '<input type="text" name="nume" autocomplete="off" required></label>'
            '<button class="buton">Șterge definitiv</button></form>',
            f'<div class="actiune"><a class="buton secundar" href="/c/{c["id"]}/rezultat">← Înapoi la rezultat</a></div>']
    return pagina("Ștergerea", "".join(corp), c, "rezultat", eroare)


MESAJ_CANDIDATURA = {"finalizat": "Candidatura e finalizată: dosarul e în „Finalizate”. O redeschizi oricând, jos, la "
                                   "„Candidatura”.",
                     "redeschis": "Candidatura e redeschisă: dosarul e din nou în „În analiză”."}


def pas_rezultat(c, eroare=None, mesaj=None):
    corp = [_antet(c, "rezultat")]
    if mesaj in MESAJ_CANDIDATURA:
        corp.append(f'<div class="cutie">{e(MESAJ_CANDIDATURA[mesaj])}</div>')
    stare, motiv = candidati.stari(c)["rezultat"]
    if stare == "blocat":
        corp.append(f'<p class="motiv">{e(motiv)}</p>')
        return pagina("Rezultatul", "\n".join(corp + [_finalizare(c)]), c, "rezultat", eroare)
    try:  # calculat acum, din interviul de acum: fara buton de recalculat
        s = candidati.rezultat(c)
    except ValueError as ex:
        s, eroare = None, (_eroare_probei(str(ex)) if str(ex).startswith("proba: ") else
                           f"Interviul are o întrebare bifată pe jumătate: {ex}. Completezi toate trei rândurile "
                           "sau le lași pe toate „nepusă”, apoi revii aici.")
    if s:
        # raportul lui, direct de aici: cine lucreaza cu un candidat il ia fara filtre; „Rapoarte” ramane in plus, nu
        # in loc (decizia autorului, 19 octombrie, peste cea din 15 octombrie)
        corp.append(f'<div class="actiune"><a class="buton" href="/c/{c["id"]}/raport">Raportul pentru dosar</a>'
                    f'<a class="buton secundar" href="/rapoarte?id={quote(c["id"])}">Alte rapoarte</a>'
                    '<span class="motiv">Pe scurt, auditul sau mai mulți candidați deodată: în „Rapoarte”.</span></div>')
        t = s["total"]
        parti = "".join(f'<div class="parte"><span>{e(n)}</span><div class="bara-progres"><i style="width:'
                        f'{(p or 0) / (100 / 3) * 100:.0f}%"></i></div><b>{"lipsă" if p is None else f"{nr(p)} din 33,3"}'
                        f'{", fără proiect cu cod" if n == "portofoliul" and t["fara_cod"] else ""}</b></div>'
                        for n, p in t["puncte"].items())
        fara = candidati.fara_proba(c)
        incomplet = ('' if t["complet"] else
                     '<div class="cutie avert"><strong>Totalul e incomplet: fără probă.</strong></div>'
                     if fara and t["lipsa"] == ["proba"] else
                     f'<div class="cutie avert"><strong>Incomplet.</strong> Lipsește: {e(", ".join(t["lipsa"]))}. '
                     'Totalul adună numai părțile făcute' + ('; de ce, la „Proba”, mai jos.' if fara else '.') + '</div>')
        m = s["medie"]
        concluzia = formular.valori(candidati.ghid(c)).get("concluzia", "")
        note = "".join(f'<tr><td>{q[0][1:]}</td><td>{e(q[2])}</td><td>{s["standard"][q[0]] or "nepusă"}</td></tr>'
                       for q in INTREBARI)
        corp.append(f'<div class="cifre"><div class="cifra"><span>Totalul</span><b>{nr(t["total"])}</b><i>din 100, '
                    f'necalibrat{"" if t["complet"] else ", incomplet: lipsește " + e(", ".join(t["lipsa"]))}'
                    f'{f"; fără proiect cu cod: cel mult {nr(t["plafon"])}" if t["fara_cod"] else ""}</i></div><div class="cifra"><span>Interviul, media</span><b>'
                    f'{"—" if m["medie"] is None else nr(m["medie"])}</b><i>din 4 · {_media_puse(m)}</i></div><div class="cifra"><span>Treapta din portofoliu</span><b class="treapta">'
                    f'{nerupt((s["nivel_fisa"] or "—").removesuffix(" (provizoriu)"))}</b><i>'
                    f'{"fără proiect cu cod" if t["fara_cod"] else "provizoriu"}</i></div></div>')
        if (f := candidati.fisa(c)) and not t["fara_cod"]:
            corp.append(_ce_e_treapta(f["fisa"]["nivel"]))
        if t["fara_cod"]:
            corp.append(_fara_cod(candidati.fara_cod(c) or "scris în ghid."))
        corp.append(f'{incomplet}<h2>Totalul pe treimi</h2><div class="parti">{parti}</div>')
        corp.append('<h2>Notele, pe întrebare</h2><table class="note"><thead><tr><th></th><th>Aria</th><th>Nota (1–4)</th></tr>'
                    f'</thead><tbody>{note}</tbody></table>')
        if fara:
            corp.append(f'<h2>Proba</h2><p>{e(_faptul_fara_proba(c))}</p>')
        else:
            corp.append(f'<h2>Proba, pe părți</h2><div class="cifre">{_parti_probei(s["proba"]["nota"])}</div>'
                        f'<p class="estompat">Ce a găsit în tabel, pe fiecare greșeală, și notițele stau în '
                        f'<a href="/c/{c["id"]}/proba">pasul 3</a>.</p>')
        corp.append('<p class="estompat">Întrebările fără notă (despre proiect și ale tale), cu ce a răspuns '
                    f'candidatul, stau în <a href="/c/{c["id"]}/interviu#proiect">interviu, partea IV</a> și în '
                    'raportul pentru dosar.</p>')
        corp.append(f'<h2>Concluzia ta</h2><p>{e(concluzia) or "<i>Încă nescrisă: o scrii la sfârșitul interviului.</i>"}</p>')
        corp.append(f'<p class="nota-mica">{e(NOTA_INTERVIU)}</p>')
    # „pasul urmator” la sfarsit, ca pe celelalte ecrane
    return pagina("Rezultatul", "\n".join(corp + [_finalizare(c), _urmator(c, "rezultat")]), c, "rezultat", eroare)


# ── Capitolul de exemple din manual ───────────────────────────────────────────

# tipul: (ce arata, profilul in doua randuri, ce citesti). Textul n-are cifre: le pune `capitol_exemple`, din
# exemple-candidati/rezultate.json, scris de `set-exemple` (tests/test_set_exemple.py)
EXEMPLE = {
    1: ("autorul, autoevaluare",
        "Autorul programului, specialist în resurse umane și salarizare, nu programator. Proiectul de portofoliu e cel "
        "mai matur al lui, Metoda: felul lui de lucru cu AI-ul, scris ca reguli; interviul și proba le-a completat singur.",
        "Cele trei părți spun același lucru: proiectul, răspunsurile și proba. E cazul în care totalul se citește aproape "
        "singur; fiind o autoevaluare, nu e judecata unui recrutor."),
    2: ("lucrează în conversații, fără cod",
        "Lucrează cu AI-ul numai în conversații (chat), pentru texte și analize de resurse umane; nu scrie cod. "
        "Recrutorul a bifat „Candidatul nu are proiect cu cod”, cu motivul.",
        "Portofoliul intră cu zero, etichetat, nu ca lipsă: totalul e complet și ajunge cel mult la {plafon} din "
        "{maxim}. Ce a adus în locul proiectului stă în partea IV a interviului, fără notă. Pe ea o compari cu ceilalți "
        "pe interviu și pe probă, nu pe total."),
    3: ("cod, dar la probă numai conversații",
        "Scrie cod cu AI-ul: proiectul lui, un calculator de concedii, are instrucțiuni pentru AI și câteva verificări "
        "automate. La probă a predat numai conversațiile cu AI-ul, fără program.",
        "Proiectul și interviul sunt bune; proba e partea care arată dacă verifică ce îi dă AI-ul. Întrebările despre "
        "proiect din partea IV, alese de program din ce lipsește în fișă, arată dacă știe ce-i lipsește proiectului."),
    4: ("fișă slabă, probă bună",
        "Folosește AI-ul des, dar prin cereri scrise de la caz la caz (prompturi), fără reguli pregătite pentru el: "
        "proiectul ei stă pe prima treaptă.",
        "Proiectul spune puțin, dar proba și interviul arată că lucrează bine cu AI-ul, chiar dacă nu-l organizează. "
        "Un portofoliu slab nu înseamnă un om slab: proba e partea care o arată."),
    5: ("fișă bună, nu-și explică proiectul",
        "Absolvent de informatică, cu un an de stagiu. Proiectul lui are tot ce caută fișa, dar a apărut întreg într-o "
        "singură zi, de la prima salvare din istoric: poate să nu fie al lui.",
        "Iese cu {total5} din {maxim}, peste Ioana Vlădescu ({total4}). Motivul: fișa n-a găsit nimic lipsă, deci "
        "programul nu pune întrebări despre proiect; le pune recrutorul, în partea IV, iar partea IV n-are notă. La "
        "întrebările cu notă a răspuns bine. Numai proba ({proba5} din {parte}) și răspunsurile lui la întrebările "
        "recrutorului („Ale tale”) îl deosebesc. De aceea totalul nu se citește singur: citești întâi părțile, apoi "
        "partea IV."),
    6: ("fără probă",
        "Scrie cod cu AI-ul, cu verificări automate și reguli pentru AI ținute la zi; la interviu răspunde mediu. A "
        "refuzat proba: nu face probe practice neplătite.",
        "Totalul e „incomplet”: proba lipsește și nu se înlocuiește cu nicio cifră, deci {total6} nu se compară cu "
        "totalurile celorlalți. Refuzul e consemnat, cu data și motivul; ce înseamnă pentru angajare hotărăști tu."),
}


def _nr(x):
    return f"{x:g}".replace(".", ",")


def _parti_exemplu(c, d):
    """Cele trei parti si totalul unui candidat din exemple, cu cifrele din rezultate.json."""
    pu, pr = c["puncte"], c["proba"]
    port = (f'treapta {c["treapta"]}, {e(c["treapta_nume"])}: {_nr(c["fisa"])} din {_nr(c["fisa_maxim"])} verificări'
            if c["treapta"] else "fără proiect cu cod, hotărârea recrutorului")
    proba_ = ("lipsă: a refuzat-o" if pu["proba"] is None else
              f'tabelul de răspuns {pr["cheia"]}%, conversațiile {pr["conversațiile"]}%, discuția {pr["discuția"]}%')
    total_ = (f'{_nr(c["total"])} din {_nr(d["maxim"])}' + ("" if c["treapta"] else
              f', din cel mult {_nr(d["plafon_fara_cod"])}') + ("" if c["complet"] else ", incomplet"))
    parte = lambda p: "" if p is None else f' → {_nr(p)} din {_nr(d["parte"])}'
    return (f'<ul><li><b>Portofoliul:</b> {port}{parte(pu["portofoliul"])}</li>'
            f'<li><b>Interviul:</b> media {_nr(c["interviul"])} din {_nr(d["interviul_maxim"])}{parte(pu["interviul"])}</li>'
            f'<li><b>Proba:</b> {proba_}{parte(pu["proba"])}</li><li><b>Totalul:</b> {total_}</li></ul>')


def capitol_exemple(cale=None):
    """Capitolul „Exemple: cum se citește rezultatul”; cifrele, din exemple-candidati/rezultate.json."""
    d = json.loads((cale or set_exemple.REZULTATE).read_text(encoding="utf-8"))
    v = {"parte": _nr(d["parte"]), "maxim": _nr(d["maxim"]), "plafon": _nr(d["plafon_fara_cod"])}
    for c in d["candidati"]:
        v[f'total{c["tip"]}'] = _nr(c["total"])
        v[f'proba{c["tip"]}'] = "—" if c["puncte"]["proba"] is None else _nr(c["puncte"]["proba"])
    lipsa = lambda p: "lipsă" if p is None else _nr(p)
    tabel = "".join(f'<tr><td>{c["tip"]}. {e(c["nume"])}</td><td>{lipsa(c["puncte"]["portofoliul"])}</td>'
                    f'<td>{lipsa(c["puncte"]["interviul"])}</td><td>{lipsa(c["puncte"]["proba"])}</td>'
                    f'<td>{_nr(c["total"])}{"" if c["complet"] else ", incomplet"}</td></tr>' for c in d["candidati"])
    tipuri = "".join(f'<h3>{c["tip"]}. {e(c["nume"])}: {EXEMPLE[c["tip"]][0]}</h3><p>{EXEMPLE[c["tip"]][1]}</p>'
                     + _parti_exemplu(c, d) + f'<p><b>Ce citești:</b> {EXEMPLE[c["tip"]][2].format(**v)}</p>'
                     for c in d["candidati"])
    return (f'<h2 id="exemple">Exemple: cum se citește rezultatul</h2><p class="nota-mica">Cei cinci candidați de după autor sunt '
            'persoane inventate: numele, proiectele și răspunsurile le-a scris asistentul AI care a construit programul; '
            'orice potrivire cu o persoană reală e întâmplătoare. Bifele la interviu și la probă le-a dat tot asistentul, '
            'la cererea autorului (interviul Elenei Dobrescu l-a bifat autorul; pe al lui, tot el). De aceea exemplele '
            'arată cum se citește rezultatul, nu judecata unui recrutor și nici o unealtă calibrată. Cifrele le calculează '
            'programul, ca pentru orice candidat.</p>'
            '<div class="actiune"><a class="buton" href="/exemple">Vezi exemplele în aplicație</a>'
            '<span class="motiv">Aceiași candidați, cu toți pașii și rapoartele lor, numai de citit („Exemple”, în bara '
            'din stânga).</span></div>'
            f'<p>Totalul are trei părți egale, de câte cel mult {v["parte"]} puncte: portofoliul, interviul și proba. '
            'Mai jos, șase candidați, fiecare de alt fel, cu ce arată cifrele lor.</p>'
            '<table class="r-tabel"><tr><th>Candidatul</th><th>Portofoliul</th><th>Interviul</th><th>Proba</th>'
            f'<th>Totalul</th></tr>{tabel}</table>{tipuri}')


MANUAL = """<h1>Manualul</h1>
<p>HarnessCraft ajută un recrutor să vadă cum lucrează un om cu AI-ul. Pornește de la un proiect al lui, cu
istoricul proiectului (git), și ajunge la un interviu structurat. E un prototip: cifrele lui arată cum funcționează unealta, înainte
de calibrarea pe candidați reali.</p>
<h2>Cum e făcut și ce reguli respectă</h2>
<p><b>Construit cu AI, de un om din resurse umane.</b> Autorul, specialist în resurse umane și salarizare, nu programator,
a scris programul împreună cu un asistent AI care scrie cod (Claude Code), după metoda lui de lucru: fiecare regulă e
scrisă înainte, verificată de teste automate care rulează la fiecare schimbare, iar fiecare schimbare
rămâne în istoricul proiectului. E chiar felul de lucru pe care programul îl caută la candidați.</p>
<p><b>Programul nu folosește AI.</b> Nicio treaptă, notă sau întrebare nu vine de la un model AI: le calculează programul,
din reguli scrise de oameni, aceleași pentru toți candidații, și oricine le poate verifica.</p>
<ul><li><b>Regulamentul european privind inteligența artificială</b> (AI Act, Regulamentul UE 2024/1689). Recrutarea și
evaluarea candidaților cu un sistem de inteligență artificială sunt „cu risc ridicat” (anexa III, punctul 4), cu obligații
de la 2 decembrie 2027 (Regulamentul UE 2026/1744). Definiția „sistemului de inteligență artificială” nu cuprinde însă
sistemele care se bazează pe reguli definite exclusiv de oameni (considerentul 12): așa e HarnessCraft.</li>
<li><b>Regulamentul general privind protecția datelor</b> (GDPR, Regulamentul UE 2016/679), articolul 22: un om are
dreptul să nu fie supus unei decizii „bazate exclusiv pe prelucrarea automată”. Programul nu ia decizii: dă cifre și un
raport, iar decizia de angajare o iau oamenii care îl citesc.</li>
<li><b>Datele rămân la tine.</b> Totul stă pe acest calculator; programul nu trimite nimic în afară. Firma care îl
folosește răspunde de datele candidaților.</li>
<li><b>Aceleași întrebări și aceeași probă pentru toți</b>, ca notele să se poată compara între candidați.</li></ul>
<p class="nota-mica">Citite în textul oficial, pe EUR-Lex, în octombrie 2026. Încadrarea e o părere, nu un aviz juridic.</p>
<h2>Pornirea și oprirea</h2>
<ul><li>Dublu-clic pe <code>Porneste_HarnessCraft.bat</code>, în dosarul programului. Se deschide browserul, cu programul;
fereastra de comandă Windows a programului (fundal negru, cu textul „HarnessCraft rulează la…”) stă micșorată, în
bara de jos.</li>
<li>Fereastra de comandă e programul însuși: o lași deschisă cât lucrezi. Când o închizi,
programul se oprește; îl pornești din nou cu același dublu-clic. O pornire nouă închide singură ce a rămas de
la cele vechi: programul, fereastra lui de comandă și taburile lui din browser.</li>
<li>Când programul nu poate porni (lipsește programul care citește istoricul proiectelor (git) sau cel care caută cheile de acces (gitleaks), sau locul lui de lucru e ocupat de alt program), o casetă pe ecran
spune de ce.</li>
<li>Programul merge numai pe acest calculator: nimic din dosarul candidatului nu pleacă în afară.</li></ul>
<h2>Ecranele și butoanele</h2>
<h3>Acasă</h3><p>Ecranul de început: ce face programul, cei patru pași, butonul <b>Candidat nou</b> și toți candidații în lucru (propuși și în analiză), oricâți ar fi. Un clic pe candidat te duce la pasul lui. <b>Vezi exemplele</b> deschide „Exemple”, din bara din stânga: candidații din capitolul de exemple, cu toți pașii și rapoartele lor, numai de citit.</p>
<h3>Istoricul candidaților</h3><p>Toți oamenii evaluați și pasul la care a ajuns fiecare, pe trei grupuri: <b>Propuse</b>
(abia adăugat), <b>În analiză</b> (de la prima analiză sau de la tabelul predat), <b>Finalizate</b> (după ce apeși
„Finalizează candidatura” la Rezultat; „Redeschide” îl întoarce). Căutarea găsește un om după nume sau proiect, în toate
trei. Un clic pe candidat te duce la pasul lui.</p>
<h3>Candidat nou</h3><p>Întâi ceri candidatului proiectul de portofoliu, unul pe care l-a făcut deja: de obicei un link GitHub, din CV sau trimis pe e-mail. Scrii
numele și lipești linkul în câmpul <b>Proiectul de portofoliu</b>, sau alegi un dosar de pe acest calculator cu
<b>Alege dosarul…</b>. <b>Adaugă</b> descarcă
proiectul și verifică dacă are istoricul proiectului (git): istoricul arată cum a lucrat omul, pas cu pas. Un proiect privat vine ca un
singur fișier cu tot istoricul, pe care candidatul îl face în dosarul lui (comanda:
<code>git bundle create proiect.bundle --all</code>): îl salvezi pe acest calculator și îl alegi cu <b>Alege fișierul
.bundle…</b>. O arhivă obișnuită
pierde uneori istoricul, iar fără el programul nu poate citi proiectul. Bifa <b>Autoevaluare,
demonstrativ</b> înseamnă că omul se evaluează singur, ca demonstrație.</p>
<p><b>Candidatul fără proiect cu cod.</b> Mulți oameni lucrează cu AI-ul numai în conversație și n-au un proiect cu cod.
Atunci lași câmpul proiectului gol, bifezi <b>Candidatul nu are proiect cu cod</b> și scrii motivul. Hotărârea e a ta și
intră în audit. Portofoliul intră în total cu 0, etichetat „fără proiect cu cod”, nu „lipsă”: totalul e complet, pe
aceeași scară ca la ceilalți, și ajunge cel mult la 66,7 din 100, din interviu și probă. Codul e un plus, nu o cerință:
judeci totalul față de cifra asta, după ce cere rolul. Ce aduce omul în loc (o conversație cu AI-ul, instrucțiunile scrise
pentru el) citești la interviu, în partea IV, fără notă. Dacă aduce totuși un proiect, îl adaugi ca un candidat nou.</p>
<h3>1. Portofoliul</h3><p><b>Analizează proiectul de portofoliu</b> citește istoricul și calculează treapta provizorie (prompter,
configurator, constructor de sistem, metodolog), cu explicația ei sub cifră, punctajul proiectului din 16, dovezile și drumul zi cu zi. Le calculează
programul, din reguli scrise de oameni. <b>Analizează din nou proiectul de portofoliu</b> reface fișa proiectului de portofoliu; răspunsurile din interviu rămân. La un candidat fără proiect cu cod,
pasul e încheiat de la adăugare: ecranul arată hotărârea și motivul.</p>
<h3>2. Interviul</h3><p>Pagina interviului se pregătește singură după fișa proiectului de portofoliu. O ții deschisă cât vorbești cu candidatul.
Are cinci părți, cu cifre romane: I. Deschiderea, II. Parcursul, III. Întrebările cu notă, IV. Întrebările fără notă,
V. Încheierea.</p>
<ul><li><b>Partea III, întrebările 1–7</b>, sunt aceleași pentru toți candidații și au notă. La fiecare: asculți,
apoi alegi <b>da</b> sau <b>nu</b> pe fiecare din cele trei rânduri; <b>nepusă</b>, dacă n-ai pus întrebarea. Nota
interviului e media întrebărilor puse, deci alegi tu pe care le pui, de pildă când timpul e scurt.</li>
<li><b>Partea IV, întrebările fără notă</b>, te ajută să vezi dacă proiectul e al candidatului: cine și-a construit
singur proiectul își explică ușor alegerile, spre deosebire de cineva care l-a copiat de pe GitHub. Două întrebări le
alege programul din ce lipsește în fișa proiectului de portofoliu, fiecare cu ce afli din răspuns; până la trei
le scrii tu. Notezi ce răspunde: îți sprijină impresia și
recomandarea din concluzie. Nota rămâne la cele 7 întrebări din partea III, aceleași pentru toți, ca să se poată
compara candidații; într-o evaluare a candidaților nota o
calculează programul, din reguli scrise de oameni (AI Act, anexa III, punctul 4).</li>
<li>Totul se salvează singur, la fiecare bifă și la ieșirea din notițe; <b>Salvează</b> salvează pe loc și îți arată
ora. Poți reveni oricând, chiar a doua zi, să schimbi o bifă sau o notiță.</li>
<li><b>Decizia: merge la probă?</b> La sfârșitul paginii hotărăști tu, nu programul: <b>da</b> sau <b>nu</b>, cu motivul
(obligatoriu la „nu”). Interviul e gata numai cu decizia luată. La „nu”, totalul rămâne fără probă și spune de ce. O
poți schimba până începe proba; fiecare schimbare intră în audit.</li></ul>
<h3>3. Proba</h3><p>Proba practică e aceeași pentru toți cei de pe aceeași meserie; la salarizare, un stat de plată
fictiv, cu greșeli puse intenționat, de verificat cu AI-ul, cum lucrează omul de obicei. Munca e gândită pentru cel mult două ore; o predă în trei zile.</p>
<ul><li><b>Invitația și acordul:</b> proba se deschide numai după ce candidatul acceptă. Ecranul îți dă invitația:
ce face, cât durează, ce predă, cum se evaluează și ce se întâmplă cu ce predă. Locul marcat „[Firma completează]” îl
completezi tu: cine prelucrează datele, temeiul, cât le păstrați, drepturile lui. Aplicația nu le știe. Acordul lui e
acordul de a da proba, nu temeiul prelucrării datelor: acela îl alege firma (interesul legitim sau pașii dinaintea unui
contract), pentru că un viitor angajat nu poate refuza cu adevărat liber (EDPB, ghidul 05/2020, paragraful 21). Salvezi
ce a răspuns, data și cum (pe e-mail, la telefon). Dacă refuză, totalul rămâne fără probă și spune de ce.</li>
<li><b>Tema:</b> descarci statul, tabelul de răspuns gol și mesajul pentru candidat și i le trimiți candidatului. Nu-i spui
câte greșeli are statul.</li>
<li><b>Tabelul de răspuns predat:</b> îl încarci cu <b>Încarcă tabelul de răspuns</b>. Programul îl potrivește cu
răspunsurile corecte (cheia), pe angajat: o greșeală e găsită dacă omul a scris angajatul ei pe o coloană în care se
vede. Arată și ce a semnalat greșit, inclusiv cazul pus intenționat, care pare greșit, dar e corect. Un tabel încărcat
din nou îl înlocuiește pe cel vechi; cel vechi rămâne în dosarul candidatului.</li>
<li><b>Conversațiile:</b> citești conversațiile cu AI-ul predate și bifezi cele patru rânduri.</li>
<li><b>Fișa probei:</b> dacă a lucrat și cu un program, scrii linkul sau dosarul lui și apeși <b>Analizează proiectul
probei</b>. Fișa se face cu același cod ca la portofoliu, ca informație, fără notă: pe două ore, multe verificări nu au
sens. O ai în față la discuție.</li>
<li><b>Discuția de după predare:</b> pui cele trei întrebări, aceleași pentru toți, și bifezi.</li></ul>
<p>Nota probei e media celor trei părți: din tabel (greșeli găsite minus semnalări greșite, împărțit la numărul
greșelilor, cel puțin 0), din conversații și din discuție. O parte lipsă face proba „incompletă”.</p>
<p><b>Proba pe altă meserie.</b> Tema și răspunsurile corecte (cheia) țin de meserie; bifele și întrebările măsoară
același lucru la oricine: dacă i-a dat AI-ului materialul și regulile, dacă a cerut sursa, dacă l-a contrazis cu motiv,
dacă și-a făcut o unealtă, unde a greșit AI-ul, cum a aflat regula schimbată de curând, ce a lăsat neverificat. Fiecare
meserie are pachetul ei: materialul de verificat, regulile, cinci feluri de greșeli puse intenționat (o cifră greșită, o
limită depășită, o rotunjire, un caz care pare greșit, dar e corect, și o regulă schimbată de curând, pe care AI-ul o
știe în forma veche), cheia și cuvintele meseriei pentru bife și pentru a doua întrebare. Primul pachet e salarizarea.
Un pachet nou îl face cineva care știe meseria și verifică cheia rând cu rând; dosarul lui stă lângă cel al salarizării,
în <code>proba</code>. Când sunt mai multe, alegi meseria la „Meseria probei”, înainte să încarci tabelul sau să bifezi:
după aceea nu se mai schimbă. Notele probei se compară numai între candidații de pe aceeași meserie.</p>
<h3>4. Rezultatul</h3><p>Se calculează singur, de fiecare dată când deschizi pagina, din ce e bifat atunci în interviu și în probă:
nota la fiecare întrebare 1–7 (1 + numărul de „da”), media și totalul pe treimi (portofoliul, interviul, proba). Ai schimbat
o bifă? Rezultatul o arată deja. O parte lipsă face totalul „incomplet”, cu partea numită. Fără proiect cu cod,
portofoliul are 0, cu eticheta lui, iar totalul ajunge cel mult la 66,7 din 100. O întrebare se bifează
întreagă (toate trei rândurile) sau deloc; una bifată pe jumătate e semnalată aici. Sub note stă concluzia ta.</p>
<h3>Raportul pentru dosar</h3><p><b>Raportul pentru dosar</b>, de pe pagina rezultatului (sau din <b>Rapoarte</b>), e o
pagină
făcută pentru tipărit: candidatul, proiectul, data, un loc pentru numele evaluatorului, rezultatul, cele 7 întrebări cu
nota și notițele, discuția fără notă, concluzia, fișa proiectului de portofoliu pe scurt și cum se citește raportul. Din browser o tipărești sau o
salvezi ca PDF („Tipărește” → „Salvează ca PDF”) și o pui la dosarul candidatului, pentru cine decide. Bara din stânga
rămâne pe ecran, ca să mergi oriunde în program; pe hârtie nu apare. <b>Raportul pe scurt</b> încape
în cel mult două pagini: rezultatul, notele pe arie, proba, concluzia și fișa pe scurt, fără notițe. E pentru un manager,
de pus lângă CV; raportul întreg rămâne la dosar.</p>
<h3>Rapoarte</h3><p>Rapoartele se scot din <b>Rapoarte</b>, în bara din stânga, numai pentru cine alegi: întâi pe cine
(după nume sau proiect, stare, meseria probei, treaptă; apoi bifa pe fiecare, sau „Toți cei găsiți”), apoi ce raport.
Iese un singur document, fiecare candidat pe pagină nouă. Pe pagina rezultatului, <b>Alte rapoarte</b> deschide
secțiunea cu el ales. Felurile: raportul pentru dosar, raportul pe scurt, raportul de audit, auditul pe scurt și lista
celor aleși, un tabel cu notele, câte unul pe meserie: notele probei se compară numai pe aceeași meserie.</p>
<h3>Raportul de audit</h3><p>Spune cum s-a ajuns la rezultat: calculul totalului, cu cifrele lui; ce a calculat
programul, ce a dat recrutorul și ce a predat candidatul; intrările (versiunea proiectului din istoricul lui, întrebările, cheia probei,
tabelul predat), fiecare cu amprenta lui, un șir scurt calculat din conținut, care se schimbă la orice literă; refacerea:
fișa calculată din nou pe aceeași versiune, cheia verificată, bifele de acum față de ultima intrare din jurnal; jurnalul,
pas cu pas, cu ora și cine a făcut fiecare lucru; ce nu acoperă. Jurnalul îl scrie programul pe loc, la fiecare pas, într-un
fișier din dosarul candidatului (<code>jurnal.jsonl</code>); nu se completează la sfârșit și nu îl scrie un model. Auditul pe scurt
are aceleași părți, fără jurnalul pas cu pas.</p>
<h3>Exemple</h3><p>Candidații din capitolul de exemple al manualului (persoane inventate, în afară de autor),
cu toți pașii făcuți. Treci de la un pas la altul, de la un candidat la altul, și scoți raportul fiecăruia, ca să vezi
aplicația înainte s-o folosești. Câmpurile și butoanele nu se apasă; candidații tăi rămân neatinși. Prima deschidere
pregătește exemplele, cam 20 de secunde; „Reface exemplele” le face din nou, după o actualizare a programului.</p>
<h3>Butonul „Cum folosesc”</h3><p>Pe fiecare ecran, lângă titlu (pe rapoarte, în bara de sus, care nu se tipărește). Deschide pașii ecranului, pe scurt; manualul
acesta e versiunea întreagă.</p>
""" + f"""<h2>Treptele</h2><p>Fișa proiectului de portofoliu așază proiectul pe una din patru trepte. Fiecare treaptă spune ce se vede în
proiect despre felul în care omul lucrează cu AI-ul.</p>
{md.html_din(chr(10).join(scara_recrutor()))}
""" + capitol_exemple() + f"""<h2>Unde stau datele</h2><p>Totul se salvează pe disc, pe acest calculator: fiecare candidat are un dosar în
<code>{e(str(candidati.DOSAR))}</code>, cu numele lui fără diacritice (de pildă <code>ana-pop</code>), într-unul din trei
dosare, cu numele stării: propuse, în analiză (<code>in-analiza</code>) și finalizate. Programul îl mută singur din „Propuse” la prima analiză și în „Finalizate” când apeși
„Finalizează candidatura”. Pe disc, dosarele stau în ordine
alfabetică; în „Istoricul candidaților”, cel adăugat ultimul e primul.</p><ul>
<li><b>Interviul și proba:</b> câte un fișier text, cu bifele și notițele (<code>ghid.md</code>, <code>proba.md</code>);
se deschid și în Notepad, fără program.</li>
<li><b>Tabelul de răspuns predat:</b> fișierul Excel primit de la candidat (<code>Raspuns.xlsx</code>); îl descarci și de pe
ecranul probei, cu „Descarcă tabelul predat”. Unul înlocuit rămâne alături, cu ora în nume.</li>
<li><b>Jurnalul:</b> urma fiecărui pas, pentru raportul de audit (<code>jurnal.jsonl</code>).</li>
<li><b>Fișele:</b> ce a calculat programul la portofoliu și la probă, pentru el (<code>fisa.json</code>,
<code>fisa-proba.json</code>); pe ecran le vezi la pașii 1 și 3.</li></ul>
<h3 id="stergerea">Ștergerea unui candidat</h3><p>Datele unui candidat se țin cât sunt de folos: de regulă, se șterg când e clar că nu
urmează angajarea, sau când omul cere. „Șterge candidatul”, la pasul 4, scoate de pe discul acestui calculator tot dosarul lui
(proiectul descărcat, fișa, interviul, proba, jurnalul), definitiv, fără Coșul de reciclare; ca să confirmi, îi scrii
numele. Rămân rapoartele salvate de tine ca PDF, fișierele primite de la candidat, acolo unde le-ai pus, și copiile de
siguranță ale calculatorului: pe acelea le ștergi tu.</p>
<p>Programul merge numai pe acest calculator: un coleg nu-l deschide de la el. Îi trimiți raportul pentru dosar (pasul 4,
salvat ca PDF) sau fișierul de care are nevoie, de pildă tabelul predat.</p>
<h2>Ce face și ce rămâne la tine</h2><ul><li>Arată ce se vede în proiect și ce a răspuns omul; judecata despre om e a
ta.</li><li>Cifrele sunt ale unui prototip: arată cum funcționează unealta, înainte de calibrarea pe candidați
reali.</li><li>Vede munca din istoricul proiectului (git); ce s-a lucrat în afara lui afli la interviu.</li></ul>"""

# Capturile din manual: cate una sub titlul fiecarui ecran din „Ecranele și butoanele”, facute de `capturi.py` pe setul
# exemplelor (tmp-set-exemple/), nu pe candidatii recrutorului. Titlul: (fisierul din static/manual/, legenda).
CAPTURI_MANUAL = {
    "Acasă": ("acasa", "Acasă, cu candidații din exemple în lucru."),
    "Istoricul candidaților": ("candidati", "Istoricul candidaților, cu căutarea deasupra listei."),
    "Candidat nou": ("nou", "Formularul pentru un candidat nou, necompletat."),
    "1. Portofoliul": ("portofoliul", "Fișa proiectului de portofoliu al Ioanei Vlădescu (persoană inventată): treapta "
                                      "și punctajul."),
    "2. Interviul": ("interviul", "Interviul Ioanei Vlădescu (persoană inventată): întrebările, cu bifele lângă."),
    "3. Proba": ("proba", "Proba Ioanei Vlădescu (persoană inventată): tema și tabelul ei, încărcat."),
    "4. Rezultatul": ("rezultatul", "Rezultatul Ioanei Vlădescu (persoană inventată): totalul, din cele trei părți."),
    "Raportul pentru dosar": ("raport", "Începutul raportului pentru dosar al Ioanei Vlădescu (persoană inventată)."),
    "Rapoarte": ("rapoarte", "Rapoarte: întâi alegi pe cine, apoi ce."),
    "Raportul de audit": ("audit", "Începutul raportului de audit al Ioanei Vlădescu (persoană inventată)."),
    "Exemple": ("exemple", "Lista exemplelor, cu pașii și rapoartele fiecăruia."),
    "Butonul „Cum folosesc”": ("cum-folosesc", "Fereastra „Cum folosesc”, deschisă pe interviul Ioanei Vlădescu "
                                              "(persoană inventată)."),
}


def _cu_capturi(manual):
    """Figura fiecarui ecran, sub titlul lui; deasupra primei, o nota: capturile sunt facute pe exemple."""
    for titlu, (fisier, legenda) in CAPTURI_MANUAL.items():
        h3 = f"<h3>{titlu}</h3>"
        manual = manual.replace(h3, f'{h3}<figure class="captura"><img src="/static/manual/{fisier}.png" alt="{e(legenda)}" '
                                    f'width="1280" height="900" loading="lazy"><figcaption>{e(legenda)}</figcaption></figure>', 1)
    nota = ('<p class="nota-mica">Capturile de mai jos sunt făcute pe <a href="#exemple">exemplele din manual</a>: '
            'persoane inventate, în afară de autor; orice potrivire cu o persoană reală e întâmplătoare.</p>')
    return manual.replace("<h2>Ecranele și butoanele</h2>", "<h2>Ecranele și butoanele</h2>" + nota, 1)


MANUAL = _cu_capturi(MANUAL)


# ── Raportul pentru dosar ─────────────────────────────────────────────────────

def _predat(text):
    """In raport: ce a predat, cu linkurile ca legaturi; pe hartie se citeste adresa."""
    if not (text or "").strip():
        return "—"
    text = text.strip()
    return "".join(e(t) + (f'<a href="{e(l)}">{e(l)}</a>' if l else "")
                   for t, l in zip(_LINK.split(text), _LINK.findall(text) + [""]))


def _raport_proba(c, p):
    """Proba in raport: ce a gasit in tabel, bifele cu textul lor si ce a raspuns la discutie."""
    v, d, ch = proba.valori(candidati.foaie_probei(c)), p["din_cheie"], p["cheia"]
    bifa = {"da": "da", "nu": "nu"}
    tabel = (f'{len(d["gasite"])} din {ch["erori_de_gasit"]} greșeli găsite, {len(d["gresite"])} semnalări greșite'
             if d else "lipsă: tabelul de răspuns nu e încărcat")
    randuri = "".join(f'<tr><td>{e(b)}</td><td class="r-nota">{bifa.get(v[f"C{i}"], "—")}</td></tr>'
                      for i, b in enumerate(p["pachet"].conversatii, 1))
    randuri += "".join(f'<tr><td><b>{e(q)}</b><div class="r-mic">Da, dacă: {e(b)}</div>'
                       f'{"<div>" + e(v[f"nota-D{i}"]) + "</div>" if v[f"nota-D{i}"] else ""}</td>'
                       f'<td class="r-nota">{bifa.get(v[f"D{i}"], "—")}</td></tr>'
                       for i, (q, b) in enumerate(p["pachet"].discutie, 1))
    n = p["nota"]
    return (f'<h2>Proba</h2><p class="r-mic">Proba pe meseria {e(p["pachet"].meseria)}, aceeași pentru toți cei de pe '
            f'ea: {e(p["pachet"].cuvinte["tema_pe_scurt"])}. Nota probei e media a trei părți: tabelul de răspuns, potrivit cu cheia; conversațiile; discuția de după '
            'predare.</p><table class="r-tabel">'
            f'<tr><th>Tabelul de răspuns</th><td>{tabel}</td></tr>'
            f'<tr><th>Conversațiile predate</th><td>{_predat(v["linkuri"])}</td></tr>'
            f'<tr><th>Programul predat</th><td>{_predat(v["cod"])}</td></tr>'
            f'<tr><th>Proba</th><td>{f"{n["nota"] * 100:.0f}%" if n["complet"] else "incompletă, lipsește: " + e(", ".join(n["lipsa"]))}'
            '</td></tr></table>'
            f'<table class="r-tabel r-intrebari"><tr><th>Conversațiile, apoi discuția</th><th>Bifa</th></tr>{randuri}</table>')


def _raport_scurt(c, s, v, fi):
    """Restul raportului pe scurt: notele pe arie, proba intr-un tabel, concluzia, fisa pe scurt. Cifrele, aceleasi."""
    note = "".join(f'<tr><td>{q[0][1:]}</td><td>{e(q[2])}</td><td class="r-nota">{s["standard"][q[0]] or "nepusă"}</td></tr>'
                   for q in INTREBARI)
    p = s["proba"]
    n, d, ch = p["nota"], p["din_cheie"], p["cheia"]
    parti = n["parti"]
    proc = lambda x: "lipsă" if x is None else f"{x * 100:.0f}%"
    tabel = (f'{len(d["gasite"])} din {ch["erori_de_gasit"]} greșeli găsite, {len(d["gresite"])} semnalări greșite: '
             f'{proc(parti["cheia"])}' if d else "lipsă: tabelul de răspuns nu e încărcat")
    principii = "".join(f'<tr><th>{e(ARII_RECRUTOR[x])}</th><td>{nr(y["puncte"])} din 4</td></tr>'
                        for x, y in fi["principii"].items() if x not in fi["goluri"]) if fi else ""
    return ('<h2>Notele interviului, pe arie</h2><table class="r-tabel r-intrebari"><tr><th></th><th>Aria</th>'
            f'<th>Nota (1–4)</th></tr>{note}</table>'
            '<h2>Proba practică</h2><table class="r-tabel">'
            f'<tr><th>Tabelul de răspuns</th><td>{tabel}</td></tr>'
            f'<tr><th>Conversațiile cu AI-ul</th><td>{proc(parti["conversațiile"])}</td></tr>'
            f'<tr><th>Discuția de după predare</th><td>{proc(parti["discuția"])}</td></tr>'
            f'<tr class="r-total"><th>Proba</th><td>{proc(n["nota"]) if n["complet"] else "incompletă"}</td></tr></table>'
            f'<h2>Concluzia evaluatorului</h2><p>{e(v.get("concluzia", "")) or "<i>nescrisă</i>"}</p>' +
            (_fara_cod_raport(c) if not fi else
             '<h2>Fișa proiectului de portofoliu</h2>'
             f'<table class="r-tabel"><tr><th>Punctajul proiectului</th><td>{nr(fi["total"])} din {nr(fi["maxim"])}</td></tr>'
             f'{principii}</table>') +
            '<p class="r-mic">Cifrele sunt ale unui prototip, necalibrat; decizia de angajare o iau oamenii care citesc '
            'raportul. Raportul întreg, cu notițele interviului și ce a predat candidatul, e la dosar.</p>')


def _plafon(t):
    return f", fără proiect cu cod: cel mult {nr(t['plafon'])}" if t["fara_cod"] else ""


def _fara_cod_raport(c):
    return ('<h2>Portofoliul: fără proiect cu cod</h2><p>Candidatul nu are proiect cu cod: a hotărât recrutorul, cu '
            f'motivul: {e(candidati.fara_cod(c))} Portofoliul intră în total cu 0, deci totalul ajunge cel mult la '
            f'{nr(PLAFON_FARA_COD)} din 100, din interviu și probă. Totalul se judecă față de cifra asta. Ce a adus în loc '
            'stă la „Discuția, fără notă”.</p>')


def raport(c, scurt=False):
    """Raportul unui candidat, cu bara de unelte: tiparirea, cealalta forma, intoarcerea."""
    if not candidati.ghid(c) or not (candidati.fisa(c) or candidati.fara_cod(c)):
        return pagina("Raportul", '<h1>Raportul</h1><p>Întâi portofoliul și interviul.</p>', c)
    alta = (f'<a class="buton secundar" href="/c/{c["id"]}/raport">Raportul întreg</a>' if scurt else
            f'<a class="buton secundar" href="/c/{c["id"]}/rezumat">Raportul pe scurt</a>')
    unelte = (f'<div class="r-unelte"><button class="buton" onclick="window.print()">Tipărește sau salvează ca PDF</button>'
              f'{alta}<a class="buton secundar" href="/c/{c["id"]}/rezultat">← Înapoi la rezultat</a>{_ajutor("raport")}</div>')
    titlu = f"Raport pe scurt — {c['nume']}" if scurt else f"Raport — {c['nume']}"
    # bara din stanga ramane pe ecran, ca sa mergi oriunde; la tipar o ascunde stil.css
    return pagina(titlu, unelte + _raport_corp(c, scurt), c, "rezultat", clasa="raport")


def _raport_corp(c, scurt=False):
    """O pagina facuta pentru tiparit: ce ramane in mana evaluatorului, pentru dosarul candidatului. Nu calculeaza
    nimic al ei: nota vine din `interviu.scor`, totalul din `total.py`, fisa din `pasi.py`. `scurt`: raportul pe scurt,
    de cel mult doua pagini, pentru un manager, langa CV (cerut de autor): fara notite si fara discutia fara nota."""
    g, f = candidati.ghid(c), candidati.fisa(c)
    if not g or not (f or candidati.fara_cod(c)):
        return f'<h1>Raportul — {e(c["nume"])}</h1><p>Întâi portofoliul și interviul.</p>'
    v = formular.valori(g)
    try:
        s, eroare = candidati.rezultat(c), None
    except ValueError as ex:
        s, eroare = None, str(ex)
    fi = f["fisa"] if f else None
    proiectul = (f'fără proiect cu cod <span class="r-mic">(hotărârea recrutorului: {e(candidati.fara_cod(c))})</span>'
                 if not f else f'{proiect(c)} <span class="r-mic">({e(cale(c["proiect"]))}; starea din '
                               f'{e(md.data(f["calculat"][:10]))}, versiunea proiectului (cod {e(f["commit"][:7])}))</span>')
    demo = ('<p class="r-demo">Autoevaluare, demonstrativ: candidatul a răspuns și a bifat singur, ca să se vadă cum '
            'funcționează unealta: o demonstrație, nu o evaluare.</p>') if c["demonstrativ"] else ""
    r = [f'<header class="r-cap"><div class="r-marca">HarnessCraft · prototip</div>'
         f'<h1>{"Raport de evaluare, pe scurt" if scurt else "Raport de evaluare"}</h1>'
         f'<table class="r-date"><tr><th>Candidatul</th><td>{e(c["nume"])}</td></tr>'
         f'<tr><th>Proiectul</th><td>{proiectul}</td></tr>'
         f'<tr><th>Data</th><td>{datetime.now():%d.%m.%Y}</td></tr>'
         '<tr><th>Evaluatorul</th><td class="r-linie"></td></tr></table>' + demo + '</header>']
    if eroare:
        r.append(f'<div class="cutie eroare">{e(_eroare_probei(eroare))}</div>' if eroare.startswith("proba: ") else
                 f'<div class="cutie eroare"><strong>Interviul are o întrebare bifată pe jumătate.</strong> {e(eroare)}</div>')
    else:
        t, m = s["total"], s["medie"]
        nivel = ("fără proiect cu cod" if not fi else
                 f'{e(NUME_TREPTE[fi["nivel"]])} ({fi["nivel"] + 1} din {len(NUME_TREPTE)}), provizoriu'
                 f'<div class="r-mic">{e(TREPTE_RECRUTOR[fi["nivel"]])}</div>')
        r.append('<h2>Rezultatul</h2><table class="r-tabel"><tr><th>Treapta din portofoliu</th>'
                 f'<td>{nivel}</td></tr>'
                 f'<tr><th>Nota interviului</th><td>{"—" if m["medie"] is None else nr(m["medie"])} din 4, {_media_puse(m)}</td></tr>'
                 + "".join(f'<tr><th>{e(n[0].upper() + n[1:])}, în total</th><td>{"lipsă" if p is None else nr(p) + " din 33,3"}'
                           f'{", fără proiect cu cod" if n == "portofoliul" and t["fara_cod"] else ""}</td></tr>'
                           for n, p in t["puncte"].items()) +
                 f'<tr class="r-total"><th>Totalul</th><td>{nr(t["total"])} din 100'
                 f'{"" if t["complet"] else ", incomplet: lipsește " + e(", ".join(t["lipsa"]))}{_plafon(t)}</td></tr></table>')
        if scurt:
            r.append(_raport_scurt(c, s, v, fi))
            return "".join(r)
        randuri = "".join(
            f'<tr><td>{q[0][1:]}</td><td><b>{e(q[4])}</b><div class="r-mic">{e(q[2])}</div>'
            f'{"<div>" + e(v.get("nota-" + q[0], "")) + "</div>" if v.get("nota-" + q[0]) else ""}</td>'
            f'<td class="r-nota">{s["standard"][q[0]] or "nepusă"}</td></tr>' for q in INTREBARI)
        r.append('<h2>Întrebările cu notă</h2><p class="r-mic">Aceleași pentru toți candidații. Nota = 1 + numărul de '
                 '„da” din cele trei rânduri bifate de evaluator; media se face pe întrebările puse.</p>'
                 f'<table class="r-tabel r-intrebari"><tr><th></th><th>Întrebarea și notițele</th><th>Nota</th></tr>'
                 f'{randuri}</table>')
        r.append(_raport_proba(c, s["proba"]))
    fara = [(q, v.get(f"nota-T{i}", "")) for i, q in tintite.din_ghid(candidati.ghid(c))]
    fara += [(v[f"L{i}"], v.get(f"nota-L{i}", "")) for i in range(1, interviu.LIBERE + 1) if v.get(f"L{i}")]
    if fara or v.get("nota-parcurs"):
        r.append('<h2>Discuția, fără notă</h2>')
        if v.get("nota-parcurs"):
            r.append(f'<p><b>Parcursul:</b> {e(v["nota-parcurs"])}</p>')
        r += [f'<p><b>{e(q)}</b><br>{e(a) or "<i>fără notițe</i>"}</p>' for q, a in fara]
    r.append(f'<h2>Concluzia evaluatorului</h2><p>{e(v.get("concluzia", "")) or "<i>nescrisă</i>"}</p>')
    if fi:
        principii = "".join(f'<tr><th>{e(ARII_RECRUTOR[n])}</th><td>{nr(x["puncte"])} din 4</td></tr>'
                            for n, x in fi["principii"].items() if n not in fi["goluri"])
        r.append('<h2>Fișa proiectului de portofoliu, pe scurt</h2><p class="r-mic">Calculată de program din istoricul proiectului (git), din reguli '
                 'scrise de oameni.</p>'
                 f'<table class="r-tabel"><tr><th>Punctajul proiectului</th><td>{nr(fi["total"])} din {nr(fi["maxim"])}</td></tr>'
                 f'{principii}</table>')
    else:
        r.append(_fara_cod_raport(c))
    r.append('<h2>Cum se citește raportul</h2><ul class="r-mic"><li>Cifrele sunt ale unui prototip: arată cum '
             'funcționează unealta, înainte de calibrarea pe candidați reali.</li><li>Raportul sprijină decizia de '
             'angajare; decizia o iau oamenii care îl citesc.</li><li>Fișa proiectului de portofoliu citește din istoricul proiectului (git) cum e organizat '
             'proiectul; lucrul practic îl arată proba, iar ce s-a lucrat în afara istoricului iese la interviu.</li></ul>')
    return "".join(r)

# ── Raportul de audit: cum s-a ajuns la rezultat, citit din jurnal (audit.py), nu scris la sfarsit ──

def _cine_a_hotarat(c, s):
    """Ce a calculat programul, ce a dat recrutorul, ce a predat candidatul."""
    vi, vp = formular.valori(candidati.ghid(c) or ""), proba.valori(candidati.foaie_probei(c))
    bi = [v for k, v in vi.items() if re.fullmatch(r"S\d+\.[123]", k)]
    bp = [v for k, v in vp.items() if re.fullmatch(r"[CD]\d", k)]
    cate = lambda b: f'{sum(x == "da" for x in b)} „da” și {sum(x == "nu" for x in b)} „nu” din {len(b)} rânduri'
    conversatii = _conversatii(vp.get("linkuri", ""))
    d = candidati.decizia_probei(c)
    a = (d or {}).get("acordul")
    decizia = ("neconsemnată" if d is None else "merge la probă" if d["decizia"] == "da" else
               f"fără probă, cu motivul: {e(d['motivul'])}")
    acordul = ("" if not d or d["decizia"] != "da" else "; răspunsul la invitația la probă: " +
               ("încă nedat" if not a else f'{"a acceptat" if a["raspuns"] == "da" else "a refuzat"}, pe '
                                          f'{e(md.data(a["data"]))} ({e(a["cum"])}), consemnat de recrutor'))
    fara_cod = (f"fără proiect cu cod, la adăugare, cu motivul: {e(candidati.fara_cod(c))}; "
                if candidati.fara_cod(c) else "")
    return ('<table class="r-tabel">'
            '<tr><th>Programul</th><td>treapta și punctajul fișei, din reguli scrise; potrivirea tabelului de răspuns cu '
            'cheia; nota fiecărei întrebări (1 + numărul de „da”), mediile și totalul pe treimi</td></tr>'
            f'<tr><th>Recrutorul</th><td>{fara_cod}bifele interviului: {cate(bi)}; bifele probei: {cate(bp)}; concluzia: '
            f'{"scrisă" if vi.get("concluzia") else "nescrisă"}; decizia de probă: {decizia}; meseria probei; finalizarea '
            'candidaturii</td></tr>'
            f'<tr><th>Candidatul</th><td>{"nimic la portofoliu" if fara_cod else "proiectul de portofoliu"}{acordul}; tabelul de răspuns '
            f'{"predat" if (c["dosar"] / "Raspuns.xlsx").exists() else "nepredat"}; conversațiile cu AI-ul: '
            f'{conversatii}; programul probei: '
            f'{"predat" if vp.get("cod") else "nepredat"}</td></tr></table>')


def _conversatii(text):
    """Conversatiile predate, numarate la fel in audit ca in raportul pentru dosar: linkurile, iar fara link, textul
    scris de recrutor (o conversatie trimisa ca fisier) inseamna tot predate."""
    n = len(_LINK.findall(text or ""))
    if n:
        return f'{n} {"link" if n == 1 else "linkuri"} de conversație'
    return "predate, fără link (le-a descris recrutorul)" if (text or "").strip() else "nepredate"


def _cum_s_a_ajuns(s, f):
    t, m, pn = s["total"], s["medie"], s["proba"]["nota"]
    pt = t["puncte"]
    lipsa = "lipsă: nu intră în total"
    fi = f["fisa"] if f else None
    proc = lambda x: "lipsă" if x is None else f"{x * 100:.0f}%"
    randuri = [
        ("Portofoliul", 'fără proiect cu cod, hotărârea recrutorului → 0 × 33,3 = <b>0</b>' if t["fara_cod"] else
                        f'punctajul fișei {nr(fi["total"])} din {nr(fi["maxim"])} → {nr(fi["total"])} / {nr(fi["maxim"])} × '
                        f'33,3 = <b>{nr(pt["portofoliul"])}</b>'),
        ("Interviul", lipsa if pt["interviul"] is None else
         # aceeasi forma ca pe „Rezultatul” (B26, B12)
         f'{_media_puse(m).capitalize()}: {nr(m["medie"])} din 4 → ({nr(m["medie"])} − 1) / 3 × '
         f'33,3 = <b>{nr(pt["interviul"])}</b>'),
        ("Proba", ("incompletă, " + lipsa) if pt["proba"] is None else
         f'media părților (tabelul {proc(pn["parti"]["cheia"])}, conversațiile {proc(pn["parti"]["conversațiile"])}, '
         f'discuția {proc(pn["parti"]["discuția"])}) = {proc(pn["nota"])}, adică <b>{nr(pt["proba"])}</b> din 33,3'),
    ]
    return ('<table class="r-tabel">' + "".join(f'<tr><th>{n}</th><td>{x}</td></tr>' for n, x in randuri) +
            f'<tr class="r-total"><th>Totalul</th><td>{nr(t["total"])} din 100, suma părților'
            f'{"" if t["complet"] else ", incomplet: lipsește " + e(", ".join(t["lipsa"]))}{_plafon(t)}</td></tr></table>'
            '<p class="r-mic">Ponderi egale, alese, nu măsurate: prototip necalibrat. Regula totalului e scrisă în '
            'program (<code>harnesscraft/total.py</code>).</p>')


def _intrarile(c, f, j):
    pa, vp = candidati.pachetul_probei(c), proba.valori(candidati.foaie_probei(c))
    g = candidati.ghid(c) or ""
    amp = re.search(r"^<!-- ghid-interviu intrebari ([0-9a-f]+) -->$", g, re.M)
    la_analiza = next((x["versiune"] for x in reversed(j) if x["pas"] == "portofoliul"), None)
    r = [("Proiectul de portofoliu", f'{e(cale(c["sursa"]))}, la versiunea proiectului din istoric (cod {e(f["commit"][:7])}), '
                                     f'analizat la {e(md.data(f["calculat"]))}' if f else
          "fără proiect cu cod, hotărârea recrutorului" if candidati.fara_cod(c) else "neanalizat"),
         ("Programul, la analiză", f"versiunea programului (cod {e(la_analiza)})" if la_analiza else
          "nescris: fișa e de dinainte de jurnal" if f else "—"),
         ("Întrebările interviului", "fără ghid" if not amp else
          f'amprenta întrebărilor (cod {amp.group(1)})' + (", aceleași ca acum" if amp.group(1) == interviu.AMPRENTA else
                                        f", altele decât acum (cod {interviu.AMPRENTA})")),
         ("Proba", f'meseria {e(pa.meseria)}, {e(pa.titlu)}; amprenta cheii (cod {e(candidati._amprenta_cheii(pa))}); '
                   f'amprenta bifelor (cod {e(pa.amprenta)})'),
         ("Tabelul de răspuns", f'amprenta tabelului (cod {audit.amprenta(c["dosar"] / "Raspuns.xlsx")})'
          if (c["dosar"] / "Raspuns.xlsx").exists() else "neîncărcat")]
    fp = candidati.fisa_probei(c)
    r.append(("Programul probei", f'{e(cale(fp["sursa"]))}, la versiunea proiectului din istoric (cod {e(fp["commit"][:7])})'
              if fp else "nepredat"))
    return ('<table class="r-tabel">' + "".join(f'<tr><th>{n}</th><td>{x}</td></tr>' for n, x in r) + '</table>'
            '<p class="r-mic">Amprenta e un șir scurt calculat din conținut: același fișier, aceeași amprentă; o literă '
            'schimbată o schimbă.</p>')


def _refacerea(c, j):
    r = []
    rf = candidati.refa_fisa(c)
    if rf is None and candidati.fara_cod(c):
        r.append("Fișa portofoliului: nimic de refăcut, candidatul nu are proiect cu cod; portofoliul intră cu 0.")
    elif rf is None:
        r.append("Fișa portofoliului: încă necalculată.")
    elif "eroare" in rf:
        r.append(f"Fișa portofoliului nu se poate reface: {e(rf['eroare'])}.")
    else:
        r.append(f'Fișa portofoliului, calculată din nou acum pe aceeași versiune: {e(NUME_TREPTE[rf["nivel"]])}, '
                 f'{nr(rf["total"])} din {nr(rf["maxim"])}: ' +
                 ("<b>aceeași treaptă și același punctaj</b>." if rf["la_fel"] else
                  "<b>diferă de cea salvată</b>: regulile s-au schimbat de atunci; „Analizează din nou” o aduce la zi."))
    try:
        candidati.pachetul_probei(c).cheia()
        r.append("Cheia probei are amprenta păstrată la verificarea ei: neschimbată de atunci.")
    except ValueError:
        r.append("<b>Cheia probei nu mai are amprenta păstrată la verificare</b>: s-a schimbat după verificare.")
    for pas, bife, nume in (("interviul", candidati._bife_interviu(candidati.ghid(c) or ""), "interviului"),
                            ("proba", candidati._bife_probei(candidati.foaie_probei(c)), "probei")):
        ultima = audit.ultima_stare(j, pas)
        if ultima is None:
            r.append(f"Bifele {nume}: jurnalul nu are încă starea lor.")
        elif ultima == bife:
            r.append(f"Bifele {nume} de acum sunt cele din ultima intrare a jurnalului.")
        else:
            dif = sorted(k for k in set(ultima) | set(bife) if ultima.get(k) != bife.get(k))
            r.append(f"<b>Bifele {nume} diferă de ultima intrare a jurnalului</b> ({e(', '.join(dif))}): schimbate în "
                     "afara aplicației, direct în fișier.")
    r.append("Nota interviului, nota probei și totalul se calculează la fiecare deschidere, din fișierele de acum: "
             "cifrele de mai sus sunt chiar refacerea lor.")
    return '<ul class="r-mic">' + "".join(f"<li>{x}</li>" for x in r) + "</ul>"


def _urme_vechi(c, f, j):
    """Ce se stie de dinainte de jurnal: numai ce e scris in fisiere, cu ora lor, fara reconstituiri."""
    inceput = j[0]["ora"] if j else None
    urme = [(c.get("creat", ""), "candidatul adăugat (candidat.json)")]
    if f:
        urme.append((f["calculat"], f"fișa portofoliului calculată, la versiunea {f['commit'][:7]} (fisa.json)"))
    if fp := candidati.fisa_probei(c):
        urme.append((fp["calculat"], f"fișa probei calculată (fisa-proba.json)"))
    for x in sorted(c["dosar"].glob("*-inlocuit-la-*")) + sorted(c["dosar"].glob("ghid.inainte-de-reanalizare-*")):
        urme.append(("", f"copie păstrată: {x.name}"))
    urme = [(o, ce) for o, ce in urme if not inceput or not o or o < inceput]
    return urme


def _audit_corp(c, scurt=False):
    f, j = candidati.fisa(c), audit.citeste(c["dosar"])
    try:
        s, eroare = candidati.rezultat(c), None
    except ValueError as ex:
        s, eroare = None, str(ex)
    demo = ('<p class="r-demo">Autoevaluare, demonstrativ: candidatul a răspuns și a bifat singur.</p>'
            if c["demonstrativ"] else "")
    r = [f'<header class="r-cap"><div class="r-marca">HarnessCraft · prototip</div>'
         f'<h1>{"Raport de audit, pe scurt" if scurt else "Raport de audit"}</h1>'
         f'<table class="r-date"><tr><th>Candidatul</th><td>{e(c["nume"])}</td></tr>'
         f'<tr><th>Proiectul</th><td>{proiect(c)}</td></tr>'
         f'<tr><th>Starea</th><td>{e(dict(candidati.STARI)[c["stare"]])}</td></tr>'
         f'<tr><th>Data</th><td>{datetime.now():%d.%m.%Y, %H:%M}</td></tr>'
         f'<tr><th>Programul</th><td>HarnessCraft, versiunea programului (cod {e(audit.VERSIUNE)})</td></tr></table>{demo}'
         '<p class="r-mic">Spune cum s-a ajuns la rezultat: ce a calculat programul și ce a dat omul, din ce intrări, '
         'și dacă se reface. E citit din jurnalul candidatului, scris de program la fiecare pas.</p></header>']
    r.append("<h2>Cum s-a ajuns la rezultat</h2>")
    if s and (f or s["total"]["fara_cod"]):
        r.append(_cum_s_a_ajuns(s, f))
    elif eroare:
        r.append(f'<div class="cutie eroare">{e(_eroare_probei(eroare) if eroare.startswith("proba: ") else eroare)}</div>')
    else:
        r.append("<p>Fără rezultat încă: întâi portofoliul și interviul.</p>")
    r += ["<h2>Cine a hotărât ce</h2>", _cine_a_hotarat(c, s), "<h2>Intrările</h2>", _intrarile(c, f, j),
          "<h2>Refacerea</h2>", _refacerea(c, j)]
    urme = _urme_vechi(c, f, j)
    if scurt:
        pe = lambda cine: sum(x["cine"] == cine for x in j)
        r.append("<h2>Jurnalul, pe scurt</h2><p>" + (
            f'{len(j)} intrări, de la {e(md.data(j[0]["ora"]))} la {e(md.data(j[-1]["ora"]))}: '
            f'{pe(audit.PROGRAM)} ale programului, {pe(audit.RECRUTOR)} ale recrutorului.' if j else "Jurnalul e gol.") +
            (f" Dinainte de jurnal: {len(urme)} urme în fișiere." if urme else "") +
            " Pas cu pas, în raportul de audit întreg.</p>")
    else:
        r.append("<h2>Jurnalul</h2>")
        if j:
            r.append('<table class="r-tabel r-jurnal"><tr><th>Ora</th><th>Cine</th><th>Ce</th></tr>' + "".join(
                f'<tr><td>{e(md.data(x["ora"]))}</td><td>{e(x["cine"])}</td><td>{_ce_jurnal(x["ce"])}</td></tr>'
                for x in j) + "</table>")
        else:
            r.append("<p>Jurnalul e gol.</p>")
        if urme:
            r.append('<h3>Dinainte de jurnal</h3><p class="r-mic">Candidatul e mai vechi decât jurnalul: ce s-a făcut '
                     'înainte se vede numai din urmele scrise în fișiere, cu ora lor.</p><ul class="r-mic">' +
                     "".join(f'<li>{e(md.data(o)) + ": " if o else ""}{e(ce)}</li>' for o, ce in urme) + "</ul>")
    r.append('<h2>Ce nu acoperă</h2><ul class="r-mic"><li>Textul notițelor nu intră în jurnal: stă în ghid și în foaia '
             'probei; jurnalul spune numai că s-a schimbat.</li><li>O schimbare făcută direct în fișiere, în afara '
             'aplicației, nu apare în jurnal; la bife, refacerea o arată.</li><li>Programul spune versiunea codului care '
             'rula; schimbările nesalvate în istoricul lui sunt semnalate, nu și conținutul lor.</li><li>Auditul arată cum s-a calculat, '
             'nu dacă regulile sunt bune: cifrele sunt ale unui prototip necalibrat.</li></ul>')
    return "".join(r)


def _ce_jurnal(ce):
    """Un rand din jurnal, cu schimbarile lui una sub alta: o salvare a interviului poate tine 21 de bife; liniuta
    din jurnalele vechi (bifa nedata) se citeste cu numele ei, iar „scorul și nivelul” cu termenii recrutorului (B7)."""
    return "<br>".join(e(x.replace("— →", "nedată →").replace("→ —", "→ nedată")
                         .replace("scorul și nivelul", "punctajul și treapta")) for x in ce.split("; "))


def audit_pagina(c, scurt=False):
    unelte = (f'<div class="r-unelte"><button class="buton" onclick="window.print()">Tipărește sau salvează ca PDF</button>'
              f'<a class="buton secundar" href="/rapoarte?id={quote(c["id"])}">Alte rapoarte</a>'
              f'<a class="buton secundar" href="/c/{c["id"]}/rezultat">← Înapoi la rezultat</a>{_ajutor("raport")}</div>')
    titlu = "Audit pe scurt" if scurt else "Audit"
    return pagina(f"{titlu} — {c['nume']}", unelte + _audit_corp(c, scurt), c, "rezultat", clasa="raport")


# ── Rapoarte: intai pe cine, apoi ce; un singur document de tiparit (decizia autorului, 15 octombrie) ──

FELURI = {"dosar": ("Raportul pentru dosar", "întreg, cu notițele interviului"),
          "scurt": ("Raportul pe scurt", "cel mult două pagini, pentru un manager, lângă CV"),
          "audit": ("Raportul de audit", "cum s-a ajuns la rezultat, pas cu pas, din jurnal"),
          "audit-scurt": ("Auditul pe scurt", "cum s-a ajuns la rezultat, fără jurnalul pas cu pas"),
          "lista": ("Lista celor aleși", "un tabel cu notele, pe meserii")}
FILTRE = ("q", "stare", "meserie", "treapta")


def _treapta(c):
    f = candidati.fisa(c)
    return f["fisa"]["nivel"] if f else None


def _meseria(c):
    """Meseria probei, numai daca proba e deschisa si a inceput sa se lucreze (foaia exista); altfel None."""
    return (candidati.pachetul_probei(c).meseria if (c["dosar"] / "proba.md").exists() and candidati.proba_deschisa(c)[0]
            else None)


def _faptul_fara_proba(c):
    """Faptul, o data, la „Proba” pe „Rezultatul” (B18): refuzul cu data lui, sau decizia „nu” cu motivul."""
    d = candidati.decizia_probei(c) or {}
    a = d.get("acordul") or {}
    if a.get("raspuns") == "nu":
        return f"Candidatul a refuzat proba pe {md.data(a['data'])} ({a['cum']})."
    return f"Nu merge la probă: {d.get('motivul', '')}".rstrip(": ") + "."


def _fara_proba(c):
    """De ce n-are proba, scurt (B13): „a refuzat proba”, „nu merge la probă” sau „fără probă încă”."""
    d = candidati.decizia_probei(c) or {}
    if (d.get("acordul") or {}).get("raspuns") == "nu":
        return "a refuzat proba"
    return "nu merge la probă" if d.get("decizia") == "nu" else "fără probă încă"


def _gasiti(dosar, q):
    v = {k: q.get(k, [""])[-1] for k in FILTRE}
    cs = candidati.lista(dosar, v["q"])
    return [c for c in cs if (not v["stare"] or c["stare"] == v["stare"])
            and (not v["meserie"] or (_meseria(c) or "fără") == v["meserie"])
            and (not v["treapta"] or str(_treapta(c) if _treapta(c) is not None else "fără") == v["treapta"])], v


def _select(nume, eticheta, optiuni, ales):
    o = "".join(f'<option value="{e(k)}"{" selected" if k == ales else ""}>{e(n)}</option>' for k, n in optiuni)
    return f'<label class="camp">{e(eticheta)}<select name="{nume}">{o}</select></label>'


def rapoarte(dosar, q=None, eroare=None):
    q = q or {}
    gasiti, v = _gasiti(dosar, q)
    alese = set(q.get("id", []))
    meserii = sorted({p.meseria for p in proba.pachete()})
    corp = [f'<div class="rand-titlu"><h1>Rapoarte</h1>{_ajutor("rapoarte")}</div>',
            '<p class="intro">Alegi întâi pe cine, apoi ce raport. Iese un singur document de tipărit, fiecare candidat '
            'pe pagină nouă.</p>', '<h2>1. Pe cine</h2>',
            '<form method="get" action="/rapoarte" class="filtre">'
            f'<label class="camp">Nume sau proiect<input type="search" name="q" value="{e(v["q"])}"></label>' +
            _select("stare", "Starea", [("", "Toate")] + candidati.STARI, v["stare"]) +
            _select("meserie", "Meseria probei", [("", "Toate")] + [(m, m) for m in meserii] + [("fără", "fără probă")],
                    v["meserie"]) +
            _select("treapta", "Treapta", [("", "Toate")] + [(str(i), n) for i, n in enumerate(NUME_TREPTE)] +
                    [("fără", "fără fișă")], v["treapta"]) +
            '<button class="buton secundar">Caută</button></form>']
    if not gasiti:
        corp.append('<p class="estompat">Niciun candidat nu se potrivește.</p>')
        return pagina("Rapoarte", "".join(corp), activ="rapoarte", eroare=eroare)
    ascunse = "".join(f'<input type="hidden" name="{k}" value="{e(x)}">' for k, x in v.items() if x)
    randuri = "".join(
        f'<label class="alegere"><input type="checkbox" name="id" value="{e(c["id"])}"'
        f'{" checked" if c["id"] in alese else ""}><b class="nume-ales">{e(c["nume"])}</b> <span class="estompat">'
        f'{"demonstrativ · " if c["demonstrativ"] else ""}{e(proiect_text(c))} · '
        f'{e(dict(candidati.STARI)[c["stare"]])} · '
        f'{e(NUME_TREPTE[_treapta(c)]) if _treapta(c) is not None else "fără fișă"} · '
        f'{e(_meseria(c) or _fara_proba(c))}</span></label>' for c in gasiti)
    felul = "".join(f'<label class="alegere"><input type="radio" name="fel" value="{k}"{" checked" if k == "dosar" else ""}>'
                    f'<b class="nume-ales">{e(n)}</b> <span class="estompat">{e(d)}</span></label>' for k, (n, d) in FELURI.items())
    corp.append(f'<form method="get" action="/rapoarte/document">{ascunse}'
                f'<label class="alegere toti"><input type="checkbox" name="toti" value="1"><b>Toți cei găsiți '
                f'({len(gasiti)})</b></label><div class="lista-alegeri">{randuri}</div>'
                f'<h2>2. Ce raport</h2><div class="lista-alegeri">{felul}</div>'
                '<div class="actiune"><button class="buton">Scoate raportul</button></div></form>')
    corp.append('<details class="pliat"><summary>Ce înseamnă treptele</summary><div class="text-ghid">'
                f'{md.html_din(chr(10).join(scara_recrutor(explicatii=False)))}</div></details>')
    return pagina("Rapoarte", "".join(corp), activ="rapoarte", eroare=eroare)


def proiect_text(c):
    return "fără proiect cu cod" if candidati.fara_cod(c) else candidati.nume_sursei(c["sursa"])


def _lista(cs):
    """Lista celor alesi: un tabel pe meserie, pentru ca notele probei se compara numai pe aceeasi meserie."""
    pe = {}
    for c in cs:
        pe.setdefault(_meseria(c) or "", []).append(c)
    r = ['<header class="r-cap"><div class="r-marca">HarnessCraft · prototip</div><h1>Lista candidaților aleși</h1>'
         f'<table class="r-date"><tr><th>Candidați</th><td>{len(cs)}</td></tr>'
         f'<tr><th>Data</th><td>{datetime.now():%d.%m.%Y}</td></tr></table>'
         '<p class="r-mic">Cifrele sunt ale unui prototip, necalibrat. Notele probei se compară numai între candidații de '
         'pe aceeași meserie: de aceea, un tabel pe meserie, în ordinea totalului. Treptele: '
         + "; ".join(f"{i + 1}. {e(n)}: {e(x.rstrip('.'))}" for i, (n, x) in enumerate(zip(NUME_TREPTE, TREPTE_RECRUTOR))) +
         '.</p></header>']
    for meseria in sorted(pe, key=lambda m: (m == "", m)):
        r.append(f'<h2>{"Proba pe meseria " + e(meseria) if meseria else "Fără probă"}</h2>'
                 '<table class="r-tabel r-lista"><colgroup><col><col class="c-stare"><col class="c-treapta"><col class="c-port">'
                 '<col class="c-interviu"><col class="c-proba"><col class="c-total"></colgroup><tr><th>Candidatul</th><th>Starea</th><th>Treapta</th><th>Portofoliul</th>'
                 '<th>Interviul</th><th>Proba</th><th>Totalul</th></tr>')
        randuri = []
        for c in pe[meseria]:
            try:
                s, motiv = candidati.rezultat(c), None
            except ValueError as ex:  # un rezultat stricat nu e o parte lipsa: se spune, cu motivul
                s, motiv = None, str(ex)
            randuri.append((c, s, motiv))
        # dupa total, ca un clasament; cei incompleti si cei fara rezultat, la sfarsit
        randuri.sort(key=lambda x: (not (x[1] and x[1]["total"]["complet"]), -(x[1]["total"]["total"] if x[1] else -1)))
        for c, s, motiv in randuri:
            pt = s["total"]["puncte"] if s else {}
            cel = lambda k: "—" if pt.get(k) is None else nr(pt[k])
            tr = _treapta(c)
            demo = " · demonstrativ" if c["demonstrativ"] else ""
            r.append(f'<tr><td><b>{e(c["nume"])}</b><div class="r-mic">{nerupt(proiect_text(c) + demo)}</div></td>'
                     f'<td>{nerupt(dict(candidati.STARI)[c["stare"]])}</td>'
                     f'<td>{nerupt(NUME_TREPTE[tr]) if tr is not None else "fără&nbsp;fișă"}</td><td>{cel("portofoliul")}</td>'
                     f'<td>{cel("interviul")}</td><td>{cel("proba") if meseria else nerupt(_fara_proba(c))}</td>'
                     f'<td>{nr(s["total"]["total"]) + ("" if s["total"]["complet"] else '<div class="r-mic">incomplet</div>') if s else ""}'
                     f'{"" if s else "nu se poate calcula" + (f"<div class=r-mic>{e(motiv)}</div>" if motiv else "")}'
                     '</td></tr>')
        r.append("</table>")
    return "".join(r)


def document(dosar, q):
    fel = q.get("fel", ["dosar"])[-1]
    if fel not in FELURI:
        return rapoarte(dosar, q, eroare="Felul raportului nu e unul din listă.")
    if q.get("toti"):
        cs = _gasiti(dosar, q)[0]
    else:
        cs = [c for c in (candidati.citeste(i, dosar) for i in q.get("id", [])) if c]
    if not cs:
        return rapoarte(dosar, q, eroare="Alegi cel puțin un candidat (sau „Toți cei găsiți”).")
    inapoi = "&".join(f"{k}={quote(x)}" for k in FILTRE for x in q.get(k, []) if x)
    unelte = ('<div class="r-unelte"><button class="buton" onclick="window.print()">Tipărește sau salvează ca PDF</button>'
              f'<a class="buton secundar" href="/rapoarte{"?" + inapoi if inapoi else ""}">← Înapoi la rapoarte</a>'
              f'{_ajutor("raport")}</div>'
              # ce s-a ales, sub bara: in bara, „Cum folosesc” trecea singur pe al doilea rand (B14)
              f'<p class="motiv r-ales">{e(FELURI[fel][0])}: {len(cs)} {"candidat" if len(cs) == 1 else "candidați"}.</p>')
    if fel == "lista":
        corp = _lista(cs)
    else:
        bucata = {"dosar": lambda c: _raport_corp(c), "scurt": lambda c: _raport_corp(c, scurt=True),
                  "audit": _audit_corp, "audit-scurt": lambda c: _audit_corp(c, scurt=True)}[fel]
        corp = "".join(f'<section class="r-candidat">{bucata(c)}</section>' for c in cs)
    return pagina(FELURI[fel][0], unelte + corp, activ="rapoarte", clasa="raport")


# ── Exemplele, numai de citit ─────────────────────────────────────────────────

# „Exemple”, in bara din stanga: cei sase din capitolul manualului, cu toti pasii si rapoartele, din setul din
# tmp-set-exemple/ (set_exemple.reface), facut la primul clic. Aceeasi aplicatie si acelasi server; paginile unui candidat
# din exemple se redau ca oricare, apoi legaturile lui raman in exemple, iar campurile si butoanele nu se apasa.
# Rapoartele se scot. candidaturi/ nu se atinge.
EXEMPLE_STARE = {"se_reface": False, "eroare": None}
_LACAT_EXEMPLE = threading.Lock()
RAPOARTE_CANDIDAT = ("raport", "rezumat", "audit", "audit_scurt")  # in exemple, fara campuri blocate: se tiparesc


def _reface_exemple(radacina):
    try:
        set_exemple.reface(radacina)
    except Exception as ex:  # se spune pe pagina de asteptare; aplicatia merge mai departe
        EXEMPLE_STARE["eroare"] = f"{type(ex).__name__}: {ex}"
    finally:
        EXEMPLE_STARE["se_reface"] = False


def reface_exemplele(radacina):
    """Setul, refacut de la zero, intr-un fir separat; un al doilea clic in timpul refacerii nu mai porneste una."""
    with _LACAT_EXEMPLE:
        if EXEMPLE_STARE["se_reface"]:
            return
        EXEMPLE_STARE.update(se_reface=True, eroare=None)
    threading.Thread(target=_reface_exemple, args=(radacina,), daemon=True).start()


def _asteapta_exemple():
    """Cat se face setul: o pagina care se reincarca singura; o eroare se spune, cu „Încearcă din nou”."""
    if EXEMPLE_STARE["eroare"]:
        corp = ('<h1>Exemplele nu s-au putut pregăti</h1><div class="cutie eroare">' + e(EXEMPLE_STARE["eroare"]) +
                '</div><div class="actiune"><a class="buton" href="/exemple?din-nou=1">Încearcă din nou</a></div>')
        return pagina("Exemple", corp, activ="exemple")
    corp = ('<h1>Se pregătesc exemplele</h1><p>Programul face proiectele și dosarele candidaților din exemple, prin '
            'aceiași pași ca butoanele: durează cam 20 de secunde. Pagina se deschide singură când sunt gata.</p>')
    return pagina("Exemple", corp, activ="exemple").replace("</head>", '<meta http-equiv="refresh" content="3"></head>', 1)


def exemple_lista(radacina):
    """Lista exemplelor, in ordinea capitolului din manual: ce arata fiecare, totalul, pasii si rapoartele lui."""
    tipuri = {c["nume"]: c for c in json.loads(set_exemple.REZULTATE.read_text(encoding="utf-8"))["candidati"]}
    cs = sorted((c for c in candidati.lista(radacina / "candidaturi") if c["nume"] in tipuri),
                key=lambda c: tipuri[c["nume"]]["tip"])
    randuri = []
    for c in cs:
        r, baza = tipuri[c["nume"]], f'/exemple/c/{c["id"]}'
        pasi = " · ".join(f'<a href="{baza}/{p}">{e(n)}</a>' for p, n in candidati.PASI)
        rap = " · ".join(f'<a href="{baza}/{p}">{n}</a>' for p, n in (("raport", "pentru dosar"), ("rezumat", "pe scurt"),
                                                                      ("audit", "auditul")))
        randuri.append(f'<div class="card"><div class="card-nume">{r["tip"]}. {e(c["nume"])}</div><p class="estompat">'
                       f'{e(EXEMPLE[r["tip"]][0])} · totalul {_nr(r["total"])}&nbsp;din&nbsp;100'
                       f'{"" if r["complet"] else ", incomplet"}</p><p>Pașii: {pasi}</p><p>Rapoartele: {rap}</p></div>')
    motiv = set_exemple.ce_lipseste_autorului()
    lipsa = f'<p class="estompat">Primul exemplu, al autorului, lipsește: {e(motiv)}.</p>' if motiv else ""
    corp = (f'<div class="rand-titlu"><h1>Exemple</h1>{_ajutor("exemple")}</div><p class="intro">Candidații din <a href="/manual#exemple">capitolul de exemple al '
            'manualului</a>, cu toți pașii făcuți: te uiți, citești, treci de la un pas la altul și scoți raportul '
            'fiecăruia, ca să vezi aplicația înainte s-o folosești. Sunt <b>numai de citit</b>: câmpurile și butoanele '
            'nu se apasă, iar candidații tăi rămân neatinși.</p><p class="nota-mica">Persoane inventate, în afară de autor; '
            'orice potrivire cu o persoană reală e întâmplătoare. Bifele le-a dat asistentul AI, la cererea '
            f'autorului; interviul Elenei Dobrescu l-a bifat autorul, iar pe al lui, tot el.</p>{lipsa}<div class="carduri">{"".join(randuri)}</div>'
            '<form method="post" action="/exemple/reface" class="actiune"><button class="buton secundar">Reface '
            'exemplele</button><span class="motiv">După o actualizare a programului, dacă un exemplu cere „Analizează '
            'din nou”: cam 20 de secunde.</span></form>')
    return pagina("Exemple", corp, activ="exemple")


_LEGATURA_CANDIDAT = re.compile(r'(href|action)="/c/')
# ce trimite sau schimba ceva: campurile si butoanele formularelor; nu ajutorul („Cum folosesc”) si nu tiparirea
_DE_BLOCAT = re.compile(r'<(input|textarea|select)\b|<button\b(?![^>]*(?:popovertarget|window\.print))')


def doar_de_citit(html, campuri=True):
    """Pagina unui candidat din exemple: legaturile lui raman in exemple, „Alte rapoarte” e gri (B10), ultimul pas duce
    la lista lor, iar cu `campuri`, campurile si butoanele care trimit ceva sunt dezactivate (nu se bifeaza, nu se
    trimite nimic)."""
    html = _LEGATURA_CANDIDAT.sub(r'\1="/exemple/c/', html)
    html = re.sub(r'href="/rapoarte\?id=[^"]*"', 'href="/exemple"', html)
    # in bara ramane marcat numai pasul, ca la un candidat obisnuit (B30); concluzia nu se poate scrie aici (B31, B3)
    html = html.replace('<h2>Concluzia ta</h2><p><i>Încă nescrisă: o scrii la sfârșitul interviului.</i></p>',
                        '<h2>Concluzia: nescrisă în acest exemplu</h2>')
    # omul ramane in exemple pana alege bara (B10)
    html = html.replace('<a class="buton" href="/">Înapoi acasă</a>', '<a class="buton" href="/exemple">Înapoi la exemple</a>')
    nota = ('<div class="cutie avert nota-exemplu"><strong>Exemplu, numai de citit:</strong> persoană inventată, în '
            'afară de autor. <a href="/exemple">Toate exemplele</a></div>')
    if campuri:
        html = _DE_BLOCAT.sub(lambda m: m.group(0) + " disabled", html)
        # „Șterge candidatul”, gri și fără legătură, ca „Finalizează” (B21)
        html = re.sub(r'<a class="(buton[^"]*)" href="/exemple/c/[^"/]+/sterge">(.*?)</a>',
                      r'<button class="\1" disabled>\2</button>', html)
    # dupa blocare, ca butonul sa nu primeasca „disabled” de doua ori; si pe barele rapoartelor (B10)
    html = html.replace('<a class="buton secundar" href="/exemple">Alte rapoarte</a>',
                        '<button class="buton secundar" disabled>Alte rapoarte</button>')
    return html.replace("<main>", "<main>" + nota, 1)


# ── Alegerea proiectului de pe calculator ─────────────────────────────────────

def alege_pe_calculator(bundle=False):
    """Fereastra Windows de ales un dosar (sau un fisier .bundle), deschisa de server, pe acelasi calculator: browserul
    nu da pagina calea unui dosar. `tkinter`, din biblioteca standard: nicio dependenta. Intoarce calea, sau "" daca
    recrutorul a inchis fereastra sau daca Python-ul n-are `tkinter` (atunci scrie calea de mana)."""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return ""
    radacina = tkinter.Tk()
    radacina.withdraw()
    radacina.attributes("-topmost", True)  # deasupra browserului, nu ascunsa in spatele lui
    try:
        if bundle:
            ales = filedialog.askopenfilename(parent=radacina, title="Alege fișierul .bundle primit de la candidat",
                                              filetypes=[("Proiect cu istoric", "*.bundle")])
        else:
            ales = filedialog.askdirectory(parent=radacina, title="Alege dosarul proiectului", mustexist=True)
    finally:
        radacina.destroy()
    return str(Path(ales)) if ales else ""


# ── Serverul ──────────────────────────────────────────────────────────────────

def aplicatie(dosar=candidati.DOSAR, radacina_exemple=None):
    """`radacina_exemple`: setul exemplelor, implicit tmp-set-exemple/."""
    radacina_exemple = radacina_exemple or set_exemple.SET
    candidati.goleste_scoasele(dosar)  # ce a ramas de la o stergere oprita de un fisier deschis
    class Cerere(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _trimite(self, corp, tip="text/html; charset=utf-8", cod=200):
            date = corp.encode("utf-8") if isinstance(corp, str) else corp
            self.send_response(cod)
            self.send_header("Content-Type", tip)
            self.send_header("Content-Length", str(len(date)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(date)

        def _redirect(self, unde):
            self.send_response(303)
            self.send_header("Location", unde)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _negasit(self):
            self._trimite(pagina("Nu există", '<h1>Pagina nu există</h1><p><a href="/">Înapoi acasă</a></p>'),
                          cod=404)

        def do_GET(self):
            cale = urlparse(self.path).path
            cauta = parse_qs(urlparse(self.path).query).get("q", [""])[0]
            if cale == "/exemple" or cale.startswith("/exemple/"):
                return self._exemple(cale)
            if cale == "/":  # o cautare de pe adresa veche merge in istoric
                return self._redirect(f"/candidati?q={quote(cauta)}") if cauta else self._trimite(acasa(dosar))
            if cale == "/candidati":
                sters = parse_qs(urlparse(self.path).query).get("sters") == ["1"]
                return self._trimite(istoric(dosar, cauta, sters))
            if cale == "/nou":
                return self._trimite(nou_formular())
            if cale in ("/rapoarte", "/rapoarte/document"):
                q = parse_qs(urlparse(self.path).query)
                return self._trimite((rapoarte if cale == "/rapoarte" else document)(dosar, q))
            if cale == "/manual":
                return self._trimite(pagina("Manualul", MANUAL, activ="manual", clasa="document"))
            if m := re.fullmatch(r"/proba/([\w.-]+)/([\w.-]+)", cale):  # numai fisierele temei; cheia nu
                try:
                    pa = proba.pachet(m.group(1))
                except ValueError:
                    return self._negasit()
                if m.group(2) in {f for _, f in pa.tema}:
                    date = (pa.dosar / m.group(2)).read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", TEMA[m.group(2).rsplit(".", 1)[1]])
                    self.send_header("Content-Disposition", f'attachment; filename="{m.group(2)}"')
                    self.send_header("Content-Length", str(len(date)))
                    self.end_headers()
                    return self.wfile.write(date)
                return self._negasit()
            if cale == "/viata":
                return self._trimite("viu", "text/plain; charset=utf-8")
            if m := re.fullmatch(r"/static/([\w.-]+(?:/[\w.-]+)?)", cale):
                f = STATIC / m.group(1)
                if ".." not in m.group(1) and f.is_file() and f.suffix in TIPURI:
                    return self._trimite(f.read_bytes(), TIPURI[f.suffix])
                return self._negasit()
            if cale.startswith("/c/"):
                return self._candidat(cale, dosar)
            return self._negasit()

        def _candidat(self, cale, d, prefix=""):
            """/c/«id»/…, pe dosarul `d`. Cu `prefix` („/exemple”): un candidat din exemple, numai de citit."""
            def trimite(corp, campuri=True):
                return self._trimite(doar_de_citit(corp, campuri) if prefix else corp)
            if m := re.fullmatch(r"/c/([a-z0-9-]+)/proba/(Raspuns_[a-z0-9-]+\.xlsx)", cale):  # tabelul predat
                c = candidati.citeste(m.group(1), d)
                f = c and c["dosar"] / "Raspuns.xlsx"
                if not (f and f.exists() and m.group(2) == _tabel_predat(c)):
                    return self._negasit()
                date = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", TEMA["xlsx"])
                self.send_header("Content-Disposition", f'attachment; filename="{m.group(2)}"')
                self.send_header("Content-Length", str(len(date)))
                self.end_headers()
                return self.wfile.write(date)
            if m := re.fullmatch(r"/c/([a-z0-9-]+)(?:/(\w+))?(/intrare)?", cale):  # /intrare: legatura veche
                c = candidati.citeste(m.group(1), d)
                if not c:
                    return self._negasit()
                pas = m.group(2)
                if pas is None:
                    return self._redirect(f"{prefix}/c/{c['id']}/{candidati.pasul_curent(c)}")
                if pas in ("raport", "rezumat") and not m.group(3):
                    return trimite(raport(c, scurt=pas == "rezumat"), campuri=False)
                if pas in ("audit", "audit_scurt") and not m.group(3):
                    return trimite(audit_pagina(c, scurt=pas == "audit_scurt"), campuri=False)
                if pas == "intrebari":  # pasul de odinioara: acum e partea 4 a interviului
                    return self._redirect(f"{prefix}/c/{c['id']}/interviu#proiect")
                ecran = {"fisa": pas_fisa, "interviu": pas_interviu, "proba": pas_proba, "rezultat": pas_rezultat,
                         "sterge": pas_sterge}.get(pas)
                if pas == "rezultat" and not m.group(3):
                    mesaj = parse_qs(urlparse(self.path).query).get("candidatura", [""])[0]
                    return trimite(pas_rezultat(c, mesaj=mesaj))
                if pas in ("interviu", "proba") and not m.group(3):
                    salvat = parse_qs(urlparse(self.path).query).get("salvat", [""])[0]
                    return trimite(ecran(c, salvat=salvat if re.fullmatch(r"[\d:]{8}", salvat) else None))
                if ecran and not m.group(3):
                    return trimite(ecran(c))
            return self._negasit()

        def _exemple(self, cale):
            """„Exemple”: setul facut la primul clic (pagina de asteptare), lista, apoi paginile unui candidat."""
            if "din-nou" in parse_qs(urlparse(self.path).query):
                EXEMPLE_STARE["eroare"] = None
            if not EXEMPLE_STARE["se_reface"] and not EXEMPLE_STARE["eroare"] and not set_exemple.gata(radacina_exemple):
                reface_exemplele(radacina_exemple)
            if EXEMPLE_STARE["se_reface"] or EXEMPLE_STARE["eroare"]:
                return self._trimite(_asteapta_exemple())
            if cale == "/exemple":
                return self._trimite(exemple_lista(radacina_exemple))
            if cale.startswith("/exemple/c/"):
                return self._candidat(cale.removeprefix("/exemple"), radacina_exemple / "candidaturi", "/exemple")
            return self._negasit()

        def _de_aici(self):
            port = self.server.server_port
            gazde = {f"127.0.0.1:{port}", f"localhost:{port}"}
            origine = self.headers.get("Origin")
            return self.headers.get("Host") in gazde and (origine is None or urlparse(origine).netloc in gazde)

        def do_POST(self):
            if not self._de_aici():
                return self._trimite("Cererea nu vine de pe pagina HarnessCraft.", "text/plain; charset=utf-8", 403)
            n = int(self.headers.get("Content-Length") or 0)
            if urlparse(self.path).path == "/exemple/reface":
                reface_exemplele(radacina_exemple)
                return self._redirect("/exemple")
            if urlparse(self.path).path.startswith("/exemple/"):  # paginile exemplelor sunt numai de citit
                return self._trimite("Exemplele sunt numai de citit.", "text/plain; charset=utf-8", 403)
            if m := re.fullmatch(r"/c/([a-z0-9-]+)/proba/raspuns", urlparse(self.path).path):
                return self._raspuns(m.group(1), n)
            if m := re.fullmatch(r"/c/([a-z0-9-]+)/proba/pachet", urlparse(self.path).path):
                c = candidati.citeste(m.group(1), dosar)
                if not c:
                    return self._negasit()
                id_ = parse_qs(self.rfile.read(n).decode("utf-8")).get("pachet", [""])[-1]
                try:
                    candidati.alege_pachetul(c, id_)
                except ValueError as ex:
                    return self._trimite(pas_proba(c, eroare=str(ex)))
                return self._redirect(f"/c/{c['id']}/proba")
            if m := re.fullmatch(r"/c/([a-z0-9-]+)/proba/fisa", urlparse(self.path).path):
                c = candidati.citeste(m.group(1), dosar)
                if not c:
                    return self._negasit()
                sursa = parse_qs(self.rfile.read(n).decode("utf-8"), keep_blank_values=True).get("cod", [""])[-1]
                try:
                    candidati.analizeaza_proba(c, sursa)
                except (ValueError, RuntimeError) as ex:
                    return self._trimite(pas_proba(c, eroare=str(ex)))
                return self._redirect(f"/c/{c['id']}/proba")
            campuri = {k: v[-1] for k, v in parse_qs(self.rfile.read(n).decode("utf-8"), keep_blank_values=True).items()}
            cale = urlparse(self.path).path
            if m := re.fullmatch(r"/c/([a-z0-9-]+)/(decizia|proba/acord)", cale):
                c = candidati.citeste(m.group(1), dosar)
                if not c:
                    return self._negasit()
                decizia = m.group(2) == "decizia"
                try:
                    if decizia:
                        candidati.hotaraste_proba(c, campuri.get("decizia", ""), campuri.get("motivul", ""))
                    else:
                        candidati.consemneaza_acordul(c, campuri.get("raspuns", ""), campuri.get("data", ""),
                                                      campuri.get("cum", ""))
                except ValueError as ex:
                    if self.headers.get("X-Autosalvare"):
                        return self._trimite(json.dumps({"salvat": False, "eroare": str(ex)}), "application/json", 400)
                    if decizia:
                        return self._trimite(pas_interviu(c, eroare=str(ex)))
                    return self._trimite(pas_proba(c, eroare=str(ex), scris=campuri))
                if self.headers.get("X-Autosalvare"):
                    return self._trimite(json.dumps({"salvat": True}), "application/json")
                # dupa „da”, ecranul probei, cu invitatia; dupa „nu”, rezultatul, fara proba
                ajunge = "proba" if not decizia or campuri.get("decizia") == "da" else "rezultat"
                return self._redirect(f"/c/{c['id']}/{ajunge}")
            if m := re.fullmatch(r"/c/([a-z0-9-]+)/(finalizeaza|redeschide)", cale):
                c = candidati.citeste(m.group(1), dosar)
                if not c:
                    return self._negasit()
                (candidati.finalizeaza if m.group(2) == "finalizeaza" else candidati.redeschide)(c)
                gata = "finalizat" if m.group(2) == "finalizeaza" else "redeschis"
                return self._redirect(f"/c/{c['id']}/rezultat?candidatura={gata}")
            if m := re.fullmatch(r"/c/([a-z0-9-]+)/sterge", cale):
                c = candidati.citeste(m.group(1), dosar)
                if not c:
                    return self._negasit()
                try:
                    candidati.sterge(c, campuri.get("nume", ""))
                except ValueError as ex:
                    if candidati.citeste(c["id"], dosar):
                        return self._trimite(pas_sterge(c, eroare=str(ex)))
                    return self._trimite(istoric(dosar, eroare=str(ex)))
                return self._redirect("/candidati?sters=1")  # fara nume in adresa: ramane in istoricul browserului
            if cale == "/nou/alege":
                return self._trimite(json.dumps({"cale": alege_pe_calculator(campuri.get("fel") == "bundle")}),
                                     "application/json")
            if cale == "/nou":
                try:
                    id_ = candidati.nou(campuri.get("nume", ""), campuri.get("sursa", ""),
                                        campuri.get("demonstrativ") == "1", dosar,
                                        campuri.get("motiv_fara_cod", "") if campuri.get("fara_cod") == "1" else None)
                except ValueError as ex:
                    return self._trimite(nou_formular(campuri, str(ex)))
                return self._redirect(f"/c/{id_}/fisa")
            m = re.fullmatch(r"/c/([a-z0-9-]+)/(fisa|interviu|proba)", cale)
            c = candidati.citeste(m.group(1), dosar) if m else None
            if not c:
                return self._negasit()
            pas = m.group(2)
            if pas == "interviu" and not candidati.fisa(c) and not candidati.fara_cod(c):  # ghidul se scrie din fisa; proba nu are nevoie de ea
                return self._redirect(f"/c/{c['id']}/fisa")
            try:
                if pas == "fisa":
                    candidati.analizeaza(c)
                elif pas in ("interviu", "proba"):
                    (candidati.salveaza_interviu if pas == "interviu" else candidati.salveaza_proba)(c, campuri)
                    if self.headers.get("X-Autosalvare"):
                        return self._trimite(json.dumps({"salvat": True}), "application/json")
            except (ValueError, RuntimeError) as ex:
                if self.headers.get("X-Autosalvare"):
                    return self._trimite(json.dumps({"salvat": False, "eroare": str(ex)}), "application/json", 400)
                ecran = {"fisa": pas_fisa, "interviu": pas_interviu, "proba": pas_proba}[pas]
                return self._trimite(ecran(c, eroare=str(ex)))
            if pas in ("interviu", "proba"):
                return self._redirect(f"/c/{c['id']}/{pas}?salvat={datetime.now():%H:%M:%S}")
            return self._redirect(f"/c/{c['id']}/{pas}")

        def _raspuns(self, id_, n):
            """Tabelul de raspuns, incarcat din browser (multipart/form-data, citit cu biblioteca standard)."""
            c = candidati.citeste(id_, dosar)
            if not c:
                return self._negasit()
            if n > MAX_INCARCARE:
                return self._trimite(pas_proba(c, eroare="Fișierul e prea mare pentru un tabel de răspuns."), cod=413)
            corp = self.rfile.read(n)
            mesaj = BytesParser(policy=POLITICA_EMAIL).parsebytes(
                b"Content-Type: " + (self.headers.get("Content-Type") or "").encode() + b"\r\n\r\n" + corp)
            fisier = next((x.get_payload(decode=True) for x in (mesaj.iter_parts() if mesaj.is_multipart() else [])
                           if x.get_param("name", header="content-disposition") == "fisier"), None)
            try:
                if not fisier:
                    raise ValueError("n-ai ales niciun fișier: apeși „Alege fișierul”, apoi „Încarcă”")
                candidati.incarca_raspuns(c, fisier)
            except ValueError as ex:
                return self._trimite(pas_proba(c, eroare=str(ex)))
            return self._redirect(f"/c/{c['id']}/proba")

    return Cerere


# Ce lasa in urma o pornire veche: fereastra neagra a lui Porneste_HarnessCraft.bat si serverul din ea. Numai dupa
# program si linia de comanda: un shell care doar pomeneste fisierul (o comanda a agentului) nu se atinge.
_VECHI = {"cmd.exe": re.compile(r"Porneste_HarnessCraft\.bat", re.I),
          "python.exe": re.compile(r"-m harnesscraft\.interfata\b")}


def de_oprit(procese, eu):
    """procese: [(pid, parinte, program, linia de comanda)]. Pornirile vechi, fara mine si fara stramosii mei (fereastra
    din care am pornit, lansatorul din .venv), ca sa nu se inchida chiar pornirea de acum."""
    parinte = {p: pp for p, pp, _, _ in procese}
    ai_mei, x = set(), eu
    while x in parinte and x not in ai_mei:
        ai_mei.add(x)
        x = parinte[x]
    ai_mei.add(x)
    return [p for p, _, prog, linie in procese
            if p not in ai_mei and (tipar := _VECHI.get((prog or "").lower())) and tipar.search(linie or "")]


PS_PROCESE = ("[Console]::OutputEncoding = [Text.Encoding]::UTF8; Get-CimInstance Win32_Process | ForEach-Object { "
              "[Console]::Out.WriteLine(('{0}{4}{1}{4}{2}{4}{3}' -f $_.ProcessId, $_.ParentProcessId, $_.Name, "
              "($_.CommandLine -replace '\\s+', ' '), [char]9)) }")


def _procese():
    # Un proces pe rand, campurile despartite de Tab, scrise direct: o lista JSON intr-un singur rand de 114.000 de
    # caractere a iesit stricata cand programul a pornit din fereastra lui (din bash mergea); asa, o iesire taiata pierde
    # cel mult ultimul rand.
    r = subprocess.run(["powershell", "-NoProfile", "-Command", PS_PROCESE],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    procese = []
    for rand in r.stdout.splitlines():
        c = rand.split("\t", 3)
        if len(c) == 4 and c[0].isdigit() and c[1].isdigit():
            procese.append((int(c[0]), int(c[1]), c[2], c[3]))
    if not procese:
        raise ValueError(f"lista proceselor e goală ({r.stderr.strip()[:200]})")
    return procese


def opreste_vechi(doar_lista=False):
    """La pornire: inchide serverele si ferestrele ramase de la pornirile vechi (cerut de autor: o pornire noua le
    inchide pe cele vechi). Numai pe Windows; intoarce cate a gasit."""
    if os.name != "nt":
        return 0
    try:
        vechi = de_oprit(_procese(), os.getpid())
    except (OSError, ValueError, subprocess.SubprocessError) as ex:  # porneste oricum; un port ocupat se spune mai jos
        print(f"Nu am putut căuta pornirile vechi ale programului ({type(ex).__name__}: {ex}).")
        return 0
    if doar_lista:
        return vechi
    for p in vechi:
        # numai procesul gasit, fara copiii lui (/T): browserul pornit de un server vechi e copilul lui, iar /T inchidea
        # tot Chrome-ul autorului, cu toate ferestrele; fereastra si serverul sunt oricum fiecare in lista
        subprocess.run(["taskkill", "/F", "/PID", str(p)], capture_output=True)
    for _ in range(30):  # portul se elibereaza dupa ce moare procesul
        try:
            server().server_close()
            break
        except OSError:
            time.sleep(0.1)
    return len(vechi)


def deschide_in_browser(adresa, deschide=webbrowser.open):
    """Deschide un tab nou, apoi inchide taburile vechi ale programului (Chrome sau Edge, prin `inchide_taburi.ps1`):
    intai cel nou, ca fereastra sa nu ramana goala; altfel Chrome isi reface sesiunea si aduce tabul vechi inapoi.
    Intoarce cate taburi vechi a inchis. Fara Windows sau fara script, numai deschide."""
    if os.name != "nt":
        deschide(adresa)
        return 0
    try:
        ps = subprocess.Popen(["powershell", "-NoProfile", "-Command", (Path(__file__).parent / "inchide_taburi.ps1")
                               .read_text(encoding="utf-8")], stdout=subprocess.PIPE, text=True)
        for rand in ps.stdout:  # „pregatit”: taburile vechi sunt tinute minte
            if rand.strip() == "pregatit":
                break
        deschide(adresa)
        rest = ps.stdout.read().split()
        ps.wait(timeout=60)
        return int(rest[-1]) if rest else 0
    except (OSError, ValueError, subprocess.SubprocessError):
        deschide(adresa)
        return 0


class _Server(ThreadingHTTPServer):
    # Pe Windows, SO_REUSEADDR (pus de HTTPServer) lasa al doilea server pe un port ocupat: doua porniri ascultau
    # deodata pe 8765, iar cererile ajungeau la cea veche. Fara el, portul ocupat se vede la pornire.
    allow_reuse_address = os.name != "nt"


def server(port=PORT, **kw):
    return _Server(("127.0.0.1", port), aplicatie(**kw))


def nu_porneste(text, caseta=None):
    """Motivul pentru care programul nu porneste: in fereastra serverului, care sta micsorata in bara de jos (cerut de
    autor), si intr-o caseta pe ecran, unde se vede."""
    print(text)
    if caseta is None and os.name == "nt":
        import ctypes
        caseta = lambda x: ctypes.windll.user32.MessageBoxW(None, x, "HarnessCraft", 0x30)  # 0x30: semnul de atentie
    if caseta:
        caseta(text)
    return 1


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not shutil.which("git"):
        return nu_porneste("HarnessCraft nu poate porni: lipsește programul care citește istoricul proiectelor (git) pe acest "
                           "calculator. Vezi docs/INSTALARE.md.")
    if not shutil.which("gitleaks"):
        return nu_porneste("HarnessCraft nu poate porni: lipsește programul care caută cheile de acces în proiecte "
                           "(gitleaks) pe acest calculator. Vezi docs/INSTALARE.md, pasul 2.")
    if n := opreste_vechi():
        print(f"Am închis {n} procese rămase de la pornirile vechi (serverul și ferestrele lui).")
    try:
        s = server()
    except OSError:  # o pornire veche a scapat prima data (inchisa intre timp, sau lista n-a venit): inca o data
        opreste_vechi()
        try:
            s = server()
        except OSError:
            s = None
    if s is None:
        return nu_porneste(f"HarnessCraft nu poate porni: portul {PORT} e ocupat. Probabil programul rulează deja: "
                           f"deschide http://127.0.0.1:{PORT} în browser.")
    adresa = f"http://127.0.0.1:{PORT}"
    print(f"HarnessCraft rulează la {adresa}\nNu închide fereastra cât lucrezi; închis-o, programul se oprește.")
    if "--fara-browser" not in sys.argv:
        def browser():
            if n := deschide_in_browser(adresa):
                print("Am închis tabul vechi al programului; a rămas cel nou." if n == 1 else
                      f"Am închis {n} taburi vechi ale programului; a rămas cel nou.")
        threading.Thread(target=browser, daemon=True).start()
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
