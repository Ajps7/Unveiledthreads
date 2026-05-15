from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, File, UploadFile
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import requests as http_requests
import resend
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from bson import ObjectId
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest
import stripe as stripe_sdk
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

def _client_ip(request):
    """Resolve the real client IP through the Kubernetes ingress proxy.
    Falls back to socket IP when no forwarding header is present."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return get_remote_address(request)

# Rate limiter (uses real client IP via X-Forwarded-For). Routes opt-in via @limiter.limit.
limiter = Limiter(key_func=_client_ip, default_limits=["120/minute"])

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

# Platform fee config
PLATFORM_FEE_PERCENT = float(os.environ.get("PLATFORM_FEE_PERCENT", "10"))

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
    email: EmailStr
    password: str
    name: str

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

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str
    sizes: List[str]
    images: List[str]
    stock: int = 0
    shipping_cost: float = 3.99
    colour: Optional[str] = None
    material: Optional[str] = None
    gender: str = "unisex"
    condition: str = "new"
    fit: Optional[str] = None

COLOURS = ["Black", "White", "Grey", "Navy", "Green", "Olive", "Brown", "Beige", "Cream", "Red", "Blue", "Purple", "Orange", "Yellow", "Pink", "Multi"]
MATERIALS = ["Cotton", "Organic Cotton", "Polyester", "Nylon", "Fleece", "Denim", "Leather", "Wool", "Linen", "Canvas", "Corduroy", "Mesh", "Mixed"]
GENDERS = ["unisex", "mens", "womens"]
CONDITIONS = ["new", "like_new", "used"]
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

REFERRAL_CREDIT = 5.0  # £5 credit

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
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

# ============ HELPER FUNCTIONS ============

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

# ============ APPLICATION RISK SCORING & AUTO-APPROVAL ============

AUTO_APPROVE_RISK_THRESHOLD = 20  # score < this → auto-approve
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
    
    # 3. Create brand profile
    brand_doc = {
        "user_id": user_id_str,
        "brand_name": application["brand_name"],
        "description": application["description"],
        "instagram_handle": application.get("instagram_handle"),
        "website": application.get("website"),
        "location": application["location"],
        "category": application["category"],
        "logo_url": None,
        "banner_url": None,
        "is_boosted": False,
        "boosted_until": None,
        "is_brand_of_week": False,
        "stripe_account_id": None,
        "stripe_charges_enabled": False,
        "stripe_payouts_enabled": False,
        "stripe_onboarded_at": None,
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
            account = await asyncio.to_thread(
                stripe_sdk.Account.create,
                type="express",
                country="GB",
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

# ============ AUTH ROUTES ============

@api_router.post("/auth/register")
@limiter.limit("10/hour")
async def register(user_data: UserCreate, request: Request, response: Response):
    email = user_data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        # Generic message to prevent email enumeration
        raise HTTPException(status_code=400, detail="Could not register account")
    
    hashed = hash_password(user_data.password)
    user_doc = {
        "email": email,
        "password_hash": hashed,
        "name": user_data.name,
        "role": "user",
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": email,
        "name": user_data.name,
        "role": "user",
        "created_at": user_doc["created_at"].isoformat()
    }

@api_router.post("/auth/login")
@limiter.limit("10/minute")
async def login(user_data: UserLogin, request: Request, response: Response):
    email = user_data.email.lower()
    user = await db.users.find_one({"email": email})
    
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "created_at": user["created_at"].isoformat() if isinstance(user["created_at"], datetime) else user["created_at"]
    }

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "created_at": user["created_at"].isoformat() if isinstance(user["created_at"], datetime) else user["created_at"]
    }

@api_router.post("/auth/refresh")
@limiter.limit("30/minute")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        user_id = str(user["_id"])
        access_token = create_access_token(user_id, user["email"])
        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=3600, path="/")
        
        return {"message": "Token refreshed"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# ============ BRAND APPLICATION ROUTES ============

@api_router.post("/brands/apply")
async def apply_for_brand(application: BrandApplicationCreate, request: Request):
    user = await get_current_user(request)
    
    # Check if user already has a pending/approved application
    existing = await db.brand_applications.find_one({
        "user_id": user["id"],
        "status": {"$in": ["pending", "approved"]}
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending or approved brand application")
    
    # Hybrid auto-approval: compute risk score from application + applicant signals
    risk_score, risk_reasons = calculate_application_risk(application, user)
    
    app_doc = {
        "user_id": user["id"],
        "brand_name": application.brand_name,
        "description": application.description,
        "instagram_handle": application.instagram_handle,
        "website": application.website,
        "location": application.location,
        "category": application.category,
        "status": "pending",
        "risk_score": risk_score,
        "risk_reasons": risk_reasons,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.brand_applications.insert_one(app_doc)
    application_id = str(result.inserted_id)
    
    # Auto-approve only if score is low. Otherwise queue for admin review.
    auto_approved = False
    if risk_score < AUTO_APPROVE_RISK_THRESHOLD:
        await _finalise_approval(application_id, app_doc, origin_url=str(request.base_url).rstrip("/"))
        auto_approved = True
    
    return {
        "id": application_id,
        "message": (
            "Application approved instantly — check your email to finish Stripe payout setup."
            if auto_approved
            else "Application submitted. Our team will review it shortly."
        ),
        "auto_approved": auto_approved,
        "risk_score": risk_score,
    }

@api_router.get("/brands/my-application")
async def get_my_application(request: Request):
    user = await get_current_user(request)
    
    application = await db.brand_applications.find_one(
        {"user_id": user["id"]},
        {"_id": 0}
    )
    
    # Also check if user has a brand profile directly (e.g. seeded brands)
    brand_profile = await db.brands.find_one({"user_id": user["id"]})
    if brand_profile:
        brand_profile["id"] = str(brand_profile["_id"])
        del brand_profile["_id"]
    
    if not application and not brand_profile:
        return None
    
    # If there's a brand profile but no application, synthesize one
    if not application and brand_profile:
        application = {
            "user_id": user["id"],
            "brand_name": brand_profile["brand_name"],
            "description": brand_profile["description"],
            "status": "approved"
        }
    
    return {
        "application": application,
        "brand_profile": brand_profile
    }

@api_router.get("/admin/applications")
async def get_all_applications(request: Request, status: Optional[str] = None):
    await require_admin(request)
    
    query = {}
    if status:
        query["status"] = status
    
    # Sort by risk score descending (highest risk first), then newest
    applications = await db.brand_applications.find(query).sort(
        [("risk_score", -1), ("created_at", -1)]
    ).to_list(100)
    
    result = []
    for app in applications:
        app["id"] = str(app["_id"])
        del app["_id"]
        # Get user info
        user = await db.users.find_one({"_id": ObjectId(app["user_id"])}, {"_id": 0, "password_hash": 0})
        app["user"] = user
        # Default scores for legacy applications submitted before risk scoring shipped
        app.setdefault("risk_score", 0)
        app.setdefault("risk_reasons", [])
        result.append(app)
    
    return result

@api_router.post("/admin/applications/{application_id}/approve")
async def approve_application(application_id: str, request: Request):
    await require_admin(request)
    
    application = await db.brand_applications.find_one({"_id": safe_object_id(application_id)})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application["status"] != "pending":
        raise HTTPException(status_code=400, detail="Application already processed")
    
    brand_id = await _finalise_approval(application_id, application, origin_url=str(request.base_url).rstrip("/"))
    return {"message": "Application approved", "brand_id": brand_id}

@api_router.post("/admin/applications/{application_id}/reject")
async def reject_application(application_id: str, request: Request):
    await require_admin(request)
    
    application = await db.brand_applications.find_one({"_id": safe_object_id(application_id)})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application["status"] != "pending":
        raise HTTPException(status_code=400, detail="Application already processed")
    
    await db.brand_applications.update_one(
        {"_id": safe_object_id(application_id)},
        {"$set": {"status": "rejected", "rejected_at": datetime.now(timezone.utc)}}
    )
    
    # Send rejection notification
    await create_notification(
        user_id=application["user_id"],
        brand_id=None,
        notification_type="application_rejected",
        title="Application Update",
        message=f"Unfortunately, your brand application for '{application['brand_name']}' was not approved at this time. You're welcome to reapply with updated details.",
        metadata={}
    )
    
    return {"message": "Application rejected"}

# ============ BRAND ROUTES ============

@api_router.get("/brands")
async def get_brands(
    category: Optional[str] = None,
    boosted: Optional[bool] = None,
    limit: int = 20
):
    query = {}
    if category:
        query["category"] = category
    if boosted is not None:
        query["is_boosted"] = boosted
    
    brands = await db.brands.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    
    result = []
    for brand in brands:
        brand["id"] = str(brand["_id"])
        del brand["_id"]
        result.append(brand)
    
    return result

@api_router.get("/brands/boosted")
async def get_boosted_brands():
    now = datetime.now(timezone.utc)
    brands = await db.brands.find({
        "is_boosted": True,
        "boosted_until": {"$gt": now}
    }).sort("boosted_until", -1).to_list(10)
    
    result = []
    for brand in brands:
        brand["id"] = str(brand["_id"])
        del brand["_id"]
        result.append(brand)
    
    return result

@api_router.get("/brands/brand-of-week")
async def get_brand_of_week():
    brand = await db.brands.find_one({"is_brand_of_week": True})
    if not brand:
        # Return most recently boosted brand as fallback
        brand = await db.brands.find_one({"is_boosted": True}, sort=[("boosted_until", -1)])
    if not brand:
        # Return any brand
        brand = await db.brands.find_one({})
    
    if brand:
        brand["id"] = str(brand["_id"])
        del brand["_id"]
        return brand
    return None

@api_router.get("/brands/{brand_id}")
async def get_brand(brand_id: str):
    brand = await db.brands.find_one({"_id": safe_object_id(brand_id)})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    brand["id"] = str(brand["_id"])
    del brand["_id"]
    
    # Get brand products
    products = await db.products.find({"brand_id": brand_id}).sort("created_at", -1).to_list(50)
    for product in products:
        product["id"] = str(product["_id"])
        del product["_id"]
    
    brand["products"] = products
    return brand

@api_router.put("/brands/profile")
async def update_brand_profile(request: Request):
    user = await require_brand(request)
    data = await request.json()
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    update_fields = {}
    allowed_fields = ["description", "instagram_handle", "website", "logo_url", "banner_url"]
    for field in allowed_fields:
        if field in data:
            update_fields[field] = data[field]
    
    if update_fields:
        await db.brands.update_one(
            {"user_id": user["id"]},
            {"$set": update_fields}
        )
    
    updated_brand = await db.brands.find_one({"user_id": user["id"]})
    updated_brand["id"] = str(updated_brand["_id"])
    del updated_brand["_id"]
    
    return updated_brand

@api_router.post("/admin/brands/{brand_id}/set-brand-of-week")
async def set_brand_of_week(brand_id: str, request: Request):
    await require_admin(request)
    
    # Remove current brand of week
    await db.brands.update_many(
        {"is_brand_of_week": True},
        {"$set": {"is_brand_of_week": False}}
    )
    
    # Set new brand of week
    result = await db.brands.update_one(
        {"_id": safe_object_id(brand_id)},
        {"$set": {"is_brand_of_week": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    return {"message": "Brand of the week updated"}

# ============ PRODUCT ROUTES ============

@api_router.post("/products")
async def create_product(product: ProductCreate, request: Request):
    user = await require_brand(request)
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    product_doc = {
        "brand_id": str(brand["_id"]),
        "brand_name": brand["brand_name"],
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "category": product.category,
        "sizes": product.sizes,
        "images": product.images,
        "stock": product.stock,
        "shipping_cost": product.shipping_cost,
        "colour": product.colour,
        "material": product.material,
        "gender": product.gender,
        "condition": product.condition,
        "fit": product.fit,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.products.insert_one(product_doc)
    
    # Remove MongoDB's _id before returning
    product_doc.pop("_id", None)
    product_doc["id"] = str(result.inserted_id)
    product_doc["created_at"] = product_doc["created_at"].isoformat()
    return product_doc

@api_router.get("/products")
async def get_products(
    category: Optional[str] = None,
    brand_id: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    size: Optional[str] = None,
    colour: Optional[str] = None,
    material: Optional[str] = None,
    gender: Optional[str] = None,
    condition: Optional[str] = None,
    fit: Optional[str] = None,
    sort: str = "latest",
    in_stock: Optional[bool] = None,
    free_shipping: Optional[bool] = None,
    limit: int = 50,
    skip: int = 0
):
    query = {}
    
    if category and category != "all":
        query["category"] = category
    if brand_id:
        query["brand_id"] = brand_id
    if min_price is not None:
        query["price"] = {"$gte": min_price}
    if max_price is not None:
        query.setdefault("price", {})["$lte"] = max_price
    if size:
        query["sizes"] = size
    if colour:
        query["colour"] = {"$regex": colour, "$options": "i"}
    if material:
        query["material"] = {"$regex": material, "$options": "i"}
    if gender and gender != "all":
        query["gender"] = gender
    if condition and condition != "all":
        query["condition"] = condition
    if fit:
        query["fit"] = {"$regex": fit, "$options": "i"}
    if in_stock:
        query["stock"] = {"$gt": 0}
    if free_shipping:
        query["$or"] = query.get("$or", [])
        query.setdefault("shipping_cost", {})["$lte"] = 0
    if search:
        search_filter = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"brand_name": {"$regex": search, "$options": "i"}}
        ]
        if "$or" in query:
            query["$and"] = [{"$or": query.pop("$or")}, {"$or": search_filter}]
        else:
            query["$or"] = search_filter
    
    # Sort
    sort_map = {
        "latest": ("created_at", -1),
        "price_low": ("price", 1),
        "price_high": ("price", -1),
        "popular": ("created_at", -1),
    }
    sort_field, sort_dir = sort_map.get(sort, ("created_at", -1))
    
    products = await db.products.find(query).sort(sort_field, sort_dir).skip(skip).limit(limit).to_list(limit)
    
    # Bulk fetch brand payment-ready state to enrich each product
    brand_ids = list({p.get("brand_id") for p in products if p.get("brand_id")})
    brand_payment_status = {}
    if brand_ids:
        try:
            brand_object_ids = [ObjectId(bid) for bid in brand_ids]
            async for b in db.brands.find(
                {"_id": {"$in": brand_object_ids}},
                {"_id": 1, "stripe_charges_enabled": 1}
            ):
                brand_payment_status[str(b["_id"])] = bool(b.get("stripe_charges_enabled"))
        except Exception:
            pass
    
    result = []
    for product in products:
        product["id"] = str(product["_id"])
        del product["_id"]
        product["seller_payments_ready"] = brand_payment_status.get(product.get("brand_id"), False)
        result.append(product)
    
    return result

@api_router.get("/products/filter-options")
async def get_filter_options():
    """Return available filter values based on existing products"""
    return {
        "colours": COLOURS,
        "materials": MATERIALS,
        "genders": [{"id": "all", "name": "All"}, {"id": "unisex", "name": "Unisex"}, {"id": "mens", "name": "Mens"}, {"id": "womens", "name": "Womens"}],
        "conditions": [{"id": "all", "name": "All"}, {"id": "new", "name": "New"}, {"id": "like_new", "name": "Like New"}, {"id": "used", "name": "Used"}],
        "fits": FITS,
        "sizes": ["XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL", "One Size"],
        "sort_options": [{"id": "latest", "name": "Latest"}, {"id": "price_low", "name": "Price: Low → High"}, {"id": "price_high", "name": "Price: High → Low"}, {"id": "popular", "name": "Popular"}],
    }

@api_router.get("/products/{product_id}")
async def get_product(product_id: str):
    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product["id"] = str(product["_id"])
    del product["_id"]
    
    # Get brand info
    brand = await db.brands.find_one({"_id": ObjectId(product["brand_id"])})
    if brand:
        brand["id"] = str(brand["_id"])
        del brand["_id"]
        product["brand"] = brand
        product["seller_payments_ready"] = bool(brand.get("stripe_charges_enabled"))
    else:
        product["seller_payments_ready"] = False
    
    return product

@api_router.put("/products/{product_id}")
async def update_product(product_id: str, request: Request):
    user = await require_brand(request)
    data = await request.json()
    
    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand or str(brand["_id"]) != product["brand_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this product")
    
    update_fields = {}
    allowed_fields = ["name", "description", "price", "category", "sizes", "images", "stock", "shipping_cost", "colour", "material", "gender", "condition", "fit"]
    for field in allowed_fields:
        if field in data:
            update_fields[field] = data[field]
    
    if update_fields:
        await db.products.update_one(
            {"_id": safe_object_id(product_id)},
            {"$set": update_fields}
        )
    
    updated = await db.products.find_one({"_id": safe_object_id(product_id)})
    updated["id"] = str(updated["_id"])
    del updated["_id"]
    
    return updated

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, request: Request):
    user = await require_brand(request)
    
    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand or str(brand["_id"]) != product["brand_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this product")
    
    await db.products.delete_one({"_id": safe_object_id(product_id)})
    return {"message": "Product deleted"}

# ============ CATEGORIES ============

CATEGORIES = [
    {"id": "hoodies", "name": "Hoodies", "icon": "shirt"},
    {"id": "t-shirts", "name": "T-Shirts", "icon": "shirt"},
    {"id": "jackets", "name": "Jackets & Coats", "icon": "shirt"},
    {"id": "trousers", "name": "Trousers & Cargos", "icon": "shirt"},
    {"id": "shorts", "name": "Shorts", "icon": "shirt"},
    {"id": "accessories", "name": "Accessories", "icon": "glasses"},
    {"id": "footwear", "name": "Footwear", "icon": "footprints"},
    {"id": "caps", "name": "Caps & Hats", "icon": "hard-hat"},
]

@api_router.get("/categories")
async def get_categories():
    return CATEGORIES

# ============ STRIPE BOOST ROUTES ============

@api_router.get("/boost/packages")
async def get_boost_packages():
    return list(BOOST_PACKAGES.values())

@api_router.post("/boost/checkout")
async def create_boost_checkout(checkout_data: CheckoutRequest, request: Request):
    # Boost feature temporarily disabled — coming soon
    raise HTTPException(
        status_code=503,
        detail="Brand boost is coming soon. We're polishing this feature and it will be available shortly.",
    )
    user = await require_brand(request)
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    package = BOOST_PACKAGES.get(checkout_data.package_id)
    if not package:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    
    success_url = f"{checkout_data.origin_url}/boost/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{checkout_data.origin_url}/brand/dashboard"
    
    checkout_request = CheckoutSessionRequest(
        amount=package["price"],
        currency="gbp",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["id"],
            "brand_id": str(brand["_id"]),
            "package_id": package["id"],
            "duration_days": str(package["duration_days"])
        }
    )
    
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": user["id"],
        "brand_id": str(brand["_id"]),
        "package_id": package["id"],
        "amount": package["price"],
        "currency": "gbp",
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/boost/status/{session_id}")
async def get_boost_status(session_id: str, request: Request):
    user = await require_brand(request)
    
    transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if already processed
    if transaction.get("payment_status") == "paid":
        return {"status": "complete", "payment_status": "paid", "already_processed": True}
    
    api_key = os.environ.get("STRIPE_API_KEY")
    
    try:
        status_data = get_stripe_session_status(session_id, api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    
    # Update transaction status
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status_data["payment_status"], "status": status_data["status"]}}
    )
    
    # If paid and not already processed, apply the boost
    if status_data["payment_status"] == "paid" and not transaction.get("boost_applied"):
        package_id = transaction["package_id"]
        package = BOOST_PACKAGES.get(package_id)
        if package:
            brand_doc = await db.brands.find_one({"_id": ObjectId(transaction["brand_id"])})
            now = datetime.now(timezone.utc)
            current_until = brand_doc.get("boosted_until") if brand_doc else None
            # Stack onto existing boost if it hasn't expired yet, else start from now
            base = current_until if (current_until and current_until > now) else now
            boosted_until = base + timedelta(days=package["duration_days"])
            await db.brands.update_one(
                {"_id": ObjectId(transaction["brand_id"])},
                {"$set": {"is_boosted": True, "boosted_until": boosted_until}}
            )
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"boost_applied": True}}
            )
    
    return {"status": status_data["status"], "payment_status": status_data["payment_status"]}

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    
    stripe_sdk.api_key = api_key
    
    # Verify signature against webhook secret. In dev (no secret set), log a loud warning
    # and accept unsigned events — but in production STRIPE_WEBHOOK_SECRET MUST be set
    # or this endpoint becomes a free path for attackers to fake payments / account state.
    raw_event = None
    if webhook_secret:
        try:
            raw_event = stripe_sdk.Webhook.construct_event(
                payload=body, sig_header=signature, secret=webhook_secret
            )
        except stripe_sdk.error.SignatureVerificationError:
            logger.warning("Stripe webhook signature verification FAILED — rejecting event")
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as e:
            logger.error(f"Stripe webhook parse error: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
    else:
        logger.warning(
            "STRIPE_WEBHOOK_SECRET is not set — webhook events are NOT being verified. "
            "Add the secret from https://dashboard.stripe.com/test/webhooks before going live."
        )
        try:
            import json as _json
            raw_event = stripe_sdk.Event.construct_from(
                _json.loads(body.decode("utf-8")), api_key
            )
        except Exception as e:
            logger.error(f"Webhook parse failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
    
    try:
        # Connect account lifecycle: keep brand connect-status fields in sync
        if raw_event.type == "account.updated":
            account = raw_event.data.object
            await db.brands.update_one(
                {"stripe_account_id": account.id},
                {"$set": {
                    "stripe_charges_enabled": bool(account.get("charges_enabled")),
                    "stripe_payouts_enabled": bool(account.get("payouts_enabled")),
                    "stripe_details_submitted": bool(account.get("details_submitted")),
                    "stripe_onboarded_at": datetime.now(timezone.utc) if account.get("charges_enabled") and account.get("payouts_enabled") else None,
                }},
            )
        
        # Checkout session completed: settle orders + (if boost) extend expiry
        if raw_event.type == "checkout.session.completed":
            session = raw_event.data.object
            session_id = session.id
            metadata = dict(session.metadata) if session.metadata else {}
            payment_status = session.payment_status
            
            # Update payment_transactions
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": payment_status, "status": session.status}}
            )
            
            # Boost flow (if still applicable when boost is re-enabled)
            transaction = await db.payment_transactions.find_one({"session_id": session_id})
            if (
                payment_status == "paid"
                and transaction
                and not transaction.get("boost_applied")
                and metadata.get("package_id")
            ):
                package = BOOST_PACKAGES.get(metadata["package_id"])
                if package:
                    brand_doc = await db.brands.find_one({"_id": ObjectId(transaction["brand_id"])})
                    now = datetime.now(timezone.utc)
                    current_until = brand_doc.get("boosted_until") if brand_doc else None
                    base = current_until if (current_until and current_until > now) else now
                    boosted_until = base + timedelta(days=package["duration_days"])
                    await db.brands.update_one(
                        {"_id": ObjectId(transaction["brand_id"])},
                        {"$set": {"is_boosted": True, "boosted_until": boosted_until}}
                    )
                    await db.payment_transactions.update_one(
                        {"session_id": session_id},
                        {"$set": {"boost_applied": True, "payment_status": "paid"}}
                    )
        
        return {"received": True}
    except HTTPException:
        raise
    except Exception as e:
        # Return 500 so Stripe retries; the previous behaviour of swallowing errors
        # would silently drop genuinely paid events.
        logger.error(f"Webhook handler error for event {getattr(raw_event, 'id', '?')}: {e}")
        raise HTTPException(status_code=500, detail="Webhook handler error")

# ============ STRIPE CONNECT (Express) ============

class ConnectOnboardRequest(BaseModel):
    origin_url: str

@api_router.post("/connect/onboard")
@limiter.limit("10/minute")
async def connect_onboard(payload: ConnectOnboardRequest, request: Request):
    """Create (or reuse) an Express connected account for the brand and return a hosted onboarding link."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_sdk.api_key = api_key
    
    account_id = brand.get("stripe_account_id")
    try:
        if not account_id:
            account = await asyncio.to_thread(
                stripe_sdk.Account.create,
                type="express",
                country="GB",
                email=user["email"],
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
                business_type="individual",
                business_profile={
                    "name": brand["brand_name"],
                    "product_description": brand.get("description", "Independent UK clothing brand"),
                },
                metadata={
                    "brand_id": str(brand["_id"]),
                    "user_id": user["id"],
                },
            )
            account_id = account.id
            await db.brands.update_one(
                {"_id": brand["_id"]},
                {"$set": {
                    "stripe_account_id": account_id,
                    "stripe_charges_enabled": False,
                    "stripe_payouts_enabled": False,
                    "stripe_onboarded_at": None,
                }},
            )
        
        # Create AccountLink for hosted onboarding
        account_link = await asyncio.to_thread(
            stripe_sdk.AccountLink.create,
            account=account_id,
            refresh_url=f"{payload.origin_url}/brand/dashboard?connect=refresh",
            return_url=f"{payload.origin_url}/brand/dashboard?connect=return",
            type="account_onboarding",
        )
        return {"url": account_link.url, "account_id": account_id}
    except stripe_sdk.error.InvalidRequestError as e:
        msg = str(e)
        if "platform-profile" in msg or "responsibilities of managing losses" in msg:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Stripe Connect platform setup required. The Unveiled Threads admin must "
                    "complete the one-time platform profile at "
                    "https://dashboard.stripe.com/settings/connect/platform-profile before brands "
                    "can onboard. Please contact support."
                ),
            )
        logger.error(f"Stripe Connect onboard failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe Connect error: {msg}")
    except Exception as e:
        logger.error(f"Stripe Connect onboard failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe Connect error: {str(e)}")

