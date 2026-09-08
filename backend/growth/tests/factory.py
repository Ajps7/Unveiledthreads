"""Synthetic marketplace builder.

Lets a test say "a marketplace with 8 brands where buyers never cross
between them" and get back the exact `raw` shape the engine consumes.
"""
from datetime import datetime, timedelta, timezone

NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def days_ago(n: float, now: datetime = NOW) -> datetime:
    """`n` days before NOW, nudged back six hours.

    The nudge keeps generated events off the exact window boundary. The
    engine's window is half-open (start <= ts < end), which is correct — an
    event stamped exactly `now` belongs to the next window — but a factory
    that emits one on the boundary makes tests fail for a reason that has
    nothing to do with the behaviour under test.
    """
    return now - timedelta(days=n) - timedelta(hours=6)


def marketplace(
    *,
    now: datetime = NOW,
    window_days: int = 90,
    brands: int = 5,
    buyers: int = 20,
    orders_per_buyer: int = 1,
    brands_per_buyer: int = 1,
    listings_per_brand: int = 10,
    views_per_order: int = 40,
    gmv_per_order: float = 45.0,
    brand_age_days: int = 200,
    listing_age_days: int = 60,
    selling_brands: int = None,
    posts: int = 0,
    referral_codes: int = 0,
    referral_uses: int = 0,
    wishlist_items: int = 0,
    wishlist_converted: int = 0,
    category: str = "tees",
    market: str = "UK",
) -> dict:
    """Build a `raw` bundle. Orders are spread evenly across the window."""
    selling_brands = brands if selling_brands is None else selling_brands
    brand_rows = [
        {"id": f"br{i}", "name": f"Brand {i}",
         "created_at": days_ago(brand_age_days, now),
         "market": market, "category": category}
        for i in range(brands)
    ]
    listing_rows = [
        {"id": f"br{b}-p{j}", "brand_id": f"br{b}",
         "created_at": days_ago(listing_age_days, now), "is_active": True}
        for b in range(brands) for j in range(listings_per_brand)
    ]

    order_rows = []
    n = 0
    for u in range(buyers):
        for o in range(orders_per_buyer):
            # Rotate the buyer across `brands_per_buyer` distinct sellers.
            brand_idx = (u + (o % max(brands_per_buyer, 1))) % max(selling_brands, 1)
            order_rows.append({
                "buyer_id": f"u{u}",
                "brand_id": f"br{brand_idx}",
                # Index the product globally, not by the buyer's order
                # number — otherwise every buyer's first order points at the
                # same listing and sell-through collapses to one product.
                "product_id": f"br{brand_idx}-p{n % max(listings_per_brand, 1)}",
                "gmv": gmv_per_order,
                "created_at": days_ago((n * 7) % max(window_days - 1, 1), now),
            })
            n += 1

    view_rows = [
        {"user_id": f"u{i % max(buyers, 1)}", "product_id": f"br0-p{i % 10}",
         "created_at": days_ago(i % max(window_days - 1, 1), now)}
        for i in range(len(order_rows) * views_per_order)
    ]

    user_rows = [
        {"id": f"u{i}", "created_at": days_ago(i % max(window_days - 1, 1), now),
         "role": "user"}
        for i in range(buyers)
    ]

    post_rows = [
        {"user_id": f"u{i % max(buyers, 1)}",
         "created_at": days_ago(i % max(window_days - 1, 1), now),
         "like_user_ids": [f"u{(i + 1) % max(buyers, 1)}"],
         "comment_count": 1, "brand_tag": "br0" if i % 2 == 0 else None}
        for i in range(posts)
    ]

    code_rows = [
        {"user_id": f"u{i}", "created_at": days_ago(window_days + 10, now)}
        for i in range(referral_codes)
    ]
    use_rows = [
        {"user_id": f"new{i}", "referrer_id": f"u{i % max(referral_codes, 1)}",
         "created_at": days_ago(i % max(window_days - 1, 1), now)}
        for i in range(referral_uses)
    ]

    wishlist_rows = []
    for i in range(wishlist_items):
        # The first `wishlist_converted` entries point at a product the same
        # buyer actually bought.
        if i < wishlist_converted and i < len(order_rows):
            o = order_rows[i]
            wishlist_rows.append({"user_id": o["buyer_id"],
                                  "product_id": o["product_id"],
                                  "created_at": days_ago(30, now)})
        else:
            wishlist_rows.append({"user_id": f"u{i % max(buyers, 1)}",
                                  "product_id": f"never-{i}",
                                  "created_at": days_ago(30, now)})

    return {
        "now": now,
        "window_days": window_days,
        "orders": order_rows,
        "views": view_rows,
        "listings": listing_rows,
        "brands": brand_rows,
        "users": user_rows,
        "referral_codes": code_rows,
        "referral_uses": use_rows,
        "posts": post_rows,
        "wishlist": wishlist_rows,
    }
