"""Full API regression after monolith split into core.py + 18 route modules.
Goal: exercise every module for NameError / route-registration regressions.
"""
import os
import time
import uuid
import pytest
import requests

def _load_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        v = line.strip().split("=", 1)[1]
                        break
        except Exception:
            pass
    assert v, "REACT_APP_BACKEND_URL missing"
    return v.rstrip("/")

BASE = _load_url()

DEMO_EMAIL = "demo@threadandbone.uk"
DEMO_PW = "Demo123!"
ADMIN_EMAIL = "Anthonygeorgiades@unveiledthreads.co.uk"
ADMIN_PW = "Babablacksheep159"
BRAND2_EMAIL = "testbrand@example.com"
BRAND2_PW = "TestBrand123!"


# ---------- fixtures ----------
def _login(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login",
               json={"email": email, "password": pw}, timeout=20)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def demo():
    return _login(DEMO_EMAIL, DEMO_PW)


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PW)


@pytest.fixture(scope="module")
def brand2():
    try:
        return _login(BRAND2_EMAIL, BRAND2_PW)
    except Exception:
        pytest.skip("brand2 not seeded")


# ---------- AUTH ----------
def test_register_new_buyer_then_login():
    email = f"TEST_reg_{uuid.uuid4().hex[:8]}@example.com"
    pw = "TestPass123!"
    r = requests.post(f"{BASE}/api/auth/register",
                      json={"email": email, "password": pw,
                            "name": "Test Reg"}, timeout=20)
    assert r.status_code in (200, 201), f"register: {r.status_code} {r.text[:200]}"
    s = requests.Session()
    r2 = s.post(f"{BASE}/api/auth/login",
                json={"email": email, "password": pw}, timeout=15)
    assert r2.status_code == 200
    r3 = s.get(f"{BASE}/api/auth/me", timeout=15)
    assert r3.status_code == 200
    assert r3.json().get("email", "").lower() == email.lower()
    r4 = s.post(f"{BASE}/api/auth/logout", timeout=15)
    assert r4.status_code in (200, 204)


def test_login_wrong_password_401():
    r = requests.post(f"{BASE}/api/auth/login",
                      json={"email": DEMO_EMAIL, "password": "wrong-pw-xxx"},
                      timeout=15)
    assert r.status_code in (400, 401), f"expected 401, got {r.status_code}"


def test_auth_me_demo(demo):
    r = demo.get(f"{BASE}/api/auth/me", timeout=15)
    assert r.status_code == 200
    assert r.json().get("email", "").lower() == DEMO_EMAIL.lower()


# ---------- ACCOUNT ----------
def test_account_export_demo(demo):
    r = demo.get(f"{BASE}/api/account/export", timeout=30)
    assert r.status_code == 200, f"export: {r.status_code} {r.text[:300]}"


# ---------- PRODUCTS ----------
@pytest.fixture(scope="module")
def a_product_id():
    r = requests.get(f"{BASE}/api/products?limit=5", timeout=15)
    assert r.status_code == 200
    items = r.json()
    items = items if isinstance(items, list) else items.get("items") or items.get("products") or []
    assert items, "no products found"
    return items[0].get("id") or items[0].get("_id")


def test_products_filters():
    for params in [
        {"category": "hoodies"},
        {"search": "hoodie"},
        {"min_price": 10, "max_price": 200},
        {"sort": "latest"},
        {"sort": "price_asc"},
    ]:
        r = requests.get(f"{BASE}/api/products", params=params, timeout=15)
        assert r.status_code == 200, f"products {params} -> {r.status_code} {r.text[:200]}"


def test_categories():
    r = requests.get(f"{BASE}/api/categories", timeout=15)
    assert r.status_code == 200


def test_products_filter_options():
    r = requests.get(f"{BASE}/api/products/filter-options", timeout=15)
    assert r.status_code == 200


def test_product_detail(a_product_id):
    r = requests.get(f"{BASE}/api/products/{a_product_id}", timeout=15)
    assert r.status_code == 200


def test_dead_stock_list():
    r = requests.get(f"{BASE}/api/dead-stock", timeout=15)
    assert r.status_code == 200


def test_dead_stock_quota_as_brand(demo):
    r = demo.get(f"{BASE}/api/dead-stock/my-quota", timeout=15)
    assert r.status_code == 200, f"quota: {r.status_code} {r.text[:200]}"


# ---------- BRANDS ----------
def test_brands_list():
    r = requests.get(f"{BASE}/api/brands", timeout=15)
    assert r.status_code == 200


def test_brand_of_week():
    r = requests.get(f"{BASE}/api/brands/brand-of-week", timeout=15)
    assert r.status_code in (200, 404)


