# Week 7: Recipe Box, concurrent agents and a generator-critic loop

FastAPI + SQLite recipe box. Features added by agents: tag filter, shopping list, ingredient scaling. See [`writeup.md`](writeup.md) and [`docs/generator-critic/`](docs/generator-critic).

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
pytest -q                    # 55 tests, each on its own temporary database
uvicorn main:app --reload    # UI at /, docs at /docs
```
Branches kept for the history: `task-tag-filter`, `task-shopping-list`, `task-scaling` (merged into `main`).
