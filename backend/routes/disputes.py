# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ BUYER PROTECTION / DISPUTES ============
# v1 — Non-Delivery Buyer Protection:
# Buyers can open a dispute on an order if they haven't received it. Eligibility
# rule (objective, easy to verify): order must be at least 14 days past payment
# AND either no tracking exists OR tracking was added more than 14 days ago.
# Admin reviews each dispute and either issues a refund (created on the seller's
# connected account — direct charges — with `refund_application_fee=True` so the
# platform returns its fee and the seller isn't out of pocket for our cut) or
# closes it with a reason.

DISPUTE_ELIGIBILITY_DAYS = int(os.environ.get("DISPUTE_ELIGIBILITY_DAYS", "14"))


def _order_dispute_eligibility(order: dict) -> Tuple[bool, str]:
    """Return (eligible, reason_or_message)."""
    if order.get("status") not in ("paid", "preorder_paid"):
        return False, "Order has not been paid"
    paid_at = order.get("created_at")
    if not isinstance(paid_at, datetime):
        return False, "Order payment date is unavailable"
    days_since_paid = (datetime.now(timezone.utc) - paid_at).days
    if days_since_paid < DISPUTE_ELIGIBILITY_DAYS:
        days_left = DISPUTE_ELIGIBILITY_DAYS - days_since_paid
        return False, f"Disputes can be opened {DISPUTE_ELIGIBILITY_DAYS} days after payment ({days_left} day(s) to go)"
    if order.get("shipping_status") == "delivered":
        return False, "Order is marked as delivered. If there's still an issue, contact the seller via messaging first."
    return True, "Eligible"


