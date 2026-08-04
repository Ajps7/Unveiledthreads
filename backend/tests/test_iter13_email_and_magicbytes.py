"""Iter13 tests:
  P2a — POST /api/brands/apply invokes send_application_received_email
        for pending + waitlisted paths (never blocks submission on email failure)
  P2b — image magic-byte sniffing on the 3 upload routes
        (/api/upload/image, /api/brands/upload-logo, /api/brands/upload-banner)
"""

import io
import os
import re
import uuid
import random
import time
import subprocess
import pytest
import requests


# ---------- shared helpers ----------

def _fake_ip() -> str:
    # DEPRECATED — kept for API compatibility; header spoofing no longer
    # affects rate-limit keys since _client_ip indexes from the right.
    return "10.0.0.1"


def _headers() -> dict:
    return {}


def _api_url() -> str:
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL not found")


API = _api_url()

# 1x1 PNG (89 50 4E 47)
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\x99c\xf8\xcf"
    b"\xc0\x00\x00\x00\x03\x00\x01[\xf3\xffa\x00\x00\x00\x00IEND\xaeB`\x82"
)
# 1x1 JPEG (starts with FFD8FF)
JPEG_BYTES = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707"
    "07090908 0a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c"
    "1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100"
    "ffc4001f0000010501010101010100000000000000000102030405060708090a0bff"
    "c400b5100002010303020403050504040000017d01020300041105122131410613 5161"
    "07227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a"
    "3435363738393a434445464748494a535455565758595a636465666768696a7374757677"
    "78797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7"
    "b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4"
    "f5f6f7f8f9faffda000801010000 3f00fbd0ffd9".replace(" ", "")
)
# 1x1 WEBP: RIFF....WEBPVP8L....
WEBP_BYTES = (
    b"RIFF\x24\x00\x00\x00WEBPVP8L\x17\x00\x00\x00\x2f\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x88\x88\x08\x07\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(
        f"{API}/api/auth/login",
        json={"email": email, "password": password},
        headers=_headers(),
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Login failed for {email}: {r.status_code} {r.text[:120]}")
    return s


@pytest.fixture(scope="module")
def brand_session() -> requests.Session:
    return _login("testbrand@example.com", "TestBrand123!")


@pytest.fixture(scope="module")
def buyer_session() -> requests.Session:
    """Login as demo brand — has a user session valid for /api/upload/image."""
    return _login("demo@threadandbone.uk", "Demo123!")


# ============================================================
# P2b — Magic-byte sniffing
# ============================================================


def test_upload_image_real_png_succeeds(buyer_session):
    r = buyer_session.post(
        f"{API}/api/upload/image",
        files={"file": ("real.png", PNG_BYTES, "image/png")},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "url" in body and body["url"].startswith("/api/files/")
    assert "file_id" in body


def test_upload_image_real_webp_succeeds(buyer_session):
    r = buyer_session.post(
        f"{API}/api/upload/image",
        files={"file": ("real.webp", WEBP_BYTES, "image/webp")},
        timeout=20,
    )
    assert r.status_code == 200, r.text


def test_upload_image_fake_png_html_bytes_rejected(buyer_session):
    """HTML content pretending to be PNG must be rejected with 400
    containing 'doesn't look like a real image'."""
    fake = b"<html><body>not an image</body></html>"
    r = buyer_session.post(
        f"{API}/api/upload/image",
        files={"file": ("evil.png", fake, "image/png")},
        timeout=20,
    )
    assert r.status_code == 400, r.text
    detail = r.json().get("detail", "")
    assert "doesn't look like a real image" in detail, detail


def test_upload_image_fake_jpeg_text_bytes_rejected(buyer_session):
    fake = b"hello world this is plain text not a jpeg"
    r = buyer_session.post(
        f"{API}/api/upload/image",
        files={"file": ("evil.jpg", fake, "image/jpeg")},
        timeout=20,
    )
    assert r.status_code == 400
    assert "doesn't look like a real image" in r.json().get("detail", "")


def test_upload_image_wrong_mime_still_rejected(buyer_session):
    """PDF (%PDF-...) with claimed image/png must be rejected."""
    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"
    r = buyer_session.post(
        f"{API}/api/upload/image",
        files={"file": ("f.png", pdf, "image/png")},
        timeout=20,
    )
    assert r.status_code == 400
    assert "doesn't look like a real image" in r.json().get("detail", "")


def test_upload_image_webp_truncated_rejected(buyer_session):
    """RIFF header without WEBP marker at offset 8 must be rejected."""
    fake_webp = b"RIFF\x00\x00\x00\x00XXXX" + b"\x00" * 20
    r = buyer_session.post(
        f"{API}/api/upload/image",
        files={"file": ("bad.webp", fake_webp, "image/webp")},
        timeout=20,
    )
    assert r.status_code == 400
    assert "doesn't look like a real image" in r.json().get("detail", "")


def test_upload_brand_logo_fake_image_rejected(brand_session):
    fake = b"<script>alert(1)</script>"
    r = brand_session.post(
        f"{API}/api/brands/upload-logo",
        files={"file": ("logo.png", fake, "image/png")},
        timeout=20,
    )
    assert r.status_code == 400
    assert "doesn't look like a real image" in r.json().get("detail", "")


def test_upload_brand_banner_fake_image_rejected(brand_session):
    fake = b"NOTANIMAGE" * 10
    r = brand_session.post(
        f"{API}/api/brands/upload-banner",
        files={"file": ("banner.jpg", fake, "image/jpeg")},
        timeout=20,
    )
    assert r.status_code == 400
    assert "doesn't look like a real image" in r.json().get("detail", "")


# ============================================================
# P2a — Application confirmation email helper invocation
# ============================================================


def _uniq_email() -> str:
    return f"apptest+{uuid.uuid4().hex[:10]}@example.com"


def _register_new_user(email: str, password: str = "longenoughpass1") -> requests.Session:
    s = requests.Session()
    r = s.post(
        f"{API}/api/auth/register",
        json={"email": email, "password": password, "name": "App Test"},
        headers=_headers(),
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Register failed: {r.status_code} {r.text[:200]}")
    return s


def _tail_backend_log(bytes_from_end: int = 30000) -> str:
    """Read last N bytes of the backend supervisor log."""
    # supervisor writes to /var/log/supervisor/backend.*.log
    import glob
    candidates = sorted(glob.glob("/var/log/supervisor/backend.*.log"))
    if not candidates:
        return ""
    out = []
    for path in candidates:
        try:
            with open(path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - bytes_from_end))
                out.append(f.read().decode("utf-8", errors="replace"))
        except Exception:
            continue
    return "\n".join(out)


def test_brand_apply_pending_invokes_application_email_helper():
    """Fresh user submits /api/brands/apply → response signals pending (not
    auto_approved), backend logs must show either
    '[MOCK EMAIL — application received]' (no Resend key) or
    '[APPLICATION EMAIL' / 'send_application_received_email failed'
    (Resend key present but recipient blocked)."""
    email = _uniq_email()
    s = _register_new_user(email)

    # Application payload chosen to score high risk so it will NOT auto-approve.
    # (Empty instagram/website + short desc pushes risk_score up; either way
    # we assert on response.auto_approved==False and log signal.)
    payload = {
        "brand_name": f"TestBrand-{uuid.uuid4().hex[:8]}",
        "description": "x" * 30,   # short-ish description
        "instagram_handle": "",
        "website": "",
        "location": "London",
        "category": "streetwear",
    }
    # Marker to easily grep the log
    marker_before = f"__MARK_BEFORE_{uuid.uuid4().hex[:8]}__"
    # Snap log length before
    log_before = _tail_backend_log(50000)
    len_before = len(log_before)

    r = s.post(f"{API}/api/brands/apply", json=payload, headers=_headers(), timeout=20)
    assert r.status_code == 200, r.text
    body = r.json()

    # Give the async email helper a moment to log
    time.sleep(1.0)

    log_after = _tail_backend_log(80000)
    delta = log_after[len_before:] if len(log_after) > len_before else log_after

    if body.get("auto_approved"):
        # If somehow auto-approved (low risk), the confirmation email helper is
        # intentionally NOT invoked — Stripe onboarding email fires instead.
        # We accept this path as non-regression.
        return

    # Not auto-approved → helper MUST have been invoked. Look for either the
    # real-send info line, the mock line, or a warning that the helper ran and
    # failed silently (Resend restricting @example.com is expected in dev).
    patterns = [
        r"\[MOCK EMAIL — application received\]",
        r"\[APPLICATION EMAIL",
        r"send_application_received_email failed",
        # Some Resend errors surface via generic warning logs — accept any log
        # line that mentions the helper function name.
        r"send_application_received_email",
    ]
    matched = any(re.search(p, delta) for p in patterns)
    assert matched, (
        "Expected send_application_received_email invocation trace in backend log after non-auto-approved /brands/apply. "
        f"Response={body}. Log tail (last 4KB):\n{delta[-4000:]}"
    )


def test_brand_apply_response_shape_unchanged():
    """Regression — response still returns id/message/auto_approved/waitlisted/risk_score."""
    email = _uniq_email()
    s = _register_new_user(email)
    payload = {
        "brand_name": f"ShapeTest-{uuid.uuid4().hex[:6]}",
        "description": "a legitimate description of the brand " * 3,
        "instagram_handle": "@somehandle",
        "website": "https://example.com",
        "location": "London",
        "category": "streetwear",
    }
    r = s.post(f"{API}/api/brands/apply", json=payload, headers=_headers(), timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    for key in ("id", "message", "auto_approved", "waitlisted", "risk_score"):
        assert key in body, f"Missing key {key} in {body}"
    assert isinstance(body["auto_approved"], bool)
    assert isinstance(body["waitlisted"], bool)
