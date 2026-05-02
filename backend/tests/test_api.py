import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://maternelle-workshops.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_PWD = "maitresse"
H = {"X-Admin-Password": ADMIN_PWD}


def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200


def test_list_children_seeded():
    r = requests.get(f"{API}/children")
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    for n in ["Léa", "Tom", "Chloé", "Noah", "Emma", "Lucas"]:
        assert n in names


def test_list_workshops_seeded():
    r = requests.get(f"{API}/workshops")
    assert r.status_code == 200
    names = [w["name"] for w in r.json()]
    for n in ["Peinture", "Puzzle", "Lettres", "Chiffres", "Construction"]:
        assert n in names


def test_admin_login_correct():
    r = requests.post(f"{API}/admin/login", json={"password": ADMIN_PWD})
    assert r.status_code == 200
    assert r.json().get("success") is True


def test_admin_login_wrong():
    r = requests.post(f"{API}/admin/login", json={"password": "wrong"})
    assert r.status_code == 401


def test_create_child_unauthorized():
    # Must supply a valid class_id so pydantic validation passes;
    # then header check returns 401.
    classes = requests.get(f"{API}/classes").json()
    assert classes, "Need at least one class"
    r = requests.post(
        f"{API}/children",
        json={"name": "TEST_NoAuth", "class_id": classes[0]["id"]},
    )
    assert r.status_code == 401


def test_admin_overview_unauthorized():
    r = requests.get(f"{API}/admin/overview")
    assert r.status_code == 401


def test_child_full_crud_and_validation_flow():
    # Fetch default class_id
    classes = requests.get(f"{API}/classes").json()
    assert classes
    class_id = classes[0]["id"]

    # CREATE child
    r = requests.post(f"{API}/children", json={"name": "TEST_Zoe", "emoji": "🦊", "color": "#FDE68A", "class_id": class_id}, headers=H)
    assert r.status_code == 200
    child = r.json()
    cid = child["id"]
    assert child["name"] == "TEST_Zoe"

    # GET child
    r = requests.get(f"{API}/children/{cid}")
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_Zoe"

    # CREATE workshop
    r = requests.post(f"{API}/workshops", json={"name": "TEST_WS", "emoji": "🎨", "color": "#FCA5A5"}, headers=H)
    assert r.status_code == 200
    wid = r.json()["id"]

    # status: not done
    r = requests.get(f"{API}/children/{cid}/status")
    assert r.status_code == 200
    statuses = r.json()
    target = next((s for s in statuses if s["workshop"]["id"] == wid), None)
    assert target is not None
    assert target["done"] is False

    # add validation
    r = requests.post(f"{API}/validations", json={"child_id": cid, "workshop_id": wid})
    assert r.status_code == 200

    # status: done
    r = requests.get(f"{API}/children/{cid}/status")
    target = next((s for s in r.json() if s["workshop"]["id"] == wid), None)
    assert target["done"] is True
    assert target["last_done_at"] is not None

    # admin overview includes done
    r = requests.get(f"{API}/admin/overview", headers=H)
    assert r.status_code == 200
    data = r.json()
    row = next((row for row in data["rows"] if row["child"]["id"] == cid), None)
    assert row is not None
    assert wid in row["done_workshop_ids"]

    # remove validation
    r = requests.delete(f"{API}/validations", params={"child_id": cid, "workshop_id": wid})
    assert r.status_code == 200
    assert r.json()["deleted"] >= 1

    # status: not done again
    r = requests.get(f"{API}/children/{cid}/status")
    target = next((s for s in r.json() if s["workshop"]["id"] == wid), None)
    assert target["done"] is False

    # add validation again, then DELETE workshop should cascade
    requests.post(f"{API}/validations", json={"child_id": cid, "workshop_id": wid})

    # DELETE workshop unauthorized
    r = requests.delete(f"{API}/workshops/{wid}")
    assert r.status_code == 401
    # DELETE workshop authorized
    r = requests.delete(f"{API}/workshops/{wid}", headers=H)
    assert r.status_code == 200

    # validations cascaded
    r = requests.get(f"{API}/children/{cid}/status")
    assert all(s["workshop"]["id"] != wid for s in r.json())

    # DELETE child unauthorized
    r = requests.delete(f"{API}/children/{cid}")
    assert r.status_code == 401
    # DELETE child authorized
    r = requests.delete(f"{API}/children/{cid}", headers=H)
    assert r.status_code == 200

    # GET deleted child -> 404
    r = requests.get(f"{API}/children/{cid}")
    assert r.status_code == 404


def test_delete_nonexistent():
    r = requests.delete(f"{API}/children/nonexistent-id-xyz", headers=H)
    assert r.status_code == 404
    r = requests.delete(f"{API}/workshops/nonexistent-id-xyz", headers=H)
    assert r.status_code == 404


def test_validation_invalid_child():
    r = requests.post(f"{API}/validations", json={"child_id": "bad", "workshop_id": "bad"})
    assert r.status_code == 404
