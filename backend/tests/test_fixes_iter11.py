"""Tests for iteration 11 fixes:
FIX 1 (refund dispute), FIX 2 (GDPR delete cascade), FIX 3 (schedulers +
reconcile endpoint), FIX 4 (referral crediting via settle_paid_order),
FIX 6 (admin dispute order_summary.total_price)."""
import os
import sys
import asyncio
import time
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
BRAND_ID = "6a46ca8929f8d1b8081c4697"
PRODUCT_ID = "6a46ca8929f8d1b8081c4698"


def _client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(sess, email, pw):
    r = sess.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r


@pytest.fixture(scope="module")
def db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


# ----------- FIX 1: dispute refund fails safe when Stripe not configured -----------

class TestFix1DisputeRefund:
    def setup_method(self):
        self.buyer = _client()
        # Register a fresh buyer to own the dispute-eligible order
        self.buyer_email = f"TEST_disp_{uuid.uuid4().hex[:8]}@example.com"
        r = self.buyer.post(f"{BASE}/api/auth/register", json={
            "email": self.buyer_email, "password": "Passw0rd!", "name": "Test Buyer"
        })
        assert r.status_code == 200, r.text
        me = self.buyer.get(f"{BASE}/api/auth/me").json()
        self.buyer_id = me["id"]

        self.admin = _client()
        _login(self.admin, ADMIN_EMAIL, ADMIN_PW)

    def test_refund_stays_open_when_no_stripe_key(self, db):
        async def run():
            # Create a paid order 20 days ago, no delivered status
            twenty_days_ago = datetime.now(timezone.utc) - timedelta(days=20)
            order_doc = {
                "session_id": f"cs_test_disp_{uuid.uuid4().hex[:10]}",
                "buyer_id": self.buyer_id,
                "buyer_email": self.buyer_email,
                "buyer_name": "Test Buyer",
                "product_id": PRODUCT_ID,
                "product_name": "Test Dispute Product",
                "brand_id": BRAND_ID,
                "brand_name": "Thread & Bone",
                "size": "M",
                "price": 85.0,
                "shipping_cost": 0.0,
                "platform_fee": 4.99,
                "credit_applied": 0.0,
                "total_charged": 89.99,
                "brand_payout": 85.0,
                "stripe_account_id": "acct_TEST_dummy",
                "status": "paid",
                "shipping_status": "confirmed",
                "tracking_number": None,
                "courier": None,
                "shipping_updates": [],
                "reviewed": False,
                "created_at": twenty_days_ago,
                "stock_deducted": True,
            }
            ins = await db.orders.insert_one(order_doc)
            order_id = str(ins.inserted_id)

            dispute_doc = {
                "order_id": order_id,
                "buyer_id": self.buyer_id,
                "brand_id": BRAND_ID,
                "type": "non_delivery",
                "status": "open",
                "buyer_message": "Never received — 20 days later.",
                "created_at": datetime.now(timezone.utc),
                "resolution": None,
            }
            dins = await db.disputes.insert_one(dispute_doc)
            dispute_id = str(dins.inserted_id)
            return order_id, dispute_id

        order_id, dispute_id = asyncio.get_event_loop().run_until_complete(run())

        # POST refund → expect 400 (no Stripe)
        r = self.admin.post(
            f"{BASE}/api/admin/disputes/{dispute_id}/refund",
            json={"note": "test"},
        )
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"
        assert "Stripe is not configured" in r.text

        # Assert Mongo state
        async def verify():
            d = await db.disputes.find_one({"_id": ObjectId(dispute_id)})
            o = await db.orders.find_one({"_id": ObjectId(order_id)})
            n = await db.notifications.find_one(
                {"user_id": self.buyer_id, "notification_type": "dispute_refunded"}
            )
            return d, o, n

        d, o, n = asyncio.get_event_loop().run_until_complete(verify())
        assert d["status"] == "open", f"dispute status = {d['status']}"
        assert o["status"] != "refunded", f"order status = {o['status']}"
        assert n is None, "should not have created dispute_refunded notification"

        # FIX 6: admin GET /disputes enriches total_price
        r2 = self.admin.get(f"{BASE}/api/admin/disputes?status=open")
        assert r2.status_code == 200
        matches = [x for x in r2.json() if x["id"] == dispute_id]
        assert matches, "our dispute should appear"
        assert matches[0]["order_summary"]["total_price"] == 89.99

        # Now close the dispute with a note → 200
        r3 = self.admin.post(
            f"{BASE}/api/admin/disputes/{dispute_id}/close",
            json={"note": "Closed by test — buyer received."},
        )
        assert r3.status_code == 200, r3.text

        async def verify_closed():
            return await db.disputes.find_one({"_id": ObjectId(dispute_id)})
        d2 = asyncio.get_event_loop().run_until_complete(verify_closed())
        assert d2["status"] == "resolved_closed"

        # Cleanup: delete the fake order + dispute
        async def cleanup():
            await db.orders.delete_one({"_id": ObjectId(order_id)})
            await db.disputes.delete_one({"_id": ObjectId(dispute_id)})
        asyncio.get_event_loop().run_until_complete(cleanup())


