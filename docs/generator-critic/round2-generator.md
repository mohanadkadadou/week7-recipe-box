# Round 2: GENERATOR revision (commits `50b81b5`, `ff60b75` on `task-scaling`)
Input: the critic's round-1 report (read from `round1-critic.md`). Instruction: fix every SHOULD-FIX, fix the shared-database test problem properly, run the suite twice.

Generator report (verbatim):
> Round 2 is committed as 50b81b5 (main work) and ff60b75 (a docstring-wording fix). It is two commits rather than the one asked for, because I only caught the docstring wording after committing. Ruff is clean and pytest passed on two consecutive runs (41 passed, 0 failed each).
> **Fixed**
> 1. Huge factor (500): the factor is now `Query(ge=0.001, le=1000, allow_inf_nan=False)`, so `1e308` returns 422 instead of crashing. Digit runs are capped at 9, so `float(Fraction)` cannot overflow.
> 2. Small factor: `_format_quantity` uses 2 decimals at or above 0.1 and otherwise keeps 2 significant figures. "0.001 g x" at 0.5 now gives "0.0005 g x", and "1 pinch" at 0.001 gives "0.001 pinch". The 0.001 minimum factor is a guard that keeps `log10` away from zero.
> 3. Malformed quantities: one regex with named groups requires a boundary (whitespace, a letter or end of text) after the number. A zero denominator, including the mixed form "1 1/0", returns None. A range ("1-2", "1 to 2", "1/2-1"), a dimension ("2x3") and a stray fraction after the number return None. "1,5 l" and "1. egg" are left unchanged.
> 4. ".5 tsp": it now scales. The unicode-fraction limitation is documented in the `_parse_quantity` docstring.
> 5. Tests: a 20-case parametrised `test_scale_ingredient` calling `scale_ingredient` directly ("200g flour", "1/3 cup" at 0.67, decimal comma, ".5 tsp", small and huge factors, zero denominators, ranges, "1.", a 400-digit number), a factor-bounds test, and the invalid-factor test now includes 1e308, 1001 and 0.0001.
> 6. NIT 6 and 7: the docstrings now state that `factor` is echoed as a float and that formatting is lossy.
> 7. NIT 8: one regex plus a single check replaces the three-regex chain.
> 8. NIT 9 and the shared-DB problem: a new `conftest.py` has an autouse fixture that monkeypatches `main.DB_PATH` to a per-test tmp file and calls `main.init_db()`. The tag-filter tests now pass on every run.
> Declined: none. The unicode-fraction half of finding 4 is documented rather than implemented, as the critic allowed.
> Tests: 41 in total.
