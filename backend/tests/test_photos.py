"""Tests for photo upload/serve/delete on children & workshops."""
import io
import os
import struct
import zlib
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://maternelle-workshops.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_PWD = "maitresse"
H = {"X-Admin-Password": ADMIN_PWD}


def _png_bytes(w=2, h=2):
    """Tiny valid PNG (red pixels)."""
    sig = b"\x89PNG\r\n\x1a\n"
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * w for _ in range(h))
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(scope="module")
def child_id():
    r = requests.post(f"{API}/children", json={"name": "TEST_Photo_Child"}, headers=H)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    yield cid
    requests.delete(f"{API}/children/{cid}", headers=H)


@pytest.fixture(scope="module")
def workshop_id():
    r = requests.post(f"{API}/workshops", json={"name": "TEST_Photo_WS"}, headers=H)
    assert r.status_code == 200, r.text
    wid = r.json()["id"]
    yield wid
    requests.delete(f"{API}/workshops/{wid}", headers=H)


# --- Auth ---
def test_upload_child_photo_unauthorized(child_id):
    files = {"file": ("a.png", _png_bytes(), "image/png")}
    r = requests.post(f"{API}/children/{child_id}/photo", files=files)
    assert r.status_code == 401


def test_upload_workshop_photo_unauthorized(workshop_id):
    files = {"file": ("a.png", _png_bytes(), "image/png")}
    r = requests.post(f"{API}/workshops/{workshop_id}/photo", files=files)
    assert r.status_code == 401


# --- Successful upload + serve + listed in GET ---
def test_upload_child_photo_success_and_serve(child_id):
    files = {"file": ("a.png", _png_bytes(), "image/png")}
    r = requests.post(f"{API}/children/{child_id}/photo", files=files, headers=H)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["photo_url"].startswith("/api/files/")
    photo_url = body["photo_url"]

    # GET /api/children should reflect photo_url
    listing = requests.get(f"{API}/children").json()
    match = [c for c in listing if c["id"] == child_id]
    assert match and match[0]["photo_url"] == photo_url

    # Serve file: /api/files/<path>
    file_resp = requests.get(f"{BASE_URL}{photo_url}")
    assert file_resp.status_code == 200
    assert file_resp.headers.get("content-type", "").startswith("image/")
    assert len(file_resp.content) > 0
    assert file_resp.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_upload_workshop_photo_success(workshop_id):
    files = {"file": ("w.png", _png_bytes(), "image/png")}
    r = requests.post(f"{API}/workshops/{workshop_id}/photo", files=files, headers=H)
    assert r.status_code == 200, r.text
    photo_url = r.json()["photo_url"]
    assert photo_url.startswith("/api/files/")

    listing = requests.get(f"{API}/workshops").json()
    match = [w for w in listing if w["id"] == workshop_id]
    assert match and match[0]["photo_url"] == photo_url


# --- Validation errors ---
def test_upload_unsupported_format(child_id):
    files = {"file": ("a.txt", b"hello world", "text/plain")}
    r = requests.post(f"{API}/children/{child_id}/photo", files=files, headers=H)
    assert r.status_code == 400
    assert "non supporté" in r.json().get("detail", "").lower() or "format" in r.json().get("detail", "").lower()


def test_upload_oversized_file(child_id):
    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (5 * 1024 * 1024 + 100)
    files = {"file": ("big.png", big, "image/png")}
    r = requests.post(f"{API}/children/{child_id}/photo", files=files, headers=H)
    assert r.status_code == 400


# --- Delete ---
def test_delete_child_photo_unauthorized(child_id):
    r = requests.delete(f"{API}/children/{child_id}/photo")
    assert r.status_code == 401


def test_delete_child_photo_success(child_id):
    r = requests.delete(f"{API}/children/{child_id}/photo", headers=H)
    assert r.status_code == 200
    listing = requests.get(f"{API}/children").json()
    match = [c for c in listing if c["id"] == child_id]
    assert match and match[0]["photo_url"] is None


def test_delete_workshop_photo_success(workshop_id):
    r = requests.delete(f"{API}/workshops/{workshop_id}/photo", headers=H)
    assert r.status_code == 200
    listing = requests.get(f"{API}/workshops").json()
    match = [w for w in listing if w["id"] == workshop_id]
    assert match and match[0]["photo_url"] is None
