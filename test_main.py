from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_and_get_recipe():
    r = client.post(
        "/recipes",
        json={
            "title": "Pancakes",
            "ingredients": ["flour", "milk"],
            "tags": ["breakfast"],
        },
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
    b = client.post(
        "/recipes", json={"title": "B", "tags": ["tagfilter-unique-a-x"]}
    ).json()
    client.post("/recipes", json={"title": "C"})
    r = client.get("/recipes", params={"tag": tag})
    assert r.status_code == 200
    ids = [rec["id"] for rec in r.json()]
    assert ids == [a["id"]]
    assert b["id"] not in ids


def test_tag_filter_is_case_insensitive():
    rid = client.post(
        "/recipes", json={"title": "D", "tags": ["TagFilter-Case-B"]}
    ).json()["id"]
    r = client.get("/recipes", params={"tag": "tagfilter-case-b"})
    assert [rec["id"] for rec in r.json()] == [rid]


def test_tag_filter_unknown_tag_is_empty():
    assert client.get("/recipes", params={"tag": "tagfilter-no-such-tag"}).json() == []


def test_no_tag_param_returns_all():
    rid = client.post(
        "/recipes", json={"title": "E", "tags": ["tagfilter-unique-c"]}
    ).json()["id"]
    assert rid in [rec["id"] for rec in client.get("/recipes").json()]


def _make(title, ingredients):
    return client.post(
        "/recipes", json={"title": title, "ingredients": ingredients}
    ).json()["id"]


def test_shopping_list_merges_and_dedupes():
    a = _make("A", ["Flour", "milk", "Eggs"])
    b = _make("B", ["  flour ", "Sugar", "MILK"])
    r = client.get(f"/shopping-list?ids={a},{b}")
    assert r.status_code == 200
    assert r.json()["ingredients"] == ["Flour", "milk", "Eggs", "Sugar"]


def test_shopping_list_single_and_repeated_id():
    a = _make("A", ["salt", "salt "])
    r = client.get(f"/shopping-list?ids={a},{a}")
    assert r.status_code == 200
    assert r.json()["ingredients"] == ["salt"]


def test_shopping_list_unknown_id_404():
    a = _make("A", ["salt"])
    r = client.get(f"/shopping-list?ids={a},99999")
    assert r.status_code == 404
    assert "99999" in r.json()["detail"]


def test_shopping_list_malformed_ids():
    for bad in ["a,b", "", "1,,2", "1,x"]:
        r = client.get("/shopping-list", params={"ids": bad})
        assert r.status_code == 422, bad
    assert client.get("/shopping-list").status_code == 422
