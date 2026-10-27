"""Depozite git sintetice, construite in test (SPEC, „Zonele”: fisiere de proba stricate anume)."""
import os
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

PRIVAT = os.path.isdir(os.path.join(os.path.dirname(__file__), "..", ".claude"))


def pytest_collection_modifyitems(items):
    """In copia publica (fara `.claude/`) testele `privat` se sar, cu motivul spus; in depozitul privat ruleaza toate."""
    if PRIVAT:
        return
    sari = pytest.mark.skip(reason="cere fisiere care raman in depozitul privat (principiile, esantioanele)")
    for item in items:
        if item.get_closest_marker("privat"):
            item.add_marker(sari)


class Depozit:
    def __init__(self, cale):
        self.cale = cale
        cale.mkdir(parents=True, exist_ok=True)
        self._git("init", "--quiet", "-b", "main")
        self._git("config", "commit.gpgsign", "false")
        self.n = 0

    def _git(self, *args, env=None):
        r = subprocess.run(["git", "-C", str(self.cale), *args], capture_output=True, text=True,
                           encoding="utf-8", env=env)
        if r.returncode:
            raise RuntimeError(r.stderr)
        return r.stdout

    def commit(self, mesaj, fisiere, autor="Ana Pop", email="ana@exemplu.ro", data=None):
        """`fisiere`: {cale: continut}; continut None sterge fisierul."""
        self.n += 1
        for rel, continut in fisiere.items():
            p = self.cale / rel
            if continut is None:
                self._git("rm", "--quiet", rel)
                continue
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(continut, encoding="utf-8")
            self._git("add", rel)
        if data is None:  # o zi pe commit, de la 1 ianuarie 2026
            data = (datetime(2026, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=self.n - 1)).isoformat()
        env = dict(os.environ, GIT_AUTHOR_NAME=autor, GIT_AUTHOR_EMAIL=email,
                   GIT_COMMITTER_NAME=autor, GIT_COMMITTER_EMAIL=email,
                   GIT_AUTHOR_DATE=data, GIT_COMMITTER_DATE=data)
        self._git("commit", "--quiet", "--allow-empty", "-m", mesaj, env=env)
        return self._git("rev-parse", "HEAD").strip()


@pytest.fixture
def depozit(tmp_path):
    return lambda nume="d": Depozit(tmp_path / nume)
