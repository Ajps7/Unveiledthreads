# ruff: noqa: F403, F405
"""Brand-scoped discount codes. Phase 2 of the promo-code programme.

Architecture rules:
  - A code ALWAYS belongs to exactly one brand (brand_id) and can discount
    ONLY that brand's own products.
  - Records are TYPED (`type` field). `evaluate_discount()` dispatches on
    type so adding BOGO / buy-X-get-Y later needs no refactor.
  - Every amount-affecting check lives on the SERVER. A client-sent
    discount value is always ignored — only the code name is trusted,
    and only after re-validation.
  - `used_count` is incremented atomically at order SETTLEMENT (see
    `settle_paid_order`) so under concurrent checkouts a popular code
    cannot be over-redeemed past its usage_limit.
"""
from core import *  # noqa: F401,F403
from routes.cart import _validate_and_price_cart


# -----------------------------------------------------------------
# Server-side evaluator
# -----------------------------------------------------------------

def _to_pence(amount_pounds: float) -> int:
    return int(round(amount_pounds * 100))


async def evaluate_discount(
    discount: dict,
    cart_brand_id: str,
    cart_merch_subtotal_pounds: float,
    now: datetime,
    buyer_identifier: Optional[str],
    is_guest: bool,
) -> dict:
    """Return the applied result or a user-facing rejection. NEVER raises —
    every rejection path yields `{"ok": False, "message": "..."}`.

    `buyer_identifier` is `user_id` for logged-in buyers and the
    lowercased `buyer_email` for guests. We count orders already carrying
    this discount code against that identifier for per-customer limits.

    Dispatch key is `discount["type"]`. Only "threshold_percent" exists
    today. Future types branch at the computation block at the bottom.
    """
    brand_doc = await db.brands.find_one({"_id": ObjectId(discount["brand_id"])})
    brand_label = (brand_doc or {}).get("brand_name") or "this brand"

    # Strict brand scoping: the cart's single brand must BE the code's brand.
    # (Phase 1 carts are always single-brand so there is no partial
    # brand-subtotal inside a mixed cart — the "brand subtotal" IS the
    # cart's whole merch subtotal.)
    if str(discount["brand_id"]) != str(cart_brand_id):
        return {"ok": False, "message": f"This code only applies to {brand_label} products."}

    if not discount.get("active"):
        return {"ok": False, "message": "This code is no longer active."}

    starts_at = discount.get("starts_at")
    ends_at = discount.get("ends_at")
    # Mongo strips tz on BSON datetimes — re-attach UTC so comparison
    # against `now` (tz-aware) doesn't blow up.
    if starts_at and starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    if ends_at and ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=timezone.utc)
    if starts_at and now < starts_at:
        return {"ok": False, "message": "This code isn't live yet."}
    if ends_at and now > ends_at:
        return {"ok": False, "message": "This code has expired."}

    # Total usage cap
    usage_limit = discount.get("usage_limit")
    used_count = int(discount.get("used_count") or 0)
    if usage_limit is not None and used_count >= usage_limit:
        return {"ok": False, "message": "This code has reached its usage limit."}

    # Per-customer limit. Count ALREADY-SETTLED orders by this buyer
    # that carried this code. `status` in {paid, preorder_paid} are the
    # only states that counted toward `used_count`.
    per_customer_limit = int(discount.get("per_customer_limit") or 1)
    if buyer_identifier:
        q: dict = {
            "discount_code": discount["code"],
            "status": {"$in": ["paid", "preorder_paid", "shipped", "delivered"]},
        }
        if is_guest:
            q["buyer_email"] = buyer_identifier
            q["buyer_id"] = None
        else:
            q["buyer_id"] = buyer_identifier
        used_by_buyer = await db.orders.count_documents(q)
        if used_by_buyer >= per_customer_limit:
            return {"ok": False, "message": "You've already used this code."}

    # Threshold on the brand's MERCHANDISE subtotal (excl. shipping + BP fee)
    subtotal_pence = _to_pence(cart_merch_subtotal_pounds)
    threshold_pence = int(discount.get("threshold_amount") or 0)
    if subtotal_pence < threshold_pence:
        diff = (threshold_pence - subtotal_pence) / 100
        return {
            "ok": False,
            "message": f"Spend £{threshold_pence / 100:.2f} on {brand_label} to use this code (you're £{diff:.2f} away).",
            "progress_hint": True,
            "threshold_amount": threshold_pence,
            "shortfall_pence": threshold_pence - subtotal_pence,
            "brand_name": brand_label,
            "percent_off": int(discount.get("percent_off") or 0),
        }

    # ----- Dispatch on `type` -----
    dtype = discount.get("type")
    if dtype == "threshold_percent":
        percent = int(discount.get("percent_off") or 0)
        discount_pence = int(round(subtotal_pence * percent / 100))
    else:
        # Unknown stored type — fail closed, never auto-apply.
        return {"ok": False, "message": "This code type isn't supported anymore."}

    # Stripe minimum per Direct Charge (GBP) is 30p. If discount would
    # drive the merch subtotal below 30p reject cleanly rather than
    # produce an invalid Checkout Session.
    discounted_subtotal_pence = max(subtotal_pence - discount_pence, 0)
    if discounted_subtotal_pence < 30:
        return {
            "ok": False,
            "message": "This code would reduce your order below the minimum charge amount.",
        }

    return {
        "ok": True,
        "discount_pence": discount_pence,
        "discounted_subtotal_pence": discounted_subtotal_pence,
        "percent_off": int(discount.get("percent_off") or 0),
        "brand_name": brand_label,
        "code": discount["code"],
        "message": f"{discount['percent_off']}% off {brand_label} applied",
    }


