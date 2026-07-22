"""Tests for iteration 12 security/correctness fixes:
FIX 1 — Product input validation (ProductCreate constrained, ProductUpdate model)
       + ReferralApplyRequest + BrandProfileUpdate Pydantic models
FIX 2 — Stock oversell guard in settle_paid_order (routes/orders.py)
FIX 3 — Password rules (register 8-128, reset-password 8-128 with new msg)
FIX 4 — HTML escaping in emails (core.esc + receipt/shipped/notification emails)
"""
import os
import sys
import asyncio
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

ADMIN_EMAIL = "Anthonygeorgiades@unveiledthreads.co.uk"
ADMIN_PW = "Babablacksheep159"
DEMO_EMAIL = "demo@threadandbone.uk"
DEMO_PW = "Demo123!"
TESTBRAND_EMAIL = "testbrand@example.com"
TESTBRAND_PW = "TestBrand123!"
BRAND_ID = "6a46ca8929f8d1b8081c4697"


def _client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(email, pw):
    s = _client()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return s


VALID_PRODUCT = {
    "name": "QA Tee",
    "description": "A quality test tee for validation purposes",
    "price": 25.0,
    "category": "tshirts",
    "sizes": ["M"],
    "images": ["https://example.com/img.png"],
    "stock": 5,
}


# ============================================================
# FIX 1 — Product & related input validation
# ============================================================

class TestFix1ProductValidation:
    @classmethod
    def setup_class(cls):
        cls.s = _login(TESTBRAND_EMAIL, TESTBRAND_PW)
        # Create one valid product used for PUT tests, cleaned up in teardown
        r = cls.s.post(f"{BASE}/api/products", json=VALID_PRODUCT)
        assert r.status_code == 200, f"valid create failed: {r.status_code} {r.text}"
        cls.product_id = r.json()["id"]

    @classmethod
    def teardown_class(cls):
        try:
            cls.s.delete(f"{BASE}/api/products/{cls.product_id}")
        except Exception:
            pass

    def _bad(self, **overrides):
        p = dict(VALID_PRODUCT, **overrides)
        return self.s.post(f"{BASE}/api/products", json=p)

    def test_price_negative_422(self):
        r = self._bad(price=-5)
        assert r.status_code == 422, r.text

    def test_price_string_422(self):
        r = self._bad(price="abc")
        assert r.status_code == 422, r.text

    def test_stock_negative_422(self):
        r = self._bad(stock=-1)
        assert r.status_code == 422, r.text

    def test_gender_invalid_422(self):
        r = self._bad(gender="alien")
        assert r.status_code == 422, r.text

    def test_name_too_short_422(self):
        r = self._bad(name="A")
        assert r.status_code == 422, r.text

    def test_description_too_short_422(self):
        r = self._bad(description="short")
        assert r.status_code == 422, r.text

    def test_sizes_empty_422(self):
        r = self._bad(sizes=[])
        assert r.status_code == 422, r.text

    def test_images_empty_422(self):
        r = self._bad(images=[])
        assert r.status_code == 422, r.text

    def test_condition_invalid_422(self):
        r = self._bad(condition="bogus")
        assert r.status_code == 422, r.text

    def test_put_negative_price_422(self):
        r = self.s.put(f"{BASE}/api/products/{self.product_id}", json={"price": -10})
        assert r.status_code == 422, r.text

    def test_put_string_price_422(self):
        r = self.s.put(f"{BASE}/api/products/{self.product_id}", json={"price": "abc"})
        assert r.status_code == 422, r.text

    def test_put_valid_price_200_and_persisted(self):
        r = self.s.put(f"{BASE}/api/products/{self.product_id}", json={"price": 49.99})
        assert r.status_code == 200, r.text
        # Verify persistence
        g = self.s.get(f"{BASE}/api/products/{self.product_id}")
        assert g.status_code == 200
        assert g.json()["price"] == 49.99

    def test_put_by_other_brand_403(self):
        other = _login(DEMO_EMAIL, DEMO_PW)
        r = other.put(f"{BASE}/api/products/{self.product_id}", json={"price": 12.34})
        assert r.status_code == 403, r.text

    def test_full_lifecycle_delete(self):
        # Sanity — normal create+update+delete lifecycle still works
        s = _login(TESTBRAND_EMAIL, TESTBRAND_PW)
        p = dict(VALID_PRODUCT, name="Lifecycle Tee")
        r = s.post(f"{BASE}/api/products", json=p)
        assert r.status_code == 200
        pid = r.json()["id"]
        r2 = s.put(f"{BASE}/api/products/{pid}", json={"price": 30.0, "stock": 3})
        assert r2.status_code == 200
        assert r2.json()["price"] == 30.0
        assert r2.json()["stock"] == 3
        r3 = s.delete(f"{BASE}/api/products/{pid}")
        assert r3.status_code == 200


