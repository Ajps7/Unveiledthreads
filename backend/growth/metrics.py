"""Pure network-effects metric computation.

Everything in here is stdlib-only and takes plain Python data, so the
formulas can be unit-tested without a database, a web server, or a running
marketplace. `collector.py` is the only module that touches Mongo; it
normalises documents into the `raw` shape below and hands them here.

raw = {
  "now": datetime (tz-aware UTC),
  "window_days": int,
  "orders":   [{"buyer_id", "brand_id", "product_id", "gmv": float,
                "created_at": datetime}],            # completed sales only
  "views":    [{"user_id": str|None, "product_id", "created_at"}],
  "listings": [{"id", "brand_id", "created_at", "is_active": bool}],
  "brands":   [{"id", "name", "created_at", "market", "category"}],
  "users":    [{"id", "created_at", "role"}],
  "referral_codes": [{"user_id", "created_at"}],
  "referral_uses":  [{"user_id", "referrer_id", "created_at"}],
  "posts":    [{"user_id", "created_at", "like_user_ids": [str],
                "comment_count": int, "brand_tag": str|None}],
  "wishlist": [{"user_id", "product_id", "created_at"}],
  "cohort_months": int,   # optional, default 12 — cohort table horizon
}

Orders passed in are *all* completed orders ever, not just the window —
cohort retention and "first sale" need the full history. Window filtering
happens here so the same input can answer several questions.
"""

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Dict, Iterable, List, Optional, Sequence

from .benchmarks import OVERSUPPLY_LISTINGS_PER_BUYER

# ---------------------------------------------------------------------------
# Small numeric helpers
# ---------------------------------------------------------------------------


def safe_div(numerator: float, denominator: float) -> Optional[float]:
    """Divide, returning None rather than 0.0 when the denominator is empty.

    None means "we cannot know"; 0.0 means "we measured zero". Collapsing the
    two is how dashboards end up reporting a confident 0% conversion for a
    marketplace that simply had no traffic that week.
    """
    if not denominator:
        return None
    return numerator / denominator


def gini(values: Sequence[float]) -> Optional[float]:
    """Gini coefficient of a distribution. 0 = perfectly even, 1 = one winner."""
    vals = sorted(v for v in values if v is not None and v >= 0)
    n = len(vals)
    total = sum(vals)
    if n == 0 or total <= 0:
        return None
    if n == 1:
        return 0.0
    weighted = sum((i + 1) * v for i, v in enumerate(vals))
    return round((2 * weighted) / (n * total) - (n + 1) / n, 4)


def hhi(values: Sequence[float]) -> Optional[float]:
    """Herfindahl-Hirschman index on shares, expressed 0..1."""
    vals = [v for v in values if v is not None and v > 0]
    total = sum(vals)
    if not vals or total <= 0:
        return None
    return round(sum((v / total) ** 2 for v in vals), 4)


def top_n_share(values: Sequence[float], n: int = 3) -> Optional[float]:
    vals = sorted((v for v in values if v is not None and v > 0), reverse=True)
    total = sum(vals)
    if not vals or total <= 0:
        return None
    return round(sum(vals[:n]) / total, 4)


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _months_between(start: str, end: str) -> int:
    sy, sm = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    return (ey - sy) * 12 + (em - sm)


def _in_window(rows: Iterable[dict], start: datetime, end: datetime,
               field: str = "created_at") -> List[dict]:
    out = []
    for r in rows:
        ts = r.get(field)
        if ts is None:
            continue
        if start <= ts < end:
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# The metric set
# ---------------------------------------------------------------------------


