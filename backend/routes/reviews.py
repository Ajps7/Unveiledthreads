# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

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

