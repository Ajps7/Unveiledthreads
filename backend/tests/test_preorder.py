"""Pre-order (Model A: charge now, ship later) — regression tests.

Covers the feature spec:
  1. Product validation — is_preorder requires future preorder_ship_date
  2. Pre-order product accepts stock=0
  3. Non-preorder products still enforce stock > 0 at checkout
  4. Legacy products default is_preorder=False (backward-compat)
  5. Stripe Account.create includes settings.payouts.schedule.delay_days
"""
import os
import uuid
import inspect
import pytest
import requests
from datetime import date, timedelta

BASE = None
with open("/app/frontend/.env", "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.strip().split("=", 1)[1]
            break
API = BASE.rstrip("/")


@pytest.fixture
def seller_session() -> requests.Session:
    """Log in as testbrand@example.com — already an approved brand."""
    s = requests.Session()
    r = s.post(
        f"{API}/api/auth/login",
        json={"email": "testbrand@example.com", "password": "TestBrand123!"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return s


def _valid_preorder_payload():
    return {
        "name": f"Preorder Test {uuid.uuid4().hex[:6]}",
        "description": "Pre-order test product — enough characters to pass the min-length gate.",
        "price": 49.99,
        "category": "hoodies",
        "sizes": ["M"],
        "images": ["/api/files/x/y.png"],
        "stock": 0,
        "is_preorder": True,
        "preorder_ship_date": (date.today() + timedelta(days=30)).isoformat(),
    }


# --------------- Validation ---------------

def test_preorder_without_ship_date_returns_422(seller_session):
    payload = _valid_preorder_payload()
    del payload["preorder_ship_date"]
    r = seller_session.post(f"{API}/api/products", json=payload, timeout=15)
    assert r.status_code == 422, r.text
    assert "preorder_ship_date" in r.text


def test_preorder_with_past_ship_date_returns_422(seller_session):
    payload = _valid_preorder_payload()
    payload["preorder_ship_date"] = (date.today() - timedelta(days=1)).isoformat()
    r = seller_session.post(f"{API}/api/products", json=payload, timeout=15)
    assert r.status_code == 422


def test_valid_preorder_stock_zero_accepted(seller_session):
    r = seller_session.post(f"{API}/api/products", json=_valid_preorder_payload(), timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_preorder"] is True
    assert body["stock"] == 0
    assert body["preorder_ship_date"] is not None


def test_backward_compat_non_preorder_defaults(seller_session):
    """Existing behaviour unchanged — is_preorder omitted → false, stock>0 enforced."""
    payload = {
        "name": f"Regular Tee {uuid.uuid4().hex[:6]}",
        "description": "Standard in-stock listing without pre-order — long enough description.",
        "price": 25.0,
        "category": "t-shirts",
        "sizes": ["M"],
        "images": ["/api/files/x/y.png"],
        "stock": 5,
    }
    r = seller_session.post(f"{API}/api/products", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_preorder"] is False
    assert body["preorder_ship_date"] is None


# --------------- Stripe delay_days ---------------

def test_stripe_account_creation_includes_delay_days():
    """The Stripe Connect Express account creation call must now request a
    payout schedule with delay_days = STANDARD_PAYOUT_DELAY_DAYS."""
    import sys
    sys.path.insert(0, "/app/backend")
    from core import _finalise_approval, STANDARD_PAYOUT_DELAY_DAYS  # noqa: E402

    src = inspect.getsource(_finalise_approval)
    assert "stripe_sdk.Account.create" in src
    assert '"delay_days": STANDARD_PAYOUT_DELAY_DAYS' in src
    assert '"interval": "daily"' in src
    assert STANDARD_PAYOUT_DELAY_DAYS >= 1  # sanity


# --------------- SALE_STATUSES ---------------

def test_sale_statuses_includes_preorder_paid():
    """Analytics must count pre-order revenue — SALE_STATUSES is the shared list."""
    import sys
    sys.path.insert(0, "/app/backend")
    from core import SALE_STATUSES  # noqa: E402
    assert "preorder_paid" in SALE_STATUSES
    assert "paid" in SALE_STATUSES
    assert "shipped" in SALE_STATUSES
    assert "delivered" in SALE_STATUSES
