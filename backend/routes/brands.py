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