@api_router.get("/connect/status")
async def connect_status(request: Request):
    """Refresh and return the brand's Connect account state."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    account_id = brand.get("stripe_account_id")
    if not account_id:
        return {
            "stripe_account_id": None,
            "charges_enabled": False,
            "payouts_enabled": False,
            "details_submitted": False,
            "requirements_due": [],
        }
    
    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_sdk.api_key = api_key
    try:
        account = await asyncio.to_thread(stripe_sdk.Account.retrieve, account_id)
    except Exception as e:
        logger.error(f"Stripe Connect status fetch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    
    charges_enabled = bool(account.charges_enabled)
    payouts_enabled = bool(account.payouts_enabled)
    details_submitted = bool(account.details_submitted)
    requirements_due = list(getattr(account.requirements, "currently_due", []) or [])
    
    update_doc = {
        "stripe_charges_enabled": charges_enabled,
        "stripe_payouts_enabled": payouts_enabled,
        "stripe_details_submitted": details_submitted,
    }
    if charges_enabled and payouts_enabled and not brand.get("stripe_onboarded_at"):
        update_doc["stripe_onboarded_at"] = datetime.now(timezone.utc)
    await db.brands.update_one({"_id": brand["_id"]}, {"$set": update_doc})
    
    return {
        "stripe_account_id": account_id,
        "charges_enabled": charges_enabled,
        "payouts_enabled": payouts_enabled,
        "details_submitted": details_submitted,
        "requirements_due": requirements_due,
    }

@api_router.get("/connect/dashboard-link")
async def connect_dashboard_link(request: Request):
    """Return a one-time login link to the Express Dashboard for the brand."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand or not brand.get("stripe_account_id"):
        raise HTTPException(status_code=400, detail="Brand has not connected Stripe yet")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_sdk.api_key = api_key
    try:
        link = await asyncio.to_thread(
            stripe_sdk.Account.create_login_link, brand["stripe_account_id"]
        )
        return {"url": link.url}
    except Exception as e:
        logger.error(f"Stripe Connect login link failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

# ============ ADMIN STATS ============

@api_router.get("/admin/stats")
async def get_admin_stats(request: Request):
    await require_admin(request)
    
    total_users = await db.users.count_documents({})
    total_brands = await db.brands.count_documents({})
    total_products = await db.products.count_documents({})
    pending_applications = await db.brand_applications.count_documents({"status": "pending"})
    boosted_brands = await db.brands.count_documents({"is_boosted": True})
    total_orders = await db.orders.count_documents({})
    total_revenue = 0
    pipeline = [{"$match": {"status": "paid"}}, {"$group": {"_id": None, "total": {"$sum": "$platform_fee"}}}]
    async for doc in db.orders.aggregate(pipeline):
        total_revenue = doc["total"]
    
    return {
        "total_users": total_users,
        "total_brands": total_brands,
        "total_products": total_products,
        "pending_applications": pending_applications,
        "boosted_brands": boosted_brands,
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2)
    }

