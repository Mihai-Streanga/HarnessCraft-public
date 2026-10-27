"""Cititorii fisierelor de instructiuni pentru agent, cate unul pe conventie.

De ce: uneltele candidatilor sunt piese inlocuibile (principiul 9). Fiecare cititor stie
numai cum arata conventia lui; semnalele primesc `FisierInstructiuni` si nu stiu din ce
unealta a venit. Arealul e inchis (SPEC, „Revizuiri de intenție”): si alte unelte; aici sunt cele trei
conventii numite in SPEC. O conventie noua e un cititor nou, nu o ramura in semnal, numai cand o aduce un candidat.
"""
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from harnesscraft.manifest import git


def _nume(cale):
    return PurePosixPath(cale).name.lower()


def claude(cale):
    return _nume(cale) == "claude.md"


def agents(cale):
    return _nume(cale) == "agents.md"


def cursor(cale):
    p = "/" + cale
    return "/.cursor/rules/" in p or _nume(cale) == ".cursorrules"


CONVENTII = {"claude": claude, "agents": agents, "cursor": cursor}


def conventia(cale):
    for nume, potriveste in CONVENTII.items():
        if potriveste(cale):
            return nume
    return None


@dataclass
class FisierInstructiuni:
    cale: str                       # calea la HEAD
    conventie: str
    commits: list = field(default_factory=list)   # commit-urile care l-au atins, vechi -> nou

    @property
    def modificari(self):
        """Commit-urile de dupa creare."""
        return self.commits[1:]


def gaseste(depozit, commits, rev="HEAD"):
    """Fisierele de instructiuni existente la `rev`, fiecare cu istoricul lui, peste redenumiri."""
    la_head = git(depozit, "-c", "core.quotepath=false", "ls-tree", "-r", "--name-only", rev).splitlines()
    # mergem de la nou la vechi; `urmarite` leaga calea de atunci de calea de la HEAD
    urmarite = {c: c for c in la_head if conventia(c)}
    istoric = {c: [] for c in urmarite}
    for commit in reversed(commits):
        for f in commit.fisiere:
            if f.cale in urmarite:
                final = urmarite[f.cale]
                istoric[final].append(commit)
                if f.stare == "R" and f.cale_veche:
                    del urmarite[f.cale]
                    urmarite[f.cale_veche] = final
                elif f.stare == "A":
                    del urmarite[f.cale]
    return [FisierInstructiuni(c, conventia(c), list(reversed(istoric[c]))) for c in sorted(istoric)]
