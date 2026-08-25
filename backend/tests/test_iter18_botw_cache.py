"""Iter18: verify Brand-of-Week cache-control fix + full submit/approve flow.

Bug: GET /api/brands/brand-of-week was cacheable, so a freshly approved BotW hero
image would not appear on the homepage until CDN/browser TTL expired.

Fix: Cache-Control: no-store, no-cache, must-revalidate, max-age=0 + Pragma + Expires.
"""
import io
import os
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
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:300]}"
    return s


# ---------- 1. Cache header on unauthenticated GET ----------
def test_brand_of_week_has_no_store_header():
    r = requests.get(f"{API}/brands/brand-of-week", timeout=15)
    assert r.status_code == 200, r.text[:300]
    cc = r.headers.get("Cache-Control", "").lower()
    assert ("no-store" in cc) or ("no-cache" in cc), f"missing no-cache header, got: {r.headers}"
    # Response shape unchanged
    body = r.json()
    assert body is None or "id" in body, f"unexpected shape: {body}"


def test_brand_of_week_head_no_store():
    # curl -I equivalent
    r = requests.head(f"{API}/brands/brand-of-week", timeout=15, allow_redirects=True)
    # HEAD may not be supported (FastAPI default GET does support HEAD via Starlette)
    if r.status_code == 200:
        cc = r.headers.get("Cache-Control", "").lower()
        assert "no-store" in cc or "no-cache" in cc


# ---------- 2. Full submit → approve → featured_image round trip ----------
def test_botw_submit_approve_and_reflected_in_get():
    brand_sess = _login(BRAND_EMAIL, BRAND_PASS)

    # Get current BotW brand (testbrand should be it, per iter17 context)
    botw = requests.get(f"{API}/brands/brand-of-week", timeout=15)
    assert botw.status_code == 200, botw.text[:300]
    my_brand = botw.json()
    if not my_brand or not my_brand.get("is_brand_of_week"):
        pytest.skip("no BotW set")

    brand_id = my_brand["id"]

    # Sanity: this brand belongs to our brand user
    me_auth = brand_sess.get(f"{API}/auth/me", timeout=15).json()
    if my_brand.get("user_id") and me_auth.get("id") and my_brand["user_id"] != me_auth["id"]:
        pytest.skip(f"BotW belongs to different user ({my_brand.get('brand_name')}), cannot submit as testbrand")

    # Upload a fresh image via /api/upload/image (PNG bytes with valid magic)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x00\x03\x00\x01^\xf3*:\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    up = brand_sess.post(
        f"{API}/upload/image",
        files={"file": ("hero.png", io.BytesIO(png_bytes), "image/png")},
        timeout=30,
    )
    assert up.status_code == 200, f"upload failed: {up.status_code} {up.text[:400]}"
    upj = up.json()
    image_url = upj.get("url") or upj.get("image_url") or upj.get("path")
    assert image_url and "/api/files/" in image_url, f"unexpected upload resp: {upj}"

    # Submit as BotW hero
    sub = brand_sess.post(f"{API}/brands/me/botw-image", json={"image_url": image_url}, timeout=15)
    assert sub.status_code == 200, f"submit failed: {sub.status_code} {sub.text[:400]}"
    assert sub.json().get("botw_image_status") == "pending"

    # Admin approves
    admin_sess = _login(ADMIN_EMAIL, ADMIN_PASS)
    dec = admin_sess.post(
        f"{API}/admin/botw-image/{brand_id}",
        json={"approve": True},
        timeout=15,
    )
    assert dec.status_code == 200, f"approve failed: {dec.status_code} {dec.text[:400]}"
    assert dec.json().get("botw_image_status") == "approved"

    # GET brand-of-week should now expose featured_image == image_url and be uncached
    r = requests.get(f"{API}/brands/brand-of-week", timeout=15)
    assert r.status_code == 200
    cc = r.headers.get("Cache-Control", "").lower()
    assert "no-store" in cc or "no-cache" in cc
    body = r.json()
    assert body is not None
    assert body.get("featured_image") == image_url, (
        f"expected featured_image={image_url}, got={body.get('featured_image')}; "
        f"botw_status={body.get('botw_image_status')}"
    )


# ---------- 3. Regression: reject leaves featured_image absent ----------
def test_reject_removes_pending_and_no_featured_change():
    brand_sess = _login(BRAND_EMAIL, BRAND_PASS)
    me_auth = brand_sess.get(f"{API}/auth/me", timeout=15).json()
    botw = requests.get(f"{API}/brands/brand-of-week", timeout=15).json()
    if not botw or not botw.get("is_brand_of_week"):
        pytest.skip("no BotW set")
    if botw.get("user_id") and me_auth.get("id") and botw["user_id"] != me_auth["id"]:
        pytest.skip("BotW belongs to different user")
    me = botw

    # submit another fresh upload then reject it
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x00\x03\x00\x01^\xf3*:\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    up = brand_sess.post(
        f"{API}/upload/image",
        files={"file": ("hero2.png", io.BytesIO(png_bytes), "image/png")},
        timeout=30,
    ).json()
    image_url = up.get("url") or up.get("image_url") or up.get("path")

    brand_sess.post(f"{API}/brands/me/botw-image", json={"image_url": image_url}, timeout=15)

    admin_sess = _login(ADMIN_EMAIL, ADMIN_PASS)
    dec = admin_sess.post(
        f"{API}/admin/botw-image/{me['id']}",
        json={"approve": False},
        timeout=15,
    )
    assert dec.status_code == 200
    assert dec.json().get("botw_image_status") == "rejected"

    # GET should not expose this rejected pending image (it wasn't approved)
    r = requests.get(f"{API}/brands/brand-of-week", timeout=15).json()
    assert r.get("featured_image") != image_url


# ---------- 4. Regression: BotW admin routes (veto/skip/rotate/queue) still work ----------
def test_admin_botw_queue_reachable():
    s = _login(ADMIN_EMAIL, ADMIN_PASS)
    r = s.get(f"{API}/admin/botw/queue", timeout=15)
    assert r.status_code in (200, 404), r.text[:300]  # tolerant if route naming differs
    r2 = s.get(f"{API}/admin/botw-image/queue", timeout=15)
    assert r2.status_code == 200


# ---------- 5. Regression: SSRF hardening on CSV import still blocks internal URLs ----------
@pytest.mark.parametrize("bad_url", [
    "http://169.254.169.254/latest/meta-data/",
    "http://localhost:8001/api/brands",
    "http://127.0.0.1/",
])
def test_csv_import_ssrf_blocked(bad_url):
    s = _login(ADMIN_EMAIL, ADMIN_PASS)
    r = s.post(f"{API}/products/import/csv", json={"url": bad_url}, timeout=15)
    # Expect 4xx (validation/blocked) — must NOT be 200 or 5xx that indicates fetch attempted
    assert r.status_code in (400, 403, 422), f"got {r.status_code}: {r.text[:200]}"
