# Backend tests for the CSV product-import feature (iteration 14).
# Covers: auth, grouping, image fetch, drafts hiding, publish gates.
import os
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://uk-streetwear-hub.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

BRAND_EMAIL = "demo@threadandbone.uk"
BRAND_PASS = "Demo123!"

SHOPIFY_CSV = """Handle,Title,Body (HTML),Vendor,Product Type,Tags,Option1 Name,Option1 Value,Variant Price,Variant Inventory Qty,Image Src
smithfield-hoodie,Smithfield Hoodie,<p>Heavyweight <strong>hoodie</strong> from East London.</p><p>Small batch craft.</p>,Thread & Bone,hoodies,streetwear,Size,S,85.00,10,https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=800
smithfield-hoodie,Smithfield Hoodie,,,,,Size,M,85.00,8,https://images.unsplash.com/photo-1571945153237-4929e783af4a?w=800
smithfield-hoodie,,,,,,Size,L,85.00,5,
smithfield-hoodie,,,,,,Size,XL,85.00,2,
brick-lane-tee,Brick Lane Tee - White,<p>220gsm organic cotton screen print.</p>,Thread & Bone,t-shirts,,Size,S,35.00,20,https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=800
brick-lane-tee,Brick Lane Tee - White,,,,,Size,M,35.00,15,
brick-lane-tee,,,,,,Size,L,35.00,12,
no-price-product,Broken Product,<p>This one has no price and should skip.</p>,Thread & Bone,accessories,,Size,One Size,,5,https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=800
"""

TINY_INVALID_CSV = "Handle,Title,Variant Price\nfoo,,\n"


@pytest.fixture(scope="module")
def brand_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": BRAND_EMAIL, "password": BRAND_PASS}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Brand login failed: {r.status_code} {r.text}")
    return s


@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


class TestAuthGates:
    def test_import_requires_auth(self, anon_session):
        files = {"file": ("t.csv", io.BytesIO(SHOPIFY_CSV.encode()), "text/csv")}
        r = anon_session.post(f"{API}/products/import/csv", files=files, timeout=15)
        assert r.status_code in (401, 403), f"Expected 401/403 got {r.status_code}"

    def test_drafts_list_requires_auth(self, anon_session):
        r = anon_session.get(f"{API}/products/my/drafts", timeout=15)
        assert r.status_code in (401, 403)


class TestCSVImport:
    def test_import_shopify_csv_groups_variants(self, brand_session):
        files = {"file": ("shopify.csv", io.BytesIO(SHOPIFY_CSV.encode()), "text/csv")}
        r = brand_session.post(f"{API}/products/import/csv", files=files, timeout=120)
        assert r.status_code == 200, f"Import failed: {r.status_code} {r.text}"
        data = r.json()
        # Expect 2 products created (Smithfield Hoodie + Brick Lane Tee), 1 skipped (no price)
        assert data["created"] == 2, f"Expected 2 created got {data}"
        assert data["skipped"] == 1, f"Expected 1 skipped got {data}"
        assert len(data["errors"]) == 1
        assert "price" in data["errors"][0]["reason"].lower()
        assert "row" in data["errors"][0]
        # Save for later tests
        pytest.created_ids = data["created_ids"]
        pytest.import_data = data

    def test_created_drafts_grouped_correctly(self, brand_session):
        r = brand_session.get(f"{API}/products/my/drafts", timeout=30)
        assert r.status_code == 200
        drafts = r.json()
        assert isinstance(drafts, list)
        # Find our just-created ones
        recent_ids = set(getattr(pytest, "created_ids", []))
        mine = [d for d in drafts if d["id"] in recent_ids]
        assert len(mine) == 2

        hoodie = next((d for d in mine if "Smithfield" in d["name"]), None)
        tee = next((d for d in mine if "Brick Lane" in d["name"]), None)
        assert hoodie is not None and tee is not None

        # Hoodie should have 4 sizes S/M/L/XL grouped
        assert set(hoodie["sizes"]) >= {"S", "M", "L", "XL"}, f"Sizes: {hoodie['sizes']}"
        # Tee should have S/M/L
        assert set(tee["sizes"]) >= {"S", "M", "L"}, f"Sizes: {tee['sizes']}"

        # Status and import_source
        assert hoodie["status"] == "draft"
        assert hoodie["import_source"] == "csv"
        assert tee["status"] == "draft"

        # Price picked up from first row that had it
        assert hoodie["price"] == 85.00
        assert tee["price"] == 35.00

        # Images should be stored locally under /api/files/, NOT external URLs
        for img in hoodie.get("images", []):
            assert img.startswith("/api/files/"), f"External URL leaked: {img}"
            assert "unsplash" not in img
            assert "shopify" not in img

        pytest.hoodie_id = hoodie["id"]
        pytest.tee_id = tee["id"]

    def test_drafts_hidden_from_public_list(self, anon_session):
        r = anon_session.get(f"{API}/products", timeout=30)
        assert r.status_code == 200
        products = r.json()
        draft_ids = set(getattr(pytest, "created_ids", []))
        visible_ids = {p.get("id") for p in products}
        assert draft_ids.isdisjoint(visible_ids), "Drafts leaked into public list"

    def test_draft_detail_404_for_anon(self, anon_session):
        pid = getattr(pytest, "hoodie_id", None)
        if not pid:
            pytest.skip("no draft created")
        r = anon_session.get(f"{API}/products/{pid}", timeout=15)
        assert r.status_code == 404

    def test_draft_detail_visible_to_owning_brand(self, brand_session):
        pid = getattr(pytest, "hoodie_id", None)
        if not pid:
            pytest.skip("no draft")
        r = brand_session.get(f"{API}/products/{pid}", timeout=15)
        assert r.status_code == 200
        assert r.json().get("status") == "draft"

    def test_checkout_on_draft_returns_404(self, brand_session):
        pid = getattr(pytest, "hoodie_id", None)
        if not pid:
            pytest.skip("no draft")
        r = brand_session.post(f"{API}/orders/checkout",
                               json={"product_id": pid, "size": "S", "quantity": 1,
                                     "origin_url": BASE_URL},
                               timeout=15)
        assert r.status_code == 404, f"Expected 404 on draft checkout, got {r.status_code} {r.text}"


