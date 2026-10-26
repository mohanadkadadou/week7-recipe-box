# Round 1: CRITIC (read-only) verdict: REVISE
Rubric: correctness, tests, clarity (1-5 each, file:line evidence). The critic could run tests and throwaway snippets but not edit.

Critic report (verbatim):
> Review of commit 42769e3 (task-scaling). Ruff is clean. pytest: 18 passed, 2 failed, identical on two consecutive runs; the failures are the existing tag-filter tests (test_main.py:~40-60), not the new scaling tests. Pre-existing cause: the shared on-disk recipes.db (main.py:26), so tests depend on database contents.
>
> 1. SHOULD-FIX (BLOCKER-grade bug) main.py:125 and :141. A huge factor crashes with HTTP 500. `float(Fraction)` raises OverflowError. Reproduced with `factor=1e308` on "200 g flour": unhandled OverflowError traceback. Fix: add an upper bound such as `Query(gt=0, le=1000)`, or format without float. Add a test for the cap and a 422 on `factor=1e308`.
> 2. SHOULD-FIX main.py:125. A small factor silently destroys quantities: "0.001 g x" at 0.5 becomes "0 g x", and "1 pinch" at 0.001 becomes "0 pinch". Fix: keep significant figures (e.g. `f"{x:.3g}"`), or enforce a minimum factor and 422 below it. Add a test.
> 3. SHOULD-FIX main.py:105-107 and :115. Malformed quantities are mangled rather than left alone: "3/0 x" at factor 2 becomes "6/0 x"; "1/2-1 cup" becomes "2/2-1 cup"; "1-2 tbsp" becomes "2-2 tbsp" (lower bound scaled, upper not); "1 to 2" becomes "2 to 2"; "1,5 l" becomes "2,5 l"; "1. egg" becomes "2. egg"; "2x3" becomes "4x3". Fix: after the number require a boundary (`(?=\s|[A-Za-z]|$)`), reject a following `/`, `-`, `,` or `.digit`, return None for a zero denominator. Scaling only half a range is the worst of these: scale both ends or leave unchanged.
> 4. SHOULD-FIX main.py:114. ".5 tsp" is not scaled and silently returned unchanged. Unicode fractions such as "½ cup" are ignored. Fix: `\d*\.?\d+` for the leading-dot case, and document the unicode limitation.
> 5. SHOULD-FIX test_main.py:129. `test_scaled_factor_one_is_identity_for_simple_quantities` is vacuously narrow; the suite never tests "200g flour" (no space) at 400g, "1/3 cup" at 0.67 (rounding), "3/0", ranges, large and small factors. This is why findings 1-3 were not caught. Fix: parametrised tests of `scale_ingredient` directly.
> 6. NIT main.py:63,68. The response adds a `factor` field returned as a float (2.0 vs 2); the task did not ask for it. State it in the docstring.
> 7. NIT main.py:49. Docstring says "(2.5, not 5/2)" but does not mention rounding is lossy (finding 2).
> 8. NIT main.py:34-41. The three-regex chain with a duplicated denominator check is more complex than needed. One regex with optional groups plus a single zero-denominator check would be shorter.
> 9. NIT test_main.py:84. `_make_recipe` creates rows in the shared recipes.db and never cleans up. New tests are order-independent, but the 2 tag-filter failures show the suite is DB-content-dependent overall. A tmp-path DB fixture or monkeypatched DB_PATH would fix it, but that is outside this commit.
>
> Scores: 1. CORRECTNESS 2/5. 2. TESTS 3/5. 3. CLARITY 4/5.
> VERDICT: REVISE
