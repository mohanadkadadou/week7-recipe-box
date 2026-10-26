# Round 2: CRITIC (read-only) verdict: REVISE
The critic re-verified every round-1 finding and attacked the revision with new inputs.

Critic report (verbatim):
> ROUND 2 CRITIC REVIEW of task-scaling (ff60b75). Ruff clean; pytest 41 passed x3 consecutive runs; conftest fixture (conftest.py:1-10) is clean, with a per-test tmp DB, monkeypatch auto-reverted, and no leakage into recipes.db. Round-1 tag-filter failures are gone.
>
> Round-1 findings verified: #1 overflow fixed (le=1000, 1e308 gives 422, main.py:167). #2 small values fixed (0.001 g at 0.5 gives 0.0005). #3 ranges, "3/0", "1,5", "1.", "2x3" fixed via _NOT_PLAIN and a boundary lookahead. #4 ".5" fixed; unicode is documented as unsupported (main.py:125-126). #5 parametrised tests added (test_main.py:~181). #6 and #7 docstrings fixed. #9 isolated DB fixed.
>
> NEW problems:
> 1. BLOCKER main.py:152 `_format_quantity` calls math.log10(0) when the scaled value is zero. A zero quantity is common ("0 g salt", "0.0 cup"), and `scale_ingredient("0 g", Fraction(2))` raises ValueError: math domain error. The endpoint then returns HTTP 500 for ANY factor (reproduced: recipe ["0 g x"], factor 2, 0.001, 0.3333 and 1000 all give 500). One such ingredient makes the whole recipe unscalable. Fix: `if value == 0: return "0"` at the top of `_format_quantity` (or return the ingredient unchanged). Add the test ("0 g x", "2", "0 g x") and one with "0.0".
> 2. SHOULD-FIX main.py:116-118 / :108-113 unicode fractions: "2 ½ cups" at factor 2 becomes "4 ½ cups", and "1 ½" becomes "2 ½". The whole part is scaled and the fraction is not: the same half-scaling mangling as round-1 #3. The docstring promises unicode fractions are "left unchanged". Fix: add the vulgar-fraction characters to the _NOT_PLAIN lookahead (or reject any following non-ASCII digit/fraction char), plus a test.
> 3. SHOULD-FIX main.py:113 the lookahead `(?=\s|[A-Za-z]|$)` lets "2xlarge eggs" become "4xlarge eggs" (a dimension-like unit glued on); "2 x 3" stays unchanged only because of the spaces. Add "2xlarge" or "2 x 3" cases to pin the intended behaviour.
> 4. NIT main.py:152: rounding to two significant figures is not documented in the endpoint docstring. "0.00001 g" at 0.001 gives "0.00000001 g" (long, but correct).
> 5. NIT test_main.py:~190: no test covers a zero quantity, a mixed number with a decimal result (12 3/4 gives 25.5), or the factor echo.
> 6. NIT main.py:178 `get_recipe` is called directly, bypassing Depends; fine.
>
> SCORES: 1. CORRECTNESS 3/5. 2. TESTS 4/5 (no zero-quantity case, which is how finding 1 slipped through). 3. CLARITY 4/5.
> VERDICT: REVISE
