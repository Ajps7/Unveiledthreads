# ruff: noqa: F403, F405
"""Multi-item cart checkout — single-brand per cart.

Entirely additive to /orders/checkout (single item) and
/orders/checkout/guest. Existing single-item "Buy Now" flow is unchanged.

Rules enforced server-side (never trust the client):
  - All items in `payload.items` MUST be from the same brand.
  - Every item is re-validated (exists, not draft, stock OR pre-order
    capacity, sizing correct).
  - Pricing is read from the DB — a client-sent price is ignored.
  - One Buyer Protection fee per order (min(subtotal*0.05+0.49, 6.00)),
    computed on COMBINED merchandise subtotal across every line.
  - Shipping is the SUM of each line's shipping_cost * quantity.
  - Mixed pre-order + in-stock baskets are allowed; the order record
    stores per-line is_preorder flags so dispatch dates ship separately.
"""
from core import *  # noqa: F401,F403
from routes.orders import send_order_receipt_email  # reuse the receipt email helper


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------

def _per_item_price(product: dict) -> float:
    """Price for a single unit of this product. Direct read — no discounts
    applied here (discounts are a Phase-2 feature on top of cart)."""
    return float(product.get("price") or 0)


async def _validate_and_price_cart(items: List[CartLineItem]) -> Tuple[dict, List[dict], float, float]:
    """Load each product, enforce single-brand, enforce stock/pre-order
    rules, and return (brand_doc, resolved_lines, merch_subtotal, total_shipping).

    `resolved_lines` is a list of dicts shaped for order_doc["items"] AND
    Stripe line_items metadata. Each dict carries: product_id, product_name,
    size, size_detail, top_size, bottom_size, quantity, unit_price,
    shipping_cost (per unit), is_preorder, preorder_ship_date.

    Raises HTTPException on any validation failure (clean status codes).
    """
    if not items:
        raise HTTPException(status_code=400, detail="Your cart is empty.")

    # Fetch every product in one round-trip. Keep the caller's order.
    product_oids = []
    for it in items:
        try:
            product_oids.append(ObjectId(it.product_id))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid product id: {it.product_id}")

    products_by_id: Dict[str, dict] = {}
    async for p in db.products.find({"_id": {"$in": product_oids}}):
        products_by_id[str(p["_id"])] = p

    # Single-brand enforcement + per-line validation
    brand_id: Optional[str] = None
    resolved_lines: List[dict] = []
    merch_subtotal = 0.0
    total_shipping = 0.0

    # Count how many pre-order units per product we're trying to add,
    # so the preorder_limit check accounts for multiple units in the same cart.
    preorder_wanted: Dict[str, int] = {}
    stock_wanted: Dict[str, int] = {}

    for it in items:
        p = products_by_id.get(it.product_id)
        if not p:
            raise HTTPException(status_code=404, detail="An item in your cart is no longer available.")
        if p.get("status") == "draft":
            raise HTTPException(status_code=404, detail=f"'{p.get('name')}' is no longer available.")

        this_brand = str(p["brand_id"])
        if brand_id is None:
            brand_id = this_brand
        elif this_brand != brand_id:
            # Single-brand cart constraint. The frontend already enforces
            # this, but we re-enforce here (tampered requests).
            raise HTTPException(
                status_code=400,
                detail="Your cart has items from more than one brand. Each cart can only contain items from a single brand.",
            )

        is_preorder = bool(p.get("is_preorder"))
        qty = int(it.quantity or 1)

        if is_preorder:
            preorder_wanted[it.product_id] = preorder_wanted.get(it.product_id, 0) + qty
        else:
            stock_wanted[it.product_id] = stock_wanted.get(it.product_id, 0) + qty

        display_size, size_detail = resolve_purchase_size(p, it.size, it.top_size, it.bottom_size)

        unit_price = _per_item_price(p)
        line_shipping = float(p.get("shipping_cost") or 0) * qty
        merch_subtotal += unit_price * qty
        total_shipping += line_shipping

        resolved_lines.append({
            "product_id": str(p["_id"]),
            "product_name": p["name"],
            "size": display_size,
            "size_detail": size_detail,
            "top_size": it.top_size,
            "bottom_size": it.bottom_size,
            "quantity": qty,
            "unit_price": round(unit_price, 2),
            "line_subtotal": round(unit_price * qty, 2),
            "shipping_cost": round(float(p.get("shipping_cost") or 0), 2),
            "is_preorder": is_preorder,
            "preorder_ship_date": p.get("preorder_ship_date") if is_preorder else None,
        })

    # Post-pass: per-product stock / pre-order cap checks accounting for
    # the full quantity requested in THIS cart (not just one unit).
    for product_id, qty in stock_wanted.items():
        p = products_by_id[product_id]
        if int(p.get("stock") or 0) < qty:
            raise HTTPException(
                status_code=400,
                detail=f"Only {p.get('stock', 0)} left of '{p['name']}' — please reduce the quantity.",
            )
    for product_id, qty in preorder_wanted.items():
        p = products_by_id[product_id]
        preorder_limit = p.get("preorder_limit")
        if preorder_limit is not None:
            current = await db.orders.count_documents({
                "product_id": product_id,
                "status": {"$in": ["preorder_paid", "shipped", "delivered", "initiated"]},
            })
            if current + qty > preorder_limit:
                raise HTTPException(
                    status_code=409,
                    detail=f"'{p['name']}' pre-order only has {max(preorder_limit - current, 0)} slots left.",
                )

    assert brand_id is not None
    brand_doc = await db.brands.find_one({"_id": ObjectId(brand_id)})
    if not brand_doc:
        raise HTTPException(status_code=404, detail="Brand not found")
    if not brand_doc.get("stripe_account_id") or not brand_doc.get("stripe_charges_enabled"):
        raise HTTPException(
            status_code=400,
            detail="This brand hasn't completed Stripe payment onboarding yet. Please check back soon.",
        )

    return brand_doc, resolved_lines, round(merch_subtotal, 2), round(total_shipping, 2)


