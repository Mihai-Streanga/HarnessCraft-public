# HarnessCraft — instructions for Claude Code

A local web application that helps a recruiter assess how a candidate works with AI: a portfolio project read from
its git history, a structured interview, a practical test, a total out of 100. A demonstration prototype, not
calibrated. Code comments, docstrings and the interface are in Romanian; keep new ones in Romanian.

## Map

| path | what it holds |
|---|---|
| `harnesscraft/interfata.py` | the local server and every page; it calls the modules below and computes nothing itself |
| `harnesscraft/pasi.py`, `candidati.py` | the steps (the same for a button and a terminal command), one folder per candidate |
| `harnesscraft/istoric.py`, `instructiuni.py` | the readers: git history, instruction files (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules`) |
| `harnesscraft/stare.py`, `harness.py` | the detectors: facts found in the analysed tree and in the instruction files |
| `harnesscraft/fisa.py`, `tintite.py` | the project sheet (16 checks, 4 levels) and the questions about the project |
| `harnesscraft/interviu.py`, `proba.py`, `total.py` | the interview guide and its marks, the practical test, the total |
| `harnesscraft/audit.py` | the candidate's journal, from which the audit report is read |
| `harnesscraft/termeni.py` | the technical terms allowed on a recruiter's screen, only in brackets |
| `proba/«package»/` | a test package: task files, answer key, its fingerprint |
| `exemple-candidati/` | the worked examples; `set_exemple.py` rebuilds them, `capturi.py` takes the manual's screenshots |
| `tests/date/` | approved texts, fixed character by character |
| `docs/ARCHITECTURE.md` | how the parts fit together |

## Commands

```bat
.venv\Scripts\python -m pip install pytest
.venv\Scripts\python -m pytest -q
Porneste_HarnessCraft.bat
.venv\Scripts\python -m harnesscraft studiu «project path»
.venv\Scripts\python -m harnesscraft interviu «project path» > guide.md
```

Tests build synthetic git repositories while they run and need git and gitleaks on `PATH`. Tests marked `privat` need
files kept in the author's private repository and are **skipped with their reason** here; keep that for any new test
that needs them.

## Invariants

None of these is broken without a written reason.

- **No model gives a verdict.** Every level, point, mark and total is computed by code from written rules; the
  program calls no AI model. A person's judgement (ticks, the test decision, the conclusion) is the recruiter's.
- **The interface computes nothing.** A button and a terminal command call the same function in the calculation
  modules.
- **The result is computed every time it is opened**, from the files. No stored result, no recalculate button.
- **An approved text changes only with its fixed copy in `tests/date/`.** The interview questions and the test ticks
  carry fingerprints; a guide is scored only with the questions it was written with.
- **The answer key is used only with its committed fingerprint** and is never served to the browser.
- **Nothing leaves the computer.** The server binds `127.0.0.1`, checks *Host* and *Origin*, and calls no service.
  Candidates' data stays in `candidaturi/`, which git ignores.
- **The journal only grows.** Every step appends a line; nothing rewrites it.
- **A technical term on a recruiter's screen appears only in brackets, after a plain explanation.** A new term goes
  into `termeni.py` first; the tests require it.