async def find_active_discount_by_code(code: str) -> Optional[dict]:
    """Case-insensitive lookup — codes are stored upper-case."""
    return await db.discounts.find_one({"code": (code or "").strip().upper()})


async def resolve_cart_discount(
    code: Optional[str],
    cart_brand_id: str,
    cart_merch_subtotal_pounds: float,
    buyer_identifier: Optional[str],
    is_guest: bool,
) -> dict:
    """Helper used by both preview and checkout. Returns a dict ALWAYS
    (either applied={...} or applied=None with a `message`), so callers
    can uniformly surface the state to the UI."""
    if not code:
        return {"applied": None, "message": None}
    d = await find_active_discount_by_code(code)
    if not d:
        return {"applied": None, "message": "That code isn't recognised."}
    res = await evaluate_discount(
        d, cart_brand_id, cart_merch_subtotal_pounds,
        datetime.now(timezone.utc), buyer_identifier, is_guest,
    )
    if not res.get("ok"):
        return {"applied": None, "message": res.get("message"), "progress_hint": res.get("progress_hint", False)}
    return {"applied": res, "message": res["message"]}


# -----------------------------------------------------------------
# Brand CRUD — a brand can only ever touch its own codes
# -----------------------------------------------------------------

async def _current_brand_doc(request: Request) -> dict:
    """Load the authed caller's brand doc or 403. Shared by every route
    here so the owner check is impossible to bypass."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


def _public_discount(d: dict) -> dict:
    """Shape the discount for the brand UI: never leak internal fields."""
    now = datetime.now(timezone.utc)
    starts_at = d.get("starts_at")
    ends_at = d.get("ends_at")
    if starts_at and starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    if ends_at and ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=timezone.utc)
    status = "scheduled" if starts_at and now < starts_at else (
        "ended" if ends_at and now > ends_at else (
            "paused" if not d.get("active") else "live"
        )
    )
    return {
        "id": str(d["_id"]),
        "brand_id": str(d["brand_id"]),
        "code": d.get("code"),
        "type": d.get("type"),
        "percent_off": d.get("percent_off"),
        "threshold_amount": d.get("threshold_amount"),
        "threshold_pounds": (d.get("threshold_amount") or 0) / 100,
        "starts_at": d.get("starts_at"),
        "ends_at": d.get("ends_at"),
        "usage_limit": d.get("usage_limit"),
        "used_count": int(d.get("used_count") or 0),
        "per_customer_limit": int(d.get("per_customer_limit") or 1),
        "active": bool(d.get("active")),
        "status": status,
        "created_at": d.get("created_at"),
    }


@api_router.post("/discounts")
async def create_discount(payload: DiscountCreate, request: Request):
    """Create a code on the caller's OWN brand. Code is case-insensitive
    unique across the whole platform (enforced by unique index)."""
    brand = await _current_brand_doc(request)
    now = datetime.now(timezone.utc)
    doc = {
        "brand_id": str(brand["_id"]),
        "code": payload.code,  # already upper-cased by the validator
        "type": payload.type,
        "percent_off": payload.percent_off,
        "threshold_amount": payload.threshold_amount,
        "starts_at": payload.starts_at,
        "ends_at": payload.ends_at,
        "usage_limit": payload.usage_limit,
        "used_count": 0,
        "per_customer_limit": payload.per_customer_limit,
        "active": payload.active,
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = await db.discounts.insert_one(doc)
    except Exception as e:
        # Duplicate code — Mongo unique index on `code`.
        if "duplicate key" in str(e).lower() or "11000" in str(e):
            raise HTTPException(status_code=409, detail="That code is already taken. Try another.")
        raise
    doc["_id"] = result.inserted_id
    return _public_discount(doc)


@api_router.get("/discounts/mine")
async def list_my_discounts(request: Request):
    """List the caller brand's codes (any status)."""
    brand = await _current_brand_doc(request)
    cursor = db.discounts.find({"brand_id": str(brand["_id"])}).sort("created_at", -1)
    out = []
    async for d in cursor:
        out.append(_public_discount(d))
    return out


