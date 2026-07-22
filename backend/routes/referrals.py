# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ REFERRAL SYSTEM ============

@api_router.get("/referral/code")
async def get_referral_code(request: Request):
    if not REFERRALS_ENABLED:
        raise HTTPException(status_code=403, detail="The referral programme is coming soon")
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
async def apply_referral_code(payload: ReferralApplyRequest, request: Request):
    if not REFERRALS_ENABLED:
        raise HTTPException(status_code=403, detail="The referral programme is coming soon")
    user = await get_current_user(request)
    code = payload.code.strip()
    
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
    if not REFERRALS_ENABLED:
        # Graceful zero so checkout/product pages never show or apply credit while gated
        await get_current_user(request)
        return {"credits_earned": 0, "credits_used": 0, "credits_available": 0}
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
    if not REFERRALS_ENABLED:
        raise HTTPException(status_code=403, detail="The referral programme is coming soon")
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