def test_fix1_referral_apply_too_short_422():
    s = _login(DEMO_EMAIL, DEMO_PW)
    r = s.post(f"{BASE}/api/referral/apply", json={"code": "ab"})
    assert r.status_code == 422, r.text


def test_fix1_brand_profile_desc_too_long_422():
    s = _login(DEMO_EMAIL, DEMO_PW)
    r = s.put(f"{BASE}/api/brands/profile", json={"description": "x" * 3001})
    assert r.status_code == 422, r.text


# ============================================================
# FIX 2 — Oversell guard in settle_paid_order
# ============================================================

def test_fix2_oversell_guard():
    asyncio.get_event_loop().run_until_complete(_fix2_oversell_guard())


async def _fix2_oversell_guard():
    import routes.orders as orders_mod
    from core import db as core_db
    db = core_db
    product_doc = {
        "brand_id": BRAND_ID,
        "brand_name": "OversellTestBrand",
        "name": "Oversell Test Tee",
        "description": "Throwaway product used by iter12 oversell test",
        "price": 20.0,
        "category": "tshirts",
        "sizes": ["M"],
        "images": ["https://example.com/img.png"],
        "stock": 1,
        "shipping_cost": 0.0,
        "gender": "unisex",
        "condition": "new",
        "created_at": datetime.now(timezone.utc),
    }
    prod_ins = await db.products.insert_one(product_doc)
    product_id = str(prod_ins.inserted_id)

    fake_buyer = "buyer_fake_iter12"
    orders_to_insert = []
    session_ids = [f"cs_test_iter12_oversell_{uuid.uuid4().hex[:8]}" for _ in range(2)]
    for sid in session_ids:
        orders_to_insert.append({
            "session_id": sid,
            "buyer_id": fake_buyer,
            "buyer_email": None,
            "buyer_name": "Fake Buyer",
            "product_id": product_id,
            "product_name": "Oversell Test Tee",
            "brand_id": BRAND_ID,
            "brand_name": "OversellTestBrand",
            "size": "M",
            "price": 20.0,
            "shipping_cost": 0.0,
            "platform_fee": 1.49,
            "credit_applied": 0.0,
            "total_charged": 21.49,
            "brand_payout": 20.0,
            "stripe_account_id": None,
            "status": "initiated",
            "shipping_status": "confirmed",
            "created_at": datetime.now(timezone.utc),
        })
    ins = await db.orders.insert_many(orders_to_insert)
    order_ids = ins.inserted_ids

    order_ids_str = [str(oid) for oid in order_ids]

    try:
        # Settle first
        o1 = await db.orders.find_one({"_id": order_ids[0]})
        ok1 = await orders_mod.settle_paid_order(o1)
        assert ok1 is True

        p_after_1 = await db.products.find_one({"_id": prod_ins.inserted_id})
        assert p_after_1["stock"] == 0, f"stock should be 0 after first settle, got {p_after_1['stock']}"
        o1_after = await db.orders.find_one({"_id": order_ids[0]})
        assert o1_after.get("oversold") is not True
        assert o1_after["status"] == "paid"

        # Settle second → should settle but be flagged oversold
        o2 = await db.orders.find_one({"_id": order_ids[1]})
        ok2 = await orders_mod.settle_paid_order(o2)
        assert ok2 is True

        p_after_2 = await db.products.find_one({"_id": prod_ins.inserted_id})
        assert p_after_2["stock"] == 0, f"stock must NEVER go negative, got {p_after_2['stock']}"
        o2_after = await db.orders.find_one({"_id": order_ids[1]})
        assert o2_after.get("oversold") is True, f"second order must be flagged oversold; got {o2_after.get('oversold')}"
        assert o2_after["status"] == "paid"

        # Brand notification 'oversold_order' should exist
        notif = await db.notifications.find_one({
            "brand_id": BRAND_ID,
            "type": "oversold_order",
            "metadata.order_id": str(order_ids[1]),
        })
        assert notif is not None, "expected oversold_order notification for brand"

        # Admin stats includes oversold_orders
        s = _login(ADMIN_EMAIL, ADMIN_PW)
        r = s.get(f"{BASE}/api/admin/stats")
        assert r.status_code == 200
        stats = r.json()
        assert "oversold_orders" in stats
        assert isinstance(stats["oversold_orders"], int)
        assert stats["oversold_orders"] >= 1
    finally:
        # Cleanup
        await db.orders.delete_many({"_id": {"$in": order_ids}})
        await db.products.delete_one({"_id": prod_ins.inserted_id})
        await db.notifications.delete_many({
            "brand_id": BRAND_ID,
            "type": "oversold_order",
            "metadata.order_id": {"$in": order_ids_str},
        })
        # Also nuke the "New Order Received!" brand notifs generated
        await db.notifications.delete_many({
            "brand_id": BRAND_ID,
            "type": "order_received",
            "metadata.order_session_id": {"$in": session_ids},
        })


