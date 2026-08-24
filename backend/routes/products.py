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

    # Moderate every image BEFORE we insert. A single flagged image blocks
    # the whole listing with a generic 422 — internal reasons stay in logs
    # so sellers can't fingerprint the classifier.
    moderation = await moderate_product_images(product.images)
    flagged = [m for m in moderation if m["status"] == "flagged"]
    if flagged:
        first = flagged[0]
        logger.warning(
            f"[MODERATION BLOCK] brand={brand['_id']} product='{product.name}' "
            f"image_index={first['index']} reason={first['reason']}"
        )
        raise HTTPException(
            status_code=422,
            detail=f"Image {first['index'] + 1} was flagged and can't be used. Please replace it and try again.",
        )
    # 'unverified' images are ALLOWED (no provider configured or external
    # source) but the listing joins the admin review queue.
    needs_admin_review = any(m["status"] == "unverified" for m in moderation)

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
        # Pre-order (Model A). preorder_ship_date is stored as an ISO string
        # so it's JSON-serialisable end-to-end without a datetime cast.
        "is_preorder": product.is_preorder,
        "preorder_ship_date": product.preorder_ship_date.isoformat() if product.preorder_ship_date else None,
        "preorder_limit": product.preorder_limit,
        # Structured description (hidden field-by-field on the frontend if empty)
        "story": product.story,
        "details": product.details,
        "materials": product.materials,
        "fit_notes": product.fit_notes,
        "care": product.care,
        # Image moderation record — one entry per image in the same order.
        "images_moderation": moderation,
        "moderation_status": "needs_review" if needs_admin_review else "passed",
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

    # Hide products taken down by moderation. 'needs_review' and 'passed'
    # stay visible — only explicit 'flagged' is removed.
    query["moderation_status"] = {"$ne": "flagged"}

    # Drafts (CSV imports awaiting brand review) must never appear in public
    # listings. Products created before the draft/published split have no
    # status field and are treated as published for backward compatibility.
    query["status"] = {"$ne": "draft"}

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
async def get_product(product_id: str, request: Request):
    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Drafts are only visible to the owning brand + admins. Everyone else
    # (including anonymous callers) gets a plain 404 — never leak the
    # existence of an unpublished listing.
    if product.get("status") == "draft":
        viewer = None
        try:
            viewer = await get_current_user(request)
        except HTTPException:
            viewer = None
        allowed = False
        if viewer:
            if viewer.get("role") == "admin":
                allowed = True
            else:
                brand = await db.brands.find_one({"user_id": viewer["id"]})
                if brand and str(brand["_id"]) == product.get("brand_id"):
                    allowed = True
        if not allowed:
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

    # preorder_ship_date is stored as an ISO string; convert here so callers
    # sending a JSON date get consistent persistence.
    if "preorder_ship_date" in update_fields and update_fields["preorder_ship_date"] is not None:
        update_fields["preorder_ship_date"] = update_fields["preorder_ship_date"].isoformat()

    # Cross-field guard: if the update is turning is_preorder ON, the product
    # (post-merge) must still have a future preorder_ship_date.
    turning_on = update_fields.get("is_preorder") is True
    if turning_on:
        effective_ship_date = update_fields.get("preorder_ship_date") or product.get("preorder_ship_date")
        if not effective_ship_date:
            raise HTTPException(
                status_code=422,
                detail="preorder_ship_date is required when enabling pre-order.",
            )

    # If the images array is being replaced, moderate any newly added URL.
    # We only inspect the delta so re-saving unchanged edits doesn't
    # re-scan the whole album.
    if "images" in update_fields and update_fields["images"] is not None:
        new_images = update_fields["images"]

        # Reject duplicate URLs in the new album. Pure reorders shouldn't
        # trip this; a buggy client re-adding a URL should.
        if len(set(new_images)) != len(new_images):
            raise HTTPException(status_code=422, detail="Image list contains duplicates.")

        # "Existing" = any URL already on the product doc, regardless of its
        # current moderation status. Reordering (or removing) previously-seen
        # images must NEVER re-invoke the moderator — the admin has already
        # had a chance to override any 'unverified' verdict via the review
        # queue, and re-scanning would wipe that decision.
        existing_urls = set(product.get("images") or [])
        existing_mod = {m["url"]: m for m in (product.get("images_moderation") or [])}

        new_urls = [u for u in new_images if u not in existing_urls]
        if new_urls:
            delta_results = await moderate_product_images(new_urls)
            flagged = [m for m in delta_results if m["status"] == "flagged"]
            if flagged:
                idx_in_full = new_images.index(flagged[0]["url"])
                logger.warning(
                    f"[MODERATION BLOCK] update product={product_id} "
                    f"image_index={idx_in_full} reason={flagged[0]['reason']}"
                )
                raise HTTPException(
                    status_code=422,
                    detail=f"Image {idx_in_full + 1} was flagged and can't be used. Please replace it and try again.",
                )
            delta_map = {m["url"]: m for m in delta_results}
        else:
            delta_map = {}

        # Rebuild images_moderation in the new album's order.
        # - New URL         → verdict from this run
        # - Existing URL    → carry forward its prior verdict verbatim
        #                     (preserves 'passed' AND any admin decisions).
        # If a URL somehow has no prior entry AND wasn't just moderated
        # (shouldn't happen, but defensive) mark unverified so it lands in
        # the review queue rather than silently passing.
        merged = []
        for i, u in enumerate(new_images):
            entry = delta_map.get(u) or existing_mod.get(u)
            if entry is None:
                entry = {"url": u, "status": "unverified", "reason": "no_record"}
            merged.append({**entry, "index": i})
        update_fields["images_moderation"] = merged

        # Only re-derive moderation_status if we actually touched moderation
        # (either new URLs came in, or a prior 'flagged'/'unverified' entry
        # is still present). Otherwise leave the field alone — a pure
        # reorder of an all-'passed' album must not disturb it, and if an
        # admin has already resolved a review, their decision stands.
        if new_urls or any(m["status"] != "passed" for m in merged):
            has_unverified = any(m["status"] == "unverified" for m in merged)
            # Only lower the status; never overwrite an admin's explicit
            # 'passed' or 'flagged' with a fresh 'needs_review'.
            if product.get("moderation_status") in (None, "needs_review") or new_urls:
                update_fields["moderation_status"] = "needs_review" if has_unverified else "passed"

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
async def admin_delete_brand(brand_id: str, request: Request, delete_user: bool = False):
    """Admin-only: delete a brand and cascade-delete its products, drafts, reviews,
    comments, wishlist entries, and unpaid orders. Refuses if the brand has
    paid/shipped/delivered orders (protect customer data).

    By default the brand OWNER is demoted back to a regular user so their
    buying history is preserved. Pass `?delete_user=true` to also hard-delete
    the owner's account and every message/notification/conversation/file
    tied to them (e.g. for wiping a demo brand entirely)."""
    await require_admin(request)

    brand = await db.brands.find_one({"_id": safe_object_id(brand_id)})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    paid_orders = await db.orders.count_documents({
        "brand_id": brand_id,
        "status": {"$in": SALE_STATUSES},
    })
    if paid_orders > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Refusing to delete: {paid_orders} paid/shipped order(s) exist for this brand. Resolve customer orders first.",
        )

    # Cascade — includes drafts because the products.delete_many query is
    # unfiltered on status (drafts already carry the same brand_id).
    product_ids = [str(p["_id"]) async for p in db.products.find({"brand_id": brand_id}, {"_id": 1})]
    deleted_products = (await db.products.delete_many({"brand_id": brand_id})).deleted_count
    deleted_unpaid_orders = (await db.orders.delete_many({"brand_id": brand_id})).deleted_count
    deleted_reviews = (await db.reviews.delete_many({"brand_id": brand_id})).deleted_count
    if product_ids:
        await db.product_comments.delete_many({"product_id": {"$in": product_ids}})
        await db.wishlists.delete_many({"product_id": {"$in": product_ids}})

    # Withdraw any pending brand applications from this user
    await db.brand_applications.delete_many({"user_id": brand["user_id"]})

    # Owner handling: demote OR hard-delete based on flag.
    owner_id = brand.get("user_id")
    deleted_user = False
    if owner_id:
        if delete_user:
            # Full user wipe. Anything the user authored gets removed too.
            try:
                oid = ObjectId(owner_id)
            except Exception:
                oid = None
            if oid:
                # Drop messages the user sent + conversations they were part of.
                await db.messages.delete_many({"sender_id": owner_id})
                await db.conversations.delete_many({"participants": owner_id})
                # Notifications addressed to them.
                await db.notifications.delete_many({"user_id": owner_id})
                # Reviews the user wrote as a buyer.
                await db.reviews.delete_many({"reviewer_id": owner_id})
                # Uploaded files they own (leaves orphan blobs in storage —
                # acceptable trade-off vs. iterating the object store).
                await db.files.delete_many({"user_id": owner_id})
                # Any wishlist entries they had.
                await db.wishlists.delete_many({"user_id": owner_id})
                # Password-reset / email-change tokens.
                await db.password_reset_tokens.delete_many({"user_id": owner_id})
                await db.email_change_tokens.delete_many({"user_id": owner_id})
                # Finally the user themselves.
                await db.users.delete_one({"_id": oid})
                deleted_user = True
        else:
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
            "user_account": deleted_user,
        },
    }


