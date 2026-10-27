"""Markdown -> HTML, numai cat folosesc fisa si ghidul: titluri, liste, citate, tabele, paragrafe, **gros**, *cursiv*,
`cod`, comentarii HTML (sarite). Textul se escapeaza intai: nimic din proiectul candidatului nu ajunge ca HTML."""
import html
import re

INLINE = [(re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
          (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
          (re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"), r"<em>\1</em>")]


def inline(text):
    t = html.escape(text, quote=False)
    for tipar, inlocuire in INLINE:
        t = tipar.sub(inlocuire, t)
    return t


def data(text):
    """O data din fisiere (`2026-10-19T14:47:17`, `2026-10-19`) in forma omului: `19.10.2026, 14:47`, `19.10.2026`.
    Fisierele de date raman in forma lor; numai ecranele si rapoartele o arata asa (decizii-audit-unic.md, B9)."""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::\d{2})?)?", (text or "").strip())
    if not m:
        return text or ""
    zi = f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return f"{zi}, {m.group(4)}:{m.group(5)}" if m.group(4) else zi


def html_din(md):
    rez, lista, tabel = [], False, []

    def inchide():
        nonlocal lista, tabel
        if lista:
            rez.append("</ul>")
            lista = False
        if tabel:
            rez.append(_tabel(tabel))
            tabel = []

    for rand in md.splitlines():
        r = rand.rstrip()
        if r.startswith("|"):
            if lista:
                rez.append("</ul>")
                lista = False
            tabel.append(r)
            continue
        if r.startswith("- "):
            if tabel:
                rez.append(_tabel(tabel))
                tabel = []
            if not lista:
                rez.append("<ul>")
                lista = True
            rez.append(f"<li>{inline(r[2:])}</li>")
            continue
        inchide()
        if not r or r.startswith("<!--"):
            continue
        if m := re.match(r"^(#{1,6})\s+(.*)$", r):
            n = min(len(m.group(1)) + 1, 6)  # h1 e titlul paginii
            rez.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif r.startswith("> "):
            rez.append(f"<blockquote>{inline(r[2:])}</blockquote>")
        else:
            rez.append(f"<p>{inline(r)}</p>")
    inchide()
    return "\n".join(rez)


def _tabel(randuri):
    celule = [[c.strip() for c in r.strip("|").split("|")] for r in randuri
              if not re.fullmatch(r"\|[\s:|-]+\|", r)]
    if not celule:
        return ""
    cap, *corp = celule
    return ("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cap) + "</tr></thead><tbody>" +
            "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in corp) +
            "</tbody></table>")