@api_router.post("/orders/{order_id}/disputes")
async def file_dispute(order_id: str, payload: DisputeCreate, request: Request):
    user = await get_current_user(request)
    
    order = await db.orders.find_one({"_id": safe_object_id(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["buyer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your order")
    
    eligible, reason = _order_dispute_eligibility(order)
    if not eligible:
        raise HTTPException(status_code=400, detail=reason)
    
    # Only one open dispute per order at a time
    existing = await db.disputes.find_one({"order_id": order_id, "status": "open"})
    if existing:
        raise HTTPException(status_code=400, detail="A dispute is already open for this order")
    
    if payload.type not in ("non_delivery",):
        raise HTTPException(status_code=400, detail="Only non-delivery disputes are supported in this version")
    
    if not payload.message or len(payload.message.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please describe the issue in at least 10 characters")
    
    dispute_doc = {
        "order_id": order_id,
        "buyer_id": user["id"],
        "brand_id": order["brand_id"],
        "type": payload.type,
        "status": "open",
        "buyer_message": payload.message.strip(),
        "created_at": datetime.now(timezone.utc),
        "resolution": None,
    }
    result = await db.disputes.insert_one(dispute_doc)
    dispute_id = str(result.inserted_id)
    
    # Notify every admin
    async for admin in db.users.find({"role": "admin"}, {"_id": 1}):
        await create_notification(
            user_id=str(admin["_id"]),
            brand_id=order["brand_id"],
            notification_type="dispute_opened",
            title="Buyer protection dispute opened",
            message=f"Buyer reports non-delivery for order #{order_id[-6:]}",
            metadata={"dispute_id": dispute_id, "order_id": order_id},
        )
    
    # Notify the seller so they can respond directly to the buyer via messaging
    brand = await db.brands.find_one({"_id": safe_object_id(order["brand_id"])})
    if brand:
        await create_notification(
            user_id=brand["user_id"],
            brand_id=order["brand_id"],
            notification_type="dispute_opened",
            title="Buyer has reported non-delivery",
            message=f"Order #{order_id[-6:]} — please respond or refund via your messages.",
            metadata={"dispute_id": dispute_id, "order_id": order_id},
        )
    
    return {"id": dispute_id, "message": "Dispute filed. Our team will investigate within 3 working days."}


@api_router.get("/orders/{order_id}/disputes")
async def get_order_disputes(order_id: str, request: Request):
    user = await get_current_user(request)
    order = await db.orders.find_one({"_id": safe_object_id(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Buyer of this order, seller of this order, or admin can view
    is_buyer = order["buyer_id"] == user["id"]
    is_admin = user.get("role") == "admin"
    is_seller = False
    if user.get("role") == "brand":
        brand = await db.brands.find_one({"user_id": user["id"]})
        is_seller = bool(brand and str(brand["_id"]) == order["brand_id"])
    if not (is_buyer or is_admin or is_seller):
        raise HTTPException(status_code=403, detail="Not authorised")
    
    disputes = await db.disputes.find({"order_id": order_id}).sort("created_at", -1).to_list(50)
    out = []
    for d in disputes:
        d["id"] = str(d["_id"])
        del d["_id"]
        out.append(d)
    return out


@api_router.get("/admin/disputes")
async def list_disputes_admin(request: Request, status: Optional[str] = None):
    await require_admin(request)
    query = {}
    if status:
        query["status"] = status
    disputes = await db.disputes.find(query).sort("created_at", -1).to_list(200)
    out = []
    for d in disputes:
        d["id"] = str(d["_id"])
        del d["_id"]
        # Enrich with order + brand summary
        try:
            order = await db.orders.find_one({"_id": safe_object_id(d["order_id"])})
            if order:
                d["order_summary"] = {
                    "product_name": order.get("product_name"),
                    "total_price": order.get("total_charged"),
                    "shipping_status": order.get("shipping_status"),
                    "tracking_number": order.get("tracking_number"),
                    "courier": order.get("courier"),
                    "created_at": order.get("created_at").isoformat() if isinstance(order.get("created_at"), datetime) else None,
                    "session_id": order.get("session_id"),
                }
            brand = await db.brands.find_one({"_id": safe_object_id(d["brand_id"])})
            if brand:
                d["brand_name"] = brand.get("brand_name")
        except Exception as e:
            logger.warning(f"Failed to enrich dispute {d['id']}: {e}")
        out.append(d)
    return out


@api_router.post("/admin/disputes/{dispute_id}/refund")
async def admin_refund_dispute(dispute_id: str, payload: DisputeResolution, request: Request):
    """Issue a full refund for the order. Direct charge: the refund is created ON
    the seller's connected account (funds come from their balance) with
    `refund_application_fee=True` so the platform returns its Buyer Protection fee.
    If Stripe fails, the dispute stays OPEN so the admin can retry."""
    await require_admin(request)
    
    dispute = await db.disputes.find_one({"_id": safe_object_id(dispute_id)})
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute["status"] != "open":
        raise HTTPException(status_code=400, detail="Dispute already resolved")
    
    order = await db.orders.find_one({"_id": safe_object_id(dispute["order_id"])})
    if not order:
        raise HTTPException(status_code=404, detail="Order missing")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Stripe is not configured — process the refund manually, then close the dispute with a note")
    
    stripe_sdk.api_key = api_key
    acct_kwargs = {"stripe_account": order["stripe_account_id"]} if order.get("stripe_account_id") else {}
    payment_intent_id = order.get("payment_intent_id")
    charge_id = order.get("charge_id")
    try:
        # Legacy orders settled before we stored payment_intent_id: recover it from the session
        if not payment_intent_id and not charge_id and order.get("session_id"):
            session = await asyncio.to_thread(
                stripe_sdk.checkout.Session.retrieve, order["session_id"], **acct_kwargs
            )
            payment_intent_id = session.payment_intent
        if not payment_intent_id and not charge_id:
            raise Exception("No payment reference found on this order")
        
        refund_kwargs = {"refund_application_fee": True, **acct_kwargs}
        if payment_intent_id:
            refund_kwargs["payment_intent"] = payment_intent_id
        else:
            refund_kwargs["charge"] = charge_id
        refund = await asyncio.to_thread(stripe_sdk.Refund.create, **refund_kwargs)
        refund_id = refund.id
        if payment_intent_id and not order.get("payment_intent_id"):
            await db.orders.update_one({"_id": order["_id"]}, {"$set": {"payment_intent_id": payment_intent_id}})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stripe refund failed for dispute {dispute_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Stripe refund failed — dispute left open so you can retry: {str(e)}")
    
    now = datetime.now(timezone.utc)
    await db.disputes.update_one(
        {"_id": safe_object_id(dispute_id)},
        {"$set": {
            "status": "resolved_refunded",
            "resolved_at": now,
            "resolution": {
                "outcome": "refunded",
                "note": payload.note or "",
                "stripe_refund_id": refund_id,
                "stripe_error": None,
            },
        }}
    )
    
    # Mark order as refunded
    await db.orders.update_one(
        {"_id": order["_id"]},
        {"$set": {"status": "refunded", "refunded_at": now}}
    )
    
    # Notify buyer + seller
    await create_notification(
        user_id=dispute["buyer_id"],
        brand_id=None,
        notification_type="dispute_refunded",
        title="Refund issued under Buyer Protection",
        message="We've refunded your order in full. It should appear in your account within 5–10 working days.",
        metadata={"dispute_id": dispute_id, "order_id": dispute["order_id"]},
    )
    brand = await db.brands.find_one({"_id": safe_object_id(dispute["brand_id"])})
    if brand:
        await create_notification(
            user_id=brand["user_id"],
            brand_id=dispute["brand_id"],
            notification_type="dispute_refunded",
            title="Order refunded under Buyer Protection",
            message=f"A buyer-protection refund was issued for order #{dispute['order_id'][-6:]}. The amount has been reversed from your Stripe balance.",
            metadata={"dispute_id": dispute_id, "order_id": dispute["order_id"]},
        )
    
    return {
        "message": "Refund processed",
        "stripe_refund_id": refund_id,
        "stripe_error": None,
    }


@api_router.post("/admin/disputes/{dispute_id}/close")
async def admin_close_dispute(dispute_id: str, payload: DisputeResolution, request: Request):
    """Close a dispute WITHOUT a refund (e.g. tracking shows delivered)."""
    await require_admin(request)
    
    dispute = await db.disputes.find_one({"_id": safe_object_id(dispute_id)})
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute["status"] != "open":
        raise HTTPException(status_code=400, detail="Dispute already resolved")
    if not payload.note or len(payload.note.strip()) < 5:
        raise HTTPException(status_code=400, detail="Please add a closing reason (visible to the buyer)")
    
    now = datetime.now(timezone.utc)
    await db.disputes.update_one(
        {"_id": safe_object_id(dispute_id)},
        {"$set": {
            "status": "resolved_closed",
            "resolved_at": now,
            "resolution": {"outcome": "closed", "note": payload.note.strip()},
        }}
    )
    
    await create_notification(
        user_id=dispute["buyer_id"],
        brand_id=None,
        notification_type="dispute_closed",
        title="Buyer Protection dispute closed",
        message=f"After review, we've closed your dispute. Reason: {payload.note.strip()[:120]}",
        metadata={"dispute_id": dispute_id, "order_id": dispute["order_id"]},
    )
    
    return {"message": "Dispute closed"}


# ============ ADMIN STATS ============

@api_router.get("/admin/stats")
async def get_admin_stats(request: Request):
    await require_admin(request)
    
    total_users = await db.users.count_documents({})
    total_buyers = await db.users.count_documents({"role": "user"})
    total_brand_owners = await db.users.count_documents({"role": "brand"})
    total_brands = await db.brands.count_documents({})
    total_products = await db.products.count_documents({})
    pending_applications = await db.brand_applications.count_documents({"status": "pending"})
    boosted_brands = await db.brands.count_documents({"is_boosted": True})
    total_orders = await db.orders.count_documents({})
    oversold_orders = await db.orders.count_documents({"oversold": True})
    total_revenue = 0
    pipeline = [{"$match": {"status": {"$in": SALE_STATUSES}}}, {"$group": {"_id": None, "total": {"$sum": "$platform_fee"}}}]
    async for doc in db.orders.aggregate(pipeline):
        total_revenue = doc["total"]
    
    return {
        "total_users": total_users,
        "total_buyers": total_buyers,
        "total_brand_owners": total_brand_owners,
        "total_brands": total_brands,
        "total_products": total_products,
        "pending_applications": pending_applications,
        "boosted_brands": boosted_brands,
        "total_orders": total_orders,
        "oversold_orders": oversold_orders,
        "total_revenue": round(total_revenue, 2)
    }