@api_router.post("/admin/brands/{brand_id}/toggle-founding")
async def admin_toggle_founding(brand_id: str, request: Request):
    """Admin-only: flip the Founding Brand badge on a brand. Used to
    correct historical mis-assignments (e.g. when a demo brand accidentally
    consumed a founding slot) without hand-editing the DB."""
    await require_admin(request)
    brand = await db.brands.find_one({"_id": safe_object_id(brand_id)})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    new_val = not bool(brand.get("is_founding"))
    await db.brands.update_one(
        {"_id": safe_object_id(brand_id)},
        {"$set": {"is_founding": new_val}},
    )
    return {"id": brand_id, "is_founding": new_val}


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
        "status": {"$in": SALE_STATUSES},
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



# ============ ADMIN — Image moderation review queue ============

@api_router.get("/admin/moderation/products")
async def admin_list_flagged_products(request: Request):
    """Products whose images landed in the manual-review queue.
    Includes anything with moderation_status='needs_review' — i.e. one or
    more images came back as 'unverified' (external URL, provider off,
    provider unclear). Never used for the auto-blocked 'flagged' verdict
    — those are 422'd before the product ever exists."""
    await require_admin(request)
    out = []
    async for p in db.products.find({"moderation_status": "needs_review"}).sort("created_at", -1).limit(200):
        p["id"] = str(p["_id"])
        del p["_id"]
        out.append(p)
    return out


class ModerationOverride(BaseModel):
    approve: bool


@api_router.post("/admin/moderation/products/{product_id}")
async def admin_moderation_override(product_id: str, payload: ModerationOverride, request: Request):
    """Admin can flip a needs-review product to 'passed' (approve) or
    'flagged' (take down) after eyeballing the album."""
    await require_admin(request)
    new_status = "passed" if payload.approve else "flagged"
    result = await db.products.update_one(
        {"_id": safe_object_id(product_id)},
        {"$set": {"moderation_status": new_status, "moderation_reviewed_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"moderation_status": new_status}