@api_router.put("/discounts/{discount_id}")
async def update_discount(discount_id: str, payload: DiscountUpdate, request: Request):
    """Edit a caller-owned code. Immutable: code, type, brand_id."""
    brand = await _current_brand_doc(request)
    try:
        oid = ObjectId(discount_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Discount not found")
    existing = await db.discounts.find_one({"_id": oid, "brand_id": str(brand["_id"])})
    if not existing:
        raise HTTPException(status_code=404, detail="Discount not found")

    set_fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not set_fields:
        return _public_discount(existing)

    # Window validity check if either edge is being moved
    new_start = set_fields.get("starts_at", existing.get("starts_at"))
    new_end = set_fields.get("ends_at", existing.get("ends_at"))
    if new_start and new_end and new_end <= new_start:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")

    set_fields["updated_at"] = datetime.now(timezone.utc)
    await db.discounts.update_one({"_id": oid}, {"$set": set_fields})
    refreshed = await db.discounts.find_one({"_id": oid})
    return _public_discount(refreshed)


@api_router.delete("/discounts/{discount_id}")
async def delete_discount(discount_id: str, request: Request):
    """Soft-delete via `active=False` + flag. Keeps historic order
    references to `discount_code` meaningful for reporting."""
    brand = await _current_brand_doc(request)
    try:
        oid = ObjectId(discount_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Discount not found")
    res = await db.discounts.update_one(
        {"_id": oid, "brand_id": str(brand["_id"])},
        {"$set": {"active": False, "deleted_at": datetime.now(timezone.utc)}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Discount not found")
    return {"ok": True}


@api_router.get("/discounts/code-available")
@limiter.limit("30/minute")
async def check_code_available(request: Request, code: str):
    """Live uniqueness check for the brand dashboard form."""
    normalised = (code or "").strip().upper()
    if not normalised or not all(c.isalnum() for c in normalised) or len(normalised) < 3:
        return {"available": False, "reason": "Codes must be at least 3 characters, A-Z / 0-9 only."}
    existing = await db.discounts.find_one({"code": normalised})
    return {"available": not bool(existing)}


# -----------------------------------------------------------------
# Public validate — buyers check a code from the cart page
# -----------------------------------------------------------------

@api_router.post("/discounts/validate")
@limiter.limit("30/minute")
async def validate_discount(payload: DiscountValidateRequest, request: Request):
    """Validate a code against the caller's current cart. Returns the
    applied discount OR a user-facing message explaining the rejection."""
    # Price the cart first — same server-authoritative pass that
    # /orders/cart/preview runs. This also enforces the single-brand rule.
    brand_doc, lines, merch_subtotal, _total_shipping = await _validate_and_price_cart(payload.items)

    # Identify the buyer for per-customer limits
    buyer_identifier: Optional[str] = None
    is_guest = True
    try:
        user = await get_current_user(request)
        buyer_identifier = user["id"]
        is_guest = False
    except HTTPException:
        if payload.buyer_email:
            buyer_identifier = payload.buyer_email.strip().lower()

    res = await resolve_cart_discount(
        payload.code,
        str(brand_doc["_id"]),
        merch_subtotal,
        buyer_identifier,
        is_guest,
    )
    if res.get("applied"):
        a = res["applied"]
        return {
            "ok": True,
            "code": a["code"],
            "percent_off": a["percent_off"],
            "brand_name": a["brand_name"],
            "discount_amount": a["discount_pence"] / 100,
            "message": a["message"],
        }
    return {
        "ok": False,
        "message": res.get("message") or "That code can't be applied to this cart.",
        "progress_hint": bool(res.get("progress_hint")),
    }
