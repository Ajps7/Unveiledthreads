# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403
from core import _normalise_slug_candidate

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

@api_router.get("/brands/founding-spots")
async def get_founding_spots():
    """Public counter for the Founding Brand programme (first N brands)."""
    taken = await db.brands.count_documents({"is_founding": True})
    return {
        "limit": FOUNDING_BRAND_LIMIT,
        "taken": min(taken, FOUNDING_BRAND_LIMIT),
        "remaining": max(0, FOUNDING_BRAND_LIMIT - taken),
    }

@api_router.get("/brands/brand-of-week")
async def get_brand_of_week(response: Response):
    # Never cache — this response changes the second admin approves a new
    # hero image or the weekly rotation flips. Any CDN/browser cache here
    # results in "I approved the new photo but the homepage still shows
    # the old one" bug reports.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

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
        # Expose the admin-APPROVED featured image so the homepage can render
        # it. The pending image is intentionally NOT exposed here — only in
        # the seller's own dashboard + the admin queue.
        if brand.get("botw_image_status") == "approved" and brand.get("botw_featured_image_approved"):
            brand["featured_image"] = brand["botw_featured_image_approved"]
        return brand
    return None


# ============ BRAND OF THE WEEK — SELLER-CHOSEN HERO IMAGE ============

class BotwImageChoice(BaseModel):
    image_url: str = Field(min_length=1, max_length=500)


@api_router.post("/brands/me/botw-image")
async def submit_botw_image(payload: BotwImageChoice, request: Request):
    """Brand-of-the-Week only: submit an image from one of your own products
    to be used as the homepage feature. Enters `pending` — admin has to
    approve before it goes live."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    if not brand.get("is_brand_of_week"):
        raise HTTPException(status_code=403, detail="Only the current Brand of the Week can set a homepage image.")

    # Ownership gate. Accept the URL if EITHER (a) it's already on one of
    # the brand's product images (legacy "reuse your product photo" flow),
    # OR (b) it's a fresh /api/files/... upload made by this same user (the
    # new "upload a hero shot from your device" flow). Both prove the brand
    # owns the imagery — closes the "point at any URL on the internet" hole
    # while allowing fresh device uploads to reach admin approval.
    is_owned = False

    owned_product = await db.products.find_one({
        "brand_id": str(brand["_id"]),
        "images": payload.image_url,
    })
    if owned_product:
        is_owned = True
    elif payload.image_url.startswith("/api/files/"):
        # Fresh upload path: the URL was minted by /api/upload/image which
        # already recorded the user_id + magic-byte-checked the bytes.
        storage_path = payload.image_url[len("/api/files/"):]
        file_doc = await db.files.find_one({
            "storage_path": storage_path,
            "user_id": user["id"],
            "is_deleted": {"$ne": True},
        })
        if file_doc:
            is_owned = True

    if not is_owned:
        raise HTTPException(
            status_code=422,
            detail="Image URL must be one of your own product images or a fresh upload you made.",
        )

    await db.brands.update_one(
        {"_id": brand["_id"]},
        {"$set": {
            "botw_featured_image_pending": payload.image_url,
            "botw_image_status": "pending",
            "botw_image_submitted_at": datetime.now(timezone.utc),
        }},
    )
    return {"botw_image_status": "pending", "botw_featured_image_pending": payload.image_url}


@api_router.get("/admin/botw-image/queue")
async def admin_botw_image_queue(request: Request):
    """Homepage-image submissions awaiting admin approval."""
    await require_admin(request)
    out = []
    async for b in db.brands.find({"botw_image_status": "pending"}).sort("botw_image_submitted_at", -1).limit(100):
        b["id"] = str(b["_id"]); del b["_id"]
        out.append(b)
    return out


class BotwImageDecision(BaseModel):
    approve: bool


@api_router.post("/admin/botw-image/{brand_id}")
async def admin_decide_botw_image(brand_id: str, payload: BotwImageDecision, request: Request):
    """Admin approves or rejects the pending homepage image."""
    await require_admin(request)
    brand = await db.brands.find_one({"_id": safe_object_id(brand_id)})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    pending = brand.get("botw_featured_image_pending")
    if not pending:
        raise HTTPException(status_code=400, detail="No pending image for this brand.")

    now = datetime.now(timezone.utc)
    if payload.approve:
        await db.brands.update_one(
            {"_id": brand["_id"]},
            {"$set": {
                "botw_featured_image_approved": pending,
                "botw_image_status": "approved",
                "botw_image_reviewed_at": now,
            }, "$unset": {"botw_featured_image_pending": ""}},
        )
        return {"botw_image_status": "approved"}
    else:
        await db.brands.update_one(
            {"_id": brand["_id"]},
            {"$set": {
                "botw_image_status": "rejected",
                "botw_image_reviewed_at": now,
            }, "$unset": {"botw_featured_image_pending": ""}},
        )
        return {"botw_image_status": "rejected"}

@api_router.get("/brands/by-slug/{slug}")
async def get_brand_by_slug(slug: str):
    """Public lookup for `/@slug` vanity URLs. Case-insensitive."""
    slug_norm = _normalise_slug_candidate(slug)
    brand = await db.brands.find_one({"slug": slug_norm})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    brand["id"] = str(brand["_id"])
    del brand["_id"]
    products = await db.products.find({"brand_id": brand["id"]}).sort("created_at", -1).to_list(50)
    for product in products:
        product["id"] = str(product["_id"])
        del product["_id"]
    brand["products"] = products
    return brand


class AdminSlugUpdateRequest(BaseModel):
    slug: str

@api_router.put("/admin/brands/{brand_id}/slug")
async def admin_update_brand_slug(brand_id: str, payload: AdminSlugUpdateRequest, request: Request):
    """Admin-only: change a brand's vanity slug. Validates uniqueness + reserved words."""
    await require_admin(request)
    brand = await db.brands.find_one({"_id": safe_object_id(brand_id)})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    candidate = _normalise_slug_candidate(payload.slug)
    if not candidate:
        raise HTTPException(status_code=400, detail="Slug must contain at least one letter or number")
    if candidate in SLUG_RESERVED:
        raise HTTPException(status_code=400, detail=f"'{candidate}' is a reserved name. Pick another.")
    existing = await db.brands.find_one({"slug": candidate, "_id": {"$ne": safe_object_id(brand_id)}}, {"_id": 1})
    if existing:
        raise HTTPException(status_code=400, detail="That slug is already taken.")
    
    await db.brands.update_one({"_id": safe_object_id(brand_id)}, {"$set": {"slug": candidate}})
    return {"slug": candidate, "url_path": f"/@{candidate}"}


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
async def update_brand_profile(payload: BrandProfileUpdate, request: Request):
    user = await require_brand(request)
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    update_fields = payload.model_dump(exclude_unset=True)
    
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