# ============ IMAGE UPLOAD ============

@api_router.post("/upload/image")
async def upload_image(request: Request, file: UploadFile = File(...)):
    user = await get_current_user(request)
    
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP and GIF images are allowed. Please upload a clear, well-lit photo.")
    
    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image must be under 5MB. Try compressing your photo.")
    
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/uploads/{user['id']}/{file_id}.{ext}"
    
    try:
        result = put_object(path, data, file.content_type)
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image. Please try again.")
    
    # Store reference in DB
    file_doc = {
        "file_id": file_id,
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": file.content_type,
        "size": result.get("size", len(data)),
        "user_id": user["id"],
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc)
    }
    await db.files.insert_one(file_doc)
    
    return {
        "file_id": file_id,
        "url": f"/api/files/{result['path']}",
        "original_filename": file.filename,
        "size": result.get("size", len(data))
    }

@api_router.get("/files/{path:path}")
async def serve_file(path: str):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        data, content_type = get_object(path)
    except Exception as e:
        logger.error(f"Storage download failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve file")
    
    return Response(
        content=data,
        media_type=record.get("content_type", content_type),
        headers={"Cache-Control": "public, max-age=86400"}
    )

# ============ BRAND PROFILE IMAGE UPLOAD ============

@api_router.post("/brands/upload-logo")
async def upload_brand_logo(request: Request, file: UploadFile = File(...)):
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP and GIF images are allowed.")
    
    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image must be under 5MB.")
    
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/brands/{str(brand['_id'])}/logo-{file_id}.{ext}"
    
    result = put_object(path, data, file.content_type)
    
    await db.files.insert_one({
        "file_id": file_id,
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": file.content_type,
        "size": result.get("size", len(data)),
        "user_id": user["id"],
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc)
    })
    
    logo_url = f"/api/files/{result['path']}"
    await db.brands.update_one({"_id": brand["_id"]}, {"$set": {"logo_url": logo_url}})
    
    return {"url": logo_url}

