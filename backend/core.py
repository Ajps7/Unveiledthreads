from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, File, UploadFile
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import requests as http_requests
import resend
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import List, Optional, Dict, Any, Tuple
import uuid
import json
import html
from urllib.parse import quote
from datetime import datetime, timezone, timedelta, date
import bcrypt
import jwt
from bson import ObjectId
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import stripe as stripe_sdk
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Number of TRUSTED reverse proxies in front of this app. In the standard
# K8s ingress → backend setup that's 1. Set higher via env if you sit
# behind a stack like Cloudflare → NGINX → app. Under-configuring is safer
# than over-configuring (falls back to socket IP), so default = 1.
TRUSTED_PROXY_HOPS = int(os.environ.get("TRUSTED_PROXY_HOPS", "1"))


def _client_ip(request):
    """Resolve the real client IP for rate-limiting.

    X-Forwarded-For is a list a proxy APPENDS to as it forwards — so the
    LEFTMOST entries are client-supplied and spoofable, and only the
    rightmost `TRUSTED_PROXY_HOPS` entries were written by proxies we
    trust. The client's real IP is the entry the outermost trusted proxy
    observed, i.e. `parts[-TRUSTED_PROXY_HOPS]`.

    Indexing from the left (`.split(',')[0]`) is the classic bypass: an
    attacker just sets `X-Forwarded-For: <random>` and gets a fresh
    rate-limit bucket every request. Never do that.
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        parts = [p.strip() for p in fwd.split(",") if p.strip()]
        if len(parts) >= TRUSTED_PROXY_HOPS:
            return parts[-TRUSTED_PROXY_HOPS]
        # Header present but shorter than expected — a proxy hop is
        # missing or the deployment topology changed. Fall through to
        # socket IP rather than trust an attacker-supplied value.

    real_ip = request.headers.get("x-real-ip")
    if real_ip and TRUSTED_PROXY_HOPS >= 1:
        # Only trust X-Real-IP when we know a proxy set it, i.e. when we
        # expect at least one hop in front of us. Same reasoning as above.
        return real_ip.strip()

    return get_remote_address(request)

# Rate limiter (uses real client IP via X-Forwarded-For). Routes opt-in via @limiter.limit.
limiter = Limiter(key_func=_client_ip, default_limits=["120/minute"])

def esc(value) -> str:
    """HTML-escape user-controlled strings before interpolating into email HTML."""
    return html.escape(str(value)) if value is not None else ""


def get_stripe_session_status(session_id: str, api_key: str, stripe_account: Optional[str] = None):
    """Direct Stripe SDK call to avoid emergentintegrations Pydantic validation bug on metadata field.
    Pass stripe_account to retrieve sessions created on a connected account (direct charges)."""
    stripe_sdk.api_key = api_key
    kwargs = {}
    if stripe_account:
        kwargs["stripe_account"] = stripe_account
    session = stripe_sdk.checkout.Session.retrieve(session_id, **kwargs)
    metadata = {}
    if session.metadata and hasattr(session.metadata, "to_dict"):
        metadata = session.metadata.to_dict()
    return {
        "status": session.status,
        "payment_status": session.payment_status,
        "amount_total": session.amount_total,
        "currency": session.currency,
        "payment_intent": getattr(session, "payment_intent", None),
        "metadata": metadata
    }

ROOT_DIR = Path(__file__).parent

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_ALGORITHM = "HS256"

# Object Storage Config
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "unveiled-threads"
storage_key = None

# Buyer Protection fee config: 5% of subtotal + £0.49, capped at £6.00 per order (paid by buyer)
PLATFORM_FEE_RATE = float(os.environ.get("PLATFORM_FEE_RATE", "0.05"))
PLATFORM_FEE_FIXED = float(os.environ.get("PLATFORM_FEE_FIXED", "0.49"))
PLATFORM_FEE_CAP = float(os.environ.get("PLATFORM_FEE_CAP", "6.00"))

def calculate_buyer_fee(subtotal: float) -> float:
    return round(min(subtotal * PLATFORM_FEE_RATE + PLATFORM_FEE_FIXED, PLATFORM_FEE_CAP), 2)

# Resend email config
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Shippo config
SHIPPO_API_KEY = ""
shippo_sdk = None
shippo_components = None

def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]

def safe_object_id(id_str: str) -> ObjectId:
    """Convert string to ObjectId safely, raise 404 if invalid."""
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")

# Create the main app
app = FastAPI(title="Unveiled Threads API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ MODELS ============

class UserCreate(BaseModel):
    # NOTE: password constraints are enforced by validate_password() in the route
    # handler so we return a specific 400 with actionable copy instead of a generic
    # 422 Pydantic error. Do not add Field(min_length=...) here.
    email: EmailStr
    password: str
    name: str = Field(min_length=1, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    created_at: datetime

class BrandApplicationCreate(BaseModel):
    brand_name: str
    description: str
    instagram_handle: Optional[str] = None
    website: Optional[str] = None
    location: str
    category: str
    # -- Decoupled marketplace vs. Stripe identity (added 2026-08) --
    # `market`: where the brand is CLASSIFIED for buyer-facing curation. For
    # this platform that's always "UK" — a brand can operate in the UK
    # regardless of where they're legally registered. Default UK so nothing
    # breaks for existing single-country brands.
    market: str = "UK"
    # `stripe_country`: ISO-3166-1 alpha-2 of the country where the business
    # is LEGALLY REGISTERED and BANKED. This is the ONLY country sent to
    # Stripe. Immutable after Stripe account creation — see
    # STRIPE_SUPPORTED_COUNTRIES below for the allowlist.
    stripe_country: str = "GB"

    @field_validator("stripe_country")
    @classmethod
    def _valid_stripe_country(cls, v: str) -> str:
        v = (v or "GB").strip().upper()
        if v not in STRIPE_SUPPORTED_COUNTRIES:
            raise ValueError(
                f"Stripe onboarding isn't supported in '{v}' on this platform. "
                f"Supported countries: {', '.join(sorted(STRIPE_SUPPORTED_COUNTRIES))}."
            )
        return v


# ISO-3166-1 alpha-2 codes for countries where Stripe Connect Express is
# generally available for our platform. Deliberately conservative — we can
# widen as brands ask. Anywhere unlisted returns a clean 400 instead of
# creating a broken Stripe account (country is immutable post-create).
STRIPE_SUPPORTED_COUNTRIES = {
    # UK
    "GB",
    # EEA
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
    "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
    "SI", "ES", "SE",
    # Non-EEA European countries Stripe supports
    "CH", "NO", "IS", "LI",
    # Other common
    "US", "CA", "AU", "NZ", "JP", "SG", "HK",
}

class BrandApplicationResponse(BaseModel):
    id: str
    user_id: str
    brand_name: str
    description: str
    instagram_handle: Optional[str]
    website: Optional[str]
    location: str
    category: str
    status: str
    created_at: datetime

GENDERS = ["unisex", "mens", "womens"]
CONDITIONS = ["new", "like_new", "used"]


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=10, max_length=3000)
    price: float = Field(gt=0, le=10000)
    category: str = Field(min_length=2, max_length=50)
    sizes: List[str] = Field(min_length=1, max_length=15)
    images: List[str] = Field(min_length=1, max_length=10)
    stock: int = Field(default=0, ge=0, le=100000)
    shipping_cost: float = Field(default=3.99, ge=0, le=100)
    colour: Optional[str] = Field(default=None, max_length=50)
    material: Optional[str] = Field(default=None, max_length=50)
    gender: str = "unisex"
    condition: str = "new"
    fit: Optional[str] = Field(default=None, max_length=50)
    # ---- Pre-order fields (Model A: charge now, ship later) ----
    is_preorder: bool = False
    preorder_ship_date: Optional[date] = None  # noqa: F821  (date imported below)
    preorder_limit: Optional[int] = Field(default=None, ge=1, le=100000)
    # ---- Optional structured description (all backward-compatible) ----
    # Empty/omitted fields are hidden entirely on the frontend — no dangling labels.
    story: Optional[str] = Field(default=None, max_length=300)
    details: Optional[List[str]] = Field(default=None, max_length=8)
    materials: Optional[str] = Field(default=None, max_length=120)
    fit_notes: Optional[str] = Field(default=None, max_length=200)
    care: Optional[str] = Field(default=None, max_length=200)

    @field_validator("gender")
    @classmethod
    def _valid_gender(cls, v):
        if v not in GENDERS:
            raise ValueError(f"gender must be one of {GENDERS}")
        return v

    @field_validator("condition")
    @classmethod
    def _valid_condition(cls, v):
        if v not in CONDITIONS:
            raise ValueError(f"condition must be one of {CONDITIONS}")
        return v

    @field_validator("details")
    @classmethod
    def _valid_details(cls, v):
        if v is None:
            return v
        cleaned = [s.strip() for s in v if s and s.strip()]
        for item in cleaned:
            if len(item) > 120:
                raise ValueError("Each detail bullet must be 120 characters or fewer")
        return cleaned or None

    @model_validator(mode="after")
    def _validate_preorder(self):
        # A pre-order product MUST commit to a future ship date. Skip on non-
        # pre-order products so existing listings are unaffected.
        if self.is_preorder:
            if self.preorder_ship_date is None:
                raise ValueError("preorder_ship_date is required when is_preorder is true")
            if self.preorder_ship_date <= date.today():
                raise ValueError("preorder_ship_date must be a future date")
        return self


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    description: Optional[str] = Field(default=None, min_length=10, max_length=3000)
    price: Optional[float] = Field(default=None, gt=0, le=10000)
    category: Optional[str] = Field(default=None, min_length=2, max_length=50)
    sizes: Optional[List[str]] = Field(default=None, min_length=1, max_length=15)
    images: Optional[List[str]] = Field(default=None, min_length=1, max_length=10)
    stock: Optional[int] = Field(default=None, ge=0, le=100000)
    shipping_cost: Optional[float] = Field(default=None, ge=0, le=100)
    colour: Optional[str] = Field(default=None, max_length=50)
    material: Optional[str] = Field(default=None, max_length=50)
    gender: Optional[str] = None
    condition: Optional[str] = None
    fit: Optional[str] = Field(default=None, max_length=50)
    # ---- Pre-order fields ----
    is_preorder: Optional[bool] = None
    preorder_ship_date: Optional[date] = None  # noqa: F821
    preorder_limit: Optional[int] = Field(default=None, ge=1, le=100000)

    @field_validator("gender")
    @classmethod
    def _valid_gender(cls, v):
        if v is not None and v not in GENDERS:
            raise ValueError(f"gender must be one of {GENDERS}")
        return v

    @field_validator("condition")
    @classmethod
    def _valid_condition(cls, v):
        if v is not None and v not in CONDITIONS:
            raise ValueError(f"condition must be one of {CONDITIONS}")
        return v

    @model_validator(mode="after")
    def _validate_preorder(self):
        # If the caller is turning ON pre-order, they must also send a future
        # ship date in the same payload (or already have one saved — see route
        # handler which reads the current doc). We can only validate what we
        # see here: if is_preorder=True and a ship date is provided, it must
        # be future; if it's provided at all it must be future.
        if self.preorder_ship_date is not None and self.preorder_ship_date <= date.today():
            raise ValueError("preorder_ship_date must be a future date")
        return self


class ReferralApplyRequest(BaseModel):
    code: str = Field(min_length=3, max_length=40)


class BrandProfileUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=3000)
    instagram_handle: Optional[str] = Field(default=None, max_length=100)
    website: Optional[str] = Field(default=None, max_length=200)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    banner_url: Optional[str] = Field(default=None, max_length=500)


class DeadStockToggle(BaseModel):
    """Move a product into dead stock with an optional new (lower) price.
    If new_price is omitted the current price is kept and shown alongside the original."""
    new_price: Optional[float] = None


class QuotaRequest(BaseModel):
    requested_quota: int
    reason: Optional[str] = None


class AdminQuotaUpdate(BaseModel):
    quota: int


class DisputeCreate(BaseModel):
    """Buyer-initiated dispute against an order. v1 only handles `non_delivery`."""
    type: str = "non_delivery"  # extensible: non_delivery | not_as_described | damaged (future)
    message: str


class DisputeResolution(BaseModel):
    note: Optional[str] = None

COLOURS = ["Black", "White", "Grey", "Navy", "Green", "Olive", "Brown", "Beige", "Cream", "Red", "Blue", "Purple", "Orange", "Yellow", "Pink", "Multi"]
MATERIALS = ["Cotton", "Organic Cotton", "Polyester", "Nylon", "Fleece", "Denim", "Leather", "Wool", "Linen", "Canvas", "Corduroy", "Mesh", "Mixed"]
FITS = ["Oversized", "Regular", "Slim", "Relaxed", "Cropped", "Boxy"]
SORT_OPTIONS = ["latest", "price_low", "price_high", "popular"]

class ProductResponse(BaseModel):
    id: str
    brand_id: str
    brand_name: str
    name: str
    description: str
    price: float
    category: str
    sizes: List[str]
    images: List[str]
    stock: int
    created_at: datetime

class BrandProfile(BaseModel):
    id: str
    user_id: str
    brand_name: str
    description: str
    instagram_handle: Optional[str]
    website: Optional[str]
    location: str
    category: str
    logo_url: Optional[str]
    banner_url: Optional[str]
    is_boosted: bool
    boosted_until: Optional[datetime]
    is_brand_of_week: bool
    created_at: datetime

class BoostPackage(BaseModel):
    id: str
    name: str
    duration_days: int
    price: float
    description: str

class CheckoutRequest(BaseModel):
    package_id: str
    origin_url: str

class ProductPurchaseRequest(BaseModel):
    product_id: str
    size: str
    origin_url: str

class OrderResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    brand_name: str
    buyer_id: str
    buyer_email: str
    size: str
    price: float
    platform_fee: float
    brand_payout: float
    status: str
    created_at: datetime

class ReviewCreate(BaseModel):
    order_id: str
    product_rating: int = Field(..., ge=1, le=5)
    brand_rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class ShipOrderRequest(BaseModel):
    tracking_number: str
    courier: str

class UpdateShippingStatus(BaseModel):
    status: str  # shipped, in_transit, out_for_delivery, delivered

UK_COURIERS = ["Royal Mail", "Evri", "DPD", "Yodel", "UPS", "FedEx", "Hermes", "Other"]

SHIPPING_STATUSES = ["confirmed", "processing", "shipped", "in_transit", "out_for_delivery", "delivered"]

class MessageSend(BaseModel):
    recipient_id: str
    content: str
    order_id: Optional[str] = None

# Referral programme feature flag — keep OFF until funding secured (set REFERRALS_ENABLED=true to launch)
REFERRALS_ENABLED = os.environ.get("REFERRALS_ENABLED", "false").lower() == "true"

REFERRAL_CREDIT = 5.0  # £5 credit

# First N approved brands are permanently marked as Founding Brands
FOUNDING_BRAND_LIMIT = int(os.environ.get("FOUNDING_BRAND_LIMIT", "40"))

# ---- Payout delay (buyer protection) ----
# Applied at the Stripe Connect account level, so it covers EVERY order —
# in-stock and pre-order alike. Buffer between charge and payout gives us a
# window to intervene on chargebacks / non-shipment before funds are on
# the brand's bank statement. Kept in one place so we can tune later.
STANDARD_PAYOUT_DELAY_DAYS = int(os.environ.get("STANDARD_PAYOUT_DELAY_DAYS", "7"))
# NOTE: true per-order payout timing tied to each pre-order's ship date
# would require separate charges & transfers (funds held on the platform),
# which changes the money-custody model and has regulatory implications.
# Do NOT implement that. The account-level delay above is the approved
# approach for pre-order protection. This constant exists so a future
# reviewer knows the number's intent, not for use in code paths today.
PREORDER_PAYOUT_DELAY_DAYS = int(os.environ.get("PREORDER_PAYOUT_DELAY_DAYS", "7"))

# ---- Order statuses that count as a settled sale ----
# preorder_paid is included so pre-order revenue is NOT invisible in analytics.
SALE_STATUSES = ["paid", "preorder_paid", "shipped", "delivered"]

# Forbidden content patterns for message surveillance
import re
FORBIDDEN_PATTERNS = [
    r'\b(?:phone|phone\s*number|call\s*me|ring\s*me)\b',
    r'\b(?:email|e-mail|gmail|hotmail|yahoo|outlook)\b',
    r'\b(?:paypal|venmo|cash\s*app|bank\s*transfer|zelle)\b',
    r'\b(?:direct|off\s*platform|outside)\b',
    r'(?:https?://|www\.)\S+',
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    r'\b(?:07\d{9}|(?:\+44)\s*\d{10,})\b',
    r'\b(?:whatsapp|telegram|signal|snapchat|discord)\b',
]

def scan_message(content: str) -> Optional[str]:
    """Scan message for forbidden content. Returns warning if found, None if clean."""
    text = content.lower()
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "Message contains content that isn't allowed. Please keep all transactions on Unveiled Threads for your protection."
    return None

# ============ OBJECT STORAGE HELPERS ============

def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    resp = http_requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = http_requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    resp = http_requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 8 * 1024 * 1024  # 8MB

# Magic-byte signatures for the image formats we allow. Trusting the client's
# Content-Type header alone is unsafe — a malicious upload could claim
# image/png while actually being an HTML/JS payload (stored-XSS via the
# /files endpoint) or a Windows PE. We sniff the first bytes and match them
# against the claimed MIME. Rejects mismatches at the boundary.
_IMAGE_MAGIC_BYTES: dict[str, tuple[bytes, ...]] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    # WEBP: bytes[0:4] == b"RIFF" AND bytes[8:12] == b"WEBP". Handled specially below.
    "image/webp": (b"RIFF",),
}


def verify_image_magic_bytes(data: bytes, claimed_content_type: str) -> bool:
    """Return True iff `data`'s magic bytes match the claimed MIME.

    Called by every image upload route BEFORE writing to object storage.
    A False result means the client lied about the file format (or the file
    is truncated / not an image at all) — the upload must be rejected.
    """
    if not data or claimed_content_type not in _IMAGE_MAGIC_BYTES:
        return False

    # WEBP needs a two-window check: RIFF magic + WEBP marker at offset 8.
    if claimed_content_type == "image/webp":
        return len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP"

    prefixes = _IMAGE_MAGIC_BYTES[claimed_content_type]
    return any(data.startswith(p) for p in prefixes)


# ================================================================
# IMAGE MODERATION — inspects every image on a listing.
# ================================================================
# Strategy:
#   1. ALWAYS run cheap server-side gates (magic bytes, decode with PIL,
#      dimension cap). These never fail open — a corrupt image is refused.
#   2. If IMAGE_MODERATION_PROVIDER is configured and reachable, ask the
#      provider whether the image contains explicit/violent content and
#      surface a pass/flagged verdict per image.
#   3. If no provider is configured OR the call fails, we log a WARNING
#      and mark the image as `unverified` (still stored, still visible,
#      but flagged for admin review) — never silently pass.
#
# Provider dispatch is a single-env-var switch so we can swap between
# providers later without touching call-sites. Currently supported:
#   - IMAGE_MODERATION_PROVIDER=none   → skip external call (default)
#   - IMAGE_MODERATION_PROVIDER=claude → Claude Haiku vision via
#                                        emergentintegrations (uses
#                                        EMERGENT_LLM_KEY, no extra key)
IMAGE_MODERATION_PROVIDER = os.environ.get("IMAGE_MODERATION_PROVIDER", "none").strip().lower()
MAX_MODERATION_BYTES = 8 * 1024 * 1024   # 8 MB per spec — larger than storage cap
MAX_MODERATION_DIMENSION = 8000          # px — sanity cap on width/height


def _fetch_image_bytes_for_moderation(image_url: str) -> Optional[bytes]:
    """Resolve an /api/files/<path> URL back to bytes for local scanning.

    Product image URLs coming from `/api/upload/image` look like
    `/api/files/<app>/uploads/<user>/<file>.png`. We reuse `get_object()`
    with that path — no HTTP round-trip needed."""
    if not image_url:
        return None
    if image_url.startswith("/api/files/"):
        try:
            data, _ct = get_object(image_url[len("/api/files/"):])
            return data
        except Exception as e:
            logger.warning(f"[MODERATION] Failed to fetch object {image_url}: {e}")
            return None
    # Anything else (absolute URL to a stock photo etc.) we do not fetch —
    # those come from vetted sources. Return None and the moderator will
    # mark them as `unverified` (admin review).
    return None


def _server_side_image_gate(data: bytes) -> Tuple[bool, str]:
    """Cheap, always-on gates: real image + within size + within dims."""
    if not data:
        return False, "empty"
    if len(data) > MAX_MODERATION_BYTES:
        return False, "too_large"
    # Decode with Pillow to prove it's a real, non-corrupt image.
    try:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
            if w > MAX_MODERATION_DIMENSION or h > MAX_MODERATION_DIMENSION:
                return False, "dimensions_too_large"
    except Exception:
        return False, "corrupt_or_not_image"
    return True, "ok"


async def _claude_image_moderation(data: bytes, mime: str) -> Tuple[str, str]:
    """Ask Claude Haiku (vision) whether the image contains explicit
    sexual content or graphic violence. Returns (status, reason) where
    status is one of: "passed", "flagged", "unverified".
    Reason is a short internal code (never surfaced to sellers).
    """
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        return "unverified", "no_emergent_key"
    try:
        # Reuse the same LLM chat harness the message moderator uses.
        # We keep the prompt tight and force a single-token answer so
        # cost + latency stay minimal. `mime` isn't a constructor arg —
        # emergentintegrations sniffs it from the base64 payload itself.
        import base64
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        _ = mime  # kept in signature for future providers that need it
        b64 = base64.b64encode(data).decode()
        chat = LlmChat(
            api_key=key,
            session_id=f"imgmod-{uuid.uuid4().hex[:8]}",
            system_message=(
                "You are a strict marketplace image moderator. Look at the "
                "image and decide if it violates our listing policy. "
                "Reply with a SINGLE lowercase word: 'flagged' if the image "
                "contains explicit sexual content, nudity, graphic violence, "
                "gore, weapons, hate symbols, or is clearly unsafe for a "
                "clothing marketplace. Reply 'ok' otherwise. No punctuation, "
                "no explanation."
            ),
        ).with_model("anthropic", "claude-haiku-4-5")
        user_msg = UserMessage(
            text="Moderate this product image.",
            file_contents=[ImageContent(image_base64=b64)],
        )
        response = await chat.send_message(user_msg)
        verdict = (response or "").strip().lower()[:20]
        if "flag" in verdict:
            return "flagged", "provider_flagged"
        if "ok" in verdict or "safe" in verdict or "pass" in verdict:
            return "passed", "provider_ok"
        # Anything else → we can't be sure, mark for admin review.
        logger.warning(f"[MODERATION] Unexpected verdict from Claude: {verdict!r}")
        return "unverified", "unclear_verdict"
    except Exception as e:
        logger.warning(f"[MODERATION] Claude call failed: {e}")
        return "unverified", "provider_error"


async def moderate_product_images(image_urls: List[str]) -> List[dict]:
    """Return a list of per-image moderation results (same order as input).

    Each item: {index, url, status: passed|flagged|unverified, reason}
    The route handler is responsible for turning any 'flagged' entry
    into a 422 and any 'unverified' entry into an admin-review flag on
    the product doc."""
    results: List[dict] = []
    for i, url in enumerate(image_urls):
        data = _fetch_image_bytes_for_moderation(url)
        if data is None:
            # External / non-storage image — not something we can gate ourselves
            results.append({"index": i, "url": url, "status": "unverified", "reason": "not_our_storage"})
            continue

        ok, gate_reason = _server_side_image_gate(data)
        if not ok:
            results.append({"index": i, "url": url, "status": "flagged", "reason": gate_reason})
            continue

        # Detect MIME from magic bytes for the provider call
        if data.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif data.startswith(b"\x89PNG"):
            mime = "image/png"
        elif data.startswith(b"GIF8"):
            mime = "image/gif"
        elif data[:4] == b"RIFF" and len(data) >= 12 and data[8:12] == b"WEBP":
            mime = "image/webp"
        else:
            results.append({"index": i, "url": url, "status": "flagged", "reason": "unknown_format"})
            continue

        if IMAGE_MODERATION_PROVIDER == "claude":
            status, reason = await _claude_image_moderation(data, mime)
        elif IMAGE_MODERATION_PROVIDER == "none":
            # No provider configured — server-side gate has already passed.
            # Mark 'unverified' so admins still see the review queue and we
            # never silently pass unmoderated images through.
            status, reason = "unverified", "no_provider"
        else:
            logger.warning(f"[MODERATION] Unknown provider {IMAGE_MODERATION_PROVIDER!r}")
            status, reason = "unverified", "unknown_provider"

        results.append({"index": i, "url": url, "status": status, "reason": reason})
    return results


# ============ HELPER FUNCTIONS ============

# ---------- Password policy (shared by register / reset / change) ----------
# UK NCSC guidance: length + a common-password blocklist beats composition rules,
# which just push users toward "Password1!". Do not add "must contain a symbol"
# checks here.
MIN_PASSWORD_LENGTH = 8
# bcrypt==4.1.3 (pinned) silently truncates the input at 72 bytes. A 100-byte
# passphrase would authenticate on its first 72 bytes with no error — reject
# explicitly rather than silently truncate.
MAX_PASSWORD_BYTES = 72

# Case-insensitive blocklist of the ~50 most commonly-breached passwords
# (SecLists / HIBP top-lists). Compared against .lower().
COMMON_PASSWORDS = frozenset({
    "password", "password1", "password123", "passw0rd", "p@ssw0rd", "p@ssword",
    "123456", "1234567", "12345678", "123456789", "1234567890",
    "qwerty", "qwerty123", "qwertyuiop", "asdfghjkl", "zxcvbnm",
    "abc123", "abcd1234", "iloveyou", "letmein", "welcome", "welcome1",
    "admin", "admin123", "administrator", "root", "toor",
    "monkey", "dragon", "master", "shadow", "sunshine", "princess",
    "football", "baseball", "superman", "batman", "starwars", "trustno1",
    "liverpool", "arsenal", "chelsea", "manutd", "spurs",
    "andrew", "michael", "jennifer", "michelle", "jessica",
    "changeme", "default", "test1234", "hello123", "unveiledthreads",
})


def validate_password(password: str) -> None:
    """Enforce the shared password policy. Raises 400 with a specific,
    actionable message. Called at every password-creation point (register,
    reset, change). Never called on login — existing users may hold
    shorter/legacy passwords and must remain able to sign in."""
    if password is None or not password.strip():
        raise HTTPException(
            status_code=400,
            detail="Password cannot be empty or just whitespace.",
        )
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
        )
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Password is too long ({MAX_PASSWORD_BYTES}-byte limit). "
                "Try a shorter passphrase — length beyond this point isn't stored."
            ),
        )
    if password.lower() in COMMON_PASSWORDS:
        raise HTTPException(
            status_code=400,
            detail="That password is too common — pick something less guessable.",
        )


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id, 
        "email": email, 
        "exp": datetime.now(timezone.utc) + timedelta(hours=1), 
        "type": "access"
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id, 
        "exp": datetime.now(timezone.utc) + timedelta(days=7), 
        "type": "refresh"
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["id"] = str(user["_id"])
        del user["_id"]
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_optional_user(request: Request) -> Optional[dict]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

async def require_admin(request: Request) -> dict:
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_brand(request: Request) -> dict:
    user = await get_current_user(request)
    if user.get("role") not in ["brand", "admin"]:
        raise HTTPException(status_code=403, detail="Brand access required")
    return user

# ============ BOOST PACKAGES ============

BOOST_PACKAGES = {
    "weekly": {"id": "weekly", "name": "Weekly Boost", "duration_days": 7, "price": 9.99, "description": "7 days of featured placement"},
    "monthly": {"id": "monthly", "name": "Monthly Boost", "duration_days": 30, "price": 29.99, "description": "30 days of premium visibility"},
    "quarterly": {"id": "quarterly", "name": "Quarterly Boost", "duration_days": 90, "price": 69.99, "description": "90 days of maximum exposure"},
}

# ============ DEAD STOCK ============
# Sellers can move up to N items into a dead-stock/archive section so buyers
# can shop discounted past-collection pieces. Quota is per brand, configurable
# per brand by an admin (sellers can request an increase).
DEAD_STOCK_DEFAULT_QUOTA = int(os.environ.get("DEAD_STOCK_DEFAULT_QUOTA", "10"))


async def _brand_dead_stock_count(brand_id: str) -> int:
    return await db.products.count_documents({"brand_id": brand_id, "is_dead_stock": True})


def _brand_quota(brand_doc: dict) -> int:
    return int(brand_doc.get("dead_stock_quota") or DEAD_STOCK_DEFAULT_QUOTA)


# ============ BRAND SLUG (vanity store URLs) ============

# Slugs collide with reserved frontend routes. Blocklist before generation/admin edits.
SLUG_RESERVED = {
    "admin", "login", "register", "logout", "products", "brands", "shop",
    "store", "cart", "checkout", "orders", "wishlist", "community",
    "messages", "notifications", "settings", "terms", "privacy", "about",
    "help", "contact", "apply", "dashboard", "api", "static", "assets",
    "favicon", "robots", "sitemap", "forgot-password", "reset-password",
    "order", "brand", "referrals",
}


def _normalise_slug_candidate(text: str) -> str:
    """Strip to lowercase a-z, 0-9, dashes. Collapse multiple dashes."""
    import re
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:40]


async def generate_unique_slug(brand_name: str, exclude_brand_id: Optional[str] = None) -> str:
    """Generate a URL-safe, unique slug for a brand. Appends -2, -3... on collision.
    `exclude_brand_id` lets the same brand keep its own slug during edits."""
    base = _normalise_slug_candidate(brand_name) or "brand"
    if base in SLUG_RESERVED:
        base = f"{base}-store"
    
    candidate = base
    suffix = 2
    while True:
        query = {"slug": candidate}
        if exclude_brand_id:
            try:
                query["_id"] = {"$ne": ObjectId(exclude_brand_id)}
            except Exception:
                pass
        existing = await db.brands.find_one(query, {"_id": 1})
        if not existing:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1
        if suffix > 999:
            # Pathological fallback — should never hit in practice
            import secrets
            return f"{base}-{secrets.token_hex(3)}"

# ============ APPLICATION RISK SCORING & AUTO-APPROVAL ============

AUTO_APPROVE_RISK_THRESHOLD = 20  # score < this → auto-approve
# MVP seller cap — keep platform small while we observe early seller behaviour and shipping ops.
# Configurable via env so we can lift it without a code change.
MAX_SELLER_ACCOUNTS = int(os.environ.get("MAX_SELLER_ACCOUNTS", "40"))


async def _seller_slots_used() -> int:
    """Count of live brand profiles (each represents a seller account)."""
    return await db.brands.count_documents({})


async def _seller_cap_reached() -> bool:
    return (await _seller_slots_used()) >= MAX_SELLER_ACCOUNTS


PROTECTED_BRAND_TERMS = [
    "supreme", "nike", "adidas", "off-white", "off white", "stussy", "stüssy",
    "palace", "yeezy", "balenciaga", "gucci", "louis vuitton", "lv ", "prada",
    "dior", "fendi", "burberry", "moncler", "bape", "fear of god", "essentials",
    "corteiz", "trapstar", "amiri", "rhude", "represent",
]
COUNTERFEIT_KEYWORDS = [
    "wholesale", "dropship", "drop ship", "aliexpress", "yupoo", "1:1",
    "replica", "rep ", " rep,", "mirror quality", "dhgate", "factory direct",
    "tier 1", "ua quality", "best fake",
]
SUSPICIOUS_EMAIL_DOMAINS = [
    "tempmail.org", "guerrillamail.com", "10minutemail.com", "mailinator.com",
    "throwaway.email", "trashmail.com", "yopmail.com", "fakeinbox.com",
]


def calculate_application_risk(application, user):
    """Returns (score, reasons[]). Higher score = higher risk.
    < AUTO_APPROVE_RISK_THRESHOLD → auto-approved. Otherwise queued for admin review."""
    score = 0
    reasons = []
    
    brand_name = (application.brand_name or "").lower()
    description = (application.description or "").lower()
    email = (user.get("email") or "").lower()
    
    # Protected brand terms (very strong counterfeit signal)
    for term in PROTECTED_BRAND_TERMS:
        if term in brand_name:
            score += 50
            reasons.append(f"brand_name_contains_protected_term:{term.strip()}")
            break
    
    # Counterfeit keywords in description
    for kw in COUNTERFEIT_KEYWORDS:
        if kw in description:
            score += 40
            reasons.append(f"description_contains_counterfeit_keyword:{kw.strip()}")
            break
    
    # Throwaway email domain
    domain = email.split("@")[-1] if "@" in email else ""
    if domain in SUSPICIOUS_EMAIL_DOMAINS:
        score += 30
        reasons.append(f"throwaway_email_domain:{domain}")
    
    # Account age < 24h
    try:
        created = user.get("created_at")
        if isinstance(created, datetime):
            age_seconds = (datetime.now(timezone.utc) - created).total_seconds()
            if age_seconds < 86400:
                score += 15
                reasons.append("account_under_24h_old")
    except Exception:
        pass
    
    # Description too short / low effort
    if len(description) < 50:
        score += 10
        reasons.append("description_too_short")
    
    # Brand name too short or numeric-heavy
    if len(brand_name) < 3:
        score += 10
        reasons.append("brand_name_too_short")
    digit_ratio = sum(c.isdigit() for c in brand_name) / max(len(brand_name), 1)
    if digit_ratio > 0.3:
        score += 10
        reasons.append("brand_name_numeric_heavy")
    
    return score, reasons


async def _finalise_approval(application_id, application, origin_url):
    """Shared approval logic used by both auto-approval and manual admin approval.
    1. Marks application approved, 2. promotes user role to 'brand',
    3. creates brand profile, 4. creates Stripe Connect account + onboarding link,
    5. sends approval email with Stripe link.
    Returns: brand_id (str)."""
    # MVP seller cap — protects both auto-approval and admin manual approval paths.
    if await _seller_cap_reached():
        raise HTTPException(
            status_code=403,
            detail=(
                f"Seller cap reached ({MAX_SELLER_ACCOUNTS} brands). "
                "This application has been kept on the waitlist. "
                "Raise MAX_SELLER_ACCOUNTS or remove an existing brand to free a slot."
            ),
        )
    user_id_str = application["user_id"]
    user_object_id = ObjectId(user_id_str)
    
    # 1. Mark approved
    await db.brand_applications.update_one(
        {"_id": safe_object_id(application_id)},
        {"$set": {
            "status": "approved",
            "approved_at": datetime.now(timezone.utc),
            "auto_approved": application.get("risk_score", 100) < AUTO_APPROVE_RISK_THRESHOLD,
        }}
    )
    
    # 2. Promote user role
    applicant = await db.users.find_one({"_id": user_object_id})
    if applicant and applicant.get("role") != "admin":
        await db.users.update_one(
            {"_id": user_object_id},
            {"$set": {"role": "brand"}}
        )
    
    # 3. Create brand profile (with unique vanity slug for /@slug URLs)
    slug = await generate_unique_slug(application["brand_name"])

    brand_doc = {
        "user_id": user_id_str,
        "brand_name": application["brand_name"],
        "slug": slug,
        "description": application["description"],
        "instagram_handle": application.get("instagram_handle"),
        "website": application.get("website"),
        "location": application["location"],
        "category": application["category"],
        # Carry the market/stripe_country split from the application → brand.
        # Legacy applications default to UK/GB so downstream reads Just Work.
        "market": application.get("market") or "UK",
        "stripe_country": (application.get("stripe_country") or "GB").upper(),
        "logo_url": None,
        "banner_url": None,
        "is_boosted": False,
        "boosted_until": None,
        "is_brand_of_week": False,
        "stripe_account_id": None,
        "stripe_charges_enabled": False,
        "stripe_payouts_enabled": False,
        "stripe_onboarded_at": None,
        "is_founding": await db.brands.count_documents({}) < FOUNDING_BRAND_LIMIT,
        "created_at": datetime.now(timezone.utc)
    }
    brand_result = await db.brands.insert_one(brand_doc)
    brand_id = str(brand_result.inserted_id)
    
    # 4. Auto-create Stripe Connect account + onboarding link
    stripe_onboarding_url = None
    if applicant:
        api_key = os.environ.get("STRIPE_API_KEY")
        stripe_sdk.api_key = api_key
        try:
            # `stripe_country` was captured at application time. Fall back to
            # "GB" if this application predates the field (backfill safety).
            stripe_country = (application.get("stripe_country") or "GB").upper()
            if stripe_country not in STRIPE_SUPPORTED_COUNTRIES:
                raise ValueError(
                    f"Stripe onboarding not supported for country '{stripe_country}'"
                )
            account = await asyncio.to_thread(
                stripe_sdk.Account.create,
                type="express",
                country=stripe_country,
                email=applicant["email"],
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
                business_type="individual",
                business_profile={
                    "name": application["brand_name"],
                    "product_description": application.get("description") or "Independent UK clothing brand",
                },
                # Rolling STANDARD_PAYOUT_DELAY_DAYS buffer between charge and
                # payout to the brand's bank — buyer-protection safeguard
                # applied to every order, including pre-orders (see
                # PREORDER_PAYOUT_DELAY_DAYS note in core.py for why we don't
                # do per-order delays instead).
                settings={
                    "payouts": {
                        "schedule": {
                            "interval": "daily",
                            "delay_days": STANDARD_PAYOUT_DELAY_DAYS,
                        }
                    }
                },
                metadata={"brand_id": brand_id, "user_id": user_id_str},
            )
            await db.brands.update_one(
                {"_id": brand_result.inserted_id},
                {"$set": {"stripe_account_id": account.id}}
            )
            # Use FRONTEND_URL for refresh/return URLs since onboarding email is opened in browser
            frontend_url = os.environ.get("FRONTEND_URL", origin_url).rstrip("/")
            link = await asyncio.to_thread(
                stripe_sdk.AccountLink.create,
                account=account.id,
                refresh_url=f"{frontend_url}/brand/dashboard?connect=refresh",
                return_url=f"{frontend_url}/brand/dashboard?connect=return",
                type="account_onboarding",
            )
            stripe_onboarding_url = link.url
        except Exception as e:
            logger.error(f"Auto Stripe Connect creation failed for brand {brand_id}: {e}")
    
    # 5. Send approval notification (Resend handles the email body)
    message = (
        f"Congratulations! Your brand '{application['brand_name']}' is approved on Unveiled Threads. "
        f"One last step: complete your secure Stripe payout setup so you can start receiving payments."
    )
    if stripe_onboarding_url:
        message += f"\n\nFinish Stripe setup (5 mins): {stripe_onboarding_url}"
    
    await create_notification(
        user_id=user_id_str,
        brand_id=brand_id,
        notification_type="application_approved",
        title="You're approved — finish Stripe setup",
        message=message,
        metadata={
            "brand_id": brand_id,
            "stripe_onboarding_url": stripe_onboarding_url,
        }
    )
    
    return brand_id


# ============ NOTIFICATIONS ============

async def create_notification(user_id: Optional[str], brand_id: Optional[str], notification_type: str, title: str, message: str, metadata: Optional[dict] = None, send_email: bool = True):
    """Create a notification and send email via Resend (falls back to mock if no API key)"""
    notif_doc = {
        "user_id": user_id,
        "brand_id": brand_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "metadata": metadata or {},
        "read": False,
        "email_sent": False,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.notifications.insert_one(notif_doc)
    
    # Try to send real email via Resend
    recipient_email = None
    if user_id:
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        if user_doc:
            recipient_email = user_doc.get("email")
    elif brand_id:
        brand_doc = await db.brands.find_one({"_id": safe_object_id(brand_id)})
        if brand_doc:
            user_doc = await db.users.find_one({"_id": ObjectId(brand_doc["user_id"])})
            if user_doc:
                recipient_email = user_doc.get("email")
    
    if RESEND_API_KEY and recipient_email and send_email:
        try:
            html_content = f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
                <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;">UNVEILED THREADS</h1>
                <hr style="border:1px solid #27272A;margin:16px 0;">
                <h2 style="color:#fff;font-size:20px;">{esc(title)}</h2>
                <p style="color:#9CA3AF;line-height:1.6;">{esc(message)}</p>
                <hr style="border:1px solid #27272A;margin:24px 0;">
                <p style="color:#9CA3AF;font-size:12px;">Unveiled Threads — UK's marketplace for independent streetwear</p>
            </div>
            """
            params = {
                "from": SENDER_EMAIL,
                "to": [recipient_email],
                "subject": f"Unveiled Threads — {title}",
                "html": html_content
            }
            await asyncio.to_thread(resend.Emails.send, params)
            await db.notifications.update_one({"_id": result.inserted_id}, {"$set": {"email_sent": True}})
            logger.info(f"[EMAIL SENT] To: {recipient_email} | {title}")
        except Exception as e:
            logger.warning(f"[EMAIL FAILED] To: {recipient_email} | {title} | Error: {e}")
    else:
        logger.info(f"[MOCK EMAIL] To: user={user_id} brand={brand_id} | {title} | {message}")


