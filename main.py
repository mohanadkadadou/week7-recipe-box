"""Recipe Box — starter app for Week 7.

A tiny FastAPI service for recipes and tags, with a static frontend. Use it as the
playground for concurrent multi-agent work and a generator-critic loop.

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload
    # open http://localhost:8000/
Test:
    pytest
"""

import json
import math
import re
import sqlite3
from contextlib import closing
from fractions import Fraction
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE = Path(__file__).parent
DB_PATH = BASE / "recipes.db"

app = FastAPI(title="Recipe Box")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_db()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS recipes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                ingredients TEXT NOT NULL,  -- JSON list of strings
                tags        TEXT NOT NULL   -- JSON list of strings
            )"""
        )
        conn.commit()


init_db()


class RecipeIn(BaseModel):
    title: str
    ingredients: list[str] = []
    tags: list[str] = []


def _row_to_recipe(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": json.loads(row["ingredients"]),
        "tags": json.loads(row["tags"]),
    }


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/recipes")
def create_recipe(recipe: RecipeIn):
    with closing(get_db()) as conn:
        cur = conn.execute(
            "INSERT INTO recipes (title, ingredients, tags) VALUES (?, ?, ?)",
            (recipe.title, json.dumps(recipe.ingredients), json.dumps(recipe.tags)),
        )
        conn.commit()
        rid = cur.lastrowid
    return {"id": rid, **recipe.model_dump()}


@app.get("/recipes")
def list_recipes(tag: str | None = None):
    with closing(get_db()) as conn:
        rows = conn.execute("SELECT * FROM recipes ORDER BY id").fetchall()
    recipes = [_row_to_recipe(r) for r in rows]
    if tag is not None:
        wanted = tag.casefold()
        recipes = [r for r in recipes if any(t.casefold() == wanted for t in r["tags"])]
    return recipes


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    with closing(get_db()) as conn:
        row = conn.execute(
            "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown recipe")
    return _row_to_recipe(row)


_QUANTITY = re.compile(
    r"""\s*(?:
        (?P<whole>\d{1,9})\s+(?P<n1>\d{1,9})/(?P<d1>\d{1,9})   # mixed: 1 1/2
      | (?P<n2>\d{1,9})/(?P<d2>\d{1,9})                        # fraction: 3/4
      | (?P<dec>\d{1,9}(?:\.\d{1,9})?|\.\d{1,9})              # 2, 2.5, .5
    )(?=\s|[A-Za-z]|$)""",
    re.VERBOSE,
)
# After the number: a range ("1-2", "1 to 2"), a dimension ("2x3", "2 x 3",
# "2xlarge"), a stray fraction ("1 1/0", "1/2/3") or a unicode vulgar fraction
# (the half sign, etc.) means this is not a plain quantity, so the whole
# ingredient is left unchanged rather than half-scaled.
_NOT_PLAIN = re.compile(
    r"(?:\s*(?:(?:to|or|[-\u2013\u2014x\u00d7])\s*\d|\d+/\d|/|[\u00bc-\u00be\u2150-\u215f\u2189])"
    r"|[xX\u00d7][A-Za-z])",
    re.IGNORECASE,
)


def _parse_quantity(text: str) -> tuple[Fraction, str] | None:
    """Split "200 g flour" into (Fraction(200), " g flour").

    Returns None (leave the text alone) when there is no leading number or it is
    not a plain one: ranges, zero denominators, "1,5", "1.", "2x3",
    "2xlarge", "1/2/3" and unicode fractions ("2 <half sign> cups"), which are
    left entirely unchanged.
    """
    m = _QUANTITY.match(text)
    if not m:
        return None
    rest = text[m.end() :]
    if _NOT_PLAIN.match(rest):
        return None
    if m["whole"] is not None:
        if not int(m["d1"]):
            return None
        return Fraction(int(m["whole"])) + Fraction(int(m["n1"]), int(m["d1"])), rest
    if m["n2"] is not None:
        if not int(m["d2"]):
            return None
        return Fraction(int(m["n2"]), int(m["d2"])), rest
    return Fraction(m["dec"]), rest


def _format_quantity(value: Fraction) -> str:
    """Render as a decimal without trailing zeros (2.5, not 5/2).

    Lossy: 2 decimals at or above 0.1, otherwise enough decimals to keep two
    significant figures, so small amounts never collapse to 0. Zero is "0".
    """
    if value == 0:
        return "0"
    x = float(value)
    decimals = 2 if x >= 0.1 else 1 - math.floor(math.log10(x))
    return f"{x:.{decimals}f}".rstrip("0").rstrip(".")


def scale_ingredient(ingredient: str, factor: Fraction) -> str:
    """Scale the leading quantity of one ingredient; leave "salt to taste" untouched."""
    parsed = _parse_quantity(ingredient)
    if parsed is None:
        return ingredient
    quantity, rest = parsed
    return _format_quantity(quantity * factor) + rest


@app.get("/recipes/{recipe_id}/scaled")
def scaled_recipe(
    recipe_id: int, factor: float = Query(ge=0.001, le=1000, allow_inf_nan=False)
):
    """The recipe with each ingredient's leading quantity multiplied by factor.

    Quantities are rounded: 2 decimals at or above 0.1, otherwise two
    significant figures (so 0.001 g at factor 0.5 gives 0.0005). Ranges,
    dimensions and unicode fractions are left unchanged.

    The response also echoes `factor` (as a float, so 2 comes back as 2.0).
    """
    recipe = get_recipe(recipe_id)
    exact = Fraction(str(factor))
    recipe["ingredients"] = [scale_ingredient(i, exact) for i in recipe["ingredients"]]
    return {**recipe, "factor": factor}


@app.get("/shopping-list")
def shopping_list(ids: str):
    """Merge the ingredients of the given recipes (comma-separated ids), de-duplicated."""
    parts = [p.strip() for p in ids.split(",")]
    try:
        recipe_ids = [int(p) for p in parts]
    except ValueError:
        raise HTTPException(
            status_code=422, detail="ids must be a comma-separated list of integers"
        ) from None
    with closing(get_db()) as conn:
        found = {}
        for rid in dict.fromkeys(recipe_ids):
            row = conn.execute("SELECT * FROM recipes WHERE id = ?", (rid,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail=f"unknown recipe id {rid}")
            found[rid] = json.loads(row["ingredients"])
    seen: set[str] = set()
    items: list[str] = []
    for rid in dict.fromkeys(recipe_ids):
        for ing in found[rid]:
            name = ing.strip()
            key = name.lower()
            if name and key not in seen:
                seen.add(key)
                items.append(name)
    return {"ids": list(dict.fromkeys(recipe_ids)), "ingredients": items}
