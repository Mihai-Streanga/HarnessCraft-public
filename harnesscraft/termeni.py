"""Termenii tehnici in textul pentru recrutor: fisa, manualul, ajutorul ecranelor, raportul.

Regula (CLAUDE.md, „Cum se scrie”): un termen tehnic apare numai in paranteza, dupa explicatia lui. Un termen nou
intra intai aici, in `TERMENI`; testele trec prin toate ecranele recrutorului si cad la un termen in afara parantezei.
Plasa prinde si un cuvant nou care arata englezeste (w, k, y, q, sh, th, -ing, -ll, -ss): el intra fie in `TERMENI`,
fie in `ACCEPTATE`, cu decizie, nu din intamplare. Ce nu prinde: un termen fara literele acestea (de pilda „merge”).
"""
import re

# termenii stiuti: numai in paranteza, dupa explicatie; „git” si „comis” / „necomis” (din commit), de la /utilizare
TERMENI = re.compile(r"\bCI\b|(?i:\b(hook|commit|skill|subagen|scoped|fals-pozitiv|harness(?!craft)|cicatric|porți|"
                     r"principi|pull request|workflow|token|prompt de sistem|gitleaks|git\b|(?:ne)?comis(?:ă|e|i)?\b))")
# cuvinte care arata englezeste, dar le stie oricine foloseste un calculator; numele uneltei
ACCEPTATE = {"github", "gitlab", "windows", "browser", "browserul", "browserului", "link", "linkul", "linkuri", "linkurile",
             "harnesscraft", "porneste_harnesscraft"}
PLASA = re.compile(r"[wkyq]|sh|th|ing$|ll$|ss$")


def fara_paranteze(text):
    return re.sub(r"\([^)]*\)", "", text)


def neexplicate(text):
    """Termenii in afara parantezei si cuvintele noi prinse de plasa, nedeclarate."""
    t = fara_paranteze(text)
    rau = [m.group(0) for m in TERMENI.finditer(t)]
    rau += [w for w in re.findall(r"\b[A-Za-z][A-Za-z_\-]{2,}\b", t)
            if PLASA.search(w.lower()) and w.lower() not in ACCEPTATE and not TERMENI.search(w)]
    return sorted(set(rau))
