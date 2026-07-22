# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403
from core import _brand_dead_stock_count, _brand_quota

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
    is_dead_stock: Optional[bool] = None,
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
    if is_dead_stock is True:
        query["is_dead_stock"] = True
    elif is_dead_stock is False:
        # Exclude dead stock from main shop listings unless explicitly requested
        query["is_dead_stock"] = {"$ne": True}
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
async def update_product(product_id: str, payload: ProductUpdate, request: Request):
    user = await require_brand(request)
    
    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand or str(brand["_id"]) != product["brand_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this product")
    
    update_fields = payload.model_dump(exclude_unset=True)
    
    if update_fields:
        await db.products.update_one(
            {"_id": safe_object_id(product_id)},
            {"$set": update_fields}
        )
    
    updated = await db.products.find_one({"_id": safe_object_id(product_id)})
    updated["id"] = str(updated["_id"])
    del updated["_id"]
    
    return updated

@api_router.delete("/admin/brands/{brand_id}")
async def admin_delete_brand(brand_id: str, request: Request):
    """Admin-only: delete a brand and cascade-delete its products, reviews, comments,
    wishlist entries, and unpaid orders. Demotes the brand owner back to a regular user.
    Refuses if the brand has paid/shipped/delivered orders to protect customer data."""
    await require_admin(request)
    
    brand = await db.brands.find_one({"_id": safe_object_id(brand_id)})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    paid_orders = await db.orders.count_documents({
        "brand_id": brand_id,
        "status": {"$in": ["paid", "shipped", "delivered"]},
    })
    if paid_orders > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Refusing to delete: {paid_orders} paid/shipped order(s) exist for this brand. Resolve customer orders first.",
        )
    
    # Cascade
    product_ids = [str(p["_id"]) async for p in db.products.find({"brand_id": brand_id}, {"_id": 1})]
    deleted_products = (await db.products.delete_many({"brand_id": brand_id})).deleted_count
    deleted_unpaid_orders = (await db.orders.delete_many({"brand_id": brand_id})).deleted_count
    deleted_reviews = (await db.reviews.delete_many({"brand_id": brand_id})).deleted_count
    if product_ids:
        await db.product_comments.delete_many({"product_id": {"$in": product_ids}})
        await db.wishlists.delete_many({"product_id": {"$in": product_ids}})
    
    # Withdraw any pending brand applications from this user
    await db.brand_applications.delete_many({"user_id": brand["user_id"]})
    
    # Demote the brand owner back to buyer (preserves their user account + buying history)
    owner_id = brand.get("user_id")
    if owner_id:
        await db.users.update_one(
            {"_id": ObjectId(owner_id), "role": "brand"},
            {"$set": {"role": "user"}},
        )
    
    await db.brands.delete_one({"_id": safe_object_id(brand_id)})
    
    return {
        "message": f"Brand '{brand['brand_name']}' deleted",
        "deleted": {
            "products": deleted_products,
            "unpaid_orders": deleted_unpaid_orders,
            "reviews": deleted_reviews,
        },
    }


@api_router.delete("/admin/products/{product_id}")
async def admin_delete_product(product_id: str, request: Request):
    """Admin-only: delete any product regardless of owner.
    Cleans up product comments and wishlist entries that reference it."""
    await require_admin(request)
    
    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    paid_orders = await db.orders.count_documents({
        "product_id": product_id,
        "status": {"$in": ["paid", "shipped", "delivered"]},
    })
    if paid_orders > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Refusing to delete: {paid_orders} paid/shipped order(s) reference this product.",
        )
    
    await db.products.delete_one({"_id": safe_object_id(product_id)})
    await db.product_comments.delete_many({"product_id": product_id})
    await db.wishlists.delete_many({"product_id": product_id})
    await db.orders.delete_many({"product_id": product_id})  # only unpaid by this point
    
    return {"message": f"Product '{product['name']}' deleted"}


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


# ============ DEAD STOCK ROUTES ============

@api_router.get("/dead-stock")
async def get_dead_stock(
    category: Optional[str] = None,
    brand_id: Optional[str] = None,
    min_discount: Optional[int] = None,
    sort: str = "latest",
    limit: int = 50,
    skip: int = 0,
):
    """Public listing of products flagged as dead stock.
    Each item carries `original_price`, `price` (current/sale) and `discount_percent`."""
    query = {"is_dead_stock": True}
    if category and category != "all":
        query["category"] = category
    if brand_id:
        query["brand_id"] = brand_id
    
    sort_map = {
        "latest": ("dead_stock_added_at", -1),
        "price_low": ("price", 1),
        "price_high": ("price", -1),
        "biggest_discount": ("discount_percent", -1),
    }
    sort_field, sort_dir = sort_map.get(sort, ("dead_stock_added_at", -1))
    
    products = await db.products.find(query).sort(sort_field, sort_dir).skip(skip).limit(limit).to_list(limit)
    
    # Enrich with seller payment status (same as main /products)
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
    
    if min_discount is not None:
        result = [p for p in result if (p.get("discount_percent") or 0) >= min_discount]
    
    return result


def _calc_discount(original: float, current: float) -> int:
    if not original or original <= 0 or current >= original:
        return 0
    return int(round((1 - current / original) * 100))


