"""Shared pytest fixtures for the backend regression suite.

The rate limiter uses the real client IP (`core._client_ip`) now that
X-Forwarded-For spoofing has been closed as a bypass. That means every
test in this run appears to slowapi as the SAME client — so a suite of
30 `POST /auth/register` calls trips the 10/hour bucket after the tenth.

Reset the shared in-memory bucket state before every test via the
non-prod-only /api/__test/reset-limiter endpoint. Also seed a "no-op"
X-Forwarded-For header so callers that used to spoof one see the value
resolved harmlessly to their real socket IP.
"""
import os
import pytest
import requests


def _load_base_url() -> str:
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        with open("/app/frontend/.env", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    v = line.strip().split("=", 1)[1]
                    break
    assert v, "REACT_APP_BACKEND_URL missing"
    return v.rstrip("/")


BASE = _load_base_url()


@pytest.fixture(autouse=True)
def _reset_rate_limiter_before_each_test():
    """Wipe the in-memory limiter buckets before every test.

    The reset endpoint is only registered when ENVIRONMENT != "production",
    so it cannot exist on the live deployment — no attack surface.
    """
    try:
        requests.post(f"{BASE}/api/__test/reset-limiter", timeout=5)
    except Exception:
        # Never let a limiter-reset hiccup mask real test failures.
        pass
    yield
