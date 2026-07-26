"""Regression tests for the shared password policy.

Covers Tasks 1–3 from the password-security fix:
  - MIN_PASSWORD_LENGTH = 8
  - MAX_PASSWORD_BYTES = 72 (bcrypt silently truncates past this — reject explicitly)
  - COMMON_PASSWORDS blocklist
  - whitespace-only rejected
  - policy applied identically on /auth/register and /auth/reset-password
  - login remains UNvalidated so legacy short-password users can still sign in
  - /auth/change-password behaviour: 401 on bad current, 400 on same-as-current, 400 on weak new
"""

import os
import uuid
import pytest
import requests


def _fake_ip() -> str:
    """Generate a unique IP per request so slowapi's per-IP rate limits don't
    interfere with the test run. The backend resolves clients via
    X-Forwarded-For (see core._client_ip)."""
    import random
    return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def _headers() -> dict:
    return {"X-Forwarded-For": _fake_ip()}


def _api_url() -> str:
    # Read the frontend .env so tests hit the same URL the frontend hits.
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL not found in frontend/.env")


API = _api_url()


def _uniq_email() -> str:
    return f"pwtest+{uuid.uuid4().hex[:10]}@example.com"


def _register(password: str, email: str | None = None):
    return requests.post(
        f"{API}/api/auth/register",
        json={"email": email or _uniq_email(), "password": password, "name": "T"},
        headers=_headers(),
        timeout=15,
    )


# ------------- register: policy rejections -------------

def test_register_empty_password_returns_400():
    r = _register("")
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower() or "whitespace" in r.json()["detail"].lower()


def test_register_whitespace_only_returns_400():
    r = _register("        ")
    assert r.status_code == 400


def test_register_one_char_returns_400():
    r = _register("a")
    assert r.status_code == 400
    assert "at least" in r.json()["detail"].lower()


def test_register_seven_char_returns_400():
    r = _register("abcdefg")
    assert r.status_code == 400


@pytest.mark.parametrize("pw", ["password", "password1", "iloveyou", "liverpool", "welcome1", "abcd1234"])
def test_register_common_password_returns_400(pw):
    # These are all ≥8 chars so they clear the length gate and land on the
    # blocklist check specifically.
    r = _register(pw)
    assert r.status_code == 400
    assert "common" in r.json()["detail"].lower() or "guessable" in r.json()["detail"].lower()


def test_register_73_byte_password_returns_400():
    # 73 ASCII chars = 73 bytes, one over bcrypt's 72-byte silent-truncation limit.
    r = _register("a" * 73)
    assert r.status_code == 400
    assert "72" in r.json()["detail"] or "too long" in r.json()["detail"].lower()


def test_register_multibyte_password_bytes_check():
    # Emoji is 4 bytes in UTF-8, so 20 emoji = 80 bytes → rejected.
    r = _register("🎉" * 20)
    assert r.status_code == 400
    assert "72" in r.json()["detail"] or "too long" in r.json()["detail"].lower()


def test_register_valid_passphrase_succeeds():
    r = _register("correct-horse-battery")
    assert r.status_code == 200
    body = r.json()
    assert "id" in body


# ------------- reset-password: same rule -------------

def test_reset_password_short_returns_400():
    r = requests.post(
        f"{API}/api/auth/reset-password",
        json={"token": "will-not-match", "new_password": "a"},
        headers=_headers(),
        timeout=15,
    )
    assert r.status_code == 400
    assert "at least" in r.json()["detail"].lower()


def test_reset_password_common_returns_400():
    r = requests.post(
        f"{API}/api/auth/reset-password",
        json={"token": "will-not-match", "new_password": "password"},
        headers=_headers(),
        timeout=15,
    )
    assert r.status_code == 400
    detail = r.json()["detail"].lower()
    assert "common" in detail or "guessable" in detail


# ------------- login: policy NOT enforced (anti-lockout) -------------

def test_login_with_short_wrong_password_returns_401_not_400():
    # Even a 1-char password must return 401 (bad creds), NOT 400 (policy violation),
    # so legacy users whose stored password predates the new policy can still sign in.
    r = requests.post(
        f"{API}/api/auth/login",
        json={"email": "does-not-exist@example.com", "password": "a"},
        headers=_headers(),
        timeout=15,
    )
    assert r.status_code == 401
    assert "invalid email or password" in r.json()["detail"].lower()


# ------------- change-password endpoint -------------

@pytest.fixture
def fresh_session():
    """Register a fresh user and return an authenticated requests.Session."""
    email = _uniq_email()
    password = "correct-horse-battery"
    r = requests.post(
        f"{API}/api/auth/register",
        json={"email": email, "password": password, "name": "T"},
        headers=_headers(),
        timeout=15,
    )
    assert r.status_code == 200, r.text

    s = requests.Session()
    s.headers.update({"X-Forwarded-For": _fake_ip()})
    r = s.post(f"{API}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    return s, email, password


def test_change_password_unauthenticated_returns_401():
    r = requests.post(
        f"{API}/api/auth/change-password",
        json={"current_password": "x", "new_password": "somenewstrong123"},
        headers=_headers(),
        timeout=15,
    )
    assert r.status_code == 401


def test_change_password_wrong_current_returns_401(fresh_session):
    s, _email, _pw = fresh_session
    r = s.post(
        f"{API}/api/auth/change-password",
        json={"current_password": "definitely-wrong", "new_password": "brandNewStrong123"},
        timeout=15,
    )
    assert r.status_code == 401
    assert "current password" in r.json()["detail"].lower()


def test_change_password_same_as_current_returns_400(fresh_session):
    s, _email, pw = fresh_session
    r = s.post(
        f"{API}/api/auth/change-password",
        json={"current_password": pw, "new_password": pw},
        timeout=15,
    )
    assert r.status_code == 400
    assert "different" in r.json()["detail"].lower()


def test_change_password_weak_new_returns_400(fresh_session):
    s, _email, pw = fresh_session
    r = s.post(
        f"{API}/api/auth/change-password",
        json={"current_password": pw, "new_password": "abc"},
        timeout=15,
    )
    assert r.status_code == 400
    assert "at least" in r.json()["detail"].lower()


def test_change_password_common_new_returns_400(fresh_session):
    s, _email, pw = fresh_session
    r = s.post(
        f"{API}/api/auth/change-password",
        json={"current_password": pw, "new_password": "password"},
        timeout=15,
    )
    assert r.status_code == 400


def test_change_password_success_flow(fresh_session):
    s, email, old_pw = fresh_session
    new_pw = "another-strong-passphrase"

    r = s.post(
        f"{API}/api/auth/change-password",
        json={"current_password": old_pw, "new_password": new_pw},
        timeout=15,
    )
    assert r.status_code == 200

    # Old password no longer works.
    r_old = requests.post(f"{API}/api/auth/login", json={"email": email, "password": old_pw}, timeout=15)
    assert r_old.status_code == 401

    # New password does.
    r_new = requests.post(f"{API}/api/auth/login", json={"email": email, "password": new_pw}, timeout=15)
    assert r_new.status_code == 200