# ============================================================
# FIX 3 — Password rules
# ============================================================

def test_fix3_register_password_too_short_422():
    s = _client()
    email = f"iter12_pw_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{BASE}/api/auth/register", json={
        "email": email, "password": "abc", "name": "P"
    })
    assert r.status_code == 422, r.text


def test_fix3_register_valid_and_reset_flow():
    asyncio.get_event_loop().run_until_complete(_fix3_register_valid_and_reset_flow())


async def _fix3_register_valid_and_reset_flow():
    import routes.auth as auth_mod
    from core import db

    email = f"iter12_pwok_{uuid.uuid4().hex[:8]}@example.com"

    # Register with valid password
    s = _client()
    r = s.post(f"{BASE}/api/auth/register", json={
        "email": email, "password": "longenough1", "name": "Reset User"
    })
    assert r.status_code == 200, r.text
    user_id = r.json()["id"]

    try:
        # Insert a valid reset token
        raw_token = "iter12_" + uuid.uuid4().hex
        token_hash = auth_mod._hash_reset_token(raw_token)
        await db.password_reset_tokens.insert_one({
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": False,
            "created_at": datetime.now(timezone.utc),
        })

        # Reset with too-short password → 400 with new message
        s2 = _client()
        r_short = s2.post(f"{BASE}/api/auth/reset-password", json={
            "token": raw_token, "new_password": "short"
        })
        assert r_short.status_code == 400, r_short.text
        # Accept either en-dash or hyphen for tolerance
        detail = r_short.json().get("detail", "")
        assert "Password must be 8" in detail and "128 characters" in detail, detail

        # Reset with valid password → 200
        r_ok = s2.post(f"{BASE}/api/auth/reset-password", json={
            "token": raw_token, "new_password": "newvalidpass1"
        })
        assert r_ok.status_code == 200, r_ok.text
    finally:
        # Cleanup user + tokens
        try:
            await db.password_reset_tokens.delete_many({"user_id": user_id})
        except Exception:
            pass
        try:
            await db.users.delete_one({"_id": ObjectId(user_id)})
        except Exception:
            pass


# ============================================================
# FIX 4 — HTML escaping in emails
# ============================================================

def test_fix4_receipt_email_escapes():
    asyncio.get_event_loop().run_until_complete(_fix4_receipt_email_escapes())


async def _fix4_receipt_email_escapes():
    """Patch resend.Emails.send to capture params sent from send_order_receipt_email."""
    import resend
    import routes.orders as orders_mod

    captured = {}

    def fake_send(params):
        captured["params"] = params
        return {"id": "fake_id"}

    original = resend.Emails.send
    original_key = orders_mod.RESEND_API_KEY
    # Ensure the send path executes even if the module was imported with no key
    orders_mod.RESEND_API_KEY = "fake_key_for_test"
    resend.Emails.send = fake_send
    try:
        order = {
            "_id": ObjectId(),
            "buyer_email": "capture@example.com",
            "product_name": "<b>Test</b><img src=x onerror=alert(1)>",
            "brand_name": "<script>evil</script>",
            "size": "M",
            "price": 20.0,
            "platform_fee": 1.49,
            "credit_applied": 0.0,
            "shipping_cost": 0.0,
            "total_charged": 21.49,
        }
        await orders_mod.send_order_receipt_email(order)
    finally:
        resend.Emails.send = original
        orders_mod.RESEND_API_KEY = original_key

    assert "params" in captured, "resend.Emails.send was not called"
    html = captured["params"]["html"]
    assert "&lt;b&gt;Test&lt;/b&gt;" in html
    assert "<img src=x" not in html
    assert "<script>evil" not in html
    assert "&lt;script&gt;evil&lt;/script&gt;" in html


