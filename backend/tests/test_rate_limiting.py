"""Rate-limiting bypass + message-triggered email throttle.

Covers Problems A / B / C from the security fix:
  A. Spoofed X-Forwarded-For no longer creates fresh limiter buckets.
     `_client_ip` indexes from the RIGHT with TRUSTED_PROXY_HOPS.
  B. Message flood no longer triggers Resend flood:
     - Route limit 20/min per sender IP
     - Conversation-level `last_email_at` cooldown gates emails
       (in-app notifications keep flowing — only the email is suppressed)
  C. Community/comment routes have explicit per-minute limits.

Every test resets the limiter first via conftest.py, so runs are
independent of prior traffic.
"""
import os
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta

try:
    from pymongo import MongoClient
    _HAS_PYMONGO = True
except ImportError:  # pragma: no cover
    _HAS_PYMONGO = False


def _api_url() -> str:
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL not found")


API = _api_url()


def _mongo():
    """Direct Mongo connection so we can assert on conversation state
    without exposing a debug API for it."""
    if not _HAS_PYMONGO:
        pytest.skip("pymongo not available")
    mongo_url = db_name = None
    with open("/app/backend/.env", "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("MONGO_URL="):
                mongo_url = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("DB_NAME="):
                db_name = line.split("=", 1)[1].strip().strip('"').strip("'")
    return MongoClient(mongo_url)[db_name]


def _register(email: str, password: str = "correct-horse-battery") -> str:
    r = requests.post(
        f"{API}/api/auth/register",
        json={"email": email, "password": password, "name": "T"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _login(email: str, password: str = "correct-horse-battery") -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    return s


# ============================================================
# Problem A — spoofed X-Forwarded-For no longer buys fresh buckets
# ============================================================

def test_a1_spoofed_xff_shares_one_bucket():
    """Registering 15 times with rotating X-Forwarded-For values must
    hit the register 10/hour limit, not slide under it forever."""
    ok = 0
    limited = 0
    for i in range(15):
        r = requests.post(
            f"{API}/api/auth/register",
            json={
                "email": f"a+{uuid.uuid4().hex[:8]}@example.com",
                "password": "correct-horse-battery",
                "name": "T",
            },
            headers={"X-Forwarded-For": f"10.{i}.{i}.{i + 1}"},
            timeout=10,
        )
        if r.status_code == 200:
            ok += 1
        elif r.status_code == 429:
            limited += 1
    assert ok <= 10, f"got {ok} 200s — spoof-header bypass is back"
    assert limited >= 3, f"expected ≥3 429s, got {limited}"


def test_a2_no_header_still_resolves():
    """A legitimate call with NO X-Forwarded-For still gets rate-limited
    per its socket IP — it should not error out and it should succeed
    for the first-of-hour."""
    r = requests.post(
        f"{API}/api/auth/register",
        json={
            "email": f"noh+{uuid.uuid4().hex[:8]}@example.com",
            "password": "correct-horse-battery",
            "name": "T",
        },
        timeout=10,
    )
    assert r.status_code == 200, r.text


# ============================================================
# Problem B — message flood → in-app burst, ONE email
# ============================================================

@pytest.fixture
def message_pair():
    """Register a sender + recipient, log in as both, return session +
    ids + the Mongo-side conversation lookup helper."""
    u1 = f"s+{uuid.uuid4().hex[:8]}@example.com"
    u2 = f"r+{uuid.uuid4().hex[:8]}@example.com"
    _register(u1)
    recipient_id = _register(u2)
    sender = _login(u1)
    return sender, u1, recipient_id


def test_b3_15_messages_produce_15_notifications_and_one_email(message_pair):
    """A 15-message burst inside the cooldown window must create 15 in-app
    notifications and update `last_email_at` on the conversation exactly
    once (proving only ONE email was fired)."""
    sender, u1, recipient_id = message_pair
    for i in range(15):
        r = sender.post(
            f"{API}/api/messages/send",
            json={"recipient_id": recipient_id, "content": f"burst #{i}"},
            timeout=30,
        )
        assert r.status_code == 200, f"msg {i}: {r.status_code} {r.text[:120]}"

    db = _mongo()
    sender_user = db.users.find_one({"email": u1})
    convo = db.conversations.find_one({
        "$or": [
            {"participant_1": str(sender_user["_id"]), "participant_2": recipient_id},
            {"participant_1": recipient_id, "participant_2": str(sender_user["_id"])},
        ]
    })
    assert convo is not None
    first_email_at = convo.get("last_email_at")
    assert first_email_at is not None, "first message should have set last_email_at"

    # Send 5 more still inside the cooldown — timestamp must NOT change
    for i in range(5):
        r = sender.post(
            f"{API}/api/messages/send",
            json={"recipient_id": recipient_id, "content": f"more #{i}"},
            timeout=30,
        )
        assert r.status_code == 200
    convo2 = db.conversations.find_one({"_id": convo["_id"]})
    assert convo2["last_email_at"] == first_email_at, "second email fired inside cooldown"

    # All 20 messages must have produced 20 in-app notifications (in-app
    # never dropped — only the email is throttled).
    n_notifs = db.notifications.count_documents({
        "user_id": recipient_id,
        "type": "new_message",
        "metadata.conversation_id": str(convo["_id"]),
    })
    assert n_notifs == 20, f"expected 20 in-app notifications, got {n_notifs}"


def test_b4_email_fires_again_after_cooldown(message_pair):
    """Roll last_email_at back past the cooldown window; the next send
    must bump the timestamp to ~now, proving a fresh email was queued."""
    sender, u1, recipient_id = message_pair

    # Prime the conversation with a first send
    r = sender.post(
        f"{API}/api/messages/send",
        json={"recipient_id": recipient_id, "content": "primer"},
        timeout=10,
    )
    assert r.status_code == 200

    db = _mongo()
    sender_user = db.users.find_one({"email": u1})
    convo = db.conversations.find_one({
        "$or": [
            {"participant_1": str(sender_user["_id"]), "participant_2": recipient_id},
            {"participant_1": recipient_id, "participant_2": str(sender_user["_id"])},
        ]
    })
    db.conversations.update_one(
        {"_id": convo["_id"]},
        {"$set": {"last_email_at": datetime.now(timezone.utc) - timedelta(minutes=20)}},
    )

    r = sender.post(
        f"{API}/api/messages/send",
        json={"recipient_id": recipient_id, "content": "after cooldown"},
        timeout=10,
    )
    assert r.status_code == 200
    convo2 = db.conversations.find_one({"_id": convo["_id"]})
    elapsed = (
        datetime.now(timezone.utc)
        - convo2["last_email_at"].replace(tzinfo=timezone.utc)
    ).total_seconds()
    assert elapsed < 10, f"last_email_at not refreshed post-cooldown; elapsed={elapsed:.1f}s"


def test_b5_21st_message_in_a_minute_returns_429(message_pair):
    """Route limit 20/minute per sender IP."""
    sender, _u1, recipient_id = message_pair
    ok = 0
    limited = 0
    for i in range(25):
        r = sender.post(
            f"{API}/api/messages/send",
            json={"recipient_id": recipient_id, "content": f"floody {i}"},
            timeout=10,
        )
        if r.status_code == 200:
            ok += 1
        elif r.status_code == 429:
            limited += 1
    assert ok <= 20, f"got {ok} 200s; limit should be 20/min"
    assert limited >= 4, f"expected ≥4 429s, got {limited}"


# ============================================================
# Problem C — community/product comment limits
# ============================================================

def test_c_community_posts_limited_to_10_per_minute():
    email = f"cp+{uuid.uuid4().hex[:8]}@example.com"
    _register(email)
    s = _login(email)
    ok = 0
    limited = 0
    for i in range(13):
        r = s.post(
            f"{API}/api/community/posts",
            json={"content": f"hi from post #{i} — lorem ipsum dolor"},
            timeout=10,
        )
        if r.status_code == 200:
            ok += 1
        elif r.status_code == 429:
            limited += 1
    assert ok <= 10, f"got {ok} 200s; expected ≤10 (10/min)"
    assert limited >= 1


def test_c_product_comments_limited_to_20_per_minute():
    email = f"pc+{uuid.uuid4().hex[:8]}@example.com"
    _register(email)
    s = _login(email)

    # Find any public product to comment on
    r = requests.get(f"{API}/api/products", timeout=10)
    products = r.json() if r.status_code == 200 else []
    if not products:
        pytest.skip("No public products to comment on")
    product_id = products[0]["id"]

    ok = 0
    limited = 0
    for i in range(24):
        r = s.post(
            f"{API}/api/products/{product_id}/comments",
            json={"content": f"nice one #{i}"},
            timeout=10,
        )
        if r.status_code == 200:
            ok += 1
        elif r.status_code == 429:
            limited += 1
    assert ok <= 20, f"got {ok} 200s; expected ≤20 (20/min)"
    assert limited >= 1
