"""Cititorul de istoric git: commit, autor, e-mail, data, mesaj, fisiere atinse.

De ce: toate semnalele de istoric si atribuirea pornesc de aici; un singur parser, cu
gardian de completitudine pe alta cale (`git rev-list --count`), ca un commit pierdut la
parsare sa nu treaca neobservat (SPEC, „Zonele”, atribuirea).

Commit-urile de merge nu intra: inregistreaza o integrare, nu autorat.
"""
from dataclasses import dataclass, field

from harnesscraft.manifest import git

SEP_COMMIT, SEP_CAMP = "\x1e", "\x1f"
FORMAT = SEP_COMMIT + SEP_CAMP.join(["%H", "%an", "%ae", "%aI", "%B"]) + SEP_CAMP


@dataclass
class Fisier:
    stare: str          # A, M, D, R (redenumire), C (copie), T
    cale: str
    cale_veche: str | None = None


@dataclass
class Commit:
    sha: str
    autor: str
    email: str
    data: str           # ISO 8601, data autorului
    mesaj: str
    fisiere: list[Fisier] = field(default_factory=list)

    @property
    def titlu(self):
        return self.mesaj.split("\n", 1)[0]


def _fisiere(bloc):
    out = []
    for linie in bloc.strip("\n").splitlines():
        if not linie.strip():
            continue
        parti = linie.split("\t")
        stare = parti[0][0]
        if stare in "RC" and len(parti) == 3:
            out.append(Fisier(stare, parti[2], parti[1]))
        else:
            out.append(Fisier(stare, parti[-1]))
    return out


def citeste(depozit, rev="HEAD"):
    """Commit-urile accesibile din `rev`, fara merge-uri, de la cel mai vechi la cel mai nou."""
    iesire = git(depozit, "-c", "core.quotepath=false", "log", "--no-merges", "--reverse",
                 "-M", "--name-status", f"--format={FORMAT}", rev)
    commits = []
    for bucata in iesire.split(SEP_COMMIT)[1:]:
        sha, autor, email, data, mesaj, rest = bucata.split(SEP_CAMP, 5)
        commits.append(Commit(sha, autor, email, data, mesaj.strip(), _fisiere(rest)))
    return commits


def gardian_completitudine(depozit, commits, rev="HEAD"):
    """Numara pe alta cale decat parserul. Intoarce mesajul abaterii sau None."""
    n = int(git(depozit, "rev-list", "--count", "--no-merges", rev).strip())
    if n != len(commits):
        return f"parserul a citit {len(commits)} commit-uri, git rev-list numara {n}"
    return None
