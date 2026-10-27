"""Contractul de module (principii/Principii.md, §2; rapoarte/decizii-audit-unic.md, B6): calculul nu importa
ecranul si dosarele; numai `capturi` importa `interfata`."""
import ast
from pathlib import Path

PACHET = Path(__file__).resolve().parent.parent / "harnesscraft"
# cine are voie sa importe fiecare modul de sus
VOIE = {"interfata": {"capturi"}, "candidati": {"interfata", "set_exemple", "capturi"}}


def _importuri(fisier: Path) -> set[str]:
    gasite = set()
    for nod in ast.walk(ast.parse(fisier.read_text(encoding="utf-8"))):
        if isinstance(nod, ast.ImportFrom):
            if nod.module and nod.module.startswith("harnesscraft."):
                gasite.add(nod.module.split(".")[1])
            elif nod.module in (None, "harnesscraft") or nod.level:
                gasite.update(a.name.split(".")[0] for a in nod.names)
                if nod.module and nod.level:
                    gasite.add(nod.module.split(".")[0])
        elif isinstance(nod, ast.Import):
            gasite.update(a.name.split(".")[1] for a in nod.names if a.name.startswith("harnesscraft."))
    return gasite


def test_calculul_nu_importa_ecranul_si_dosarele():
    calcate = [(f.stem, sus) for f in PACHET.glob("*.py") for sus, voie in VOIE.items()
               if f.stem != sus and f.stem not in voie and sus in _importuri(f)]
    assert calcate == []


def test_plasa_vede_importurile_de_azi():
    assert "interfata" in _importuri(PACHET / "capturi.py")
    assert "candidati" in _importuri(PACHET / "interfata.py")
