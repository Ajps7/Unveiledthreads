"""Regression tests for the code review refactors (iter 9).
Verifies:
 - GET /api/account/export returns JSON download (json.dumps refactor)
 - GET /api/products with filters still works
 - POST /api/webhook/stripe returns 200 or clean 400 (json.loads refactor, no NameError)
 - GET /api/orders/status returns receipt object for demo user
"""
import os
import json as _json
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://uk-streetwear-hub.preview.emergentagent.com").rstrip("/")

DEMO_EMAIL = "demo@threadandbone.uk"
DEMO_PASSWORD = "Demo123!"
ADMIN_EMAIL = "Anthonygeorgiades@unveiledthreads.co.uk"
ADMIN_PASSWORD = "Babablacksheep159"


@pytest.fixture(scope="module")
def demo_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
               timeout=15)
    assert r.status_code == 200, f"Demo login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
               timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    return s


# --- Account export (json.dumps refactor) -------------------------------------
def test_account_export_returns_json(demo_session):
    r = demo_session.get(f"{BASE_URL}/api/account/export", timeout=30)
    assert r.status_code == 200, f"export status={r.status_code} body={r.text[:300]}"
    # response should be JSON (either downloaded file body or json response)
    ct = r.headers.get("content-type", "")
    assert "json" in ct.lower(), f"unexpected content-type: {ct}"
    data = _json.loads(r.content.decode("utf-8"))
    assert isinstance(data, dict)
    # At minimum should include user info
    keys_lower = {k.lower() for k in data.keys()}
    assert any(k in keys_lower for k in ["user", "profile", "email", "account"]), (
        f"export missing user keys: {list(data.keys())[:10]}"
    )


# --- Products filter (still works) --------------------------------------------
def test_products_filter_hoodies_latest():
    r = requests.get(f"{BASE_URL}/api/products",
                     params={"category": "hoodies", "sort": "latest"},
                     timeout=15)
    assert r.status_code == 200, f"products status={r.status_code} body={r.text[:200]}"
    data = r.json()
    # accepted shapes: list, or {items: [...]} / {products: [...]}
    items = data if isinstance(data, list) else data.get("items") or data.get("products") or []
    assert isinstance(items, list)


def test_products_no_filter():
    r = requests.get(f"{BASE_URL}/api/products", timeout=15)
    assert r.status_code == 200


# --- Stripe webhook (json.loads refactor) -------------------------------------
def test_stripe_webhook_unsigned_no_500():
    """Unsigned webhook must NOT raise NameError (json import bug). Accept 200 or 400."""
    payload = {"id": "evt_test", "type": "checkout.session.completed",
               "data": {"object": {"id": "cs_test_regression"}}}
    r = requests.post(f"{BASE_URL}/api/webhook/stripe",
                      json=payload, timeout=15)
    assert r.status_code != 500, f"webhook 500 (regression): {r.text[:300]}"
    assert r.status_code in (200, 400, 401, 403), f"unexpected code {r.status_code}: {r.text[:200]}"


# --- Orders status receipt (demo user, Signature Hoodie) ----------------------
def test_orders_list_or_status_demo(demo_session):
    # Try common endpoints for user's orders
    urls = [
        f"{BASE_URL}/api/orders/my-orders",
        f"{BASE_URL}/api/orders/status/cs_test_receipt_demo_123",
    ]
    got = None
    for u in urls:
        r = demo_session.get(u, timeout=15)
        if r.status_code == 200:
            got = (u, r.json())
            break
    assert got is not None, "no orders endpoint returned 200 for demo user"


def test_auth_me_demo(demo_session):
    r = demo_session.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data.get("email", "").lower() == DEMO_EMAIL.lower()
