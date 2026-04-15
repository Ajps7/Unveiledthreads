from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from bson import ObjectId
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_ALGORITHM = "HS256"

def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]

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
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15), 
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

# ============ AUTH ROUTES ============

@api_router.post("/auth/register")
async def register(user_data: UserCreate, response: Response):
    email = user_data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
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
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": email,
        "name": user_data.name,
        "role": "user",
        "created_at": user_doc["created_at"].isoformat()
    }

@api_router.post("/auth/login")
async def login(user_data: UserLogin, response: Response):
    email = user_data.email.lower()
    user = await db.users.find_one({"email": email})
    
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "created_at": user["created_at"].isoformat() if isinstance(user["created_at"], datetime) else user["created_at"]
    }

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
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
        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
        
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
    
    app_doc = {
        "user_id": user["id"],
        "brand_name": application.brand_name,
        "description": application.description,
        "instagram_handle": application.instagram_handle,
        "website": application.website,
        "location": application.location,
        "category": application.category,
        "status": "pending",
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.brand_applications.insert_one(app_doc)
    
    return {
        "id": str(result.inserted_id),
        "message": "Application submitted successfully"
    }

@api_router.get("/brands/my-application")
async def get_my_application(request: Request):
    user = await get_current_user(request)
    
    application = await db.brand_applications.find_one(
        {"user_id": user["id"]},
        {"_id": 0}
    )
    if not application:
        return None
    
    # Get brand profile if approved
    brand_profile = None
    if application["status"] == "approved":
        brand_profile = await db.brands.find_one(
            {"user_id": user["id"]},
            {"_id": 0}
        )
    
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
    
    applications = await db.brand_applications.find(query).sort("created_at", -1).to_list(100)
    
    result = []
    for app in applications:
        app["id"] = str(app["_id"])
        del app["_id"]
        # Get user info
        user = await db.users.find_one({"_id": ObjectId(app["user_id"])}, {"_id": 0, "password_hash": 0})
        app["user"] = user
        result.append(app)
    
    return result

@api_router.post("/admin/applications/{application_id}/approve")
async def approve_application(application_id: str, request: Request):
    await require_admin(request)
    
    application = await db.brand_applications.find_one({"_id": ObjectId(application_id)})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application["status"] != "pending":
        raise HTTPException(status_code=400, detail="Application already processed")
    
    # Update application status
    await db.brand_applications.update_one(
        {"_id": ObjectId(application_id)},
        {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc)}}
    )
    
    # Update user role to brand
    await db.users.update_one(
        {"_id": ObjectId(application["user_id"])},
        {"$set": {"role": "brand"}}
    )
    
    # Create brand profile
    brand_doc = {
        "user_id": application["user_id"],
        "brand_name": application["brand_name"],
        "description": application["description"],
        "instagram_handle": application["instagram_handle"],
        "website": application["website"],
        "location": application["location"],
        "category": application["category"],
        "logo_url": None,
        "banner_url": None,
        "is_boosted": False,
        "boosted_until": None,
        "is_brand_of_week": False,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.brands.insert_one(brand_doc)
    
    return {"message": "Application approved", "brand_id": str(result.inserted_id)}

@api_router.post("/admin/applications/{application_id}/reject")
async def reject_application(application_id: str, request: Request):
    await require_admin(request)
    
    application = await db.brand_applications.find_one({"_id": ObjectId(application_id)})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application["status"] != "pending":
        raise HTTPException(status_code=400, detail="Application already processed")
    
    await db.brand_applications.update_one(
        {"_id": ObjectId(application_id)},
        {"$set": {"status": "rejected", "rejected_at": datetime.now(timezone.utc)}}
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
    brand = await db.brands.find_one({"_id": ObjectId(brand_id)})
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
        {"_id": ObjectId(brand_id)},
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
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.products.insert_one(product_doc)
    
    product_doc["id"] = str(result.inserted_id)
    return product_doc

@api_router.get("/products")
async def get_products(
    category: Optional[str] = None,
    brand_id: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 50,
    skip: int = 0
):
    query = {}
    
    if category:
        query["category"] = category
    if brand_id:
        query["brand_id"] = brand_id
    if min_price is not None:
        query["price"] = {"$gte": min_price}
    if max_price is not None:
        query.setdefault("price", {})["$lte"] = max_price
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"brand_name": {"$regex": search, "$options": "i"}}
        ]
    
    products = await db.products.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    result = []
    for product in products:
        product["id"] = str(product["_id"])
        del product["_id"]
        result.append(product)
    
    return result