@api_router.post("/products/{product_id}/dead-stock")
async def move_to_dead_stock(product_id: str, payload: DeadStockToggle, request: Request):
    """Move a product into the brand's dead stock zone. Optionally apply a markdown."""
    user = await require_brand(request)
    
    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand or str(brand["_id"]) != product["brand_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    brand_id = str(brand["_id"])
    quota = _brand_quota(brand)
    
    if not product.get("is_dead_stock"):
        current_count = await _brand_dead_stock_count(brand_id)
        if current_count >= quota:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Dead stock quota reached ({current_count}/{quota}). "
                    "Remove an item from Dead Stock or request a quota increase from the admin team."
                ),
            )
    
    original_price = product.get("original_price") or product["price"]
    new_price = payload.new_price if payload.new_price is not None else product["price"]
    
    if new_price <= 0:
        raise HTTPException(status_code=400, detail="Price must be greater than 0")
    if new_price > original_price:
        raise HTTPException(status_code=400, detail="Dead stock price cannot be higher than the original price")
    
    discount = _calc_discount(original_price, new_price)
    
    await db.products.update_one(
        {"_id": safe_object_id(product_id)},
        {"$set": {
            "is_dead_stock": True,
            "original_price": float(original_price),
            "price": float(new_price),
            "discount_percent": discount,
            "dead_stock_added_at": datetime.now(timezone.utc),
        }}
    )
    
    return {
        "message": "Product moved to dead stock",
        "original_price": original_price,
        "price": new_price,
        "discount_percent": discount,
    }


@api_router.delete("/products/{product_id}/dead-stock")
async def remove_from_dead_stock(product_id: str, request: Request):
    """Take a product back out of the dead stock zone. Restores the original price."""
    user = await require_brand(request)
    
    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand or str(brand["_id"]) != product["brand_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    original_price = product.get("original_price") or product["price"]
    await db.products.update_one(
        {"_id": safe_object_id(product_id)},
        {"$set": {
            "is_dead_stock": False,
            "price": float(original_price),
            "discount_percent": 0,
        }, "$unset": {"dead_stock_added_at": ""}}
    )
    return {"message": "Product restored to main shop", "price": original_price}


@api_router.get("/dead-stock/my-quota")
async def get_dead_stock_quota(request: Request):
    """Quota status for the current brand. Returns used/quota/remaining + any pending request."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    brand_id = str(brand["_id"])
    used = await _brand_dead_stock_count(brand_id)
    quota = _brand_quota(brand)
    pending = brand.get("dead_stock_quota_request")
    return {
        "used": used,
        "quota": quota,
        "remaining": max(0, quota - used),
        "pending_request": pending,
    }


@api_router.post("/dead-stock/quota-request")
async def request_dead_stock_quota(payload: QuotaRequest, request: Request):
    """Brand requests an increase to their dead stock quota. Logged on the brand doc
    and a notification is sent to all admins for action."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    current_quota = _brand_quota(brand)
    if payload.requested_quota <= current_quota:
        raise HTTPException(status_code=400, detail=f"Requested quota must be greater than current ({current_quota})")
    if payload.requested_quota > 200:
        raise HTTPException(status_code=400, detail="Maximum requestable quota is 200")
    
    await db.brands.update_one(
        {"_id": brand["_id"]},
        {"$set": {"dead_stock_quota_request": {
            "requested_quota": payload.requested_quota,
            "reason": payload.reason or "",
            "requested_at": datetime.now(timezone.utc),
            "status": "pending",
        }}}
    )
    
    # Ping every admin so they see the request in their notifications
    async for admin in db.users.find({"role": "admin"}, {"_id": 1}):
        await create_notification(
            user_id=str(admin["_id"]),
            brand_id=str(brand["_id"]),
            notification_type="quota_request",
            title="Dead Stock quota request",
            message=f"{brand['brand_name']} is requesting {payload.requested_quota} dead stock slots (currently {current_quota}).",
            metadata={"brand_id": str(brand["_id"]), "requested_quota": payload.requested_quota},
        )
    
    return {"message": "Quota request submitted. We'll review it and email you shortly."}


@api_router.get("/admin/dead-stock-quota-requests")
async def list_quota_requests(request: Request):
    """All pending dead stock quota requests, for admin review."""
    await require_admin(request)
    out = []
    async for brand in db.brands.find({"dead_stock_quota_request.status": "pending"}):
        used = await _brand_dead_stock_count(str(brand["_id"]))
        out.append({
            "brand_id": str(brand["_id"]),
            "brand_name": brand.get("brand_name"),
            "current_quota": _brand_quota(brand),
            "used": used,
            "request": brand["dead_stock_quota_request"] | {
                "requested_at": brand["dead_stock_quota_request"]["requested_at"].isoformat()
                if isinstance(brand["dead_stock_quota_request"].get("requested_at"), datetime)
                else brand["dead_stock_quota_request"].get("requested_at"),
            },
        })
    return out


@api_router.post("/admin/brands/{brand_id}/dead-stock-quota")
async def admin_set_dead_stock_quota(brand_id: str, payload: AdminQuotaUpdate, request: Request):
    """Admin overrides a brand's dead stock quota and clears any pending request."""
    await require_admin(request)
    brand = await db.brands.find_one({"_id": safe_object_id(brand_id)})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    if payload.quota < 0:
        raise HTTPException(status_code=400, detail="Quota cannot be negative")
    
    await db.brands.update_one(
        {"_id": safe_object_id(brand_id)},
        {"$set": {"dead_stock_quota": int(payload.quota)},
         "$unset": {"dead_stock_quota_request": ""}}
    )
    
    # Notify the brand owner that the quota changed
    await create_notification(
        user_id=brand["user_id"],
        brand_id=brand_id,
        notification_type="quota_updated",
        title="Dead Stock quota updated",
        message=f"Your dead stock quota has been set to {payload.quota}.",
        metadata={"new_quota": payload.quota},
    )
    
    return {"message": "Quota updated", "quota": payload.quota}

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

