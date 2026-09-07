"""Mongo → engine input. The only module in this package that touches I/O.

Everything else in `growth/` is pure, which is what makes the formulas
testable. This module's whole job is to read the marketplace's collections
once, normalise them into the plain dict shape `metrics.compute_metrics`
expects, and cap the read so an admin page can never take the database down.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)

# Hard ceilings. A growth dashboard is never worth a slow query on the
# production database; past these volumes the rates are stable anyway, so
# truncation costs accuracy that does not exist.
MAX_ORDERS = 20000
MAX_VIEWS = 200000
MAX_LISTINGS = 20000
MAX_USERS = 50000
MAX_POSTS = 5000
MAX_WISHLIST = 20000


def _as_utc(value) -> Optional[datetime]:
    """Normalise whatever Mongo hands back into a tz-aware UTC datetime.

    Documents written before the codebase standardised on tz-aware UTC come
    back naive; comparing those against an aware `now` raises, which would
    take out the whole dashboard for one legacy row.
    """
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def collect(db, window_days: int = 90, sale_statuses: Optional[List[str]] = None,
                  now: Optional[datetime] = None) -> dict:
    """Read every collection the engine needs and return the `raw` bundle.

    Orders are read across all time (cohorts and first-sale timing need the
    full history); the high-volume event collections are read only for the
    window plus the prior comparison window.
    """
    now = now or datetime.now(timezone.utc)
    sale_statuses = sale_statuses or ["paid", "preorder_paid", "shipped", "delivered"]
    window_start = now - timedelta(days=window_days)
    # Views and posts are only ever read within the window and the prior one.
    event_start = now - timedelta(days=window_days * 2)

    orders = []
    async for o in db.orders.find(
        {"status": {"$in": sale_statuses}},
        {"buyer_id": 1, "brand_id": 1, "product_id": 1, "brand_payout": 1,
         "price": 1, "created_at": 1},
    ).sort("created_at", -1).limit(MAX_ORDERS):
        created = _as_utc(o.get("created_at"))
        if created is None:
            continue
        orders.append({
            "buyer_id": o.get("buyer_id"),
            "brand_id": o.get("brand_id"),
            "product_id": o.get("product_id"),
            # GMV is the merchandise value the buyer paid for goods, which is
            # what marketplace GMV means. `brand_payout` includes shipping and
            # would inflate it; the buyer-protection fee is platform revenue,
            # not GMV, so it is excluded from both.
            "gmv": float(o.get("price") or 0),
            "created_at": created,
        })

    views = []
    async for v in db.product_views.find(
        {"created_at": {"$gte": event_start}},
        {"user_id": 1, "product_id": 1, "created_at": 1},
    ).limit(MAX_VIEWS):
        created = _as_utc(v.get("created_at"))
        if created is None:
            continue
        views.append({
            "user_id": v.get("user_id"),
            "product_id": v.get("product_id"),
            "created_at": created,
        })

    listings = []
    async for pdoc in db.products.find(
        {}, {"brand_id": 1, "created_at": 1, "stock": 1, "is_dead_stock": 1,
             "moderation_status": 1},
    ).limit(MAX_LISTINGS):
        created = _as_utc(pdoc.get("created_at"))
        listings.append({
            "id": str(pdoc["_id"]),
            "brand_id": pdoc.get("brand_id"),
            "created_at": created,
            # "Live" means a buyer could actually buy it right now: in stock
            # and not withheld by moderation.
            "is_active": bool(
                int(pdoc.get("stock") or 0) > 0
                and pdoc.get("moderation_status") != "flagged"
            ),
        })

    brands = []
    async for b in db.brands.find(
        {}, {"brand_name": 1, "created_at": 1, "market": 1, "category": 1},
    ).limit(MAX_LISTINGS):
        brands.append({
            "id": str(b["_id"]),
            "name": b.get("brand_name"),
            "created_at": _as_utc(b.get("created_at")),
            "market": b.get("market") or "UK",
            "category": b.get("category"),
        })

    users = []
    async for u in db.users.find(
        {"created_at": {"$gte": event_start}}, {"created_at": 1, "role": 1},
    ).limit(MAX_USERS):
        created = _as_utc(u.get("created_at"))
        if created is None:
            continue
        users.append({"id": str(u["_id"]), "created_at": created,
                      "role": u.get("role")})

    referral_codes = []
    async for r in db.referrals.find({}, {"user_id": 1, "created_at": 1}).limit(MAX_USERS):
        referral_codes.append({
            "user_id": r.get("user_id"), "created_at": _as_utc(r.get("created_at")),
        })

    referral_uses = []
    async for r in db.referral_uses.find(
        {}, {"user_id": 1, "referrer_id": 1, "created_at": 1},
    ).limit(MAX_USERS):
        referral_uses.append({
            "user_id": r.get("user_id"),
            "referrer_id": r.get("referrer_id"),
            "created_at": _as_utc(r.get("created_at")),
        })

    posts = []
    async for pdoc in db.community_posts.find(
        {"created_at": {"$gte": event_start}},
        {"user_id": 1, "created_at": 1, "likes": 1, "comment_count": 1,
         "brand_tag": 1},
    ).limit(MAX_POSTS):
        created = _as_utc(pdoc.get("created_at"))
        if created is None:
            continue
        posts.append({
            "user_id": pdoc.get("user_id"),
            "created_at": created,
            "like_user_ids": list(pdoc.get("likes") or []),
            "comment_count": int(pdoc.get("comment_count") or 0),
            "brand_tag": pdoc.get("brand_tag"),
        })

    wishlist = []
    async for w in db.wishlist.find(
        {}, {"user_id": 1, "product_id": 1, "created_at": 1},
    ).limit(MAX_WISHLIST):
        created = _as_utc(w.get("created_at"))
        if created is None:
            continue
        wishlist.append({
            "user_id": w.get("user_id"), "product_id": w.get("product_id"),
            "created_at": created,
        })

    logger.info(
        "growth collector: %d orders, %d views, %d listings, %d brands, "
        "%d users, %d posts, %d wishlist",
        len(orders), len(views), len(listings), len(brands), len(users),
        len(posts), len(wishlist),
    )

    return {
        "now": now,
        "window_days": window_days,
        "orders": orders,
        "views": views,
        "listings": listings,
        "brands": brands,
        "users": users,
        "referral_codes": referral_codes,
        "referral_uses": referral_uses,
        "posts": posts,
        "wishlist": wishlist,
        "truncated": {
            "orders": len(orders) >= MAX_ORDERS,
            "views": len(views) >= MAX_VIEWS,
            "listings": len(listings) >= MAX_LISTINGS,
        },
        "window_start": window_start,
    }