def test_fix4_shipped_email_escapes():
    asyncio.get_event_loop().run_until_complete(_fix4_shipped_email_escapes())


async def _fix4_shipped_email_escapes():
    import resend
    import routes.shipping as ship_mod

    captured = {}
    def fake_send(params):
        captured["params"] = params
        return {"id": "fake"}

    original = resend.Emails.send
    original_key = ship_mod.RESEND_API_KEY
    ship_mod.RESEND_API_KEY = "fake_key_for_test"
    resend.Emails.send = fake_send
    try:
        order = {
            "_id": ObjectId(),
            "buyer_email": "capture@example.com",
            "product_name": "<img src=x onerror=alert(1)>",
            "brand_name": "TestBrand",
            "size": "M",
        }
        await ship_mod.send_order_shipped_email(order, "<svg onload=alert(1)>", "TN123<script>")
    finally:
        resend.Emails.send = original
        ship_mod.RESEND_API_KEY = original_key

    html = captured["params"]["html"]
    assert "<img src=x" not in html
    assert "<svg onload=" not in html
    assert "<script>" not in html
    assert "&lt;img src=x" in html
    assert "&lt;svg onload=" in html


def test_fix4_create_notification_escapes():
    asyncio.get_event_loop().run_until_complete(_fix4_create_notification_escapes())


async def _fix4_create_notification_escapes():
    """Notification email body escapes title/message.
    Create a temp user with a fake resend patched in, then call create_notification."""
    import resend
    import core as core_mod
    from core import db, create_notification

    captured = {}
    def fake_send(params):
        captured["params"] = params
        return {"id": "fake"}

    # Create a throwaway user
    user_ins = await db.users.insert_one({
        "email": f"iter12_notify_{uuid.uuid4().hex[:6]}@example.com",
        "password_hash": "x",
        "name": "Notify Test",
        "role": "user",
        "created_at": datetime.now(timezone.utc),
    })
    user_id = str(user_ins.inserted_id)

    original = resend.Emails.send
    original_key = core_mod.RESEND_API_KEY
    core_mod.RESEND_API_KEY = "fake_key_for_test"
    resend.Emails.send = fake_send
    try:
        await create_notification(
            user_id=user_id,
            brand_id=None,
            notification_type="test",
            title="<b>Alert</b>",
            message="<script>alert(1)</script>",
        )
    finally:
        resend.Emails.send = original
        core_mod.RESEND_API_KEY = original_key
        await db.users.delete_one({"_id": user_ins.inserted_id})
        await db.notifications.delete_many({"user_id": user_id})

    assert "params" in captured, "resend.Emails.send was not called for notification"
    html = captured["params"]["html"]
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;b&gt;Alert&lt;/b&gt;" in html


def test_fix4_normal_strings_pass_unchanged():
    asyncio.get_event_loop().run_until_complete(_fix4_normal_strings_pass_unchanged())


async def _fix4_normal_strings_pass_unchanged():
    """Sanity: benign strings are not mutated beyond entity-safe passthrough."""
    import resend
    import routes.orders as orders_mod

    captured = {}
    def fake_send(params):
        captured["params"] = params
        return {"id": "fake"}

    original = resend.Emails.send
    original_key = orders_mod.RESEND_API_KEY
    orders_mod.RESEND_API_KEY = "fake_key_for_test"
    resend.Emails.send = fake_send
    try:
        order = {
            "_id": ObjectId(),
            "buyer_email": "capture@example.com",
            "product_name": "Signature Hoodie",
            "brand_name": "Thread & Bone",
            "size": "L",
            "price": 85.0,
            "platform_fee": 4.74,
            "credit_applied": 0.0,
            "shipping_cost": 4.99,
            "total_charged": 94.73,
        }
        await orders_mod.send_order_receipt_email(order)
    finally:
        resend.Emails.send = original
        orders_mod.RESEND_API_KEY = original_key

    html = captured["params"]["html"]
    assert "Signature Hoodie" in html
    # html.escape converts & → &amp; — that's expected and correct
    assert "Thread &amp; Bone" in html
    assert "Size L" in html
