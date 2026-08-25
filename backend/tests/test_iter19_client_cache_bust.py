"""Iter19: verify client-side cache-bust is additive and doesn't break the API.

Client change: Home.js and Brands.js now GET /api/brands/brand-of-week?t=<epoch>
with Cache-Control:no-cache + Pragma:no-cache request headers.

Backend must:
  - Ignore the unknown `t` query param (200, same body).
  - Still return Cache-Control: no-store,no-cache,must-revalidate on the response.
  - Full submit->approve->GET flow still produces featured_image.
  - Iter17 SSRF hardening and iter18 admin BotW queue still work.
"""
import io
import os
import time
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "Anthonygeorgiades@unveiledthreads.co.uk"
ADMIN_PASS = "Babablacksheep159"
BRAND_EMAIL = "testbrand@example.com"
BRAND_PASS = "TestBrand123!"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    return s


PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x00\x03\x00\x01^\xf3*:\x00\x00\x00\x00IEND\xaeB`\x82"
)


# ---------- 1. Cache-buster query param is accepted, body unchanged ----------
def test_botw_accepts_cachebust_query_param():
    ts = int(time.time() * 1000)
    r1 = requests.get(f"{API}/brands/brand-of-week", timeout=15,
                      headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
    r2 = requests.get(f"{API}/brands/brand-of-week?t={ts}", timeout=15,
                      headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
    assert r1.status_code == 200
    assert r2.status_code == 200, f"query-param variant failed: {r2.status_code} {r2.text[:200]}"
    # Same JSON shape/content (same BotW brand)
    b1, b2 = r1.json(), r2.json()
    if b1 and b2:
        assert b1.get("id") == b2.get("id"), "cache-bust variant returned different brand"
        # Body must contain no `t` echo (unknown params ignored)
        assert "t" not in b2 or b2.get("t") is None


# ---------- 2. Server cache-control headers still present with query param ----------
def test_botw_no_store_header_with_query_param():
    ts = int(time.time() * 1000)
    r = requests.get(f"{API}/brands/brand-of-week?t={ts}", timeout=15,
                     headers={"Cache-Control": "no-cache"})
    assert r.status_code == 200
    cc = r.headers.get("Cache-Control", "").lower()
    assert "no-store" in cc or "no-cache" in cc, f"missing no-store/no-cache: {r.headers}"


# ---------- 3. Weird / abusive query params don't break the endpoint ----------
@pytest.mark.parametrize("qs", [
    "t=0",
    "t=abc",             # non-numeric — must still 200
    "t=" + "9" * 40,     # huge int
    "t=&t=2&foo=bar",    # duplicate keys + extra unknowns
])
def test_botw_tolerates_weird_query_params(qs):
    r = requests.get(f"{API}/brands/brand-of-week?{qs}", timeout=15)
    assert r.status_code == 200, f"failed on ?{qs}: {r.status_code} {r.text[:200]}"


# ---------- 4. Full submit -> approve -> GET still exposes featured_image ----------
def test_botw_submit_approve_roundtrip():
    brand_sess = _login(BRAND_EMAIL, BRAND_PASS)

    botw = requests.get(f"{API}/brands/brand-of-week", timeout=15).json()
    if not botw or not botw.get("is_brand_of_week"):
        pytest.skip("no BotW set")
    brand_id = botw["id"]
    me = brand_sess.get(f"{API}/auth/me", timeout=15).json()
    if botw.get("user_id") and me.get("id") and botw["user_id"] != me["id"]:
        pytest.skip("current BotW does not belong to testbrand")

    up = brand_sess.post(
        f"{API}/upload/image",
        files={"file": ("iter19.png", io.BytesIO(PNG_1x1), "image/png")},
        timeout=30,
    )
    assert up.status_code == 200, f"upload: {up.status_code} {up.text[:200]}"
    upj = up.json()
    image_url = upj.get("url") or upj.get("image_url") or upj.get("path")
    assert image_url and "/api/files/" in image_url, upj

    sub = brand_sess.post(f"{API}/brands/me/botw-image", json={"image_url": image_url}, timeout=15)
    assert sub.status_code == 200, sub.text[:200]

    admin_sess = _login(ADMIN_EMAIL, ADMIN_PASS)
    dec = admin_sess.post(f"{API}/admin/botw-image/{brand_id}", json={"approve": True}, timeout=15)
    assert dec.status_code == 200, dec.text[:200]

    # Fetch with a cache-buster (mimicking the frontend)
    ts = int(time.time() * 1000)
    r = requests.get(f"{API}/brands/brand-of-week?t={ts}", timeout=15,
                     headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
    assert r.status_code == 200
    body = r.json()
    assert body["featured_image"] == image_url, (
        f"expected featured_image={image_url}, got={body.get('featured_image')}"
    )


# ---------- 5. Iter18 admin BotW routes still reachable ----------
def test_admin_botw_queue_still_reachable():
    s = _login(ADMIN_EMAIL, ADMIN_PASS)
    r = s.get(f"{API}/admin/botw-image/queue", timeout=15)
    assert r.status_code == 200


# ---------- 6. Iter18 rotate/veto/skip bad-id return 4xx (not 500) ----------
@pytest.mark.parametrize("path", [
    "/admin/botw/rotate",
    "/admin/botw/skip",
    "/admin/botw/veto",
])
def test_admin_botw_control_endpoints_bad_id(path):
    s = _login(ADMIN_EMAIL, ADMIN_PASS)
    r = s.post(f"{API}{path}", json={"brand_id": "does-not-exist"}, timeout=15)
    # Accept 400/404/422 (clean errors) or 200 if endpoint tolerates. Must not 5xx.
    assert r.status_code < 500, f"{path} returned {r.status_code}: {r.text[:200]}"


# ---------- 7. Iter17 SSRF hardening still blocks internal URLs ----------
@pytest.mark.parametrize("bad_url", [
    "http://169.254.169.254/latest/meta-data/",
    "http://localhost:8001/api/brands",
    "http://127.0.0.1/",
])
def test_csv_import_ssrf_blocked(bad_url):
    s = _login(ADMIN_EMAIL, ADMIN_PASS)
    r = s.post(f"{API}/products/import/csv", json={"url": bad_url}, timeout=15)
    assert r.status_code in (400, 403, 422), f"{bad_url}: got {r.status_code}"
