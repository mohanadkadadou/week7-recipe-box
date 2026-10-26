from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_and_get_recipe():
    r = client.post(
        "/recipes",
        json={"title": "Pancakes", "ingredients": ["flour", "milk"], "tags": ["breakfast"]},
    )
    assert r.status_code == 200
    rid = r.json()["id"]
    r2 = client.get(f"/recipes/{rid}")
    assert r2.status_code == 200
    assert r2.json()["title"] == "Pancakes"
    assert r2.json()["tags"] == ["breakfast"]


def test_list_recipes():
    client.post("/recipes", json={"title": "Toast"})
    r = client.get("/recipes")
    assert r.status_code == 200
    assert any(rec["title"] == "Toast" for rec in r.json())


def test_unknown_recipe_404():
    r = client.get("/recipes/99999")
    assert r.status_code == 404


def test_tag_filter_returns_only_matching_recipes():
    tag = "tagfilter-unique-a"
    a = client.post("/recipes", json={"title": "A", "tags": [tag, "other"]}).json()
    b = client.post("/recipes", json={"title": "B", "tags": ["tagfilter-unique-a-x"]}).json()
    client.post("/recipes", json={"title": "C"})
    r = client.get("/recipes", params={"tag": tag})
    assert r.status_code == 200
    ids = [rec["id"] for rec in r.json()]
    assert ids == [a["id"]]
    assert b["id"] not in ids


def test_tag_filter_is_case_insensitive():
    rid = client.post("/recipes", json={"title": "D", "tags": ["TagFilter-Case-B"]}).json()["id"]
    r = client.get("/recipes", params={"tag": "tagfilter-case-b"})
    assert [rec["id"] for rec in r.json()] == [rid]


def test_tag_filter_unknown_tag_is_empty():
    assert client.get("/recipes", params={"tag": "tagfilter-no-such-tag"}).json() == []


def test_no_tag_param_returns_all():
    rid = client.post("/recipes", json={"title": "E", "tags": ["tagfilter-unique-c"]}).json()["id"]
    assert rid in [rec["id"] for rec in client.get("/recipes").json()]
