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


def _parse_quantity(text: str) -> tuple[Fraction, str] | None:
    """Split "200 g flour" into (Fraction(200), " g flour"); None if no leading number."""
    m = re.match(r"\s*(\d+)\s+(\d+)/(\d+)(?=\s|$)", text)  # mixed: 1 1/2
    if m:
        whole, num, den = m.groups()
        if int(den):
            return Fraction(int(whole)) + Fraction(int(num), int(den)), text[m.end() :]
    m = re.match(r"\s*(\d+)/(\d+)(?=\s|$)", text)  # fraction: 3/4
    if m and int(m.group(2)):
        return Fraction(int(m.group(1)), int(m.group(2))), text[m.end() :]
    m = re.match(r"\s*(\d+(?:\.\d+)?)", text)  # integer or decimal
    if m:
        return Fraction(m.group(1)), text[m.end() :]
    return None


def _format_quantity(value: Fraction) -> str:
    """Render without trailing zeros, rounded to at most 2 decimals (2.5, not 5/2)."""
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


def scale_ingredient(ingredient: str, factor: Fraction) -> str:
    """Scale the leading quantity of one ingredient; leave "salt to taste" untouched."""
    parsed = _parse_quantity(ingredient)
    if parsed is None:
        return ingredient
    quantity, rest = parsed
    return _format_quantity(quantity * factor) + rest


@app.get("/recipes/{recipe_id}/scaled")
def scaled_recipe(recipe_id: int, factor: float = Query(gt=0, allow_inf_nan=False)):
    """The recipe with each ingredient's leading quantity multiplied by factor."""
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
