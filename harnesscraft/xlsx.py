"""Un .xlsx cu o singura foaie, scris si citit numai cu biblioteca standard.

Un .xlsx e o arhiva zip cu cateva fisiere XML. Scrierea pune textul direct in celula (inlineStr) si ingroasa
primul rand; citirea intelege si textele comune (sharedStrings), cum salveaza Excel. Destul pentru statul probei
si pentru tabelul de raspuns al candidatului; formule, stiluri si mai multe foi nu se citesc.
"""
import re
import zipfile
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

_TIPURI = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""
_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
_WB_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
_STILURI = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border/></borders>
<cellStyleXfs count="1"><xf/></cellStyleXfs>
<cellXfs count="3"><xf/><xf fontId="1" applyFont="1"><alignment wrapText="1" vertical="top"/></xf><xf><alignment wrapText="1" vertical="top"/></xf></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def litera(i):
    """0 -> A, 25 -> Z, 26 -> AA."""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _celula(ref, v, stil):
    s = f' s="{stil}"' if stil else ""
    if v is None or v == "":
        return ""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return f'<c r="{ref}" t="inlineStr"{s}><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'
    return f'<c r="{ref}"{s}><v>{v}</v></c>'


def scrie(cale, randuri, foaie="Foaie1", latimi=None, text_lung=()):
    """randuri: liste de valori; primul rand e capul de tabel, ingrosat. text_lung: coloanele cu text pe mai multe randuri."""
    linii = []
    for r, rand in enumerate(randuri, start=1):
        celule = "".join(_celula(f"{litera(c)}{r}", v, 1 if r == 1 else (2 if c in text_lung else 0))
                         for c, v in enumerate(rand))
        linii.append(f'<row r="{r}">{celule}</row>')
    cols = ""
    if latimi:
        cols = "<cols>" + "".join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>'
                                  for i, w in enumerate(latimi)) + "</cols>"
    foaia = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
             f'</sheetView></sheetViews>{cols}<sheetData>{"".join(linii)}</sheetData></worksheet>')
    carte = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
             'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
             f'<sheets><sheet name="{escape(foaie)}" sheetId="1" r:id="rId1"/></sheets></workbook>')
    with zipfile.ZipFile(cale, "w", zipfile.ZIP_DEFLATED) as z:
        # data fixa: aceleasi date dau aceiasi octeti, deci aceeasi amprenta
        for nume, text in [("[Content_Types].xml", _TIPURI), ("_rels/.rels", _RELS), ("xl/workbook.xml", carte),
                           ("xl/_rels/workbook.xml.rels", _WB_RELS), ("xl/styles.xml", _STILURI),
                           ("xl/worksheets/sheet1.xml", foaia)]:
            z.writestr(zipfile.ZipInfo(nume, (2026, 1, 1, 0, 0, 0)), text.encode("utf-8"), zipfile.ZIP_DEFLATED)
    return cale


def _coloana(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


def _numar(t):
    x = float(t)
    return int(x) if x.is_integer() else x


def citeste(cale):
    """Prima foaie, ca lista de randuri (liste de valori: text, numar sau None)."""
    with zipfile.ZipFile(cale) as z:
        nume = z.namelist()
        comune = []
        if "xl/sharedStrings.xml" in nume:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si"):
                comune.append("".join(t.text or "" for t in si.iter(NS + "t")))
        foi = sorted(n for n in nume if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
        foaia = ET.fromstring(z.read(foi[0]))
    randuri = []
    for row in foaia.iter(NS + "row"):
        rand = {}
        for c in row.iter(NS + "c"):
            tip, v = c.get("t"), c.find(NS + "v")
            if tip == "inlineStr":
                val = "".join(t.text or "" for t in c.iter(NS + "t"))
            elif v is None or v.text is None:
                continue
            elif tip == "s":
                val = comune[int(v.text)]
            elif tip in ("str", "e"):
                val = v.text
            elif tip == "b":
                val = v.text == "1"
            else:
                val = _numar(v.text)
            rand[_coloana(c.get("r"))] = val
        randuri.append([rand.get(i) for i in range(max(rand) + 1)] if rand else [])
    return randuri
