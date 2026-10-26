# Week 7 Writeup: Agent Orchestration (Recipe Box Sprint)

**Mohanad Kadadou (2309115218).** Orchestrator: Claude Code (Claude Sonnet 5.5) running sub-agents through its Agent tool, not Antigravity's Agent Manager. Every agent is a Claude subagent; "two agents" means two separately prompted contexts, not two different models. Final state: `main` with 55 passing tests, ruff clean.

## Part I: two agents in parallel, in worktrees
**Tasks:** (A) tag filter `GET /recipes?tag=` (task 2) and (B) shopping list `GET /shopping-list?ids=` (task 1). Both touch `main.py` and `test_main.py`, which made them a real collision test.
```bash
git worktree add ../week7-wt-tag-filter     -b task-tag-filter
git worktree add ../week7-wt-shopping-list  -b task-shopping-list
```
Both agents were launched **in the same message, in the background**, at 12:19:38 and each committed on its own branch at 12:19:59 (identical commit timestamps in `git log`: `c286f3b` and `cc08761`, both children of `5a8af79`). Neither was told what the other was doing except that another agent shared the repo.

**How collisions were avoided:**
- *Filesystem isolation:* each agent worked only inside its own worktree (the prompt named the one directory it may touch and forbade the others); a shared virtualenv was used read-only. `recipes.db` lives next to `main.py`, so each worktree had its **own database file**: the agents could not clobber each other's data.
- *Git isolation:* each agent owned one branch; no push, merge, rebase or branch switching.
- *Late integration by one human-supervised step:* I merged `task-tag-filter` (fast-forward-like) then `task-shopping-list`.

**Collisions and risks that actually happened:**
1. `main.py` auto-merged (different regions: one edited `list_recipes`, one appended a new endpoint).
2. `test_main.py` had an **append/append conflict** (both agents appended tests at end of file): resolved by hand, keeping both groups (merge commit `d2e5586`). Both agents had predicted exactly this in their reports.
3. A latent risk neither agent saw: a helper name (`_make`) and shared mutable state. Within a worktree, tests shared one persistent `recipes.db`, so the tag-filter tests passed once and failed on the second run (leftover rows). This surfaced later in Part II and was fixed with an isolated per-test database fixture.

## Part II: generator-critic loop (task 3, ingredient scaling)
Worktree `week7-wt-scaling`, branch `task-scaling`. The critic was **read-only** (it could run tests and throwaway snippets but not edit), was given a rubric (correctness, tests, clarity, scored 1-5) and had to end with `VERDICT: SIGN-OFF` or `REVISE`. Full verbatim transcripts: [`docs/generator-critic/`](docs/generator-critic).

| Round | Generator | Critic (scores C/T/Cl) | Verdict |
|---|---|---|---|
| 1 | first version: fractions, mixed numbers, 10 tests | 2/3/4. Real bugs: `factor=1e308` gives HTTP 500; small factors round to "0 g"; ranges and "3/0" half-scaled ("1-2 tbsp" -> "2-2 tbsp"); ".5 tsp" ignored; weak tests; suite depends on shared DB | **REVISE** |
| 2 | bounded factor, one robust regex, significant-figure rounding, 20 parametrised tests, per-test DB fixture (41 tests) | 3/4/4. Verified all round-1 fixes, then found a **new BLOCKER the revision introduced**: a zero quantity ("0 g salt") crashes `math.log10(0)` -> HTTP 500 for the whole recipe; unicode fractions half-scaled ("2 ½" -> "4 ½"); "2xlarge" scaled | **REVISE** |
| 3 | zero handled, vulgar fractions untouched, dimension-like text pinned, same-class sweep ("1/2/3"), rounding documented (55 tests) | 5/5/4. Re-ran every reproduction, fuzzed 500k random strings: no exceptions; only exotic NITs left ("1e3 g") | **SIGN-OFF** |

So the loop ran **two full revision rounds** before sign-off; the critic's round-2 finding is a good argument for the pattern: the generator's own tests and self-review missed a crash that a hostile reader found in minutes. I did not coach the critic to be harsh; the prompt required sign-off only if no real defect was found, and I re-ran the suite and ruff in the worktree myself after round 3 (55 passed) instead of trusting the report.

## Autonomy levels and supervision
| Agent | Allowed | Forbidden | Supervision |
|---|---|---|---|
| A / B (parallel workers) | edit `main.py`, `test_main.py`; run pytest/ruff; `git add`/`commit` in own worktree | push, merge, rebase, branch switching, touching other worktrees | I read each report, re-ran tests, resolved the merge conflict myself |
| Generator (rounds 1-3) | same, plus read exactly one outside file (the critic's report) | anything else outside its worktree | I verified each commit's tests/ruff in the worktree |
| Critic | read, `git show/diff`, run tests and throwaway `python -c` | any file write, any git write | report is data; verdict acted on only after my own re-run |

Honest limits: the "autonomy" boundaries were enforced by prompt instructions, not by tool permissions (the critic could technically have written files; it did not); the critic and generator are the same underlying model, so shared blind spots are possible (the fuzzing helped); in round 3 the generator reported one process slip (a failing test it amended before finishing).

## What I learned
Parallel agents are cheap if the work is partitioned by files or regions, but "independent" tasks still collide at the seams (here, two appends to one test file), so isolation (worktrees, separate DB files) buys safety while integration stays a deliberate human step. The generator-critic loop earned its cost: separating the writer from a read-only reviewer with a rubric and a mandatory verdict found a crash on the second pass that the writer introduced while fixing the first, and requiring explicit sign-off made "done" something measurable. The weak point is trust: every agent report is a claim, so I re-ran the checks myself, and the strongest improvement to the loop would be giving the critic tools the generator cannot influence (fuzzers, a clean database), which is what made round 3 convincing.