class TestPublish:
    def test_publish_valid_draft(self, brand_session):
        pid = getattr(pytest, "hoodie_id", None)
        if not pid:
            pytest.skip("no draft")
        # Refresh draft first
        r = brand_session.get(f"{API}/products/{pid}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        r = brand_session.post(f"{API}/products/{pid}/publish", timeout=30)
        if d.get("missing_images") or not d.get("images"):
            # If image fetch failed, expect 422 blocker
            assert r.status_code == 422
            assert "image" in r.json().get("detail", "").lower()
            pytest.hoodie_published = False
        else:
            assert r.status_code == 200, f"Publish failed: {r.status_code} {r.text}"
            assert r.json()["status"] == "published"
            pytest.hoodie_published = True

    def test_published_appears_in_public_list(self, anon_session):
        if not getattr(pytest, "hoodie_published", False):
            pytest.skip("hoodie not published (missing images)")
        pid = pytest.hoodie_id
        r = anon_session.get(f"{API}/products", timeout=30)
        assert r.status_code == 200
        ids = {p.get("id") for p in r.json()}
        assert pid in ids

    def test_publish_all_returns_skipped_details(self, brand_session):
        r = brand_session.post(f"{API}/products/drafts/publish-all", timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert "published" in data
        assert "skipped" in data
        assert "skipped_details" in data
        # Each skipped item should carry a reason
        for s in data["skipped_details"]:
            assert "reason" in s and s["reason"]

    def test_publish_nonexistent_returns_404(self, brand_session):
        r = brand_session.post(f"{API}/products/507f1f77bcf86cd799439011/publish", timeout=15)
        assert r.status_code == 404


class TestCapsAndValidation:
    def test_empty_csv_rejected(self, brand_session):
        files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
        r = brand_session.post(f"{API}/products/import/csv", files=files, timeout=15)
        assert r.status_code == 400

    def test_only_header_csv_rejected(self, brand_session):
        files = {"file": ("h.csv", io.BytesIO(b"Handle,Title\n"), "text/csv")}
        r = brand_session.post(f"{API}/products/import/csv", files=files, timeout=15)
        assert r.status_code == 400

    def test_oversize_csv_rejected(self, brand_session):
        # Build > 5MB CSV
        row = b"h,t,1.0\n"
        big = b"Handle,Title,Variant Price\n" + (row * ((5 * 1024 * 1024 // len(row)) + 1000))
        files = {"file": ("big.csv", io.BytesIO(big), "text/csv")}
        r = brand_session.post(f"{API}/products/import/csv", files=files, timeout=30)
        assert r.status_code == 400


class TestBackwardCompat:
    def test_products_without_status_field_still_visible(self, anon_session):
        r = anon_session.get(f"{API}/products", timeout=30)
        assert r.status_code == 200
        # Just verify endpoint works & returns list; existing legacy products count > 0 not guaranteed
        assert isinstance(r.json(), list)


def teardown_module(module):
    # Clean up any drafts we created
    try:
        s = requests.Session()
        s.post(f"{API}/auth/login", json={"email": BRAND_EMAIL, "password": BRAND_PASS}, timeout=10)
        for pid in getattr(pytest, "created_ids", []):
            s.delete(f"{API}/products/{pid}", timeout=10)
    except Exception:
        pass
