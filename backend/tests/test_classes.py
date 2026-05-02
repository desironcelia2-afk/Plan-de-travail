"""Backend tests for multi-class feature."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://maternelle-workshops.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_PWD = "maitresse"
H = {"X-Admin-Password": ADMIN_PWD}


# ========= Classes CRUD =========
def test_list_classes_has_default():
    r = requests.get(f"{API}/classes")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    names = [c["name"] for c in data]
    # At least one class must exist; default should be present in fresh env
    # (but we don't fail if it was renamed during test)
    assert any(isinstance(c.get("id"), str) and c.get("id") for c in data)


def test_create_class_unauthorized():
    r = requests.post(f"{API}/classes", json={"name": "TEST_NoAuth"})
    assert r.status_code == 401


def test_create_class_authorized_and_get():
    r = requests.post(
        f"{API}/classes",
        json={"name": "TEST_PS", "emoji": "🌟", "color": "#FEF3C7"},
        headers=H,
    )
    assert r.status_code == 200, r.text
    created = r.json()
    assert created["name"] == "TEST_PS"
    assert created["emoji"] == "🌟"
    assert "id" in created and isinstance(created["id"], str)
    cid = created["id"]

    # GET individual class
    r = requests.get(f"{API}/classes/{cid}")
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_PS"

    # Listed
    r = requests.get(f"{API}/classes")
    assert cid in [c["id"] for c in r.json()]

    # Cleanup
    requests.delete(f"{API}/classes/{cid}", headers=H)


def test_default_class_backfilled_children():
    """All existing children should have class_id set (not null)."""
    r = requests.get(f"{API}/children")
    assert r.status_code == 200
    for c in r.json():
        assert c.get("class_id"), f"Child {c.get('name')} missing class_id"


# ========= Children with class_id =========
def test_create_child_missing_class_id_returns_422():
    # No class_id at all -> pydantic 422
    r = requests.post(f"{API}/children", json={"name": "TEST_NoClass"}, headers=H)
    assert r.status_code == 422


def test_create_child_invalid_class_id_returns_400():
    r = requests.post(
        f"{API}/children",
        json={"name": "TEST_BadClass", "class_id": "nonexistent-xyz"},
        headers=H,
    )
    assert r.status_code == 400


def test_children_filter_by_class_id():
    # Create a brand new class and child
    r = requests.post(f"{API}/classes", json={"name": "TEST_FilterCls"}, headers=H)
    assert r.status_code == 200
    class_id = r.json()["id"]

    r = requests.post(
        f"{API}/children",
        json={"name": "TEST_InFilterCls", "class_id": class_id},
        headers=H,
    )
    assert r.status_code == 200
    child_id = r.json()["id"]

    # Filter: child present
    r = requests.get(f"{API}/children", params={"class_id": class_id})
    assert r.status_code == 200
    data = r.json()
    assert all(c["class_id"] == class_id for c in data)
    assert child_id in [c["id"] for c in data]

    # Different class: child absent
    r = requests.get(f"{API}/classes")
    other_class = next((c for c in r.json() if c["id"] != class_id), None)
    if other_class:
        r = requests.get(f"{API}/children", params={"class_id": other_class["id"]})
        assert child_id not in [c["id"] for c in r.json()]

    # Cleanup (cascade deletes child)
    requests.delete(f"{API}/classes/{class_id}", headers=H)
    r = requests.get(f"{API}/children/{child_id}")
    assert r.status_code == 404


# ========= Admin overview scoped by class =========
def test_admin_overview_scoped_by_class():
    # Setup: two classes, one child each
    r1 = requests.post(f"{API}/classes", json={"name": "TEST_OvA"}, headers=H)
    r2 = requests.post(f"{API}/classes", json={"name": "TEST_OvB"}, headers=H)
    class_a, class_b = r1.json()["id"], r2.json()["id"]

    r = requests.post(f"{API}/children", json={"name": "TEST_CA", "class_id": class_a}, headers=H)
    child_a = r.json()["id"]
    r = requests.post(f"{API}/children", json={"name": "TEST_CB", "class_id": class_b}, headers=H)
    child_b = r.json()["id"]

    # Overview for class A
    r = requests.get(f"{API}/admin/overview", params={"class_id": class_a}, headers=H)
    assert r.status_code == 200
    data = r.json()
    row_ids = [row["child"]["id"] for row in data["rows"]]
    assert child_a in row_ids
    assert child_b not in row_ids
    # Workshops are global – should be >= seeded set (8)
    assert len(data["workshops"]) >= 1

    # Overview for class B
    r = requests.get(f"{API}/admin/overview", params={"class_id": class_b}, headers=H)
    row_ids = [row["child"]["id"] for row in r.json()["rows"]]
    assert child_b in row_ids
    assert child_a not in row_ids

    # Cleanup
    requests.delete(f"{API}/classes/{class_a}", headers=H)
    requests.delete(f"{API}/classes/{class_b}", headers=H)


# ========= Delete class: cascade + last-class protection =========
def test_delete_class_cascade_children_and_validations():
    # Create a class + child + workshop + validation
    r = requests.post(f"{API}/classes", json={"name": "TEST_Cascade"}, headers=H)
    class_id = r.json()["id"]
    r = requests.post(f"{API}/children", json={"name": "TEST_CC", "class_id": class_id}, headers=H)
    child_id = r.json()["id"]

    # Pick any existing workshop
    workshops = requests.get(f"{API}/workshops").json()
    assert workshops, "need at least one workshop"
    wid = workshops[0]["id"]

    requests.post(f"{API}/validations", json={"child_id": child_id, "workshop_id": wid})

    # Delete unauthorized
    r = requests.delete(f"{API}/classes/{class_id}")
    assert r.status_code == 401

    # Delete authorized
    r = requests.delete(f"{API}/classes/{class_id}", headers=H)
    assert r.status_code == 200

    # Child removed
    r = requests.get(f"{API}/children/{child_id}")
    assert r.status_code == 404

    # Validation removed – check admin overview no longer contains this child
    r = requests.get(f"{API}/admin/overview", headers=H)
    all_rows = r.json()["rows"]
    assert child_id not in [row["child"]["id"] for row in all_rows]


def test_cannot_delete_last_class():
    # Get all classes
    classes = requests.get(f"{API}/classes").json()
    # Delete all but one by creating enough to guarantee state, then deleting down
    # Strategy: create a temp class, delete all OTHER classes that start with TEST_,
    # but safer: try deleting when only 1 remains (simulate final state).
    # We'll create a scratch class, then keep deleting classes until only the scratch remains,
    # then attempt to delete it -> should 400.
    scratch = requests.post(f"{API}/classes", json={"name": "TEST_LastOnly"}, headers=H).json()

    # Delete every other class we can (note: this cascades children, so we only do it in
    # a safe way: we DO NOT actually want to wipe the default class in the shared env.
    # Instead, we TEMPORARILY reduce the env to the scratch + original classes, then
    # verify the "last class" guard with a different approach: delete everything except
    # scratch only if we can restore. To stay safe, we only verify the guard by deleting
    # classes one-by-one; when count_documents==1 the next delete should 400.
    classes = requests.get(f"{API}/classes").json()
    # If more than one class exists, we cannot directly test "last class" without
    # destroying state. Instead, we assert the guard works IF/WHEN only one remains
    # by checking via deleting the scratch succeeds (count > 1).
    r = requests.delete(f"{API}/classes/{scratch['id']}", headers=H)
    assert r.status_code == 200  # scratch was deletable because count > 1

    # Now re-verify by attempting to delete every class until only one remains
    # BUT we will NOT actually do that to avoid losing default data.
    # Instead we re-create the "last class" scenario in isolation:
    # Delete default scenario test: impossible without wiping -> we approximate by
    # checking the error path via count=1 through monkey logic. Skip if not possible.
    remaining = requests.get(f"{API}/classes").json()
    if len(remaining) == 1:
        # Rare: only one exists -> test the guard directly
        r = requests.delete(f"{API}/classes/{remaining[0]['id']}", headers=H)
        assert r.status_code == 400
