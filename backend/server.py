# Unveiled Threads API — app assembly.
# The old monolith was split into core.py (shared foundation) and routes/*.
from core import *  # noqa: F401,F403
from core import app, api_router, limiter, logger, db, client
from core import _rate_limit_exceeded_handler

# Route modules — import order preserves original route registration order.
import routes.auth  # noqa: E402,F401
import routes.account  # noqa: E402,F401
import routes.applications  # noqa: E402,F401
import routes.brands  # noqa: E402,F401
import routes.products  # noqa: E402,F401
import routes.imports  # noqa: E402,F401
import routes.payments  # noqa: E402,F401
import routes.connect  # noqa: E402,F401
import routes.disputes  # noqa: E402,F401
import routes.uploads  # noqa: E402,F401
import routes.orders  # noqa: E402,F401
import routes.engagement  # noqa: E402,F401
import routes.reviews  # noqa: E402,F401
import routes.shipping  # noqa: E402,F401
import routes.wishlist  # noqa: E402,F401
import routes.analytics  # noqa: E402,F401
import routes.referrals  # noqa: E402,F401
import routes.messaging  # noqa: E402,F401
import routes.community  # noqa: E402,F401
import routes.botw  # noqa: E402,F401

# Test-only rate-limiter reset — gated by ENVIRONMENT so it can never
# exist on production. Used by the pytest suite to isolate rate-limit
# buckets between tests now that _client_ip resolves from the RIGHT of
# X-Forwarded-For (i.e. header spoofing no longer creates fresh buckets).
if os.environ.get("ENVIRONMENT", "development").strip().lower() != "production":
    from fastapi import Request as _Request  # noqa: E402

    @api_router.post("/__test/reset-limiter")
    async def _reset_limiter_for_tests(request: _Request):  # noqa: ARG001
        limiter.reset()
        return {"ok": True}

from routes.engagement import low_stock_digest_loop, abandoned_checkout_loop  # noqa: E402
from routes.orders import order_reconciliation_loop  # noqa: E402
from routes.botw import botw_rotation_loop  # noqa: E402

# ============ SEED DATA ============

async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "").lower().strip()
    admin_password = os.environ.get("ADMIN_PASSWORD", "").strip()
    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()

    # Refuse to seed with baked-in defaults in production. The old defaults
    # (admin@ukstreetwear.com / Admin123!) would otherwise silently create a
    # known-credential admin on every restart if the env vars were forgotten.
    if not admin_email or not admin_password:
        if environment == "production":
            logger.critical(
                "REFUSING to seed admin: ADMIN_EMAIL and ADMIN_PASSWORD must be set "
                "in production environment variables. Admin account NOT created."
            )
            return
        # Dev-only fallback with a clear log line so nobody deploys this by accident
        admin_email = admin_email or "admin@ukstreetwear.com"
        admin_password = admin_password or "Admin123!"
        logger.warning(
            "Using DEV admin credentials (%s). Set ADMIN_EMAIL and ADMIN_PASSWORD "
            "env vars in production.", admin_email
        )

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
    # NEVER seed demo data in production. The demo brand ships with a hardcoded
    # password ("Demo123!") so must not exist on any real deployment.
    if os.environ.get("ENVIRONMENT", "development").strip().lower() == "production":
        return
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


# Security headers — applied to every response served by FastAPI.
# NOTE ON SCOPE: this middleware only runs on `/api/*` responses because that's what
# FastAPI serves in this deployment. The frontend HTML/JS is served separately by
# Emergent's static hosting (Cloudflare / edge CDN), so these headers do NOT cover
# that response. See the audit reply in chat for the hosting-layer follow-up needed.
#
# CSP allowlist mirrors the frontend meta-tag CSP in /app/frontend/public/index.html.
# Keep them in sync when adding new third-party origins.
_BACKEND_CSP = " ".join([
    "default-src 'self';",
    # We serve JSON only from FastAPI — no scripts should ever be executed from a
    # backend response. Keeping 'self' + 'unsafe-inline' covers the FastAPI docs
    # UI (Swagger) without opening the door to arbitrary CDNs.
    "script-src 'self' 'unsafe-inline';",
    "style-src 'self' 'unsafe-inline';",
    "img-src 'self' data: https:;",
    "font-src 'self' data:;",
    # Backends never need to embed frames from anywhere.
    "frame-src 'none';",
    "frame-ancestors 'self';",
    "base-uri 'self';",
    "form-action 'self';",
    "object-src 'none';",
    "upgrade-insecure-requests;",
])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = _BACKEND_CSP
    # DENY is stricter than SAMEORIGIN. Frontend HTML is served from a separate
    # origin anyway, so the backend never needs to be iframed by itself.
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Cross-Origin-Resource-Policy"] = "same-site"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


# CORS: read allowed origins from env, with safe fallback behaviour.
# In production, missing/wildcard CORS_ORIGINS is a critical CSRF risk
# (cross-site JS could ride users' login cookies). We fail CLOSED:
# - production + missing/* → restrict to the known production domain only
# - dev (no ENVIRONMENT set) → permissive wildcard for local + preview testing
_cors_raw = os.environ.get("CORS_ORIGINS", "").strip()
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
_environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
_production_fallback_origins = [
    "https://unveiledthreads.co.uk",
    "https://www.unveiledthreads.co.uk",
]

