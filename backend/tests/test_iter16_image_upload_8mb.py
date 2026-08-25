"""Iter16 tests — image upload 8MB bump + BotW fresh image flow verification.

Covers:
  * POST /api/upload/image accepts 7MB JPEG (was rejected at 5MB before bump)
  * POST /api/upload/image rejects 9MB JPEG with 400
  * Magic-byte sniffing still active (.txt renamed to .png rejected)
  * POST /api/brands/me/botw-image with a fresh (non-product) image URL
    — verifies whether backend accepts fresh uploads from device
"""
import io
import os
import struct
import zlib
import pytest
import requests


def _api_url() -> str:
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL not found")


API = _api_url()


def _make_jpeg_bytes(target_size: int) -> bytes:
    """Return a valid-magic JPEG whose total size is `target_size` bytes.
    Real JPEG magic (FFD8FF) + JFIF header + arbitrary padding + EOI (FFD9).
    The magic-byte gate only inspects the first 3 bytes, and the storage
    layer doesn't decode. Padding stays inside a JPEG comment segment (FFFE)."""
    head = bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000"  # SOI + JFIF APP0
    )
    tail = b"\xff\xd9"  # EOI
    # We'll put a JPEG comment marker (FFFE + 2-byte length + payload).
    # Comment length includes its own 2 length bytes, max 65533 payload.
    # Chain multiple comment blocks if we need more than 65k padding.
    remaining = target_size - len(head) - len(tail)
    if remaining < 0:
        raise ValueError("target_size too small")
    body = bytearray()
    while remaining > 0:
        chunk = min(remaining, 65533)
        seg_len = chunk + 2  # length field includes itself
        body += b"\xff\xfe" + struct.pack(">H", seg_len) + b"\x00" * chunk
        remaining -= (chunk + 4)  # marker(2)+length(2)+payload
    return head + bytes(body) + tail


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\x99c\xf8\xcf"
    b"\xc0\x00\x00\x00\x03\x00\x01[\xf3\xffa\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(scope="module")
def brand_session():
    s = requests.Session()
    r = s.post(
        f"{API}/api/auth/login",
        json={"email": "testbrand@example.com", "password": "TestBrand123!"},
        timeout=15,
    )
    if r.status_code != 200:
        pytest.skip(f"Login failed: {r.status_code} {r.text[:120]}")
    return s


# ---- 8MB cap tests ----

def test_upload_7mb_jpeg_accepted(brand_session):
    """7MB was rejected pre-bump. Should now succeed."""
    data = _make_jpeg_bytes(7 * 1024 * 1024)
    assert data[:3] == b"\xff\xd8\xff"
    r = brand_session.post(
        f"{API}/api/upload/image",
        files={"file": ("big.jpg", data, "image/jpeg")},
        timeout=60,
    )
    assert r.status_code == 200, f"7MB should be accepted after bump: {r.status_code} {r.text[:300]}"
    body = r.json()
    assert body.get("url", "").startswith("/api/files/")


def test_upload_9mb_jpeg_rejected(brand_session):
    """9MB exceeds the 8MB cap → 400."""
    data = _make_jpeg_bytes(9 * 1024 * 1024)
    r = brand_session.post(
        f"{API}/api/upload/image",
        files={"file": ("huge.jpg", data, "image/jpeg")},
        timeout=60,
    )
    assert r.status_code == 400, r.text[:300]


def test_upload_txt_renamed_png_rejected(brand_session):
    """Magic-byte sniff still active."""
    fake = b"This is a plain text file, not a real image at all."
    r = brand_session.post(
        f"{API}/api/upload/image",
        files={"file": ("evil.png", fake, "image/png")},
        timeout=20,
    )
    assert r.status_code == 400
    assert "doesn't look like a real image" in r.json().get("detail", "")


# ---- BotW fresh image submission ----

def test_botw_fresh_image_rejected_because_not_own_product(brand_session):
    """CRITICAL: The frontend's `submitFresh()` in BotwImagePicker uploads a
    fresh device image then POSTs the returned URL to /api/brands/me/botw-image.
    But the backend requires the image URL to belong to one of the brand's
    own products (routes/brands.py line ~100-105). So a fresh upload URL
    that hasn't been attached to any product will be rejected with 422.
    This test documents that gap."""
    # First upload a valid image
    up = brand_session.post(
        f"{API}/api/upload/image",
        files={"file": ("fresh.png", PNG_BYTES, "image/png")},
        timeout=20,
    )
    if up.status_code != 200:
        pytest.skip(f"Upload failed: {up.text[:200]}")
    fresh_url = up.json()["url"]

    # Try to submit as BotW image. This will 403 (not BotW) or 422 (not own product) —
    # but if the brand were BotW, it would still 422 because the URL isn't on any product.
    r = brand_session.post(
        f"{API}/api/brands/me/botw-image",
        json={"image_url": fresh_url},
        timeout=20,
    )
    # Document behaviour
    print(f"BotW fresh submit → {r.status_code}: {r.text[:200]}")
    # Expected outcomes: 403 (test brand isn't BotW) or 422 (would be for a BotW brand)
    assert r.status_code in (403, 422), r.text[:300]
