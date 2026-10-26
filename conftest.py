import pytest

import main


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Give every test its own empty SQLite file so tests never share state."""
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "test-recipes.db")
    main.init_db()
