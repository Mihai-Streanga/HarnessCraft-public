# What was measured

HarnessCraft rests on one assumption: **the traces in a person's git history tell good practice in working with AI
apart from weak practice.** If that is false, the mechanical part gives noise and the tool shrinks to an interview
guide. This page says how the assumption was tested and what came out. The per-project results are not published:
they grade real people, by name.

## How it was tested

1. **The projects.** Open-source projects with one dominant author (more than 80% of the commits), at least three
   months of history, an instruction file for the AI agent changed several times, and signs that other people use
   them. Each is pinned to an exact commit in a manifest, and a guard confirms every clone sits on that commit.
2. **The blind ranking.** Before seeing any score, the author splits the projects into a top half and a bottom half,
   by general impression of the project, not by the list of signals. The ranking is committed before any run; a
   guard stops every detector until it is committed, unchanged and complete.
3. **The comparison.** The test counts how many projects land in the same half for the author and for the tool.
   Ties at the boundary are not broken by a rule chosen afterwards: the test reports the agreement range over every
   possible split, and passes only if it passes in the worst case. A threshold may change only for the next round,
   with the reason written down, never to rescue a round that has just failed.

## Results

| What was compared | Agreement | Threshold | Verdict |
|---|---|---|---|
| a score from the state signals, first sample | 12–18 of 24 | 18 | inconclusive |
| **the project sheet (level, then score), second sample, new projects** | **10 of 12** | **10** | **passes** |
| the history signals, first sample | 12 of 24 | 18 | below threshold: chance level |
| code quality, against a separate calibration set | 8 of 12 | 10 | below threshold |

**The assumption is borne out narrowly: the sheet passes at the threshold, 10 of 12, with a single rater; the history
signals failed.** *(In Romanian, as the author states it: „adeverită îngustat: fișa trece la prag, 10 din 12, cu un
singur evaluator; istoricul a căzut”.)* The project sheet is the part the application uses. The history signals and code quality are
measured and shown in the technical view, but stay **outside the score** until a calibration passes its threshold.

## The detectors on new text

Four rounds checked the sheet's detectors on instruction files they had not seen, against verdicts given in advance (by the AI agent, at the author's decision, not by the author):
rules written in Romanian, limits put on the agent, PowerShell commands, and keys in tests and examples. Each round
had two groups: a repair was allowed only on group A, and group B ran once, after A was closed and committed.
**All four pass on group B** (the PowerShell and limits rounds 6 of 6, the keys round 5 of 6).

## The check over time

On the author's own projects, the sheet was computed at a quarter, a half, three quarters and the end of each
history. The prediction was that the first months would come out weaker than the last. The level does not fall, but
it does not rise either: **the check over time failed, on 5 projects** *(„căzută, pe 5 proiecte”)*.

## What the figures do not say

- **One rater.** The blind ranking is one person's judgement; a second rater would test the agreement itself.
- **Small samples.** 24 projects, then 12. With 12 projects, chance alone reaches 10 of 12 in 37 of the 924 possible
  splits (4%), but one project more or less on either side changes the verdict.
- **Not calibrated on candidates.** The projects are open-source, not job applicants. Weights and thresholds were
  chosen in advance; a calibrated version needs real data from whoever wants to use it.
- **A project is not a person.** The sheet reads what a project shows. The interview and the practical test are there
  because much of how someone works with AI leaves no trace in git.