def compute_metrics(raw: dict) -> dict:
    """Compute every network-effect metric the diagnostic layer needs.

    Returns a JSON-serialisable dict with three top-level sections:
      metrics  — the headline numbers (None where unknowable)
      detail   — supporting breakdowns for the UI (series, tables)
      coverage — which inputs were empty, so nothing is graded on no data
    """
    now: datetime = raw.get("now") or datetime.now(timezone.utc)
    window_days: int = int(raw.get("window_days") or 90)
    start = now - timedelta(days=window_days)
    prior_start = start - timedelta(days=window_days)

    all_orders: List[dict] = list(raw.get("orders") or [])
    views: List[dict] = list(raw.get("views") or [])
    listings: List[dict] = list(raw.get("listings") or [])
    brands: List[dict] = list(raw.get("brands") or [])
    users: List[dict] = list(raw.get("users") or [])
    codes: List[dict] = list(raw.get("referral_codes") or [])
    uses: List[dict] = list(raw.get("referral_uses") or [])
    posts: List[dict] = list(raw.get("posts") or [])
    wishlist: List[dict] = list(raw.get("wishlist") or [])

    orders = _in_window(all_orders, start, now)
    prior_orders = _in_window(all_orders, prior_start, start)
    views_win = _in_window(views, start, now)

    brand_by_id = {b["id"]: b for b in brands}

    # ---- Transaction basics -------------------------------------------------
    gmv = round(sum(float(o.get("gmv") or 0) for o in orders), 2)
    order_count = len(orders)
    aov = safe_div(gmv, order_count)

    buyer_orders: Dict[str, int] = {}
    buyer_brands: Dict[str, set] = {}
    brand_gmv: Dict[str, float] = {}
    for o in orders:
        bid = o.get("buyer_id")
        if bid and bid != "deleted-user":
            buyer_orders[bid] = buyer_orders.get(bid, 0) + 1
            buyer_brands.setdefault(bid, set()).add(o.get("brand_id"))
        br = o.get("brand_id")
        if br:
            brand_gmv[br] = brand_gmv.get(br, 0.0) + float(o.get("gmv") or 0)

    active_buyers = len(buyer_orders)
    selling_brands = len(brand_gmv)

    repeat_buyers = sum(1 for c in buyer_orders.values() if c >= 2)
    repeat_buyer_rate = safe_div(repeat_buyers, active_buyers)

    # Multi-brand rate is measured against repeat buyers only: a buyer with a
    # single order *cannot* have bought from two brands, so including them
    # would make the metric a restatement of the repeat rate.
    multi_brand = sum(
        1 for b, c in buyer_orders.items() if c >= 2 and len(buyer_brands.get(b, ())) >= 2
    )
    multi_brand_buyer_rate = safe_div(multi_brand, repeat_buyers)
    avg_brands_per_repeat_buyer = safe_div(
        sum(len(buyer_brands[b]) for b in buyer_brands if buyer_orders[b] >= 2),
        repeat_buyers,
    )

    # ---- Concentration ------------------------------------------------------
    gmv_values = list(brand_gmv.values())
    gmv_hhi = hhi(gmv_values)
    gmv_gini = gini(gmv_values)
    top3_share = top_n_share(gmv_values, 3)

    # ---- Supply-side liquidity ---------------------------------------------
    # Denominator: listings that were available to be bought during the window
    # (created before the window ended). A listing created yesterday has not
    # had a fair chance to sell, so listings younger than the shorter of 14
    # days or a third of the window are excluded from the denominator.
    maturity_days = min(14, max(1, window_days // 3))
    maturity_cutoff = now - timedelta(days=maturity_days)
    eligible_listings = [
        l for l in listings
        if l.get("created_at") is not None and l["created_at"] <= maturity_cutoff
    ]
    sold_listing_ids = {o.get("product_id") for o in orders if o.get("product_id")}
    sold_eligible = sum(1 for l in eligible_listings if l["id"] in sold_listing_ids)
    sell_through_rate = safe_div(sold_eligible, len(eligible_listings))

    live_listings = sum(1 for l in listings if l.get("is_active"))
    listings_per_active_buyer = safe_div(live_listings, active_buyers)

    # ---- Demand-side liquidity ---------------------------------------------
    view_to_order_rate = safe_div(order_count, len(views_win))

    viewers = {v["user_id"] for v in views_win if v.get("user_id")}
    signed_in_viewer_conversion = safe_div(
        len(viewers & set(buyer_orders.keys())), len(viewers)
    )

    # ---- Supply activation --------------------------------------------------
    first_sale_at: Dict[str, datetime] = {}
    for o in sorted(all_orders, key=lambda x: x.get("created_at") or now):
        br = o.get("brand_id")
        if br and br not in first_sale_at and o.get("created_at"):
            first_sale_at[br] = o["created_at"]

    # Only judge brands that have had a fair chance: onboarded at least
    # `maturity_days` ago.
    mature_brands = [
        b for b in brands
        if b.get("created_at") is not None and b["created_at"] <= maturity_cutoff
    ]
    activated = [b for b in mature_brands if b["id"] in first_sale_at]
    brand_activation_rate = safe_div(len(activated), len(mature_brands))

    ttfs = [
        (first_sale_at[b["id"]] - b["created_at"]).total_seconds() / 86400.0
        for b in activated
    ]
    days_to_first_sale = round(median(ttfs), 1) if ttfs else None

    # Brands that listed but have never sold — the quiet churn risk.
    listing_brand_ids = {l.get("brand_id") for l in listings}
    stalled_brands = [
        {
            "id": b["id"],
            "name": b.get("name"),
            "days_since_join": round((now - b["created_at"]).total_seconds() / 86400.0),
            "has_listings": b["id"] in listing_brand_ids,
        }
        for b in mature_brands if b["id"] not in first_sale_at
    ]
    stalled_brands.sort(key=lambda x: x["days_since_join"], reverse=True)

    # ---- Referral loop ------------------------------------------------------
    # Observed K: successful referred signups in the window per user who held
    # a referral code at the start of it. This is the *realised* K, which is
    # what matters — the theoretical one is a pitch-deck number.
    code_holders_at_start = sum(
        1 for c in codes if c.get("created_at") and c["created_at"] < start
    )
    referred_in_window = _in_window(uses, start, now)
    k_factor = safe_div(len(referred_in_window), code_holders_at_start)

    new_users_in_window = _in_window(users, start, now)
    referral_share_of_new_users = safe_div(
        len(referred_in_window), len(new_users_in_window)
    )

    cycle_times = []
    code_created_by_user = {c["user_id"]: c["created_at"] for c in codes if c.get("user_id")}
    for u in referred_in_window:
        ref_at = code_created_by_user.get(u.get("referrer_id"))
        if ref_at and u.get("created_at"):
            cycle_times.append((u["created_at"] - ref_at).total_seconds() / 86400.0)
    referral_cycle_days = round(median(cycle_times), 1) if cycle_times else None

    # ---- Community loop -----------------------------------------------------
    posts_win = _in_window(posts, start, now)
    engaged_users = set()
    total_likes = 0
    total_comments = 0
    tagged_posts = 0
    for p in posts_win:
        if p.get("user_id"):
            engaged_users.add(p["user_id"])
        likes = p.get("like_user_ids") or []
        total_likes += len(likes)
        engaged_users.update(likes)
        total_comments += int(p.get("comment_count") or 0)
        if p.get("brand_tag"):
            tagged_posts += 1

    # "Active users" for the participation denominator = anyone who bought or
    # viewed while signed in during the window. Using total registered users
    # would flatter or crush the number depending only on list decay.
    active_user_ids = set(buyer_orders.keys()) | viewers
    community_participation_rate = safe_div(len(engaged_users), len(active_user_ids))
    engagement_per_post = safe_div(total_likes + total_comments, len(posts_win))
    brand_tag_rate = safe_div(tagged_posts, len(posts_win))

    # ---- Wishlist → purchase ------------------------------------------------
    purchased_pairs = {
        (o.get("buyer_id"), o.get("product_id")) for o in all_orders
    }
    wishlist_win = _in_window(wishlist, start, now)
    wishlist_converted = sum(
        1 for w in wishlist_win
        if (w.get("user_id"), w.get("product_id")) in purchased_pairs
    )
    wishlist_conversion_rate = safe_div(wishlist_converted, len(wishlist_win))

    # ---- Atomic network cell ------------------------------------------------
    atomic = _atomic_cell(orders, brand_by_id)

    # ---- Growth deltas ------------------------------------------------------
    prior_gmv = sum(float(o.get("gmv") or 0) for o in prior_orders)
    prior_buyers = len({o.get("buyer_id") for o in prior_orders if o.get("buyer_id")})
    gmv_growth = safe_div(gmv - prior_gmv, prior_gmv)
    buyer_growth = safe_div(active_buyers - prior_buyers, prior_buyers)

    metrics = {
        "gmv": gmv,
        "orders": order_count,
        "aov": round(aov, 2) if aov is not None else None,
        "active_buyers": active_buyers,
        "selling_brands": selling_brands,
        "live_listings": live_listings,
        "sell_through_rate": _r(sell_through_rate),
        "view_to_order_rate": _r(view_to_order_rate, 5),
        "signed_in_viewer_conversion": _r(signed_in_viewer_conversion),
        "listings_per_active_buyer": _r(listings_per_active_buyer, 2),
        "repeat_buyer_rate": _r(repeat_buyer_rate),
        "multi_brand_buyer_rate": _r(multi_brand_buyer_rate),
        "avg_brands_per_repeat_buyer": _r(avg_brands_per_repeat_buyer, 2),
        "gmv_hhi": gmv_hhi,
        "gmv_gini": gmv_gini,
        "top3_gmv_share": top3_share,
        "brand_activation_rate": _r(brand_activation_rate),
        "days_to_first_sale": days_to_first_sale,
        "k_factor": _r(k_factor, 4),
        "referral_share_of_new_users": _r(referral_share_of_new_users),
        "referral_cycle_days": referral_cycle_days,
        "community_participation_rate": _r(community_participation_rate),
        "engagement_per_post": _r(engagement_per_post, 2),
        "brand_tag_rate": _r(brand_tag_rate),
        "wishlist_conversion_rate": _r(wishlist_conversion_rate),
        # Deliberately unknowable from the current schema — see coverage below.
        "organic_share_of_new_buyers": None,
        "gmv_growth": _r(gmv_growth),
        "buyer_growth": _r(buyer_growth),
        "oversupplied": bool(
            listings_per_active_buyer is not None
            and listings_per_active_buyer > OVERSUPPLY_LISTINGS_PER_BUYER
        ),
    }

    detail = {
        "window": {
            "days": window_days,
            "start": start.isoformat(),
            "end": now.isoformat(),
            "listing_maturity_days": maturity_days,
        },
        "weekly": _weekly_series(orders, new_users_in_window, start, now),
        "cohorts": cohort_retention(
            all_orders, months=int(raw.get("cohort_months") or 12), now=now
        ),
        "top_brands": _top_brands(brand_gmv, brand_by_id, orders),
        "atomic_cell": atomic,
        "stalled_brands": stalled_brands[:10],
        "stalled_brand_count": len(stalled_brands),
        "prior_window": {"gmv": round(prior_gmv, 2), "active_buyers": prior_buyers},
    }

    coverage = {
        "orders": len(all_orders),
        "orders_in_window": order_count,
        "views_in_window": len(views_win),
        "listings": len(listings),
        "brands": len(brands),
        "referral_codes": len(codes),
        "referral_uses": len(uses),
        "posts_in_window": len(posts_win),
        "wishlist_in_window": len(wishlist_win),
        "gaps": _coverage_gaps(
            order_count, len(views_win), len(codes), len(posts_win), len(wishlist_win)
        ),
    }

    return {"metrics": metrics, "detail": detail, "coverage": coverage}


def _r(value: Optional[float], places: int = 4) -> Optional[float]:
    return None if value is None else round(value, places)


def _coverage_gaps(orders: int, views: int, codes: int, posts: int,
                   wishes: int) -> List[dict]:
    """Name what the data cannot answer, so nothing is graded on a vacuum."""
    gaps: List[dict] = []
    gaps.append({
        "key": "acquisition_attribution",
        "severity": "high",
        "what": "No acquisition-channel attribution is captured anywhere in "
                "the schema.",
        "consequence": "Organic vs paid share, blended CAC and channel-level "
                       "LTV cannot be computed, so paid spend cannot be "
                       "judged. This is the highest-value instrumentation "
                       "gap in the product.",
    })
    if orders < 30:
        gaps.append({
            "key": "thin_orders",
            "severity": "high",
            "what": f"Only {orders} completed orders in the window.",
            "consequence": "Every rate below is a small-sample estimate. "
                           "Treat the direction as signal and the decimal "
                           "places as noise.",
        })
    if views == 0:
        gaps.append({
            "key": "no_views",
            "severity": "medium",
            "what": "No product views were tracked in the window.",
            "consequence": "Demand-side liquidity (view → order) cannot be "
                           "measured. Check that the view-tracking call "
                           "fires on the product page.",
        })
    if codes == 0:
        gaps.append({
            "key": "referrals_off",
            "severity": "medium",
            "what": "No referral codes exist — the programme is gated off.",
            "consequence": "K-factor is unmeasurable, so the cheapest "
                           "acquisition loop is both unbuilt and invisible.",
        })
    if posts == 0:
        gaps.append({
            "key": "no_community",
            "severity": "low",
            "what": "No community posts in the window.",
            "consequence": "The content loop contributes nothing to "
                           "retention or supply discovery right now.",
        })
    if wishes == 0:
        gaps.append({
            "key": "no_wishlist",
            "severity": "low",
            "what": "No wishlist activity in the window.",
            "consequence": "Declared purchase intent — the cheapest "
                           "re-engagement trigger available — is unused.",
        })
    return gaps


def _atomic_cell(orders: List[dict], brand_by_id: Dict[str, dict]) -> dict:
    """Find the densest category × market cell — the candidate atomic network.

    Cold-start theory: a marketplace does not need liquidity everywhere, it
    needs it *somewhere*, in a cell small enough to saturate. This finds the
    cell that is already closest to working.
    """
    cells: Dict[tuple, dict] = {}
    for o in orders:
        b = brand_by_id.get(o.get("brand_id"))
        if not b:
            continue
        key = (b.get("category") or "uncategorised", b.get("market") or "unknown")
        cell = cells.setdefault(key, {"orders": 0, "gmv": 0.0, "brands": set(),
                                      "buyers": set()})
        cell["orders"] += 1
        cell["gmv"] += float(o.get("gmv") or 0)
        cell["brands"].add(o.get("brand_id"))
        if o.get("buyer_id"):
            cell["buyers"].add(o["buyer_id"])

    if not cells:
        return {"found": False, "cells": []}

    ranked = sorted(
        (
            {
                "category": k[0],
                "market": k[1],
                "orders": v["orders"],
                "gmv": round(v["gmv"], 2),
                "brands": len(v["brands"]),
                "buyers": len(v["buyers"]),
                # Density = repeat transactions per participant. A cell where
                # each buyer bought once from each brand is not yet a network.
                "density": round(v["orders"] / max(len(v["buyers"]), 1), 2),
            }
            for k, v in cells.items()
        ),
        key=lambda c: (c["orders"], c["gmv"]),
        reverse=True,
    )
    top = ranked[0]
    return {
        "found": True,
        "top": top,
        "cells": ranked[:8],
        "concentration": round(top["orders"] / max(sum(c["orders"] for c in ranked), 1), 4),
    }


def _top_brands(brand_gmv: Dict[str, float], brand_by_id: Dict[str, dict],
                orders: List[dict]) -> List[dict]:
    counts: Dict[str, int] = {}
    buyers: Dict[str, set] = {}
    for o in orders:
        br = o.get("brand_id")
        if not br:
            continue
        counts[br] = counts.get(br, 0) + 1
        if o.get("buyer_id"):
            buyers.setdefault(br, set()).add(o["buyer_id"])
    total = sum(brand_gmv.values()) or 1.0
    rows = [
        {
            "brand_id": bid,
            "name": (brand_by_id.get(bid) or {}).get("name") or "Unknown",
            "gmv": round(v, 2),
            "orders": counts.get(bid, 0),
            "buyers": len(buyers.get(bid, ())),
            "gmv_share": round(v / total, 4),
        }
        for bid, v in brand_gmv.items()
    ]
    rows.sort(key=lambda r: r["gmv"], reverse=True)
    return rows[:10]


def _weekly_series(orders: List[dict], new_users: List[dict],
                   start: datetime, now: datetime) -> List[dict]:
    buckets: Dict[str, dict] = {}
    cursor = start
    while cursor < now:
        buckets[cursor.strftime("%Y-%m-%d")] = {
            "week": cursor.strftime("%Y-%m-%d"), "gmv": 0.0, "orders": 0,
            "buyers": set(), "new_users": 0,
        }
        cursor += timedelta(days=7)
    keys = sorted(buckets.keys())

    def _bucket_for(ts: datetime) -> Optional[dict]:
        idx = int((ts - start).total_seconds() // (7 * 86400))
        if 0 <= idx < len(keys):
            return buckets[keys[idx]]
        return None

    for o in orders:
        b = _bucket_for(o["created_at"])
        if b is not None:
            b["gmv"] += float(o.get("gmv") or 0)
            b["orders"] += 1
            if o.get("buyer_id"):
                b["buyers"].add(o["buyer_id"])
    for u in new_users:
        b = _bucket_for(u["created_at"])
        if b is not None:
            b["new_users"] += 1

    return [
        {
            "week": buckets[k]["week"],
            "gmv": round(buckets[k]["gmv"], 2),
            "orders": buckets[k]["orders"],
            "buyers": len(buckets[k]["buyers"]),
            "new_users": buckets[k]["new_users"],
        }
        for k in keys
    ]


def cohort_retention(all_orders: List[dict], months: int = 6,
                     now: Optional[datetime] = None) -> dict:
    """Monthly buyer cohorts by first purchase, with repeat-purchase retention.

    Row = the month a buyer first bought. Column = months since. The value is
    the share of that cohort who placed at least one order in that later
    month. Month 0 is always 100% by construction and is omitted.
    """
    now = now or datetime.now(timezone.utc)
    first_order: Dict[str, datetime] = {}
    activity: Dict[str, set] = {}
    for o in sorted(all_orders, key=lambda x: x.get("created_at") or now):
        buyer = o.get("buyer_id")
        ts = o.get("created_at")
        if not buyer or buyer == "deleted-user" or ts is None:
            continue
        first_order.setdefault(buyer, ts)
        activity.setdefault(buyer, set()).add(_month_key(ts))

    if not first_order:
        return {"months": [], "rows": []}

    cutoff = _month_key(now - timedelta(days=31 * months))
    cohorts: Dict[str, List[str]] = {}
    for buyer, ts in first_order.items():
        mk = _month_key(ts)
        if mk >= cutoff:
            cohorts.setdefault(mk, []).append(buyer)

    now_month = _month_key(now)
    rows = []
    max_offset = 0
    for mk in sorted(cohorts.keys()):
        buyers = cohorts[mk]
        span = _months_between(mk, now_month)
        max_offset = max(max_offset, span)
        values = []
        for offset in range(1, span + 1):
            target = _shift_month(mk, offset)
            retained = sum(1 for b in buyers if target in activity.get(b, ()))
            values.append({
                "offset": offset,
                "retained": retained,
                "rate": round(retained / len(buyers), 4),
            })
        rows.append({"cohort": mk, "size": len(buyers), "values": values})

    return {"months": list(range(1, max_offset + 1)), "rows": rows}


def _shift_month(month_key: str, offset: int) -> str:
    y, m = (int(x) for x in month_key.split("-"))
    total = (y * 12 + (m - 1)) + offset
    return f"{total // 12:04d}-{total % 12 + 1:02d}"
