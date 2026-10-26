# Round 3: GENERATOR revision (commit `ec64057` on `task-scaling`)
Input: the critic's round-2 report (BLOCKER: zero quantity -> HTTP 500; two SHOULD-FIX).

Generator report (verbatim):
> Round 3 fixes are committed as ec64057 on task-scaling. ruff is clean and pytest gives 55 passed (41 before), three runs in a row.
> - BLOCKER fixed: `_format_quantity` returns "0" for a zero value, so "0 g", "0.0 cup" and "0/5 cup" no longer reach `math.log10`. A new endpoint test checks that a recipe with zero-quantity ingredients returns 200 at factors 2, 0.001, 0.3333 and 1000.
> - SHOULD-FIX fixed: `_NOT_PLAIN` now covers unicode vulgar fractions (U+00BC-BE, U+2150-215F, U+2189), so "2 ½ cups", "1½ cups" and "½ cup" stay fully unchanged.
> - SHOULD-FIX pinned: "2xlarge eggs" and "2 x 3 tray" stay unchanged because an `x` glued to a letter now counts as not plain. "2 xanthan gum" still scales to "4 xanthan gum", and a test documents that.
> - NITs done: the endpoint docstring documents the two-significant-figure rounding. New tests cover "0 g x", "0.0 cup", "12 3/4 cups" at factor 2 giving "25.5 cups", and the factor echo.
> - Declined: the `get_recipe` direct-call nit, which the critic itself called fine.
> - Same-class check: `log10` only sees positive values now. The smallest non-zero scaled value is about 1e-12, which formats fine. A decimal or fraction followed by `/` ("1/2/3", "1.5/2") was half-scaled: same class as the unicode bug, fixed and tested.
> - Process slip: I first committed with one failing test (a wrong expected value in my own new test), then fixed it and amended. There is still a single commit.
