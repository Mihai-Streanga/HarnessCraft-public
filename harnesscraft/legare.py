"""Intrebarea de legare: un commit al proiectului, ales dupa o regula fixa, pe care candidatul il explica.

De ce: un proiect care trece toate verificarile fisei nu primea nicio intrebare despre el, iar intrebarile din goluri
intreaba de ce lipseste ceva, nu daca omul a construit ce exista.
Regula, incercata pe cele 36 de proiecte ale esantioanelor (verdictele autorului):
ultimul commit, fara imbinari, care e mai ales despre regulile pentru agent; daca nu e niciunul, commit-ul care a
creat fisierul de reguli. Fara nota, fara model.
"""
from harnesscraft.instructiuni import conventia
from harnesscraft.manifest import git

MAX_FISIERE_REGULI = 3   # peste atat e o schimbare in masa, nu o regula scrisa
MIN_RANDURI = 3          # sub atat e o corectura, nu o regula


def _commits(depozit, rev):
    """[(sha, data, autor, mesaj, [(cale, randuri adaugate)])], de la nou la vechi, fara imbinari."""
    log = git(depozit, "-c", "core.quotepath=false", "log", "--no-merges", "--format=@%H|%ad|%an|%s", "--date=short",
              "--numstat", rev)
    r = []
    for rand in log.splitlines():
        if rand.startswith("@"):
            r.append((*rand[1:].split("|", 3), []))
        elif rand.strip() and r:
            plus, _, cale = rand.split("\t", 2)
            r[-1][4].append((cale.split(" => ")[-1].rstrip("}"), int(plus) if plus != "-" else 0))
    return r


def alege(depozit, rev="HEAD"):
    """Commit-ul intrebarii de legare, sau None cand proiectul n-are reguli pentru agent."""
    commits = _commits(depozit, rev)
    for sha, data, autor, mesaj, fisiere in commits:
        reguli = [(c, n) for c, n in fisiere if conventia(c)]
        if (reguli and 2 * len(reguli) >= len(fisiere) and len(reguli) <= MAX_FISIERE_REGULI
                and sum(n for _, n in reguli) >= MIN_RANDURI):
            fel, cale = "schimbare", max(reguli, key=lambda x: x[1])[0]
            break
    else:
        create = [(c, x) for x in reversed(commits) for c, n in x[4] if conventia(c)]
        if not create:
            return None
        cale, (sha, data, autor, mesaj, fisiere) = create[0]
        fel = "creare"
    return {"commit": sha[:7], "data": data, "autor": autor, "mesaj": mesaj, "fisier": cale, "fel": fel,
            "fisiere": len(fisiere)}