# ----------- FIX 2: GDPR delete cascade + export conversations ----------- 

def test_fix2_gdpr_delete_cascade():
    async def _run(db):
        sess = _client()
        email = f"TEST_gdpr_{uuid.uuid4().hex[:8]}@example.com"
        pw = "Passw0rd!"
        r = sess.post(f"{BASE}/api/auth/register", json={"email": email, "password": pw, "name": "GDPR Test"})
        assert r.status_code == 200, r.text
        me = sess.get(f"{BASE}/api/auth/me").json()
        uid = me["id"]

        # add to wishlist
        r = sess.post(f"{BASE}/api/wishlist/{PRODUCT_ID}")
        assert r.status_code == 200, r.text

        # send a message to demo brand (owner)
        brand_row = await db.brands.find_one({"_id": ObjectId(BRAND_ID)})
        brand_owner_id = brand_row["user_id"]
        r = sess.post(f"{BASE}/api/messages/send", json={
            "recipient_id": brand_owner_id,
            "product_id": PRODUCT_ID,
            "content": "Hi is this still available for shipping to London?"
        })
        assert r.status_code == 200, r.text
        msg_id = r.json().get("id") or r.json().get("message_id")

        # snapshot pre-delete
        pre_wish = await db.wishlist.count_documents({"user_id": uid})
        assert pre_wish >= 1
        pre_convs = await db.conversations.count_documents({"$or": [{"participant_1": uid}, {"participant_2": uid}]})
        assert pre_convs >= 1
        pre_msgs = await db.messages.find({"sender_id": uid}).to_list(20)
        assert len(pre_msgs) >= 1

        # delete
        r = sess.post(f"{BASE}/api/account/delete", json={"password": pw, "confirm": "DELETE"})
        assert r.status_code == 200, r.text

        # user gone
        u = await db.users.find_one({"_id": ObjectId(uid)})
        assert u is None
        # wishlist gone (db.wishlist, singular)
        wc = await db.wishlist.count_documents({"user_id": uid})
        assert wc == 0
        # message body redacted
        msgs = await db.messages.find({"sender_id": "deleted-user"}).to_list(1000)
        redacted = [m for m in msgs if m.get("content") == "[message removed — account deleted]"]
        assert len(redacted) >= 1, "sent message content not redacted"
        # conversations detached
        stale = await db.conversations.count_documents({"$or": [{"participant_1": uid}, {"participant_2": uid}]})
        assert stale == 0

    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    asyncio.get_event_loop().run_until_complete(_run(db))


def test_fix2_export_includes_conversations():
    sess = _client()
    _login(sess, DEMO_EMAIL, DEMO_PW)
    r = sess.get(f"{BASE}/api/account/export")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "conversations" in data
    assert "messages" in data
    assert isinstance(data["conversations"], list)
    assert isinstance(data["messages"], list)


# ----------- FIX 3: reconcile endpoint returns empty settled list ----------- 

def test_fix3_reconcile_endpoint():
    sess = _client()
    _login(sess, ADMIN_EMAIL, ADMIN_PW)
    r = sess.post(f"{BASE}/api/admin/orders/reconcile")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data == {"settled": [], "count": 0}


def test_fix3_scheduler_symbols_import():
    """Verify all three loop functions are importable (proves server.py wires them)."""
    from routes.engagement import low_stock_digest_loop, abandoned_checkout_loop  # noqa
    from routes.orders import order_reconciliation_loop  # noqa
    assert callable(low_stock_digest_loop)
    assert callable(abandoned_checkout_loop)
    assert callable(order_reconciliation_loop)


# ----------- FIX 4: referral crediting via settle_paid_order ----------- 