# ============ APPLICATION CONFIRMATION EMAIL ============

async def send_application_received_email(
    recipient_email: str,
    brand_name: str,
    is_waitlisted: bool = False,
) -> None:
    """Fire a branded "we got your application" email that also hypes the
    Founding-Brand badge. Sent for pending + waitlisted apps only —
    auto-approved brands already receive the Stripe onboarding email via
    _finalise_approval, so no double-mail there.

    Failures are logged, never raised: an email hiccup must not block an
    application submission.
    """
    if not (RESEND_API_KEY and recipient_email):
        logger.info(
            f"[MOCK EMAIL — application received] To: {recipient_email} | "
            f"brand={brand_name} waitlisted={is_waitlisted}"
        )
        return

    try:
        founding_taken = await db.brands.count_documents({"is_founding": True})
        founding_remaining = max(0, FOUNDING_BRAND_LIMIT - founding_taken)
    except Exception:  # DB hiccup — still send the mail without the counter
        founding_remaining = 0

    show_founding_badge = founding_remaining > 0 and not is_waitlisted

    if is_waitlisted:
        headline = "You're on the waitlist"
        intro = (
            f"Thanks for applying to sell on Unveiled Threads with "
            f"<strong style=\"color:#fff;\">{esc(brand_name)}</strong>. "
            f"We're capping the platform during our MVP phase, so you're on the "
            f"waitlist — we'll email you the moment a slot opens up."
        )
    else:
        headline = "Application received"
        intro = (
            f"Thanks for applying to sell on Unveiled Threads with "
            f"<strong style=\"color:#fff;\">{esc(brand_name)}</strong>. "
            f"Our team is reviewing your application now — you'll hear back within 24 hours."
        )

    founding_block = ""
    if show_founding_badge:
        founding_block = f"""
            <div style="border:1px solid #39FF14;background:#0A0A0A;padding:20px;margin:24px 0;">
                <p style="color:#39FF14;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;margin:0 0 8px;">
                    Founding Brand — first 40 only
                </p>
                <p style="color:#fff;font-size:16px;font-weight:bold;margin:0 0 8px;">
                    You're in line for the Founding Brand badge.
                </p>
                <p style="color:#9CA3AF;font-size:13px;line-height:1.6;margin:0;">
                    The first 40 brands approved on Unveiled Threads get a permanent, exclusive
                    Founding Brand badge on their profile — a metallic mark that stays with your
                    shop forever. Only
                    <strong style="color:#39FF14;">{founding_remaining}</strong> of 40 spots
                    left. Tell your community while the badge is still up for grabs.
                </p>
            </div>
        """

    html_content = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
            <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;letter-spacing:1px;">UNVEILED THREADS</h1>
            <hr style="border:1px solid #27272A;margin:16px 0;">
            <h2 style="color:#fff;font-size:22px;margin:0 0 12px;">{headline}</h2>
            <p style="color:#9CA3AF;line-height:1.6;margin:0 0 16px;">{intro}</p>
            {founding_block}
            <p style="color:#9CA3AF;font-size:13px;line-height:1.6;">
                While you wait, follow us and tell your community you're joining Unveiled Threads —
                the UK's marketplace for independent streetwear.
            </p>
            <hr style="border:1px solid #27272A;margin:24px 0;">
            <p style="color:#9CA3AF;font-size:12px;">Unveiled Threads — UK's marketplace for independent streetwear</p>
        </div>
    """

    subject = (
        "Unveiled Threads — You're on the waitlist"
        if is_waitlisted
        else "Unveiled Threads — Application received"
    )

    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": SENDER_EMAIL,
                "to": [recipient_email],
                "subject": subject,
                "html": html_content,
            },
        )
        logger.info(f"[APPLICATION EMAIL SENT] To: {recipient_email} | waitlisted={is_waitlisted}")
    except Exception as e:
        logger.warning(f"[APPLICATION EMAIL FAILED] To: {recipient_email} | Error: {e}")
