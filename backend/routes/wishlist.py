# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

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