def test_fix4_referral_settle_paid_order():
    """End-to-end python-level test of settle_paid_order.
    A = demo (referrer), B = fresh registered user (referred buyer)."""
    from routes.orders import settle_paid_order

    async def _run():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]

        # Get A's referral code
        a_sess = _client()
        _login(a_sess, DEMO_EMAIL, DEMO_PW)
        me_a = a_sess.get(f"{BASE}/api/auth/me").json()
        a_id = me_a["id"]
        code_res = a_sess.get(f"{BASE}/api/referral/code").json()
        code = code_res["code"]

        # A's credits BEFORE
        pre_a_ref = await db.referrals.find_one({"user_id": a_id})
        pre_earned = (pre_a_ref or {}).get("credits_earned", 0.0)

        # Register B
        b_sess = _client()
        b_email = f"TEST_ref_{uuid.uuid4().hex[:8]}@example.com"
        b_sess.post(f"{BASE}/api/auth/register", json={"email": b_email, "password": "Passw0rd!", "name": "Ref Buyer B"})
        me_b = b_sess.get(f"{BASE}/api/auth/me").json()
        b_id = me_b["id"]

        # Apply A's code
        r = b_sess.post(f"{BASE}/api/referral/apply", json={"code": code})
        assert r.status_code == 200, r.text

        # Confirm referral_uses doc has credit_pending
        rusage = await db.referral_uses.find_one({"user_id": b_id})
        assert rusage is not None and rusage.get("credit_pending") is True
        assert rusage["referrer_id"] == a_id

        # Get product stock before
        prod_before = await db.products.find_one({"_id": ObjectId(PRODUCT_ID)})
        stock_before = prod_before["stock"]

        # Insert fake paid-ready order for B
        session_id_fake = f"cs_test_fix4_{uuid.uuid4().hex[:12]}"
        order_doc = {
            "session_id": session_id_fake,
            "buyer_id": b_id,
            "buyer_email": b_email,
            "buyer_name": "Ref Buyer B",
            "product_id": PRODUCT_ID,
            "product_name": "Smithfield Hoodie - Black",
            "brand_id": BRAND_ID,
            "brand_name": "Thread & Bone",
            "size": "M",
            "price": 85.0,
            "shipping_cost": 0.0,
            "platform_fee": 1.49,
            "credit_applied": 0.0,
            "total_charged": 86.49,
            "brand_payout": 10.0,
            "stripe_account_id": "acct_TEST",
            "status": "initiated",
            "shipping_status": "confirmed",
            "tracking_number": None,
            "courier": None,
            "shipping_updates": [],
            "reviewed": False,
            "created_at": datetime.now(timezone.utc),
        }
        ins = await db.orders.insert_one(order_doc)
        order_from_db = await db.orders.find_one({"_id": ins.inserted_id})

        # First call → True (settles)
        first = await settle_paid_order(order_from_db, payment_intent_id="pi_test_fake_abc")
        assert first is True, "first settle_paid_order should return True"

        # Assertions
        rusage_after = await db.referral_uses.find_one({"user_id": b_id})
        assert rusage_after["credit_pending"] is False

        a_ref_after = await db.referrals.find_one({"user_id": a_id})
        assert round(a_ref_after["credits_earned"] - pre_earned, 2) == 5.0

        prod_after = await db.products.find_one({"_id": ObjectId(PRODUCT_ID)})
        assert prod_after["stock"] == stock_before - 1

        # GET /referral/credits as A shows credits_available ≥ 5.0
        cr = a_sess.get(f"{BASE}/api/referral/credits").json()
        assert cr["credits_available"] >= 5.0

        # Second call → False (idempotent)
        order_reloaded = await db.orders.find_one({"_id": ins.inserted_id})
        second = await settle_paid_order(order_reloaded, payment_intent_id="pi_test_fake_abc")
        assert second is False

        prod_after2 = await db.products.find_one({"_id": ObjectId(PRODUCT_ID)})
        assert prod_after2["stock"] == stock_before - 1, "double-deduction detected"

        a_ref_after2 = await db.referrals.find_one({"user_id": a_id})
        assert round(a_ref_after2["credits_earned"] - pre_earned, 2) == 5.0, "double-credit detected"

        # Cleanup: restore stock, delete fake order. Leave A's £5 credit in place.
        await db.products.update_one({"_id": ObjectId(PRODUCT_ID)}, {"$inc": {"stock": 1}})
        await db.orders.delete_one({"_id": ins.inserted_id})
        # cleanup B (registered buyer) + their referral_uses so we don't pollute future tests
        await db.users.delete_one({"_id": ObjectId(b_id)})
        await db.referral_uses.delete_many({"user_id": b_id})

    asyncio.get_event_loop().run_until_complete(_run())