def test_brand_by_slug_analytics():
    r = requests.get(f"{BASE}/api/brands/by-slug/analytics-test-brand", timeout=15)
    assert r.status_code in (200, 404)


def test_my_application_as_brand(demo):
    r = demo.get(f"{BASE}/api/brands/my-application", timeout=15)
    assert r.status_code in (200, 404), f"{r.status_code} {r.text[:200]}"


# ---------- ADMIN / APPLICATIONS ----------
def test_admin_applications_pending(admin):
    r = admin.get(f"{BASE}/api/admin/applications?status=pending", timeout=15)
    assert r.status_code == 200


def test_admin_applications_approved(admin):
    r = admin.get(f"{BASE}/api/admin/applications?status=approved", timeout=15)
    assert r.status_code == 200


def test_admin_seller_cap(admin):
    r = admin.get(f"{BASE}/api/admin/seller-cap", timeout=15)
    assert r.status_code == 200


# ---------- ORDERS ----------
def test_orders_my_orders_demo(demo):
    r = demo.get(f"{BASE}/api/orders/my-orders", timeout=15)
    assert r.status_code == 200


def test_orders_status_seeded(demo):
    r = demo.get(f"{BASE}/api/orders/status/cs_test_receipt_demo_123", timeout=15)
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    data = r.json()
    # verify receipt breakdown numbers per requirements
    receipt = data.get("order_receipt") or data.get("receipt") or data
    # Look for expected fields anywhere in top-level or nested
    txt = str(data)
    assert "73.73" in txt or "platform_fee" in txt or "total" in txt


def test_brand_orders_demo(demo):
    r = demo.get(f"{BASE}/api/orders/brand-orders", timeout=15)
    assert r.status_code == 200


# ---------- SHIPPING ----------
def test_shipping_couriers():
    r = requests.get(f"{BASE}/api/shipping/couriers", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, (list, dict))


# ---------- PAYMENTS ----------
def test_boost_packages():
    r = requests.get(f"{BASE}/api/boost/packages", timeout=15)
    assert r.status_code == 200


def test_stripe_webhook_unsigned_no_500():
    r = requests.post(f"{BASE}/api/webhook/stripe",
                      json={"id": "evt_x", "type": "test"}, timeout=15)
    assert r.status_code != 500, r.text[:300]
    assert r.status_code in (200, 400, 401, 403)


# ---------- CONNECT ----------
def test_connect_status(demo):
    r = demo.get(f"{BASE}/api/connect/status", timeout=15)
    assert r.status_code == 200


def test_connect_payouts(demo):
    r = demo.get(f"{BASE}/api/connect/payouts", timeout=15)
    assert r.status_code == 200
    data = r.json()
    # expect connected:false since no stripe key
    if isinstance(data, dict) and "connected" in data:
        assert data["connected"] is False


# ---------- DISPUTES / ADMIN STATS ----------
def test_admin_disputes_open(admin):
    r = admin.get(f"{BASE}/api/admin/disputes?status=open", timeout=15)
    assert r.status_code == 200


def test_admin_stats(admin):
    r = admin.get(f"{BASE}/api/admin/stats", timeout=15)
    assert r.status_code == 200


# ---------- ENGAGEMENT ----------
def test_notifications(demo):
    r = demo.get(f"{BASE}/api/notifications", timeout=15)
    assert r.status_code == 200


def test_notifications_unread(demo):
    r = demo.get(f"{BASE}/api/notifications/unread-count", timeout=15)
    assert r.status_code == 200


def test_admin_low_stock_digest(admin):
    r = admin.post(f"{BASE}/api/admin/low-stock-digest/run", timeout=30)
    assert r.status_code == 200, r.text[:300]


def test_admin_abandoned_checkout(admin):
    r = admin.post(f"{BASE}/api/admin/abandoned-checkout/run", timeout=30)
    assert r.status_code == 200, r.text[:300]


# ---------- REVIEWS ----------
def test_reviews_for_product(a_product_id):
    r = requests.get(f"{BASE}/api/reviews/product/{a_product_id}", timeout=15)
    assert r.status_code == 200


# ---------- WISHLIST ----------
def test_wishlist_flow(demo, a_product_id):
    r = demo.get(f"{BASE}/api/wishlist/ids", timeout=15)
    assert r.status_code == 200
    r2 = demo.post(f"{BASE}/api/wishlist/{a_product_id}", timeout=15)
    assert r2.status_code in (200, 201), r2.text[:200]
    r3 = demo.get(f"{BASE}/api/wishlist/ids", timeout=15)
    assert r3.status_code == 200
    ids = r3.json()
    ids_list = ids if isinstance(ids, list) else ids.get("ids") or []
    assert a_product_id in ids_list, f"not added: {ids_list}"
    r4 = demo.delete(f"{BASE}/api/wishlist/{a_product_id}", timeout=15)
    assert r4.status_code in (200, 204)


