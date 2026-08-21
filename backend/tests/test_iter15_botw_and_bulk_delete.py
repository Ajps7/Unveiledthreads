"""Iteration 15 backend regression tests:
   - Bulk delete drafts (POST /api/products/drafts/delete-many)
   - Brand of the Week auto-rotation admin endpoints (/api/admin/botw/*)

Uses the same public REACT_APP_BACKEND_URL as all other suites, driven via
cookie sessions (admin + brand). Reads test credentials from
/app/memory/test_credentials.md.
"""
import os
import io
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.strip().split("=", 1)[1].rstrip("/")
                break

ADMIN_EMAIL = "anthonygeorgiades@unveiledthreads.co.uk"
ADMIN_PASSWORD = "Babablacksheep159"
BRAND_EMAIL = "demo@threadandbone.uk"
BRAND_PASSWORD = "Demo123!"


# ---------- Session fixtures ----------
def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def brand():
    return _login(BRAND_EMAIL, BRAND_PASSWORD)


@pytest.fixture(scope="module")
def unauth():
    return requests.Session()


# ============ BULK DELETE DRAFTS ============
def _create_draft_via_csv(brand_session: requests.Session, name: str) -> str:
    """Create a single draft by uploading a tiny CSV. Returns product_id."""
    csv_bytes = (
        "Title,Body (HTML),Product Type,Option1 Value,Variant Price,Variant Inventory Qty,Image Src\n"
        f"{name},A test draft product for iter15 regression suite,accessories,One Size,25.00,5,\n"
    ).encode("utf-8")
    r = brand_session.post(
        f"{BASE}/api/products/import/csv",
        files={"file": (f"{name}.csv", io.BytesIO(csv_bytes), "text/csv")},
        timeout=30,
    )
    assert r.status_code == 200, f"csv import failed: {r.status_code} {r.text}"
    ids = r.json().get("created_ids", [])
    assert ids, f"no drafts created: {r.json()}"
    return ids[0]


class TestBulkDeleteDrafts:
    def test_empty_ids_returns_422(self, brand):
        r = brand.post(f"{BASE}/api/products/drafts/delete-many", json={"ids": []}, timeout=15)
        assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"

    def test_all_invalid_ids_returns_400(self, brand):
        r = brand.post(
            f"{BASE}/api/products/drafts/delete-many",
            json={"ids": ["not-an-objectid", "still-not"]},
            timeout=15,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"

    def test_bulk_delete_own_drafts_succeeds(self, brand):
        # Create 2 drafts, delete both in one call
        id1 = _create_draft_via_csv(brand, "TEST_iter15_bulk_A")
        id2 = _create_draft_via_csv(brand, "TEST_iter15_bulk_B")
        r = brand.post(
            f"{BASE}/api/products/drafts/delete-many",
            json={"ids": [id1, id2]},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("deleted") == 2, f"expected deleted=2, got {data}"

        # Verify persistence: GET drafts should not include them
        r2 = brand.get(f"{BASE}/api/products/my/drafts", timeout=15)
        assert r2.status_code == 200
        remaining = {d["id"] for d in r2.json()}
        assert id1 not in remaining and id2 not in remaining

    def test_bulk_delete_foreign_ids_deletes_zero(self, brand):
        # Fake objectid that's syntactically valid but not owned
        fake_id = "507f1f77bcf86cd799439011"
        r = brand.post(
            f"{BASE}/api/products/drafts/delete-many",
            json={"ids": [fake_id]},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("deleted") == 0


# ============ BOTW ADMIN ENDPOINTS ============
class TestBotwAdmin:
    def test_queue_requires_admin(self, brand, unauth):
        r = unauth.get(f"{BASE}/api/admin/botw/queue", timeout=15)
        assert r.status_code in (401, 403), f"unauth got {r.status_code}"
        r2 = brand.get(f"{BASE}/api/admin/botw/queue", timeout=15)
        assert r2.status_code == 403, f"brand got {r2.status_code}: {r2.text}"

    def test_queue_returns_expected_shape(self, admin):
        r = admin.get(f"{BASE}/api/admin/botw/queue", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        for key in (
            "current_brand_id", "current_brand",
            "next_brand_id", "next_scheduled_at",
            "cycle_index", "will_be_performance_pick", "eligible_brands",
        ):
            assert key in data, f"missing key '{key}' in queue response: {list(data.keys())}"
        assert isinstance(data["eligible_brands"], list)

    def test_veto_invalid_brand_id_400(self, admin):
        r = admin.post(f"{BASE}/api/admin/botw/veto", json={"brand_id": "nope"}, timeout=15)
        assert r.status_code == 400, r.text

    def test_veto_unknown_brand_id_404(self, admin):
        # Valid ObjectId shape, non-existent
        r = admin.post(
            f"{BASE}/api/admin/botw/veto",
            json={"brand_id": "507f1f77bcf86cd799439099"},
            timeout=15,
        )
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"

    def test_veto_requires_admin(self, brand):
        r = brand.post(
            f"{BASE}/api/admin/botw/veto",
            json={"brand_id": "507f1f77bcf86cd799439011"},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_skip_recomputes_and_returns_candidate(self, admin):
        r = admin.post(f"{BASE}/api/admin/botw/skip", json={}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # Either a candidate was picked, or the pool was empty (both valid).
        assert "next_brand_id" in data or "message" in data

    def test_skip_requires_admin(self, brand):
        r = brand.post(f"{BASE}/api/admin/botw/skip", json={}, timeout=15)
        assert r.status_code == 403

    def test_veto_with_valid_brand_succeeds(self, admin):
        # Grab first eligible brand from queue
        q = admin.get(f"{BASE}/api/admin/botw/queue", timeout=15).json()
        eligible = q.get("eligible_brands") or []
        if not eligible:
            pytest.skip("No eligible brands to veto to")
        target = eligible[0]
        r = admin.post(
            f"{BASE}/api/admin/botw/veto",
            json={"brand_id": target["id"]},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["next_brand_id"] == target["id"]
        assert data.get("brand_name") == target["brand_name"]

        # Verify persistence
        q2 = admin.get(f"{BASE}/api/admin/botw/queue", timeout=15).json()
        assert q2.get("next_brand_id") == target["id"]

    def test_rotate_now_promotes_and_flips_botw(self, admin):
        # Ensure a next_brand_id is queued (veto in previous test may have set it)
        q = admin.get(f"{BASE}/api/admin/botw/queue", timeout=15).json()
        prev_cycle = int(q.get("cycle_index") or 0)
        queued_next_id = q.get("next_brand_id")

        r = admin.post(f"{BASE}/api/admin/botw/rotate-now", json={}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["cycle_index"] == prev_cycle + 1, f"cycle didn't increment: {data}"
        new_current = data.get("current_brand_id")
        assert new_current, "no current_brand_id after rotate-now"
        if queued_next_id:
            assert new_current == queued_next_id, "rotate-now didn't promote the queued brand"

        # Public endpoint should return the newly-promoted brand.
        pub = requests.get(f"{BASE}/api/brands/brand-of-week", timeout=15)
        assert pub.status_code == 200, pub.text
        pub_data = pub.json()
        assert str(pub_data.get("id") or pub_data.get("_id") or "") == new_current or \
               pub_data.get("is_brand_of_week") is True, \
               f"public brand-of-week mismatch: {pub_data}"

    def test_rotate_now_requires_admin(self, brand):
        r = brand.post(f"{BASE}/api/admin/botw/rotate-now", json={}, timeout=15)
        assert r.status_code == 403
