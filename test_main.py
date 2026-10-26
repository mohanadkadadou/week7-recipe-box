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


def _make_recipe(ingredients):
    return client.post(
        "/recipes", json={"title": "Scale me", "ingredients": ingredients}
    ).json()["id"]


def _scaled(rid, factor):
    return client.get(f"/recipes/{rid}/scaled", params={"factor": factor})


def test_scaled_doubles_quantities():
    rid = _make_recipe(["200 g flour", "2 eggs", "1 cup milk"])
    r = _scaled(rid, 2)
    assert r.status_code == 200
    body = r.json()
    assert body["ingredients"] == ["400 g flour", "4 eggs", "2 cup milk"]
    assert body["id"] == rid and body["title"] == "Scale me"
    assert body["factor"] == 2


def test_scaled_does_not_modify_stored_recipe():
    rid = _make_recipe(["200 g flour"])
    _scaled(rid, 3)
    assert client.get(f"/recipes/{rid}").json()["ingredients"] == ["200 g flour"]


def test_scaled_fractional_factor_and_decimals():
    rid = _make_recipe(["200 g flour", "1 egg", "0.5 tsp salt"])
    assert _scaled(rid, 0.5).json()["ingredients"] == [
        "100 g flour",
        "0.5 egg",
        "0.25 tsp salt",
    ]


def test_scaled_handles_fraction_and_mixed_quantities():
    rid = _make_recipe(["1/2 cup sugar", "1 1/2 cup water"])
    assert _scaled(rid, 2).json()["ingredients"] == ["1 cup sugar", "3 cup water"]


def test_scaled_leaves_ingredients_without_quantity_unchanged():
    rid = _make_recipe(["salt to taste", "", "2 eggs"])
    assert _scaled(rid, 2).json()["ingredients"] == ["salt to taste", "", "4 eggs"]


def test_scaled_factor_one_is_identity_for_simple_quantities():
    rid = _make_recipe(["200 g flour", "salt"])
    assert _scaled(rid, 1).json()["ingredients"] == ["200 g flour", "salt"]


def test_scaled_unknown_recipe_404():
    assert _scaled(99999, 2).status_code == 404


def test_scaled_rejects_invalid_factor():
    rid = _make_recipe(["200 g flour"])
    for bad in ["0", "-1", "abc", "nan", "inf"]:
        assert _scaled(rid, bad).status_code == 422, bad


def test_scaled_requires_factor():
    rid = _make_recipe(["200 g flour"])
    assert client.get(f"/recipes/{rid}/scaled").status_code == 422