if _environment == "production":
    if not _cors_origins or "*" in _cors_origins:
        # Refuse to be permissive in production — hard-restrict to the known domain.
        logger.critical(
            "CORS_ORIGINS is not set (or set to '*') in production. "
            "Hard-restricting to %s. Set CORS_ORIGINS in deployment env vars.",
            _production_fallback_origins,
        )
        _cors_origins = list(_production_fallback_origins)
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=_cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif "*" in _cors_origins or _cors_raw == "*" or not _cors_origins:
    # Dev / preview: allow any origin, but echo it back so credentials still work.
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origin_regex=".*",
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=_cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

def _validate_env_or_die():
    """Fail-closed check for every critical env var. Runs at app startup.
    In production, missing critical secrets = hard fail (process exits).
    In development, missing secrets = loud warning but the app continues so devs
    can work on non-affected areas."""
    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()

    # (key, description, weakens_if_missing)
    critical = [
        ("MONGO_URL", "Database connection", "cannot start"),
        ("DB_NAME", "Database name", "cannot start"),
        ("JWT_SECRET", "Signing key for auth cookies", "auth is completely broken"),
        ("STRIPE_API_KEY", "Payment processing", "checkout is broken"),
        ("STRIPE_WEBHOOK_SECRET", "Account-webhook signature verification", "webhook can be forged"),
        ("STRIPE_CONNECT_WEBHOOK_SECRET", "Connect-webhook signature verification", "Connect events can be forged"),
        ("CORS_ORIGINS", "CORS allowlist", "cross-site attacks possible (falls back to hard-coded prod domain)"),
        ("RESEND_API_KEY", "Transactional email", "email flows fail silently"),
        ("EMERGENT_LLM_KEY", "AI moderation + image storage", "moderation degrades to regex-only"),
        ("ADMIN_EMAIL", "Admin seed email", "admin account seeding is skipped"),
        ("ADMIN_PASSWORD", "Admin seed password", "admin account seeding is skipped"),
        ("ENVIRONMENT", "Deployment environment gate", "demo data and fallback admin credentials may be seeded in production"),
    ]

    missing = [(k, desc, impact) for k, desc, impact in critical if not os.environ.get(k, "").strip()]

    if not missing:
        logger.info("Env validation OK — all critical secrets present")
        return

    if environment == "production":
        logger.critical("=" * 70)
        logger.critical("REFUSING TO START — missing critical env vars in production:")
        for k, desc, impact in missing:
            logger.critical(f"  - {k}: {desc}. Without it: {impact}")
        logger.critical("Set the above in Emergent Secrets Hub and redeploy.")
        logger.critical("=" * 70)
        raise RuntimeError(
            f"Cannot start in production without: {', '.join(k for k, _, _ in missing)}"
        )
    else:
        logger.warning("=" * 70)
        logger.warning("Env vars missing (dev mode — continuing anyway):")
        for k, desc, impact in missing:
            logger.warning(f"  - {k}: {desc}. Without it: {impact}")
        logger.warning("=" * 70)


@app.on_event("startup")
async def startup_event():
    # Boot-time validation — refuse to start in production if any critical
    # secret is missing. This is the safety net that stops the app from
    # deploying in a permissively-configured state.
    _validate_env_or_die()
    
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
    # Password reset tokens: lookup by hash; auto-expire docs 7 days after expiry
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.password_reset_tokens.create_index("user_id")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=86400 * 7)
    # Brand slug: unique sparse index for /@slug vanity URLs
    await db.brands.create_index("slug", unique=True, sparse=True)
    # Back-fill slugs for any pre-existing brands missing one (idempotent)
    async for b in db.brands.find({"$or": [{"slug": {"$exists": False}}, {"slug": None}, {"slug": ""}]}):
        new_slug = await generate_unique_slug(b.get("brand_name") or "brand", exclude_brand_id=str(b["_id"]))
        await db.brands.update_one({"_id": b["_id"]}, {"$set": {"slug": new_slug}})
    
    # Init object storage
    try:
        init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.warning(f"Object storage init failed (will retry on first use): {e}")
    
    # Seed data
    await seed_admin()
    await seed_demo_data()
    
    # Weekly low-stock digest scheduler (per-brand 7-day guard makes restarts safe)
    asyncio.create_task(low_stock_digest_loop())
    
    # Abandoned checkout win-back scheduler (per-order sent flag makes restarts safe)
    asyncio.create_task(abandoned_checkout_loop())
    
    # Paid-order reconciliation sweep (settles orders when the buyer never returned)
    asyncio.create_task(order_reconciliation_loop())

    # Brand-of-the-Week weekly hybrid auto-rotation (fair × 3 weeks, performance
    # every 4th, 24h admin veto window). See routes/botw.py for the cycle logic.
    asyncio.create_task(botw_rotation_loop())
    
    # Write test credentials file — DEV ONLY. Never write cleartext admin
    # credentials on production, where the file could leak via a mis-mounted volume.
    if os.environ.get("ENVIRONMENT", "development").strip().lower() != "production":
        memory_dir = Path("/app/memory")
        memory_dir.mkdir(exist_ok=True)
        with open(memory_dir / "test_credentials.md", "w") as f:
            f.write("# Test Credentials (dev environment only)\n\n")
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