@api_router.get("/products/{product_id}")
async def get_product(product_id: str):
    product = await db.products.find_one({"_id": ObjectId(product_id)})
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
    
    return product

@api_router.put("/products/{product_id}")
async def update_product(product_id: str, request: Request):
    user = await require_brand(request)
    data = await request.json()
    
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand or str(brand["_id"]) != product["brand_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this product")
    
    update_fields = {}
    allowed_fields = ["name", "description", "price", "category", "sizes", "images", "stock"]
    for field in allowed_fields:
        if field in data:
            update_fields[field] = data[field]
    
    if update_fields:
        await db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": update_fields}
        )
    
    updated = await db.products.find_one({"_id": ObjectId(product_id)})
    updated["id"] = str(updated["_id"])
    del updated["_id"]
    
    return updated

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, request: Request):
    user = await require_brand(request)
    
    product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand or str(brand["_id"]) != product["brand_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this product")
    
    await db.products.delete_one({"_id": ObjectId(product_id)})
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
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    
    status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction status
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status.payment_status, "status": status.status}}
    )
    
    # If paid and not already processed, apply the boost
    if status.payment_status == "paid" and not transaction.get("boost_applied"):
        package_id = transaction["package_id"]
        package = BOOST_PACKAGES.get(package_id)
        if package:
            boosted_until = datetime.now(timezone.utc) + timedelta(days=package["duration_days"])
            await db.brands.update_one(
                {"_id": ObjectId(transaction["brand_id"])},
                {"$set": {"is_boosted": True, "boosted_until": boosted_until}}
            )
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"boost_applied": True}}
            )
    
    return {"status": status.status, "payment_status": status.payment_status}

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    
    try:
        event = await stripe_checkout.handle_webhook(body, signature)
        
        if event.payment_status == "paid":
            transaction = await db.payment_transactions.find_one({"session_id": event.session_id})
            if transaction and not transaction.get("boost_applied"):
                package_id = event.metadata.get("package_id")
                package = BOOST_PACKAGES.get(package_id)
                if package:
                    boosted_until = datetime.now(timezone.utc) + timedelta(days=package["duration_days"])
                    await db.brands.update_one(
                        {"_id": ObjectId(transaction["brand_id"])},
                        {"$set": {"is_boosted": True, "boosted_until": boosted_until}}
                    )
                    await db.payment_transactions.update_one(
                        {"session_id": event.session_id},
                        {"$set": {"boost_applied": True, "payment_status": "paid"}}
                    )
        
        return {"received": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"received": True}

# ============ ADMIN STATS ============

@api_router.get("/admin/stats")
async def get_admin_stats(request: Request):
    await require_admin(request)
    
    total_users = await db.users.count_documents({})
    total_brands = await db.brands.count_documents({})
    total_products = await db.products.count_documents({})
    pending_applications = await db.brand_applications.count_documents({"status": "pending"})
    boosted_brands = await db.brands.count_documents({"is_boosted": True})
    
    return {
        "total_users": total_users,
        "total_brands": total_brands,
        "total_products": total_products,
        "pending_applications": pending_applications,
        "boosted_brands": boosted_brands
    }

# ============ SEED DATA ============

async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@ukstreetwear.com")
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
            {"$set": {"password_hash": hash_password(admin_password)}}
        )
        logger.info("Admin password updated")

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
