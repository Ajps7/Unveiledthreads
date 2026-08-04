# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ BRAND ANALYTICS ============

@api_router.post("/analytics/view/{product_id}")
async def track_product_view(product_id: str, request: Request):
    """Track a product view (anonymous or authenticated)"""
    user = await get_optional_user(request)
    
    await db.product_views.insert_one({
        "product_id": product_id,
        "user_id": user["id"] if user else None,
        "created_at": datetime.now(timezone.utc)
    })
    return {"message": "View tracked"}

@api_router.get("/analytics/brand")
async def get_brand_analytics(request: Request, days: int = 30):
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    brand_id = str(brand["_id"])
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    # Priority 2 — prior window of identical length, immediately preceding current window.
    # e.g. days=30 → current [now-30 .. now], prior [now-60 .. now-30].
    prior_start = start_date - timedelta(days=days)
    prior_end = start_date
    
    # Get brand's products (include stock + is_dead_stock for restock nudge)
    products = await db.products.find(
        {"brand_id": brand_id},
        {"_id": 1, "name": 1, "stock": 1, "is_dead_stock": 1}
    ).to_list(100)
    product_ids = [str(p["_id"]) for p in products]
    product_names = {str(p["_id"]): p["name"] for p in products}
    product_map = {str(p["_id"]): p for p in products}
    
    # Total views
    total_views = await db.product_views.count_documents({
        "product_id": {"$in": product_ids},
        "created_at": {"$gte": start_date}
    })
    
    # Views per day for chart
    views_pipeline = [
        {"$match": {"product_id": {"$in": product_ids}, "created_at": {"$gte": start_date}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    daily_views = []
    async for doc in db.product_views.aggregate(views_pipeline):
        daily_views.append({"date": doc["_id"], "views": doc["count"]})
    
    # Orders and revenue — include preorder_paid so pre-order revenue isn't invisible.
    orders = await db.orders.find({
        "brand_id": brand_id,
        "status": {"$in": SALE_STATUSES},
        "created_at": {"$gte": start_date}
    }).to_list(500)
    
    total_orders = len(orders)
    total_revenue = sum(o.get("brand_payout", 0) for o in orders)
    
    # Revenue per day for chart
    revenue_by_day = {}
    for order in orders:
        day = order["created_at"].strftime("%Y-%m-%d") if isinstance(order["created_at"], datetime) else str(order["created_at"])[:10]
        revenue_by_day[day] = revenue_by_day.get(day, 0) + order.get("brand_payout", 0)
    
    daily_revenue = [{"date": k, "revenue": round(v, 2)} for k, v in sorted(revenue_by_day.items())]
    
    # Top selling products
    product_sales = {}
    for order in orders:
        pid = order["product_id"]
        product_sales[pid] = product_sales.get(pid, {"count": 0, "revenue": 0})
        product_sales[pid]["count"] += 1
        product_sales[pid]["revenue"] += order.get("brand_payout", 0)
    
    top_products = []
    for pid, stats in sorted(product_sales.items(), key=lambda x: x[1]["revenue"], reverse=True)[:5]:
        top_products.append({
            "product_id": pid,
            "name": product_names.get(pid, "Unknown"),
            "orders": stats["count"],
            "revenue": round(stats["revenue"], 2)
        })
    
    # -------- Priority 1: Repeat-buyer rate --------
    # Verified field: orders use `buyer_id` (string, mirrors user["id"]).
    # Count orders and revenue per buyer within the window, then split by cohort.
    buyer_orders = {}
    buyer_revenue = {}
    for order in orders:
        bid = order.get("buyer_id")
        if not bid or bid == "deleted-user":
            # Skip orders where buyer was deleted (GDPR anonymised) — they'd
            # otherwise all collapse into one "repeat" buyer.
            continue
        buyer_orders[bid] = buyer_orders.get(bid, 0) + 1
        buyer_revenue[bid] = buyer_revenue.get(bid, 0) + order.get("brand_payout", 0)
    
    unique_buyers = len(buyer_orders)
    repeat_buyers = sum(1 for count in buyer_orders.values() if count >= 2)
    repeat_rate = round((repeat_buyers / unique_buyers * 100), 1) if unique_buyers > 0 else 0
    repeat_revenue = sum(rev for bid, rev in buyer_revenue.items() if buyer_orders[bid] >= 2)
    repeat_revenue_share = round((repeat_revenue / total_revenue * 100), 1) if total_revenue > 0 else 0

    # -------- Priority 2: Period-over-period deltas --------
    # Compute the same 4 headline metrics for the immediately preceding window
    # of equal length. Returns `None` for delta when the prior window has no
    # data — the frontend renders this as "—" (not a divide-by-zero or infinity).
    prior_views = await db.product_views.count_documents({
        "product_id": {"$in": product_ids},
        "created_at": {"$gte": prior_start, "$lt": prior_end}
    })
    prior_orders_list = await db.orders.find({
        "brand_id": brand_id,
        "status": {"$in": SALE_STATUSES},
        "created_at": {"$gte": prior_start, "$lt": prior_end}
    }).to_list(500)
    prior_orders = len(prior_orders_list)
    prior_revenue = sum(o.get("brand_payout", 0) for o in prior_orders_list)
    prior_conversion = round((prior_orders / prior_views * 100), 2) if prior_views > 0 else 0

    def _delta(current: float, prior: float):
        """% change vs prior period. Returns None if prior is 0 (undefined)."""
        if not prior or prior == 0:
            return None
        return round(((current - prior) / prior) * 100, 1)

    deltas = {
        "views": _delta(total_views, prior_views),
        "orders": _delta(total_orders, prior_orders),
        "revenue": _delta(total_revenue, prior_revenue),
        "conversion": _delta(total_orders / total_views * 100 if total_views > 0 else 0, prior_conversion),
    }

    # -------- Priority 3: Restock nudge --------
    # Surface best-selling products (by orders in window) whose stock has dropped
    # to a low level. Excludes dead stock (those are meant to run out).
    # Threshold is env-configurable so it can be tuned without a redeploy.
    LOW_STOCK_THRESHOLD = int(os.environ.get("LOW_STOCK_THRESHOLD", "3"))
    restock_nudges = []
    for pid, stats in sorted(product_sales.items(), key=lambda x: x[1]["count"], reverse=True):
        pdoc = product_map.get(pid)
        if not pdoc:
            continue
        if pdoc.get("is_dead_stock"):
            continue
        current_stock = int(pdoc.get("stock", 0) or 0)
        if current_stock > LOW_STOCK_THRESHOLD:
            continue
        # Only nudge if it actually sold something in the window — no point telling
        # the seller to restock a product nobody wants.
        if stats["count"] < 1:
            continue
        restock_nudges.append({
            "product_id": pid,
            "name": pdoc.get("name", "Unknown"),
            "stock": current_stock,
            "orders_in_window": stats["count"],
            "revenue_in_window": round(stats["revenue"], 2),
        })
        if len(restock_nudges) >= 5:  # cap so the UI stays tidy
            break
    
    # Views per product
    views_per_product_pipeline = [
        {"$match": {"product_id": {"$in": product_ids}, "created_at": {"$gte": start_date}}},
        {"$group": {"_id": "$product_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_viewed = []
    async for doc in db.product_views.aggregate(views_per_product_pipeline):
        top_viewed.append({
            "product_id": doc["_id"],
            "name": product_names.get(doc["_id"], "Unknown"),
            "views": doc["count"]
        })
    
    return {
        "period_days": days,
        "total_views": total_views,
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "daily_views": daily_views,
        "daily_revenue": daily_revenue,
        "top_products": top_products,
        "top_viewed": top_viewed,
        "conversion_rate": round((total_orders / total_views * 100), 2) if total_views > 0 else 0,
        # Priority 1 — repeat-buyer metrics (additive; existing fields untouched)
        "unique_buyers": unique_buyers,
        "repeat_buyers": repeat_buyers,
        "repeat_rate": repeat_rate,
        "repeat_revenue_share": repeat_revenue_share,
        # Priority 2 — period-over-period deltas (%; null = no prior data)
        "deltas": deltas,
        # Priority 3 — restock nudges (best-sellers in window with low stock)
        "restock_nudges": restock_nudges,
    }