@api_router.post("/brands/upload-banner")
async def upload_brand_banner(request: Request, file: UploadFile = File(...)):
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP and GIF images are allowed.")
    
    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image must be under 5MB.")
    
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/brands/{str(brand['_id'])}/banner-{file_id}.{ext}"
    
    result = put_object(path, data, file.content_type)
    
    await db.files.insert_one({
        "file_id": file_id,
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": file.content_type,
        "size": result.get("size", len(data)),
        "user_id": user["id"],
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc)
    })
    
    banner_url = f"/api/files/{result['path']}"
    await db.brands.update_one({"_id": brand["_id"]}, {"$set": {"banner_url": banner_url}})
    
    return {"url": banner_url}

# ============ PRODUCT PURCHASE / ORDERS ============

@api_router.post("/orders/checkout")
@limiter.limit("20/minute")
async def create_order_checkout(purchase: ProductPurchaseRequest, request: Request):
    user = await get_current_user(request)
    
    product = await db.products.find_one({"_id": ObjectId(purchase.product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product["stock"] <= 0:
        raise HTTPException(status_code=400, detail="Product is out of stock")
    
    if purchase.size not in product["sizes"]:
        raise HTTPException(status_code=400, detail="Selected size is not available")
    
    # Verify brand has completed Stripe Connect onboarding (required for split payments)
    brand_doc = await db.brands.find_one({"_id": ObjectId(product["brand_id"])})
    if not brand_doc:
        raise HTTPException(status_code=404, detail="Brand not found")
    if not brand_doc.get("stripe_account_id") or not brand_doc.get("stripe_charges_enabled"):
        raise HTTPException(
            status_code=400,
            detail="This brand hasn't completed Stripe payment onboarding yet. Please check back soon.",
        )
    
    # Calculate platform fee and shipping
    product_price = product["price"]
    shipping_cost = product.get("shipping_cost", 0)
    platform_fee = round(product_price * PLATFORM_FEE_PERCENT / 100, 2)
    total_price = round(product_price + platform_fee + shipping_cost, 2)
    
    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_sdk.api_key = api_key
    
    success_url = f"{purchase.origin_url}/order/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{purchase.origin_url}/products/{purchase.product_id}"
    
    metadata = {
        "type": "product_purchase",
        "user_id": user["id"],
        "product_id": str(product["_id"]),
        "brand_id": product["brand_id"],
        "size": purchase.size,
        "product_price": str(product_price),
        "platform_fee": str(platform_fee),
        "shipping_cost": str(shipping_cost),
    }
    
    try:
        # Direct charge: payment is processed on the seller's connected account
        # (passed via stripe_account header). The seller is liable for chargebacks.
        # Platform takes its 4% via `application_fee_amount`.
        session = await asyncio.to_thread(
            stripe_sdk.checkout.Session.create,
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "gbp",
                    "product_data": {
                        "name": f"{product['name']} (Size: {purchase.size})",
                        "description": f"Sold by {product['brand_name']} via Unveiled Threads",
                    },
                    "unit_amount": int(round(total_price * 100)),
                },
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            payment_intent_data={
                "application_fee_amount": int(round(platform_fee * 100)),
                "metadata": metadata,
            },
            stripe_account=brand_doc["stripe_account_id"],
        )
    except Exception as e:
        logger.error(f"Stripe direct charge checkout failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    
    # Create order record
    order_doc = {
        "session_id": session.id,
        "buyer_id": user["id"],
        "buyer_email": user["email"],
        "buyer_name": user["name"],
        "product_id": str(product["_id"]),
        "product_name": product["name"],
        "brand_id": product["brand_id"],
        "brand_name": product["brand_name"],
        "size": purchase.size,
        "price": product_price,
        "shipping_cost": shipping_cost,
        "platform_fee": platform_fee,
        "total_charged": total_price,
        "brand_payout": product_price + shipping_cost,
        "stripe_account_id": brand_doc["stripe_account_id"],
        "status": "initiated",
        "shipping_status": "confirmed",
        "tracking_number": None,
        "courier": None,
        "shipping_updates": [],
        "reviewed": False,
        "created_at": datetime.now(timezone.utc)
    }
    await db.orders.insert_one(order_doc)
    
    # Also add to payment_transactions
    await db.payment_transactions.insert_one({
        "session_id": session.id,
        "user_id": user["id"],
        "type": "product_purchase",
        "amount": total_price,
        "currency": "gbp",
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"url": session.url, "session_id": session.id}

@api_router.get("/orders/status/{session_id}")
async def get_order_status(session_id: str, request: Request):
    user = await get_current_user(request)
    
    order = await db.orders.find_one({"session_id": session_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["buyer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if order.get("status") == "paid":
        return {"status": "complete", "payment_status": "paid", "already_processed": True}
    
    api_key = os.environ.get("STRIPE_API_KEY")
    
    try:
        # Direct charge: session lives on the seller's connected account
        status_data = get_stripe_session_status(
            session_id, api_key, stripe_account=order.get("stripe_account_id")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    
    await db.orders.update_one(
        {"session_id": session_id},
        {"$set": {"status": status_data["payment_status"]}}
    )
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status_data["payment_status"], "status": status_data["status"]}}
    )
    
    # If paid and not already processed
    if status_data["payment_status"] == "paid" and not order.get("stock_deducted"):
        # Deduct stock
        await db.products.update_one(
            {"_id": ObjectId(order["product_id"])},
            {"$inc": {"stock": -1}}
        )
        await db.orders.update_one(
            {"session_id": session_id},
            {"$set": {"stock_deducted": True}}
        )
        
        # Send notification to brand
        await create_notification(
            user_id=None,
            brand_id=order["brand_id"],
            notification_type="order_received",
            title="New Order Received!",
            message=f"New order for {order['product_name']} (Size: {order['size']}) from {order['buyer_name']}. Payout: £{order['brand_payout']:.2f}",
            metadata={"order_session_id": session_id}
        )
    
    return {"status": status_data["status"], "payment_status": status_data["payment_status"]}

@api_router.get("/orders/my-orders")
async def get_my_orders(request: Request):
    user = await get_current_user(request)
    
    orders = await db.orders.find({"buyer_id": user["id"]}).sort("created_at", -1).to_list(50)
    result = []
    for order in orders:
        order["id"] = str(order["_id"])
        del order["_id"]
        result.append(order)
    return result

@api_router.get("/orders/brand-orders")
async def get_brand_orders(request: Request):
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    orders = await db.orders.find({"brand_id": str(brand["_id"])}).sort("created_at", -1).to_list(50)
    result = []
    for order in orders:
        order["id"] = str(order["_id"])
        del order["_id"]
        result.append(order)
    return result

# ============ NOTIFICATIONS ============

async def create_notification(user_id: Optional[str], brand_id: Optional[str], notification_type: str, title: str, message: str, metadata: Optional[dict] = None):
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
    
    if RESEND_API_KEY and recipient_email:
        try:
            html_content = f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
                <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;">UNVEILED THREADS</h1>
                <hr style="border:1px solid #27272A;margin:16px 0;">
                <h2 style="color:#fff;font-size:20px;">{title}</h2>
                <p style="color:#9CA3AF;line-height:1.6;">{message}</p>
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

@api_router.get("/notifications")
async def get_notifications(request: Request):
    user = await get_current_user(request)
    
    query = {"$or": [{"user_id": user["id"]}]}
    
    # If user is a brand, also get brand notifications
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        query["$or"].append({"brand_id": str(brand["_id"])})
    
    notifications = await db.notifications.find(query).sort("created_at", -1).to_list(50)
    result = []
    for notif in notifications:
        notif["id"] = str(notif["_id"])
        del notif["_id"]
        result.append(notif)
    return result

@api_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, request: Request):
    await get_current_user(request)
    await db.notifications.update_one(
        {"_id": safe_object_id(notification_id)},
        {"$set": {"read": True}}
    )
    return {"message": "Marked as read"}

@api_router.get("/notifications/unread-count")
async def get_unread_count(request: Request):
    user = await get_current_user(request)
    
    query = {"read": False, "$or": [{"user_id": user["id"]}]}
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        query["$or"].append({"brand_id": str(brand["_id"])})
    
    count = await db.notifications.count_documents(query)
    return {"count": count}

@api_router.get("/notifications/poll")
async def poll_notifications(request: Request):
    """Combined poll endpoint for real-time in-app notifications. Returns all unread counts + latest notifications."""
    user = await get_current_user(request)
    
    # Notification count
    notif_query = {"read": False, "$or": [{"user_id": user["id"]}]}
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        notif_query["$or"].append({"brand_id": str(brand["_id"])})
    
    notif_count = await db.notifications.count_documents(notif_query)
    
    # Unread messages count
    convos = await db.conversations.find({
        "$or": [{"participant_1": user["id"]}, {"participant_2": user["id"]}]
    }, {"_id": 1}).to_list(100)
    convo_ids = [str(c["_id"]) for c in convos]
    
    msg_count = 0
    if convo_ids:
        msg_count = await db.messages.count_documents({
            "conversation_id": {"$in": convo_ids},
            "sender_id": {"$ne": user["id"]},
            "read": False
        })
    
    # Latest 3 unread notifications
    latest = []
    latest_notifs = await db.notifications.find(notif_query).sort("created_at", -1).limit(3).to_list(3)
    for n in latest_notifs:
        n["id"] = str(n["_id"])
        del n["_id"]
        if isinstance(n.get("created_at"), datetime):
            n["created_at"] = n["created_at"].isoformat()
        latest.append(n)
    
    return {
        "notifications": notif_count,
        "messages": msg_count,
        "total": notif_count + msg_count,
        "latest": latest
    }

# ============ REVIEWS & RATINGS ============

@api_router.post("/reviews")
async def create_review(review: ReviewCreate, request: Request):
    user = await get_current_user(request)
    
    order = await db.orders.find_one({"_id": safe_object_id(review.order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["buyer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your order")
    if order.get("status") != "paid":
        raise HTTPException(status_code=400, detail="Order must be paid before reviewing")
    if order.get("reviewed"):
        raise HTTPException(status_code=400, detail="Already reviewed this order")
    
    review_doc = {
        "order_id": review.order_id,
        "product_id": order["product_id"],
        "brand_id": order["brand_id"],
        "buyer_id": user["id"],
        "buyer_name": user["name"],
        "product_name": order["product_name"],
        "brand_name": order["brand_name"],
        "product_rating": review.product_rating,
        "brand_rating": review.brand_rating,
        "comment": review.comment,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.reviews.insert_one(review_doc)
    
    # Mark order as reviewed
    await db.orders.update_one({"_id": ObjectId(review.order_id)}, {"$set": {"reviewed": True}})
    
    # Notify brand
    await create_notification(
        user_id=None,
        brand_id=order["brand_id"],
        notification_type="new_review",
        title="New Review Received",
        message=f"{user['name']} left a review for {order['product_name']}: {review.product_rating}/5 stars",
        metadata={"review_id": str(result.inserted_id)}
    )
    
    review_doc.pop("_id", None)
    review_doc["id"] = str(result.inserted_id)
    return review_doc

@api_router.get("/reviews/product/{product_id}")
async def get_product_reviews(product_id: str):
    reviews = await db.reviews.find({"product_id": product_id}).sort("created_at", -1).to_list(50)
    result = []
    for r in reviews:
        r["id"] = str(r["_id"])
        del r["_id"]
        result.append(r)
    
    # Calculate average
    avg_product = sum(r["product_rating"] for r in result) / len(result) if result else 0
    avg_brand = sum(r["brand_rating"] for r in result) / len(result) if result else 0
    
    return {
        "reviews": result,
        "count": len(result),
        "avg_product_rating": round(avg_product, 1),
        "avg_brand_rating": round(avg_brand, 1)
    }

@api_router.get("/reviews/brand/{brand_id}")
async def get_brand_reviews(brand_id: str):
    reviews = await db.reviews.find({"brand_id": brand_id}).sort("created_at", -1).to_list(50)
    result = []
    for r in reviews:
        r["id"] = str(r["_id"])
        del r["_id"]
        result.append(r)
    
    avg_product = sum(r["product_rating"] for r in result) / len(result) if result else 0
    avg_brand = sum(r["brand_rating"] for r in result) / len(result) if result else 0
    
    return {
        "reviews": result,
        "count": len(result),
        "avg_product_rating": round(avg_product, 1),
        "avg_brand_rating": round(avg_brand, 1)
    }

# ============ SHIPPING / TRACKING ============

@api_router.get("/shipping/couriers")
async def get_couriers():
    return UK_COURIERS

@api_router.put("/orders/{order_id}/ship")
async def ship_order(order_id: str, ship_data: ShipOrderRequest, request: Request):
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    order = await db.orders.find_one({"_id": safe_object_id(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["brand_id"] != str(brand["_id"]):
        raise HTTPException(status_code=403, detail="Not your order")
    if order.get("status") != "paid":
        raise HTTPException(status_code=400, detail="Order must be paid before shipping")
    
    now = datetime.now(timezone.utc)
    shipping_update = {
        "status": "shipped",
        "message": f"Shipped via {ship_data.courier}. Tracking: {ship_data.tracking_number}",
        "timestamp": now
    }
    
    await db.orders.update_one(
        {"_id": safe_object_id(order_id)},
        {
            "$set": {
                "shipping_status": "shipped",
                "tracking_number": ship_data.tracking_number,
                "courier": ship_data.courier,
                "shipped_at": now
            },
            "$push": {"shipping_updates": shipping_update}
        }
    )
    
    # Notify buyer
    await create_notification(
        user_id=order["buyer_id"],
        brand_id=None,
        notification_type="order_shipped",
        title="Your Order Has Been Shipped!",
        message=f"Your order for {order['product_name']} has been shipped via {ship_data.courier}. Tracking: {ship_data.tracking_number}",
        metadata={"order_id": order_id, "tracking_number": ship_data.tracking_number, "courier": ship_data.courier}
    )
    
    return {"message": "Order marked as shipped"}

@api_router.put("/orders/{order_id}/shipping-status")
async def update_shipping_status(order_id: str, status_data: UpdateShippingStatus, request: Request):
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    order = await db.orders.find_one({"_id": safe_object_id(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["brand_id"] != str(brand["_id"]):
        raise HTTPException(status_code=403, detail="Not your order")
    
    if status_data.status not in SHIPPING_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(SHIPPING_STATUSES)}")
    
    now = datetime.now(timezone.utc)
    status_messages = {
        "processing": "Order is being prepared",
        "shipped": "Order has been shipped",
        "in_transit": "Package is in transit",
        "out_for_delivery": "Package is out for delivery",
        "delivered": "Package has been delivered"
    }
    
    shipping_update = {
        "status": status_data.status,
        "message": status_messages.get(status_data.status, status_data.status),
        "timestamp": now
    }
    
    update_fields = {"shipping_status": status_data.status}
    if status_data.status == "delivered":
        update_fields["delivered_at"] = now
    
    await db.orders.update_one(
        {"_id": safe_object_id(order_id)},
        {"$set": update_fields, "$push": {"shipping_updates": shipping_update}}
    )
    
    # Notify buyer of status change
    await create_notification(
        user_id=order["buyer_id"],
        brand_id=None,
        notification_type="shipping_update",
        title=f"Shipping Update: {status_messages.get(status_data.status, status_data.status)}",
        message=f"Your order for {order['product_name']} — {status_messages.get(status_data.status, '')}",
        metadata={"order_id": order_id, "status": status_data.status}
    )
    
    return {"message": f"Shipping status updated to {status_data.status}"}

@api_router.get("/orders/{order_id}")
async def get_order_detail(order_id: str, request: Request):
    user = await get_current_user(request)
    
    order = await db.orders.find_one({"_id": safe_object_id(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check access: buyer or brand owner
    brand = await db.brands.find_one({"user_id": user["id"]})
    is_buyer = order["buyer_id"] == user["id"]
    is_brand = brand and order["brand_id"] == str(brand["_id"])
    is_admin = user.get("role") == "admin"
    
    if not (is_buyer or is_brand or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    order["id"] = str(order["_id"])
    del order["_id"]
    
    # Convert datetime objects in shipping_updates
    if "shipping_updates" in order:
        for update in order["shipping_updates"]:
            if isinstance(update.get("timestamp"), datetime):
                update["timestamp"] = update["timestamp"].isoformat()
    
    for field in ["created_at", "shipped_at", "delivered_at"]:
        if field in order and isinstance(order[field], datetime):
            order[field] = order[field].isoformat()
    
    return order

# ============ WISHLIST ============

@api_router.post("/wishlist/{product_id}")
async def add_to_wishlist(product_id: str, request: Request):
    user = await get_current_user(request)
    
    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    existing = await db.wishlist.find_one({"user_id": user["id"], "product_id": product_id})
    if existing:
        return {"message": "Already in wishlist", "in_wishlist": True}
    
    await db.wishlist.insert_one({
        "user_id": user["id"],
        "product_id": product_id,
        "created_at": datetime.now(timezone.utc)
    })
    return {"message": "Added to wishlist", "in_wishlist": True}

@api_router.delete("/wishlist/{product_id}")
async def remove_from_wishlist(product_id: str, request: Request):
    user = await get_current_user(request)
    await db.wishlist.delete_one({"user_id": user["id"], "product_id": product_id})
    return {"message": "Removed from wishlist", "in_wishlist": False}

@api_router.get("/wishlist")
async def get_wishlist(request: Request):
    user = await get_current_user(request)
    
    wishlist_items = await db.wishlist.find({"user_id": user["id"]}).sort("created_at", -1).to_list(50)
    
    result = []
    for item in wishlist_items:
        product = await db.products.find_one({"_id": ObjectId(item["product_id"])})
        if product:
            product["id"] = str(product["_id"])
            del product["_id"]
            product["wishlisted_at"] = item["created_at"]
            result.append(product)
    
    return result

@api_router.get("/wishlist/check/{product_id}")
async def check_wishlist(product_id: str, request: Request):
    user = await get_current_user(request)
    existing = await db.wishlist.find_one({"user_id": user["id"], "product_id": product_id})
    return {"in_wishlist": existing is not None}

@api_router.get("/wishlist/ids")
async def get_wishlist_ids(request: Request):
    user = await get_current_user(request)
    items = await db.wishlist.find({"user_id": user["id"]}, {"product_id": 1, "_id": 0}).to_list(200)
    return [item["product_id"] for item in items]

# ============ BRAND ANALYTICS ============

@api_router.post("/analytics/view/{product_id}")
async def track_product_view(product_id: str, request: Request):
    """Track a product view (anonymous or authenticated)"""
    user = await get_optional_user(request)
    
    await db.product_views.insert_one({
        "product_id": product_id,
        "user_id": user["id"] if user else None,
        "created_at": datetime.now(timezone.utc)
    })
    return {"message": "View tracked"}

@api_router.get("/analytics/brand")
async def get_brand_analytics(request: Request, days: int = 30):
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    brand_id = str(brand["_id"])
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Get brand's product IDs
    products = await db.products.find({"brand_id": brand_id}, {"_id": 1, "name": 1}).to_list(100)
    product_ids = [str(p["_id"]) for p in products]
    product_names = {str(p["_id"]): p["name"] for p in products}
    
    # Total views
    total_views = await db.product_views.count_documents({
        "product_id": {"$in": product_ids},
        "created_at": {"$gte": start_date}
    })
    
    # Views per day for chart
    views_pipeline = [
        {"$match": {"product_id": {"$in": product_ids}, "created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    daily_views = []
    async for doc in db.product_views.aggregate(views_pipeline):
        daily_views.append({"date": doc["_id"], "views": doc["count"]})
    
    # Orders and revenue
    orders = await db.orders.find({
        "brand_id": brand_id,
        "status": "paid",
        "created_at": {"$gte": start_date}
    }).to_list(500)
    
    total_orders = len(orders)
    total_revenue = sum(o.get("brand_payout", 0) for o in orders)
    
    # Revenue per day for chart
    revenue_by_day = {}
    for order in orders:
        day = order["created_at"].strftime("%Y-%m-%d") if isinstance(order["created_at"], datetime) else str(order["created_at"])[:10]
        revenue_by_day[day] = revenue_by_day.get(day, 0) + order.get("brand_payout", 0)
    
    daily_revenue = [{"date": k, "revenue": round(v, 2)} for k, v in sorted(revenue_by_day.items())]
    
    # Top selling products
    product_sales = {}
    for order in orders:
        pid = order["product_id"]
        product_sales[pid] = product_sales.get(pid, {"count": 0, "revenue": 0})
        product_sales[pid]["count"] += 1
        product_sales[pid]["revenue"] += order.get("brand_payout", 0)
    
    top_products = []
    for pid, stats in sorted(product_sales.items(), key=lambda x: x[1]["revenue"], reverse=True)[:5]:
        top_products.append({
            "product_id": pid,
            "name": product_names.get(pid, "Unknown"),
            "orders": stats["count"],
            "revenue": round(stats["revenue"], 2)
        })
    
    # Views per product
    views_per_product_pipeline = [
        {"$match": {"product_id": {"$in": product_ids}, "created_at": {"$gte": start_date}}},
        {"$group": {"_id": "$product_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_viewed = []
    async for doc in db.product_views.aggregate(views_per_product_pipeline):
        top_viewed.append({
            "product_id": doc["_id"],
            "name": product_names.get(doc["_id"], "Unknown"),
            "views": doc["count"]
        })
    
    return {
        "period_days": days,
        "total_views": total_views,
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "daily_views": daily_views,
        "daily_revenue": daily_revenue,
        "top_products": top_products,
        "top_viewed": top_viewed,
        "conversion_rate": round((total_orders / total_views * 100), 2) if total_views > 0 else 0
    }

# ============ REFERRAL SYSTEM ============

@api_router.get("/referral/code")
async def get_referral_code(request: Request):
    user = await get_current_user(request)
    
    # Check if user already has a referral code
    existing = await db.referrals.find_one({"user_id": user["id"]})
    if existing:
        code = existing["code"]
    else:
        code = f"UT-{user['name'][:3].upper()}-{str(uuid.uuid4())[:6].upper()}"
        await db.referrals.insert_one({
            "user_id": user["id"],
            "code": code,
            "referred_users": [],
            "credits_earned": 0,
            "credits_used": 0,
            "created_at": datetime.now(timezone.utc)
        })
    
    return {"code": code, "credit_value": REFERRAL_CREDIT}

@api_router.post("/referral/apply")
async def apply_referral_code(request: Request):
    user = await get_current_user(request)
    data = await request.json()
    code = data.get("code", "").strip()
    
    if not code:
        raise HTTPException(status_code=400, detail="Referral code required")
    
    # Check if user already used a referral
    already_referred = await db.referral_uses.find_one({"user_id": user["id"]})
    if already_referred:
        raise HTTPException(status_code=400, detail="You've already used a referral code")
    
    # Find referral
    referral = await db.referrals.find_one({"code": code})
    if not referral:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    if referral["user_id"] == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot use your own referral code")
    
    # Mark as referred
    await db.referral_uses.insert_one({
        "user_id": user["id"],
        "referrer_id": referral["user_id"],
        "code": code,
        "credit_pending": True,
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"message": f"Referral code applied! The referrer will earn £{REFERRAL_CREDIT:.2f} credit after your first purchase."}

@api_router.get("/referral/credits")
async def get_referral_credits(request: Request):
    user = await get_current_user(request)
    
    referral = await db.referrals.find_one({"user_id": user["id"]})
    if not referral:
        return {"credits_available": 0, "credits_earned": 0, "credits_used": 0, "referred_count": 0}
    
    return {
        "credits_available": round(referral.get("credits_earned", 0) - referral.get("credits_used", 0), 2),
        "credits_earned": referral.get("credits_earned", 0),
        "credits_used": referral.get("credits_used", 0),
        "referred_count": len(referral.get("referred_users", []))
    }

@api_router.get("/referral/share-links")
async def get_share_links(request: Request):
    user = await get_current_user(request)
    
    referral = await db.referrals.find_one({"user_id": user["id"]})
    if not referral:
        # Auto-create
        code = f"UT-{user['name'][:3].upper()}-{str(uuid.uuid4())[:6].upper()}"
        await db.referrals.insert_one({
            "user_id": user["id"],
            "code": code,
            "referred_users": [],
            "credits_earned": 0,
            "credits_used": 0,
            "created_at": datetime.now(timezone.utc)
        })
    else:
        code = referral["code"]
    
    frontend_url = os.environ.get("FRONTEND_URL", "")
    ref_link = f"{frontend_url}?ref={code}"
    text = f"Check out Unveiled Threads — UK's marketplace for independent streetwear brands! Use my code {code} to join."
    
    return {
        "code": code,
        "link": ref_link,
        "twitter": f"https://twitter.com/intent/tweet?text={text}&url={ref_link}",
        "whatsapp": f"https://wa.me/?text={text} {ref_link}",
    }

# ============ MESSAGING ============

@api_router.get("/conversations")
async def get_conversations(request: Request):
    user = await get_current_user(request)
    
    convos = await db.conversations.find({
        "$or": [{"participant_1": user["id"]}, {"participant_2": user["id"]}]
    }).sort("last_message_at", -1).to_list(50)
    
    result = []
    for c in convos:
        c["id"] = str(c["_id"])
        del c["_id"]
        # Get other participant info
        other_id = c["participant_2"] if c["participant_1"] == user["id"] else c["participant_1"]
        other_user = await db.users.find_one({"_id": ObjectId(other_id)}, {"_id": 0, "password_hash": 0})
        c["other_user"] = other_user
        # Get brand name if other is a brand
        brand = await db.brands.find_one({"user_id": other_id})
        c["other_brand_name"] = brand["brand_name"] if brand else None
        result.append(c)
    
    return result

@api_router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, request: Request):
    user = await get_current_user(request)
    
    convo = await db.conversations.find_one({"_id": safe_object_id(conversation_id)})
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user["id"] not in [convo["participant_1"], convo["participant_2"]]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    messages = await db.messages.find({"conversation_id": conversation_id}).sort("created_at", 1).to_list(200)
    
    result = []
    for m in messages:
        m["id"] = str(m["_id"])
        del m["_id"]
        result.append(m)
    
    # Mark messages from other user as read
    other_id = convo["participant_2"] if convo["participant_1"] == user["id"] else convo["participant_1"]
    await db.messages.update_many(
        {"conversation_id": conversation_id, "sender_id": other_id, "read": False},
        {"$set": {"read": True}}
    )
    
    return result

@api_router.post("/messages/send")
async def send_message(msg: MessageSend, request: Request):
    user = await get_current_user(request)
    
    if user["id"] == msg.recipient_id:
        raise HTTPException(status_code=400, detail="Cannot message yourself")
    
    # Scan message for forbidden content
    warning = scan_message(msg.content)
    if warning:
        raise HTTPException(status_code=400, detail=warning)
    
    # Check recipient exists
    recipient = await db.users.find_one({"_id": safe_object_id(msg.recipient_id)})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Find or create conversation
    convo = await db.conversations.find_one({
        "$or": [
            {"participant_1": user["id"], "participant_2": msg.recipient_id},
            {"participant_1": msg.recipient_id, "participant_2": user["id"]}
        ]
    })
    
    now = datetime.now(timezone.utc)
    
    if not convo:
        convo_result = await db.conversations.insert_one({
            "participant_1": user["id"],
            "participant_2": msg.recipient_id,
            "order_id": msg.order_id,
            "last_message": msg.content[:100],
            "last_message_at": now,
            "created_at": now
        })
        conversation_id = str(convo_result.inserted_id)
    else:
        conversation_id = str(convo["_id"])
        await db.conversations.update_one(
            {"_id": convo["_id"]},
            {"$set": {"last_message": msg.content[:100], "last_message_at": now}}
        )
    
    # Insert message
    msg_doc = {
        "conversation_id": conversation_id,
        "sender_id": user["id"],
        "sender_name": user["name"],
        "content": msg.content,
        "flagged": False,
        "read": False,
        "created_at": now
    }
    result = await db.messages.insert_one(msg_doc)
    
    # Notify recipient
    await create_notification(
        user_id=msg.recipient_id,
        brand_id=None,
        notification_type="new_message",
        title=f"New message from {user['name']}",
        message=msg.content[:100],
        metadata={"conversation_id": conversation_id}
    )
    
    msg_doc.pop("_id", None)
    msg_doc["id"] = str(result.inserted_id)
    return msg_doc

@api_router.get("/messages/unread-count")
async def get_unread_message_count(request: Request):
    user = await get_current_user(request)
    
    # Get all conversation IDs for this user
    convos = await db.conversations.find({
        "$or": [{"participant_1": user["id"]}, {"participant_2": user["id"]}]
    }, {"_id": 1}).to_list(100)
    
    convo_ids = [str(c["_id"]) for c in convos]
    if not convo_ids:
        return {"count": 0}
    
    count = await db.messages.count_documents({
        "conversation_id": {"$in": convo_ids},
        "sender_id": {"$ne": user["id"]},
        "read": False
    })
    return {"count": count}

# ============ COMMUNITY FEED ============

class CommunityPostCreate(BaseModel):
    content: str
    brand_tag: Optional[str] = None
    image_url: Optional[str] = None

class CommentCreate(BaseModel):
    content: str

@api_router.post("/community/posts")
async def create_community_post(post: CommunityPostCreate, request: Request):
    user = await get_current_user(request)
    
    warning = scan_message(post.content)
    if warning:
        raise HTTPException(status_code=400, detail=warning)
    
    post_doc = {
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user.get("role", "user"),
        "content": post.content,
        "brand_tag": post.brand_tag,
        "image_url": post.image_url,
        "likes": [],
        "comment_count": 0,
        "created_at": datetime.now(timezone.utc)
    }
    
    # If user is a brand, attach brand info
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        post_doc["brand_name"] = brand["brand_name"]
        post_doc["brand_id"] = str(brand["_id"])
    
    result = await db.community_posts.insert_one(post_doc)
    post_doc.pop("_id", None)
    post_doc["id"] = str(result.inserted_id)
    return post_doc

@api_router.get("/community/posts")
async def get_community_posts(
    sort: str = "latest",
    brand_tag: Optional[str] = None,
    limit: int = 30,
    skip: int = 0
):
    query = {}
    if brand_tag:
        query["brand_tag"] = brand_tag
    
    sort_field = "created_at" if sort == "latest" else "created_at"
    sort_dir = -1
    
    if sort == "trending":
        # Sort by like count (approximated by likes array length)
        posts = await db.community_posts.find(query).sort("created_at", -1).limit(100).to_list(100)
        posts.sort(key=lambda p: len(p.get("likes", [])), reverse=True)
        posts = posts[skip:skip+limit]
    else:
        posts = await db.community_posts.find(query).sort(sort_field, sort_dir).skip(skip).limit(limit).to_list(limit)
    
    result = []
    for p in posts:
        p["id"] = str(p["_id"])
        del p["_id"]
        p["like_count"] = len(p.get("likes", []))
        result.append(p)
    
    return result

@api_router.post("/community/posts/{post_id}/like")
async def toggle_like_post(post_id: str, request: Request):
    user = await get_current_user(request)
    
    post = await db.community_posts.find_one({"_id": safe_object_id(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    likes = post.get("likes", [])
    if user["id"] in likes:
        await db.community_posts.update_one(
            {"_id": safe_object_id(post_id)},
            {"$pull": {"likes": user["id"]}}
        )
        return {"liked": False, "like_count": len(likes) - 1}
    else:
        await db.community_posts.update_one(
            {"_id": safe_object_id(post_id)},
            {"$push": {"likes": user["id"]}}
        )
        return {"liked": True, "like_count": len(likes) + 1}

@api_router.get("/community/posts/{post_id}/comments")
async def get_post_comments(post_id: str):
    comments = await db.community_comments.find({"post_id": post_id}).sort("created_at", 1).to_list(100)
    result = []
    for c in comments:
        c["id"] = str(c["_id"])
        del c["_id"]
        result.append(c)
    return result

@api_router.post("/community/posts/{post_id}/comments")
async def add_post_comment(post_id: str, comment: CommentCreate, request: Request):
    user = await get_current_user(request)
    
    warning = scan_message(comment.content)
    if warning:
        raise HTTPException(status_code=400, detail=warning)
    
    post = await db.community_posts.find_one({"_id": safe_object_id(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    comment_doc = {
        "post_id": post_id,
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user.get("role", "user"),
        "content": comment.content,
        "created_at": datetime.now(timezone.utc)
    }
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        comment_doc["brand_name"] = brand["brand_name"]
    
    result = await db.community_comments.insert_one(comment_doc)
    
    await db.community_posts.update_one(
        {"_id": safe_object_id(post_id)},
        {"$inc": {"comment_count": 1}}
    )
    
    comment_doc.pop("_id", None)
    comment_doc["id"] = str(result.inserted_id)
    return comment_doc

@api_router.delete("/community/posts/{post_id}")
async def delete_community_post(post_id: str, request: Request):
    user = await get_current_user(request)
    post = await db.community_posts.find_one({"_id": safe_object_id(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["user_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.community_posts.delete_one({"_id": safe_object_id(post_id)})
    await db.community_comments.delete_many({"post_id": post_id})
    return {"message": "Post deleted"}

# ============ PRODUCT COMMENTS ============

@api_router.get("/products/{product_id}/comments")
async def get_product_comments(product_id: str):
    comments = await db.product_comments.find({"product_id": product_id}).sort("created_at", -1).to_list(50)
    result = []
    for c in comments:
        c["id"] = str(c["_id"])
        del c["_id"]
        result.append(c)
    return result

@api_router.post("/products/{product_id}/comments")
async def add_product_comment(product_id: str, comment: CommentCreate, request: Request):
    user = await get_current_user(request)
    
    warning = scan_message(comment.content)
    if warning:
        raise HTTPException(status_code=400, detail=warning)
    
    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    comment_doc = {
        "product_id": product_id,
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user.get("role", "user"),
        "content": comment.content,
        "likes": [],
        "created_at": datetime.now(timezone.utc)
    }
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        comment_doc["brand_name"] = brand["brand_name"]
    
    result = await db.product_comments.insert_one(comment_doc)
    comment_doc.pop("_id", None)
    comment_doc["id"] = str(result.inserted_id)
    return comment_doc

@api_router.post("/products/{product_id}/comments/{comment_id}/like")
async def toggle_like_product_comment(product_id: str, comment_id: str, request: Request):
    user = await get_current_user(request)
    comment = await db.product_comments.find_one({"_id": safe_object_id(comment_id)})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    likes = comment.get("likes", [])
    if user["id"] in likes:
        await db.product_comments.update_one({"_id": safe_object_id(comment_id)}, {"$pull": {"likes": user["id"]}})
        return {"liked": False}
    else:
        await db.product_comments.update_one({"_id": safe_object_id(comment_id)}, {"$push": {"likes": user["id"]}})
        return {"liked": True}

@api_router.delete("/products/{product_id}/comments/{comment_id}")
async def delete_product_comment(product_id: str, comment_id: str, request: Request):
    user = await get_current_user(request)
    comment = await db.product_comments.find_one({"_id": safe_object_id(comment_id)})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment["user_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.product_comments.delete_one({"_id": safe_object_id(comment_id)})
    return {"message": "Comment deleted"}

# ============ SEED DATA ============

async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@ukstreetwear.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin123!")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        hashed = hash_password(admin_password)
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hashed,
            "name": "Admin",
            "role": "admin",
            "created_at": datetime.now(timezone.utc)
        })
        logger.info(f"Admin user created: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password), "role": "admin"}}
        )
        logger.info("Admin password updated")
    elif existing.get("role") != "admin":
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"role": "admin"}}
        )
        logger.info("Admin role restored")

async def seed_demo_data():
    # Check if we already have demo data
    brand_count = await db.brands.count_documents({})
    if brand_count > 0:
        return
    
    # Create demo brand user - Thread & Bone (fictional small East London brand)
    demo_email = "demo@threadandbone.uk"
    existing = await db.users.find_one({"email": demo_email})
    if not existing:
        hashed = hash_password("Demo123!")
        result = await db.users.insert_one({
            "email": demo_email,
            "password_hash": hashed,
            "name": "Thread & Bone",
            "role": "brand",
            "created_at": datetime.now(timezone.utc)
        })
        user_id = str(result.inserted_id)
        
        # Create brand profile
        brand_result = await db.brands.insert_one({
            "user_id": user_id,
            "brand_name": "Thread & Bone",
            "description": "Small-batch streetwear handmade in East London. Every piece tells a story — raw materials, honest craft, zero compromise.",
            "instagram_handle": "@threadandbone",
            "website": "https://threadandbone.uk",
            "location": "London",
            "category": "hoodies",
            "logo_url": "https://images.pexels.com/photos/3395708/pexels-photo-3395708.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
            "banner_url": "https://images.pexels.com/photos/5319298/pexels-photo-5319298.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
            "is_boosted": True,
            "boosted_until": datetime.now(timezone.utc) + timedelta(days=30),
            "is_brand_of_week": True,
            "created_at": datetime.now(timezone.utc)
        })
        brand_id = str(brand_result.inserted_id)
        
        # Create demo products
        demo_products = [
            {
                "brand_id": brand_id,
                "brand_name": "Thread & Bone",
                "name": "Smithfield Hoodie - Black",
                "description": "Heavyweight hoodie cut from brushed-back fleece. Oversized fit, hand-finished details. Made in small batches.",
                "price": 85.00,
                "category": "hoodies",
                "sizes": ["S", "M", "L", "XL"],
                "images": ["https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=800"],
                "stock": 25,
                "created_at": datetime.now(timezone.utc)
            },
            {
                "brand_id": brand_id,
                "brand_name": "Thread & Bone",
                "name": "Workshop Cargos - Olive",
                "description": "Relaxed-fit cargo trousers with utility pockets. Washed cotton twill, garment-dyed.",
                "price": 68.00,
                "category": "trousers",
                "sizes": ["S", "M", "L", "XL"],
                "images": ["https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=800"],
                "stock": 15,
                "created_at": datetime.now(timezone.utc)
            },
            {
                "brand_id": brand_id,
                "brand_name": "Thread & Bone",
                "name": "Brick Lane Tee - White",
                "description": "Screen-printed graphic tee on 220gsm organic cotton. Limited run of 50.",
                "price": 35.00,
                "category": "t-shirts",
                "sizes": ["S", "M", "L", "XL", "XXL"],
                "images": ["https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=800"],
                "stock": 50,
                "created_at": datetime.now(timezone.utc)
            }
        ]
        await db.products.insert_many(demo_products)
        
        logger.info("Demo data seeded")
    
    # Create more fictional small indie brands
    more_brands = [
        {
            "brand_name": "Nocturne Studios",
            "description": "Night-inspired streetwear from a one-person studio in Peckham. Dark palettes, reflective details, limited drops.",
            "location": "London",
            "category": "jackets"
        },
        {
            "brand_name": "Concrete Poetry",
            "description": "Graphic-heavy streetwear born in a Birmingham garage. Bold prints, organic cotton, community first.",
            "location": "Birmingham",
            "category": "t-shirts"
        },
        {
            "brand_name": "Raw Stitch Co.",
            "description": "Manchester-based brand focused on durable, everyday streetwear. Ethically sourced, locally sewn, built to last.",
            "location": "Manchester",
            "category": "hoodies"
        }
    ]
    
    for brand_data in more_brands:
        existing = await db.brands.find_one({"brand_name": brand_data["brand_name"]})
        if not existing:
            # Create user for brand
            brand_email = f"demo@{brand_data['brand_name'].lower().replace(' ', '')}.uk"
            user_exists = await db.users.find_one({"email": brand_email})
            if not user_exists:
                user_result = await db.users.insert_one({
                    "email": brand_email,
                    "password_hash": hash_password("Demo123!"),
                    "name": brand_data["brand_name"],
                    "role": "brand",
                    "created_at": datetime.now(timezone.utc)
                })
                user_id = str(user_result.inserted_id)
                
                await db.brands.insert_one({
                    "user_id": user_id,
                    "brand_name": brand_data["brand_name"],
                    "description": brand_data["description"],
                    "instagram_handle": f"@{brand_data['brand_name'].lower().replace(' ', '')}",
                    "website": f"https://{brand_data['brand_name'].lower().replace(' ', '')}.uk",
                    "location": brand_data["location"],
                    "category": brand_data["category"],
                    "logo_url": None,
                    "banner_url": None,
                    "is_boosted": False,
                    "boosted_until": None,
                    "is_brand_of_week": False,
                    "created_at": datetime.now(timezone.utc)
                })

# Include the router in the main app
app.include_router(api_router)

# Wire up rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000")],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.brands.create_index("user_id")
    await db.brands.create_index("is_boosted")
    await db.brands.create_index("is_brand_of_week")
    await db.products.create_index("brand_id")
    await db.products.create_index("category")
    await db.brand_applications.create_index("user_id")
    await db.payment_transactions.create_index("session_id")
    await db.orders.create_index("buyer_id")
    await db.orders.create_index("brand_id")
    await db.orders.create_index("session_id")
    await db.notifications.create_index("user_id")
    await db.notifications.create_index("brand_id")
    await db.files.create_index("storage_path")
    await db.files.create_index("file_id")
    await db.wishlist.create_index([("user_id", 1), ("product_id", 1)], unique=True)
    await db.product_views.create_index("product_id")
    await db.product_views.create_index("created_at")
    await db.reviews.create_index("product_id")
    await db.reviews.create_index("brand_id")
    await db.reviews.create_index("order_id", unique=True)
    await db.referrals.create_index("user_id", unique=True)
    await db.referrals.create_index("code", unique=True)
    await db.referral_uses.create_index("user_id", unique=True)
    await db.conversations.create_index([("participant_1", 1), ("participant_2", 1)])
    await db.messages.create_index("conversation_id")
    await db.messages.create_index("sender_id")
    await db.community_posts.create_index("created_at")
    await db.community_posts.create_index("brand_tag")
    await db.community_comments.create_index("post_id")
    await db.product_comments.create_index("product_id")
    
    # Init object storage
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.warning(f"Object storage init failed (will retry on first use): {e}")
    
    # Seed data
    await seed_admin()
    await seed_demo_data()
    
    # Write test credentials
    memory_dir = Path("/app/memory")
    memory_dir.mkdir(exist_ok=True)
    with open(memory_dir / "test_credentials.md", "w") as f:
        f.write("# Test Credentials\n\n")
        f.write("## Admin Account\n")
        f.write(f"- Email: {os.environ.get('ADMIN_EMAIL', 'admin@ukstreetwear.com')}\n")
        f.write(f"- Password: {os.environ.get('ADMIN_PASSWORD', 'Admin123!')}\n")
        f.write("- Role: admin\n\n")
        f.write("## Demo Brand Account\n")
        f.write("- Email: demo@threadandbone.uk\n")
        f.write("- Password: Demo123!\n")
        f.write("- Role: brand\n\n")
        f.write("## Auth Endpoints\n")
        f.write("- POST /api/auth/register\n")
        f.write("- POST /api/auth/login\n")
        f.write("- POST /api/auth/logout\n")
        f.write("- GET /api/auth/me\n")
        f.write("- POST /api/auth/refresh\n")
    
    logger.info("Application started successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