def _build_stripe_line_items(lines: List[dict], brand_name: str, fee_charged: float, total_shipping: float, credit_applied: float = 0, discount: Optional[dict] = None) -> list:
    """Build Stripe Checkout line_items array: one entry per cart line
    (quantity preserved), plus a Buyer Protection line and a Shipping line
    (if > 0).

    A `discount` {code, percent_off, amount, brand_name} applies the
    percent uniformly to EVERY merchandise line (so Stripe's sub-total
    equals the discounted merch subtotal). The saving is also surfaced
    in the line description so buyers see it on the hosted page.
    Buyer Protection and Shipping are NEVER discounted — same rule as
    the preview endpoint. Stripe doesn't allow negative unit_amount so
    we can't add a "- Discount" line; the per-line reduction is the
    canonical way to show it on the hosted page."""
    pct = 0
    discount_label = ""
    if discount and discount.get("percent_off"):
        pct = int(discount["percent_off"])
        discount_label = f" — {pct}% off applied (code {discount.get('code')})"
    stripe_lines = []
    for ln in lines:
        name_parts = [ln["product_name"]]
        if ln.get("size"):
            name_parts.append(f"({ln['size']})")
        # Apply the percent reduction to each merchandise line's unit
        # price (rounded in PENCE). A client-sent discount is not trusted
        # — only the server's `discount` dict reaches here.
        unit_pence = int(round(ln["unit_price"] * 100))
        if pct > 0:
            unit_pence = int(round(unit_pence * (100 - pct) / 100))
        stripe_lines.append({
            "price_data": {
                "currency": "gbp",
                "product_data": {
                    "name": " ".join(name_parts),
                    "description": (f"Sold by {brand_name} via Unveiled Threads"
                                    + (" — pre-order" if ln.get("is_preorder") else "")
                                    + discount_label),
                },
                "unit_amount": max(unit_pence, 0),
            },
            "quantity": ln["quantity"],
        })
    if fee_charged > 0:
        fee_desc = "5% + £0.49 (max £6): money-back guarantee, easy returns, and hand-vetted independent brands"
        if credit_applied > 0:
            fee_desc += f" (£{credit_applied:.2f} referral credit applied)"
        stripe_lines.append({
            "price_data": {
                "currency": "gbp",
                "product_data": {"name": "Buyer Protection", "description": fee_desc},
                "unit_amount": int(round(fee_charged * 100)),
            },
            "quantity": 1,
        })
    if total_shipping > 0:
        stripe_lines.append({
            "price_data": {
                "currency": "gbp",
                "product_data": {"name": "Shipping"},
                "unit_amount": int(round(total_shipping * 100)),
            },
            "quantity": 1,
        })
    return stripe_lines


# ------------------------------------------------------------------
# Authenticated cart checkout
# ------------------------------------------------------------------

