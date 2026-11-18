"""Iter20 — Guest Checkout regression suite.

Two layers:
  * In-process (httpx ASGITransport against server.app) with Stripe
    `checkout.Session.create` / `get_stripe_session_status` monkeypatched,
    so we can verify the persisted order shape / pricing / opt-in / auto-link.
  * Live public URL (REACT_APP_BACKEND_URL) for pre-Stripe validation paths,
    lookup / status-token authorisation and rate limits.

All fixtures are TEST_-prefixed and deleted by id at module teardown.
Run from /app/backend (core.load_dotenv() is cwd-relative).
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
import requests
from bson import ObjectId

sys.path.insert(0, "/app/backend")
os.chdir("/app/backend")

LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(LOOP)

import server  # noqa: E402
import core  # noqa: E402
import routes.orders as orders_mod  # noqa: E402

from conftest import BASE  # noqa: E402

db = core.db
run = LOOP.run_until_complete

CREATED = {"products": [], "brands": [], "orders_sessions": [], "users": [], "emails": [], "pt_sessions": []}


# ---------- Stripe mocks ----------
STRIPE_CALLS = []


def _fake_session_create(**kwargs):
    STRIPE_CALLS.append(kwargs)
    sid = f"cs_test_TEST_{uuid.uuid4().hex[:16]}"
    CREATED["orders_sessions"].append(sid)
    return SimpleNamespace(id=sid, url=f"https://checkout.stripe.com/c/pay/{sid}")


def _fake_status(session_id, api_key, stripe_account=None):
    return {"status": "open", "payment_status": "unpaid", "payment_intent": None, "metadata": {}}


orders_mod.stripe_sdk.checkout.Session.create = _fake_session_create
orders_mod.get_stripe_session_status = _fake_status
core.limiter.enabled = False  # in-process only; live server limiter untouched


def asgi_client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://testserver")


async def _req(method, path, **kw):
    async with asgi_client() as c:
        return await c.request(method, path, **kw)


def call(method, path, **kw):
    return run(_req(method, path, **kw))


# ---------- fixtures (DB seeding) ----------
def _mk_brand(charges=True, acct="acct_TEST_fake"):
    doc = {"brand_name": f"TEST_Brand_{uuid.uuid4().hex[:6]}", "user_id": "TEST_none", "status": "approved",
           "stripe_account_id": acct, "stripe_charges_enabled": charges, "created_at": datetime.now(timezone.utc)}
    bid = run(db.brands.insert_one(doc)).inserted_id
    CREATED["brands"].append(bid)
    return str(bid), doc["brand_name"]


def _mk_product(brand_id, brand_name, **over):
    doc = {"brand_id": brand_id, "brand_name": brand_name, "name": f"TEST_Prod_{uuid.uuid4().hex[:6]}",
           "price": 80.0, "sizes": ["S", "M"], "images": [], "stock": 5, "shipping_cost": 4.99,
           "category": "hoodies", "created_at": datetime.now(timezone.utc)}
    doc.update(over)
    pid = run(db.products.insert_one(doc)).inserted_id
    CREATED["products"].append(pid)
    return str(pid)


@pytest.fixture(scope="module")
def world():
    bid, bname = _mk_brand(True)
    bid_noob, bname_noob = _mk_brand(False, acct=None)
    w = {
        "brand": bid,
        "p_ok": _mk_product(bid, bname),
        "p_free_ship": _mk_product(bid, bname, price=200.0, shipping_cost=0),
        "p_draft": _mk_product(bid, bname, status="draft"),
        "p_oos": _mk_product(bid, bname, stock=0),
        "p_pre_full": _mk_product(bid, bname, stock=0, is_preorder=True, preorder_limit=0, preorder_ship_date="2026-03-01"),
        "p_pre_ok": _mk_product(bid, bname, stock=0, is_preorder=True, preorder_limit=50, preorder_ship_date="2026-03-15"),
        "p_noob": _mk_product(bid_noob, bname_noob),
    }
    yield w
    # teardown — by id only
    run(db.products.delete_many({"_id": {"$in": CREATED["products"]}}))
    run(db.brands.delete_many({"_id": {"$in": CREATED["brands"]}}))
    run(db.orders.delete_many({"session_id": {"$in": CREATED["orders_sessions"]}}))
    run(db.payment_transactions.delete_many({"session_id": {"$in": CREATED["orders_sessions"]}}))
    run(db.users.delete_many({"_id": {"$in": [ObjectId(u) for u in CREATED["users"]]}}))
    run(db.marketing_subscribers.delete_many({"email": {"$in": CREATED["emails"]}}))


def _email(tag):
    e = f"test_{tag}_{uuid.uuid4().hex[:8]}@example.com"
    CREATED["emails"].append(e)
    return e


def _payload(pid, email, size="S", opt=False, **extra):
    p = {"product_id": pid, "size": size, "origin_url": "https://example.test", "buyer_email": email,
         "shipping_address": {"name": "TEST_Guest", "line1": "1 Test St", "line2": None, "city": "London",
                              "postcode": "E1 6AN", "country": "GB"},
         "marketing_opt_in": opt}
    p.update(extra)
    return p


# ===== In-process: success path / DB shape / pricing =====
class TestGuestCheckoutInProcess:
    def test_success_and_order_shape(self, world):
        email = _email("shape")
        r = call("POST", "/api/orders/checkout/guest",
                 json=_payload(world["p_ok"], email, price=0.01, platform_fee=0, total_charged=0.01, credit_applied=99))
        assert r.status_code == 200, r.text
        d = r.json()
        assert set(d.keys()) == {"url", "session_id", "lookup_token"}
        assert len(d["lookup_token"]) >= 32
        o = run(db.orders.find_one({"session_id": d["session_id"]}))
        assert o["buyer_id"] is None and o["guest_order"] is True and o["status"] == "initiated"
        assert o["shipping_address"]["postcode"] == "E1 6AN" and o["shipping_address"]["city"] == "London"
        assert o["lookup_token"] == d["lookup_token"]
        fee = core.calculate_buyer_fee(80.0)
        assert o["price"] == 80.0 and o["platform_fee"] == fee and o["credit_applied"] == 0
        assert o["total_charged"] == round(80.0 + fee + 4.99, 2)
        assert o["is_preorder"] is False and o["preorder_ship_date"] is None
        # stripe kwargs
        kw = STRIPE_CALLS[-1]
        assert kw["customer_email"] == email and kw["stripe_account"] == "acct_TEST_fake"
        assert f"token={d['lookup_token']}" in kw["success_url"] and "guest=1" in kw["success_url"]
        assert kw["payment_intent_data"]["application_fee_amount"] == int(round(fee * 100))
        # opt-in false -> no subscriber
        assert run(db.marketing_subscribers.count_documents({"email": email.lower()})) == 0
        pt = run(db.payment_transactions.find_one({"session_id": d["session_id"]}))
        assert pt["user_id"] is None and pt["guest"] is True

    def test_fee_cap_and_free_shipping(self, world):
        r = call("POST", "/api/orders/checkout/guest", json=_payload(world["p_free_ship"], _email("cap")))
        assert r.status_code == 200, r.text
        o = run(db.orders.find_one({"session_id": r.json()["session_id"]}))
        assert o["platform_fee"] == core.calculate_buyer_fee(200.0) == 6.0
        assert o["total_charged"] == 206.0
        names = [li["price_data"]["product_data"]["name"] for li in STRIPE_CALLS[-1]["line_items"]]
        assert "Shipping" not in names

    def test_preorder_within_limit(self, world):
        r = call("POST", "/api/orders/checkout/guest", json=_payload(world["p_pre_ok"], _email("pre")))
        assert r.status_code == 200, r.text
        o = run(db.orders.find_one({"session_id": r.json()["session_id"]}))
        assert o["is_preorder"] is True and o["preorder_ship_date"] == "2026-03-15"

    def test_marketing_opt_in_upsert_no_dupes(self, world):
        email = _email("mkt")
        for _ in range(2):
            r = call("POST", "/api/orders/checkout/guest", json=_payload(world["p_ok"], email, opt=True))
            assert r.status_code == 200, r.text
        subs = run(db.marketing_subscribers.find({"email": email.lower()}).to_list(10))
        assert len(subs) == 1
        assert subs[0]["source"] == "guest_checkout" and subs[0]["consent_timestamp"] is not None

    def test_mixed_case_email_subscriber_dedup(self, world):
        base = _email("case")
        for e in (base, base.upper()):
            r = call("POST", "/api/orders/checkout/guest", json=_payload(world["p_ok"], e, opt=True))
            assert r.status_code == 200
        assert run(db.marketing_subscribers.count_documents({"email": base.lower()})) == 1

    def test_status_poll_with_token_in_process(self, world):
        r = call("POST", "/api/orders/checkout/guest", json=_payload(world["p_ok"], _email("poll")))
        d = r.json()
        ok = call("GET", f"/api/orders/status/{d['session_id']}", params={"token": d["lookup_token"]})
        assert ok.status_code == 200, ok.text
        body = ok.json()
        assert body["payment_status"] == "unpaid" and body["order"]["id"]
        assert "lookup_token" not in body["order"] and "stripe_account_id" not in body["order"]
        assert call("GET", f"/api/orders/status/{d['session_id']}", params={"token": "x" * 43}).status_code == 404
        assert call("GET", f"/api/orders/status/{d['session_id']}").status_code == 404


# ===== In-process: auto-link on register / login =====
class TestAutoLink:
    def test_register_links_guest_orders(self, world):
        email = _email("reg")
        other = _email("other")
        s1 = call("POST", "/api/orders/checkout/guest", json=_payload(world["p_ok"], email)).json()["session_id"]
        s2 = call("POST", "/api/orders/checkout/guest", json=_payload(world["p_ok"], other)).json()["session_id"]
        r = call("POST", "/api/auth/register", json={"email": email, "password": "TestPass123!x", "name": "TEST_Reg"})
        assert r.status_code == 200, r.text
        uid = r.json()["id"]
        CREATED["users"].append(uid)
        o1 = run(db.orders.find_one({"session_id": s1}))
        o2 = run(db.orders.find_one({"session_id": s2}))
        assert o1["buyer_id"] == uid and o1["guest_order"] is False
        assert o2["buyer_id"] is None and o2["guest_order"] is True
        # linked buyer can poll without token
        tok = core.create_access_token(uid, email)
        st = call("GET", f"/api/orders/status/{s1}", headers={"Authorization": f"Bearer {tok}"})
        assert st.status_code == 200, st.text
        mine = call("GET", "/api/orders/my-orders", headers={"Authorization": f"Bearer {tok}"}).json()
        assert any(m["session_id"] == s1 for m in mine)

    def test_login_links_guest_orders(self, world):
        email = _email("login")
        r = call("POST", "/api/auth/register", json={"email": email, "password": "TestPass123!x", "name": "TEST_Login"})
        uid = r.json()["id"]
        CREATED["users"].append(uid)
        s = call("POST", "/api/orders/checkout/guest", json=_payload(world["p_ok"], email)).json()["session_id"]
        assert run(db.orders.find_one({"session_id": s}))["buyer_id"] is None
        lr = call("POST", "/api/auth/login", json={"email": email, "password": "TestPass123!x"})
        assert lr.status_code == 200
        o = run(db.orders.find_one({"session_id": s}))
        assert o["buyer_id"] == uid and o["guest_order"] is False

    def test_mixed_case_guest_email_links_on_register(self, world):
        """Guest types 'Test_X@Example.com'; register lowercases — order must still link."""
        email = _email("mixed")
        s = call("POST", "/api/orders/checkout/guest", json=_payload(world["p_ok"], email.upper())).json()["session_id"]
        r = call("POST", "/api/auth/register", json={"email": email, "password": "TestPass123!x", "name": "TEST_Mixed"})
        uid = r.json()["id"]
        CREATED["users"].append(uid)
        o = run(db.orders.find_one({"session_id": s}))
        assert o["buyer_id"] == uid, f"mixed-case guest email not linked (stored buyer_email={o['buyer_email']})"


# ===== In-process: authed checkout regression =====
class TestAuthedCheckoutRegression:
    def test_authed_checkout_shape(self, world):
        email = _email("authed")
        r = call("POST", "/api/auth/register", json={"email": email, "password": "TestPass123!x", "name": "TEST_Authed"})
        uid = r.json()["id"]
        CREATED["users"].append(uid)
        tok = core.create_access_token(uid, email)
        cr = call("POST", "/api/orders/checkout", headers={"Authorization": f"Bearer {tok}"},
                  json={"product_id": world["p_ok"], "size": "M", "origin_url": "https://example.test"})
        assert cr.status_code == 200, cr.text
        assert set(cr.json().keys()) == {"url", "session_id"}
        o = run(db.orders.find_one({"session_id": cr.json()["session_id"]}))
        assert o["buyer_id"] == uid and not o.get("guest_order")


# ===== Live server: validation (no order docs created) =====
class TestLiveValidation:
    def _count(self, pid):
        return run(db.orders.count_documents({"product_id": pid}))

    @pytest.mark.parametrize("key,code", [("p_draft", 404), ("p_oos", 400), ("p_noob", 400), ("p_pre_full", 409)])
    def test_rejections(self, world, key, code):
        pid = world[key]
        r = requests.post(f"{BASE}/api/orders/checkout/guest", json=_payload(pid, _email("v")), timeout=20)
        assert r.status_code == code, r.text
        assert self._count(pid) == 0

    def test_nonexistent_product(self, world):
        r = requests.post(f"{BASE}/api/orders/checkout/guest", json=_payload(str(ObjectId()), _email("v")), timeout=20)
        assert r.status_code == 404

    def test_bad_size(self, world):
        r = requests.post(f"{BASE}/api/orders/checkout/guest", json=_payload(world["p_ok"], _email("v"), size="XXL"), timeout=20)
        assert r.status_code == 400 and "size" in r.json()["detail"].lower()

    def test_malformed_product_id(self, world):
        r = requests.post(f"{BASE}/api/orders/checkout/guest", json=_payload("not-an-objectid", _email("v")), timeout=20)
        assert r.status_code in (400, 404), f"malformed product_id gives {r.status_code}"

    def test_missing_fields_422(self, world):
        p = _payload(world["p_ok"], "not-an-email")
        assert requests.post(f"{BASE}/api/orders/checkout/guest", json=p, timeout=20).status_code == 422
        p = _payload(world["p_ok"], _email("v"))
        p["shipping_address"]["postcode"] = ""
        assert requests.post(f"{BASE}/api/orders/checkout/guest", json=p, timeout=20).status_code == 422

    def test_reaches_stripe_with_fake_account(self, world):
        r = requests.post(f"{BASE}/api/orders/checkout/guest", json=_payload(world["p_ok"], _email("v")), timeout=30)
        assert r.status_code == 500 and r.json()["detail"].startswith("Stripe error:")


# ===== Live server: lookup + status token =====
class TestLiveLookup:
    @pytest.fixture(scope="class")
    def seeded(self, world):
        r = call("POST", "/api/orders/checkout/guest", json=_payload(world["p_ok"], _email("lk")))
        d = r.json()
        o = run(db.orders.find_one({"session_id": d["session_id"]}))
        run(db.orders.update_one({"_id": o["_id"]}, {"$set": {"tracking_number": "TEST123", "courier": "Royal Mail",
                                                             "shipping_updates": [{"status": "Shipped", "at": "2026-01-10T10:00:00Z"}]}}))
        return {"oid": str(o["_id"]), **d}

    def test_lookup_ok_trimmed(self, seeded):
        r = requests.get(f"{BASE}/api/orders/lookup", params={"order_id": seeded["oid"], "token": seeded["lookup_token"]}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("buyer_id", "buyer_email", "stripe_account_id", "payment_intent_id", "lookup_token", "session_id",
                  "brand_payout", "shipping_address", "_id", "platform_fee"):
            assert k not in d, f"leaked {k}"
        assert d["tracking_number"] == "TEST123" and d["courier"] == "Royal Mail" and d["is_guest"] is True

    def test_lookup_wrong_missing_malformed(self, seeded):
        assert requests.get(f"{BASE}/api/orders/lookup", params={"order_id": seeded["oid"], "token": "wrong"}, timeout=20).status_code == 404
        assert requests.get(f"{BASE}/api/orders/lookup", params={"order_id": "zzz", "token": "wrong"}, timeout=20).status_code == 404
        assert requests.get(f"{BASE}/api/orders/lookup", params={"order_id": str(ObjectId()), "token": "x"}, timeout=20).status_code == 404
        r = requests.get(f"{BASE}/api/orders/lookup", params={"order_id": seeded["oid"]}, timeout=20)
        assert r.status_code in (404, 422)

    def test_lookup_empty_token_on_authed_order_404(self, world):
        """Authed orders have no lookup_token; empty token must not match ''."""
        o = run(db.orders.find_one({"guest_order": {"$ne": True}, "session_id": {"$in": CREATED["orders_sessions"]}}))
        if not o:
            pytest.skip("no authed TEST order")
        r = requests.get(f"{BASE}/api/orders/lookup", params={"order_id": str(o["_id"]), "token": ""}, timeout=20)
        assert r.status_code == 404

    def test_status_wrong_token_live(self, seeded):
        r = requests.get(f"{BASE}/api/orders/status/{seeded['session_id']}", params={"token": "nope"}, timeout=20)
        assert r.status_code == 404
        r = requests.get(f"{BASE}/api/orders/status/{seeded['session_id']}", timeout=20)
        assert r.status_code == 404

    def test_status_correct_token_live_reaches_stripe(self, seeded):
        r = requests.get(f"{BASE}/api/orders/status/{seeded['session_id']}", params={"token": seeded["lookup_token"]}, timeout=30)
        # authorised → proceeds to Stripe retrieve which fails on fake session (500 Stripe error) — proves auth passed
        assert r.status_code in (200, 500)
        if r.status_code == 500:
            assert "Stripe error" in r.json()["detail"]

    def test_status_paid_returns_receipt_live(self, seeded):
        run(db.orders.update_one({"session_id": seeded["session_id"]}, {"$set": {"status": "paid"}}))
        r = requests.get(f"{BASE}/api/orders/status/{seeded['session_id']}", params={"token": seeded["lookup_token"]}, timeout=20)
        assert r.status_code == 200 and r.json()["already_processed"] is True
        assert r.json()["order"]["id"] == seeded["oid"]


# ===== Live server: rate limits =====
class TestLiveRateLimit:
    def test_guest_checkout_5_per_minute(self, world):
        codes = [requests.post(f"{BASE}/api/orders/checkout/guest", json=_payload(world["p_oos"], _email("rl")), timeout=20).status_code
                 for _ in range(7)]
        assert 429 in codes and codes[:5].count(400) == 5, codes

    def test_lookup_30_per_minute(self, world):
        codes = [requests.get(f"{BASE}/api/orders/lookup", params={"order_id": "x", "token": "y"}, timeout=20).status_code
                 for _ in range(33)]
        assert 429 in codes and codes[:30].count(404) == 30, codes
