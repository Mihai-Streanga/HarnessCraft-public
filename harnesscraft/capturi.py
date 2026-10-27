"""Capturile de ecran din manual.

Aplicatia porneste in acest proces, pe alt port decat 8765 (instanta deschisa a recrutorului ramane), pe setul
exemplelor (tmp-set-exemple/); Chrome-ul instalat, prin Playwright, face cate o captura pentru fiecare ecran din
„Ecranele și butoanele” (interfata.CAPTURI_MANUAL). candidaturi/ nu se atinge: o pagina pe care apare un nume de acolo
opreste rularea, fara imagini.

Ruleaza cu Python-ul sistemului, unde e Playwright, nu din .venv: aplicatia nu primeste nicio dependenta.
    py -m harnesscraft.capturi              face capturile si scrie capturi.json (commitul la care s-au facut)
    py -m harnesscraft.capturi --verifica   spune daca ecranele s-au schimbat de atunci, deci daca se refac;
                                            inaintea copiei publice, nu in suita de teste (ar cadea la orice schimbare)
"""
import io
import json
import subprocess
import sys
import threading
from datetime import date

from harnesscraft import candidati, interfata, set_exemple

PORT = 8790
DOSAR = interfata.STATIC / "manual"
JURNAL = DOSAR / "capturi.json"
RADACINA = interfata.STATIC.parents[1]
# codul ecranelor: o schimbare aici dupa capturi le poate face vechi
COD_ECRANE = ("harnesscraft/interfata.py", "harnesscraft/static/stil.css", "harnesscraft/static/app.js")
CANDIDAT = "ioana-vladescu"  # tipul 4: toate cele trei parti, cu verificari trecute si picate
LATIME, INALTIME = 1280, 900  # ce vede recrutorul cand deschide ecranul, nu pagina intreaga
# fisierul: (pagina, ce se face inainte de captura: un clic, sau elementul adus sus, sub marginea paginii)
PAGINI = {
    "acasa": ("/", None),
    "candidati": ("/candidati", None),
    "nou": ("/nou", None),
    "portofoliul": (f"/c/{CANDIDAT}/fisa", None),
    "interviul": (f"/c/{CANDIDAT}/interviu", ("sus", "h4")),  # prima intrebare, cu bifele ei
    "proba": (f"/c/{CANDIDAT}/proba", None),
    "rezultatul": (f"/c/{CANDIDAT}/rezultat", None),
    "raport": (f"/c/{CANDIDAT}/raport", None),
    "rapoarte": ("/rapoarte", None),
    "audit": (f"/c/{CANDIDAT}/audit", None),
    "exemple": ("/exemple", None),
    "cum-folosesc": (f"/c/{CANDIDAT}/interviu", ("clic", ".buton-info")),
}


def _git(*a):
    return subprocess.run(["git", *a], cwd=RADACINA, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def _nume_de_ascuns():
    """Numele candidatilor recrutorului care nu sunt si in set (autorul e in amandoua)."""
    din_set = {c["nume"] for c in candidati.lista(set_exemple.SET / "candidaturi")}
    return sorted({c["nume"] for c in candidati.lista()} - din_set)


def _micsoreaza(png):
    """PNG cu paleta: un ecran are putine culori, iar imaginea scade de cateva ori; fara Pillow, ramane cum e."""
    try:
        from PIL import Image
    except ImportError:
        return png
    iesire = io.BytesIO()
    Image.open(io.BytesIO(png)).convert("RGB").quantize(256).save(iesire, "PNG", optimize=True)
    return iesire.getvalue()


def fa():
    if set(PAGINI) != {f for f, _ in interfata.CAPTURI_MANUAL.values()}:
        sys.exit("Capturile din manual (interfata.CAPTURI_MANUAL) și paginile de aici nu sunt aceleași.")
    if not set_exemple.gata():
        sys.exit("Setul exemplelor lipsește: întâi py -m harnesscraft set-exemple.")
    if schimbate := _git("status", "--porcelain", "--", *COD_ECRANE):
        sys.exit(f"Codul ecranelor are schimbări necomise:\n{schimbate}\nÎntâi commit: capturi.json ține commitul.")
    ascunse = _nume_de_ascuns()
    from playwright.sync_api import sync_playwright
    s = interfata.server(port=PORT, dosar=set_exemple.SET / "candidaturi")
    threading.Thread(target=s.serve_forever, daemon=True).start()
    imagini = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")  # Chrome-ul instalat: Playwright fara browserul lui
            pagina = browser.new_page(viewport={"width": LATIME, "height": INALTIME})
            for fisier, (cale, actiune) in PAGINI.items():
                pagina.goto(f"http://127.0.0.1:{PORT}{cale}", wait_until="networkidle")
                if gasite := [n for n in ascunse if n in pagina.content()]:
                    sys.exit(f"{cale}: apare un candidat din candidaturi/ ({len(gasite)}); nicio captură scrisă.")
                if actiune and actiune[0] == "clic":
                    pagina.click(actiune[1])
                elif actiune:
                    pagina.locator(actiune[1]).first.evaluate(
                        "e => window.scrollTo(0, e.getBoundingClientRect().top + window.scrollY - 24)")
                pagina.evaluate("document.fonts.ready")
                imagini[fisier] = _micsoreaza(pagina.screenshot())
            browser.close()
    finally:
        s.shutdown()
        s.server_close()
    DOSAR.mkdir(exist_ok=True)
    for fisier, png in imagini.items():
        (DOSAR / f"{fisier}.png").write_bytes(png)
    JURNAL.write_text(json.dumps({"commit": _git("rev-parse", "--short", "HEAD"), "data": date.today().isoformat(),
                                  "candidat": CANDIDAT, "imagini": sorted(imagini)}, ensure_ascii=False, indent=1) + "\n",
                      encoding="utf-8")
    total = sum(map(len, imagini.values()))
    print(f"{len(imagini)} capturi în {DOSAR.relative_to(RADACINA)}, {total / 1e6:.2f} MB, la commitul "
          f"{_git('rev-parse', '--short', 'HEAD')}.")
    return 0


def verifica():
    """0: ecranele n-au schimbari de la capturi; 1: s-au schimbat (se spune ce), capturile se refac."""
    if not JURNAL.exists():
        print("Capturile nu sunt făcute: py -m harnesscraft.capturi.")
        return 1
    facute = json.loads(JURNAL.read_text(encoding="utf-8"))["commit"]
    if schimbate := _git("diff", "--name-only", facute, "--", *COD_ECRANE):
        print(f"Ecranele s-au schimbat de la capturi (commitul {facute}):\n{schimbate}\n"
              "Refă-le: py -m harnesscraft.capturi.")
        return 1
    print(f"Capturile sunt la zi: codul ecranelor e cel de la commitul {facute}.")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(verifica() if "--verifica" in sys.argv else fa())