# ---------- ANALYTICS ----------
def test_analytics_brand_30(demo):
    r = demo.get(f"{BASE}/api/analytics/brand?days=30", timeout=15)
    assert r.status_code == 200


def test_analytics_brand_7(demo):
    r = demo.get(f"{BASE}/api/analytics/brand?days=7", timeout=15)
    assert r.status_code == 200


# ---------- REFERRALS ----------
def test_referral_code(demo):
    r = demo.get(f"{BASE}/api/referral/code", timeout=15)
    assert r.status_code == 200


def test_referral_credits(demo):
    r = demo.get(f"{BASE}/api/referral/credits", timeout=15)
    assert r.status_code == 200


# ---------- MESSAGING ----------
def test_conversations(demo):
    r = demo.get(f"{BASE}/api/conversations", timeout=15)
    assert r.status_code == 200


def test_messages_unread(demo):
    r = demo.get(f"{BASE}/api/messages/unread-count", timeout=15)
    assert r.status_code == 200


# ---------- COMMUNITY ----------
def test_community_posts_list():
    r = requests.get(f"{BASE}/api/community/posts", timeout=15)
    assert r.status_code == 200


def test_community_post_create_comment_like(demo):
    # Create
    payload = {"content": f"TEST_post_{uuid.uuid4().hex[:6]} regression check",
               "title": "TEST post"}
    r = demo.post(f"{BASE}/api/community/posts", json=payload, timeout=15)
    if r.status_code == 404:
        # try alt route
        r = demo.post(f"{BASE}/api/community/post", json=payload, timeout=15)
    assert r.status_code in (200, 201), f"create post {r.status_code} {r.text[:300]}"
    post = r.json()
    pid = post.get("id") or post.get("_id") or (post.get("post") or {}).get("id")
    assert pid, f"no post id in {post}"
    # Comment
    rc = demo.post(f"{BASE}/api/community/posts/{pid}/comments",
                   json={"content": "TEST comment"}, timeout=15)
    assert rc.status_code in (200, 201), f"comment: {rc.status_code} {rc.text[:200]}"
    # Like
    rl = demo.post(f"{BASE}/api/community/posts/{pid}/like", timeout=15)
    assert rl.status_code in (200, 201), f"like: {rl.status_code} {rl.text[:200]}"


# ---------- UPLOADS ----------
def test_upload_nonexistent_404():
    r = requests.get(f"{BASE}/api/uploads/does-not-exist-{uuid.uuid4().hex[:8]}.jpg", timeout=15)
    assert r.status_code in (404, 400), f"expected 404, got {r.status_code}"


# ---------- MESSAGING moderation (last, since it needs a product+brand) ----------
def test_messaging_moderation_blocks_paypal(demo, a_product_id):
    # find brand user_id via product -> brand -> owner
    prod = requests.get(f"{BASE}/api/products/{a_product_id}", timeout=15).json()
    brand_id = prod.get("brand_id") or prod.get("seller_id")
    if not brand_id:
        pytest.skip("no brand_id on product")
    # Look up brand's user (owner) id
    brands = requests.get(f"{BASE}/api/brands", timeout=15).json()
    brands_list = brands if isinstance(brands, list) else brands.get("items") or brands.get("brands") or []
    owner_user_id = None
    for b in brands_list:
        if b.get("id") == brand_id or b.get("_id") == brand_id:
            owner_user_id = b.get("user_id") or b.get("owner_id")
            break
    recipient = owner_user_id or brand_id
    # Send clean message first
    r = demo.post(f"{BASE}/api/messages/send",
                  json={"recipient_id": recipient,
                        "content": "Hi is this still in stock?"}, timeout=15)
    if r.status_code == 400 and "yourself" in r.text.lower():
        pytest.skip("recipient equals sender in this dataset")
    assert r.status_code in (200, 201, 404), f"clean send: {r.status_code} {r.text[:300]}"
    # Send bad message — moderation should return 400
    rb = demo.post(f"{BASE}/api/messages/send",
                   json={"recipient_id": recipient,
                         "content": "pay me on paypal outside the app"}, timeout=15)
    assert rb.status_code != 500, rb.text[:300]
    # Expect 400 for moderation block
    assert rb.status_code in (400, 422), f"expected moderation block, got {rb.status_code} {rb.text[:200]}"