@api_router.post("/orders/checkout/cart")
@limiter.limit("20/minute")
async def create_cart_checkout(payload: CartCheckoutRequest, request: Request):
    user = await get_current_user(request)
    brand_doc, lines, merch_subtotal, total_shipping = await _validate_and_price_cart(payload.items)

    # Server-side discount re-validation. A client-sent discount amount
    # is always ignored — only the `code` string is trusted, and only
    # after it re-passes evaluate_discount against the current cart.
    from routes.discounts import resolve_cart_discount
    code_res = await resolve_cart_discount(
        payload.code, str(brand_doc["_id"]), merch_subtotal, user["id"], is_guest=False,
    )
    if payload.code and not code_res.get("applied"):
        # A code was supplied but it failed re-validation at the final step
        # (e.g. window just closed, cap just hit). Fail cleanly instead of
        # silently charging the full price.
        raise HTTPException(status_code=400, detail=code_res.get("message") or "This code can't be applied.")
    applied = code_res.get("applied")
    discount_amount = (applied["discount_pence"] / 100) if applied else 0.0
    discounted_subtotal = round(merch_subtotal - discount_amount, 2)

    platform_fee = calculate_buyer_fee(discounted_subtotal)

    credit_applied = 0.0
    if REFERRALS_ENABLED:
        referral = await db.referrals.find_one({"user_id": user["id"]})
        if referral:
            available = round(referral.get("credits_earned", 0) - referral.get("credits_used", 0), 2)
            if available > 0:
                credit_applied = round(min(available, platform_fee), 2)
    fee_charged = round(platform_fee - credit_applied, 2)
    total_charged = round(discounted_subtotal + fee_charged + total_shipping, 2)

    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_sdk.api_key = api_key

    success_url = f"{payload.origin_url}/order/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{payload.origin_url}/cart"

    # Pick a primary product for metadata (Stripe metadata is scalar-only)
    # — the full line list lives in the order_doc.
    primary = lines[0]
    any_preorder = any(ln["is_preorder"] for ln in lines)

    metadata = {
        "type": "cart_purchase",
        "user_id": user["id"],
        "brand_id": str(brand_doc["_id"]),
        "item_count": str(sum(ln["quantity"] for ln in lines)),
        "line_count": str(len(lines)),
        "primary_product_id": primary["product_id"],
        "merch_subtotal": str(merch_subtotal),
        "discount_code": applied["code"] if applied else "",
        "discount_amount": str(discount_amount),
        "platform_fee": str(fee_charged),
        "shipping_cost": str(total_shipping),
    }

    stripe_lines = _build_stripe_line_items(lines, brand_doc.get("brand_name", ""), fee_charged, total_shipping, credit_applied, discount=applied)

    payment_intent_data = {"metadata": metadata}
    fee_pence = int(round(fee_charged * 100))
    if fee_pence > 0:
        payment_intent_data["application_fee_amount"] = fee_pence

    try:
        session = await asyncio.to_thread(
            stripe_sdk.checkout.Session.create,
            mode="payment",
            line_items=stripe_lines,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            payment_intent_data=payment_intent_data,
            stripe_account=brand_doc["stripe_account_id"],
        )
    except Exception as e:
        logger.error(f"Cart checkout Stripe session failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    now = datetime.now(timezone.utc)
    order_doc = {
        "session_id": session.id,
        "buyer_id": user["id"],
        "buyer_email": user["email"],
        "buyer_name": user["name"],
        # Top-level mirror of the first line — keeps every existing reader
        # (receipt email, order display, brand notifications) working on
        # the primary item, and `items[]` carries the full basket.
        "product_id": primary["product_id"],
        "product_name": primary["product_name"],
        "brand_id": str(brand_doc["_id"]),
        "brand_name": brand_doc.get("brand_name"),
        "size": primary["size"],
        "size_detail": primary.get("size_detail"),
        "price": primary["unit_price"],
        "shipping_cost": total_shipping,
        "platform_fee": fee_charged,
        "credit_applied": credit_applied,
        "total_charged": total_charged,
        "brand_payout": round(discounted_subtotal + total_shipping, 2),
        "stripe_account_id": brand_doc["stripe_account_id"],
        "status": "initiated",
        "shipping_status": "confirmed",
        "tracking_number": None,
        "courier": None,
        "shipping_updates": [],
        "reviewed": False,
        "is_preorder": any_preorder,  # cart is mixed? the per-line flag lives in items[]
        "preorder_ship_date": primary.get("preorder_ship_date"),
        # NEW: full cart structure
        "items": lines,
        "merch_subtotal": merch_subtotal,
        "cart_order": True,
        # Discount — null when no code was applied. `discount_code` is
        # the stored normalised (upper-case) code string. Kept flat so
        # analytics / reporting can `$group` on code directly.
        "discount_code": applied["code"] if applied else None,
        "discount_amount": discount_amount,
        "discount_percent": applied["percent_off"] if applied else None,
        "discounted_subtotal": discounted_subtotal,
        "created_at": now,
    }
    await db.orders.insert_one(order_doc)
    await db.payment_transactions.insert_one({
        "session_id": session.id,
        "user_id": user["id"],
        "type": "cart_purchase",
        "amount": total_charged,
        "currency": "gbp",
        "payment_status": "initiated",
        "created_at": now,
    })

    return {"url": session.url, "session_id": session.id}


# ------------------------------------------------------------------
# Guest cart checkout
# ------------------------------------------------------------------

@api_router.post("/orders/checkout/cart/guest")
@limiter.limit("5/minute")
async def create_cart_checkout_guest(payload: CartGuestCheckoutRequest, request: Request):
    brand_doc, lines, merch_subtotal, total_shipping = await _validate_and_price_cart(payload.items)

    # Discount re-validation keyed to the guest's email (lowercased).
    from routes.discounts import resolve_cart_discount
    buyer_email_norm = payload.buyer_email.strip().lower()
    code_res = await resolve_cart_discount(
        payload.code, str(brand_doc["_id"]), merch_subtotal, buyer_email_norm, is_guest=True,
    )
    if payload.code and not code_res.get("applied"):
        raise HTTPException(status_code=400, detail=code_res.get("message") or "This code can't be applied.")
    applied = code_res.get("applied")
    discount_amount = (applied["discount_pence"] / 100) if applied else 0.0
    discounted_subtotal = round(merch_subtotal - discount_amount, 2)

    platform_fee = calculate_buyer_fee(discounted_subtotal)
    credit_applied = 0.0
    fee_charged = round(platform_fee, 2)
    total_charged = round(discounted_subtotal + fee_charged + total_shipping, 2)

    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_sdk.api_key = api_key

    lookup_token = secrets.token_urlsafe(32)
    success_url = (
        f"{payload.origin_url}/order/success?session_id={{CHECKOUT_SESSION_ID}}"
        f"&guest=1&token={lookup_token}"
    )
    cancel_url = f"{payload.origin_url}/cart"

    primary = lines[0]
    any_preorder = any(ln["is_preorder"] for ln in lines)

    metadata = {
        "type": "cart_purchase",
        "guest": "1",
        "brand_id": str(brand_doc["_id"]),
        "item_count": str(sum(ln["quantity"] for ln in lines)),
        "line_count": str(len(lines)),
        "primary_product_id": primary["product_id"],
        "merch_subtotal": str(merch_subtotal),
        "discount_code": applied["code"] if applied else "",
        "discount_amount": str(discount_amount),
        "platform_fee": str(fee_charged),
        "shipping_cost": str(total_shipping),
    }

    stripe_lines = _build_stripe_line_items(lines, brand_doc.get("brand_name", ""), fee_charged, total_shipping, discount=applied)

    payment_intent_data = {"metadata": metadata}
    fee_pence = int(round(fee_charged * 100))
    if fee_pence > 0:
        payment_intent_data["application_fee_amount"] = fee_pence

    try:
        session = await asyncio.to_thread(
            stripe_sdk.checkout.Session.create,
            mode="payment",
            line_items=stripe_lines,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            payment_intent_data=payment_intent_data,
            customer_email=payload.buyer_email,
            stripe_account=brand_doc["stripe_account_id"],
        )
    except Exception as e:
        logger.error(f"Guest cart checkout Stripe session failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    now = datetime.now(timezone.utc)
    order_doc = {
        "session_id": session.id,
        "buyer_id": None,
        "buyer_email": buyer_email_norm,
        "buyer_name": payload.shipping_address.name,
        "product_id": primary["product_id"],
        "product_name": primary["product_name"],
        "brand_id": str(brand_doc["_id"]),
        "brand_name": brand_doc.get("brand_name"),
        "size": primary["size"],
        "size_detail": primary.get("size_detail"),
        "price": primary["unit_price"],
        "shipping_cost": total_shipping,
        "platform_fee": fee_charged,
        "credit_applied": credit_applied,
        "total_charged": total_charged,
        "brand_payout": round(discounted_subtotal + total_shipping, 2),
        "stripe_account_id": brand_doc["stripe_account_id"],
        "status": "initiated",
        "shipping_status": "confirmed",
        "shipping_address": payload.shipping_address.model_dump(),
        "tracking_number": None,
        "courier": None,
        "shipping_updates": [],
        "reviewed": False,
        "is_preorder": any_preorder,
        "preorder_ship_date": primary.get("preorder_ship_date"),
        "items": lines,
        "merch_subtotal": merch_subtotal,
        "cart_order": True,
        "discount_code": applied["code"] if applied else None,
        "discount_amount": discount_amount,
        "discount_percent": applied["percent_off"] if applied else None,
        "discounted_subtotal": discounted_subtotal,
        "guest_order": True,
        "lookup_token": lookup_token,
        "marketing_opt_in": bool(payload.marketing_opt_in),
        "consent_timestamp": now if payload.marketing_opt_in else None,
        "created_at": now,
    }
    await db.orders.insert_one(order_doc)
    await db.payment_transactions.insert_one({
        "session_id": session.id,
        "user_id": None,
        "guest": True,
        "type": "cart_purchase",
        "amount": total_charged,
        "currency": "gbp",
        "payment_status": "initiated",
        "created_at": now,
    })

    if payload.marketing_opt_in:
        await db.marketing_subscribers.update_one(
            {"email": buyer_email_norm},
            {"$setOnInsert": {
                "email": buyer_email_norm,
                "source": "guest_cart_checkout",
                "consent_timestamp": now,
                "synced_to_mailerlite": False,
            }},
            upsert=True,
        )

    return {"url": session.url, "session_id": session.id, "lookup_token": lookup_token}


# ------------------------------------------------------------------
# Cart preview (dry-run pricing — frontend uses to show totals before
# clicking Checkout). Single-brand, same rules, no Stripe call.
# ------------------------------------------------------------------

@api_router.post("/orders/cart/preview")
@limiter.limit("60/minute")
async def preview_cart(payload: CartCheckoutRequest, request: Request):
    """Return the exact totals the server would charge if this cart is
    checked out now. Never trust the client for pricing — this is the
    single source of truth for what buyers see on the cart page."""
    brand_doc, lines, merch_subtotal, total_shipping = await _validate_and_price_cart(payload.items)

    # Optional discount code — re-evaluated server-side on EVERY preview
    # call. The buyer can reach this endpoint without being signed in
    # (guest flow), so we only look up a per-user id when a session exists.
    buyer_identifier: Optional[str] = None
    is_guest = True
    try:
        user = await get_current_user(request)
        buyer_identifier = user["id"]
        is_guest = False
    except HTTPException:
        pass

    # Lazy-import to avoid a hard import cycle (discounts depends on
    # _validate_and_price_cart which lives here).
    from routes.discounts import resolve_cart_discount
    code_res = await resolve_cart_discount(
        payload.code, str(brand_doc["_id"]), merch_subtotal, buyer_identifier, is_guest,
    )
    applied = code_res.get("applied")
    discount_amount = (applied["discount_pence"] / 100) if applied else 0.0
    discounted_subtotal = round(merch_subtotal - discount_amount, 2)

    # Platform application fee is computed on the DISCOUNTED merch amount
    # (no-op at 0% founding commission, but wired correctly now).
    platform_fee = calculate_buyer_fee(discounted_subtotal)
    fee_charged = round(platform_fee, 2)
    total_charged = round(discounted_subtotal + fee_charged + total_shipping, 2)

    any_preorder = any(ln["is_preorder"] for ln in lines)
    has_in_stock = any(not ln["is_preorder"] for ln in lines)
    return {
        "brand_id": str(brand_doc["_id"]),
        "brand_name": brand_doc.get("brand_name"),
        "lines": lines,
        "merch_subtotal": merch_subtotal,
        "shipping_cost": total_shipping,
        "platform_fee": fee_charged,
        "total_charged": total_charged,
        "mixed_fulfilment": any_preorder and has_in_stock,
        "has_preorder": any_preorder,
        # Discount surface — `discount` is null when no code was sent or
        # the code failed; `discount_error` carries the user-facing reason.
        "discount": {
            "code": applied["code"],
            "percent_off": applied["percent_off"],
            "amount": discount_amount,
            "message": applied["message"],
            "brand_name": applied["brand_name"],
        } if applied else None,
        "discount_error": None if applied else code_res.get("message"),
        "progress_hint": bool(code_res.get("progress_hint")),
    }
