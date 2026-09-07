"""Benchmark bands and stage gates for the Network Effects Command Center.

These are the numbers a marketplace CMO carries in their head. They are
*heuristics*, not laws — public marketplace benchmarks vary wildly by
category, basket size and geography. Every band below is therefore stated
with the reasoning behind it so an operator can argue with it, and every
one is overridable via environment variables at the route layer.

Where a band came from:
  - Sell-through / liquidity bands follow the resale-marketplace convention
    that a listing which does not sell in ~90 days is functionally dead
    inventory, and that healthy peer-to-peer fashion marketplaces clear
    roughly a quarter to a half of live listings per quarter.
  - The multi-brand ("cross-side density") band encodes the structural test
    for whether a marketplace has a network effect at all: if buyers only
    ever transact with one seller, the marketplace is a directory with a
    payment button, and both sides can disintermediate it at will.
  - K-factor bands follow the standard viral-loop reading: K >= 1.0 is
    self-sustaining growth (rare and usually temporary), 0.3-1.0 is a
    meaningful accelerant on paid, below 0.15 is noise.
  - HHI bands are the competition-authority convention (0.15 / 0.25) applied
    to GMV share across sellers rather than firms in a market.
"""

from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Metric bands
# ---------------------------------------------------------------------------
# Each band is (weak_below, healthy_at_or_above). A value between the two is
# "developing". `higher_is_better=False` inverts the reading.

BANDS: Dict[str, dict] = {
    "sell_through_rate": {
        "weak": 0.15, "healthy": 0.35, "higher_is_better": True,
        "label": "Sell-through rate",
        "unit": "pct",
        "why": "Share of live listings that sold in the window. Below ~15% "
               "sellers conclude the marketplace does not work and churn; "
               "supply churn is the single most common marketplace death.",
    },
    "view_to_order_rate": {
        "weak": 0.008, "healthy": 0.02, "higher_is_better": True,
        "label": "View → order conversion",
        "unit": "pct",
        "why": "Demand-side liquidity. Low conversion with healthy traffic is "
               "a discovery/trust problem, not a traffic problem.",
    },
    "listings_per_active_buyer": {
        "weak": 1.5, "healthy": 6.0, "higher_is_better": True,
        "label": "Live listings per active buyer",
        "unit": "ratio",
        "why": "Choice depth. Calibrated for a CURATED marketplace of "
               "independent brands, not for peer-to-peer resale — a C2C site "
               "where every user also lists carries ten times this ratio, and "
               "borrowing its benchmark would make a healthy curated "
               "catalogue look empty. Too few and buyers leave empty-handed; "
               "past the oversupply ceiling, listings rot unseen and sellers "
               "churn.",
    },
    "multi_brand_buyer_rate": {
        "weak": 0.20, "healthy": 0.45, "higher_is_better": True,
        "label": "Multi-brand buyer rate",
        "unit": "pct",
        "why": "Of buyers who bought more than once, the share who bought "
               "from more than one brand. THE test for a real network "
               "effect: single-brand buyers belong to the brand, not to you.",
    },
    "repeat_buyer_rate": {
        "weak": 0.12, "healthy": 0.30, "higher_is_better": True,
        "label": "Repeat buyer rate",
        "unit": "pct",
        "why": "Retention is the multiplier on every acquisition pound. "
               "Scaling spend under a leaky bucket burns cash faster.",
    },
    "gmv_hhi": {
        "weak": 0.25, "healthy": 0.15, "higher_is_better": False,
        "label": "GMV concentration (HHI)",
        "unit": "index",
        "why": "Herfindahl index of GMV share across brands. Above 0.25 the "
               "marketplace's numbers are one brand's numbers, and that "
               "brand can leave.",
    },
    "k_factor": {
        "weak": 0.15, "healthy": 0.30, "higher_is_better": True,
        "label": "K-factor (referral)",
        "unit": "ratio",
        "why": "Invites per user × invite conversion. Below 0.15 word of "
               "mouth is not a channel; above 0.3 it meaningfully lowers "
               "blended CAC.",
    },
    "brand_activation_rate": {
        "weak": 0.40, "healthy": 0.70, "higher_is_better": True,
        "label": "Brand activation rate",
        "unit": "pct",
        "why": "Share of approved brands that ever made a sale. Unactivated "
               "supply is the quietest, most expensive churn there is.",
    },
    "days_to_first_sale": {
        "weak": 30.0, "healthy": 14.0, "higher_is_better": False,
        "label": "Median days to a brand's first sale",
        "unit": "days",
        "why": "Supply time-to-value. Every week a new brand waits raises "
               "the odds it never lists again.",
    },
    "community_participation_rate": {
        "weak": 0.03, "healthy": 0.10, "higher_is_better": True,
        "label": "Community participation rate",
        "unit": "pct",
        "why": "Share of active users who posted, liked or commented. The "
               "content loop is the cheapest retention mechanism a "
               "marketplace has, and the only one that also creates supply.",
    },
    "wishlist_conversion_rate": {
        "weak": 0.05, "healthy": 0.15, "higher_is_better": True,
        "label": "Wishlist → purchase rate",
        "unit": "pct",
        "why": "Declared intent that never converts is the cheapest revenue "
               "in the business going unclaimed.",
    },
    "organic_share_of_new_buyers": {
        "weak": 0.30, "healthy": 0.60, "higher_is_better": True,
        "label": "Organic share of new buyers",
        "unit": "pct",
        "why": "Escape velocity indicator. A marketplace whose growth stops "
               "when spend stops has not built a network.",
    },
}

# Secondary bands: metrics that feed a loop score but are not headline
# scorecard numbers in their own right. Kept separate so the scorecard stays
# short — an operator can hold about a dozen numbers in their head, not thirty.
SECONDARY_BANDS: Dict[str, dict] = {
    "engagement_per_post": {
        "weak": 1.0, "healthy": 5.0, "higher_is_better": True,
        "label": "Engagement per post", "unit": "ratio",
        "why": "Likes plus comments per post. A feed nobody reacts to is "
               "publishing, not community.",
    },
    "referral_share_of_new_users": {
        "weak": 0.05, "healthy": 0.20, "higher_is_better": True,
        "label": "Referred share of new users", "unit": "pct",
        "why": "What proportion of new signups arrived through someone "
               "else's code. K measures the loop's rate; this measures "
               "whether it is yet material to growth.",
    },
    "brand_tag_rate": {
        "weak": 0.15, "healthy": 0.40, "higher_is_better": True,
        "label": "Posts tagged to a brand", "unit": "pct",
        "why": "Tagged posts are the only community content that also does "
               "cross-brand discovery work.",
    },
}


def lookup_band(metric_key: str) -> Optional[dict]:
    """Band for a metric, headline or secondary."""
    return BANDS.get(metric_key) or SECONDARY_BANDS.get(metric_key)


# Beyond this many listings per active buyer, adding supply stops helping and
# starts hurting: listings go unseen, sellers see zero sales and churn.
OVERSUPPLY_LISTINGS_PER_BUYER = 40.0

# ---------------------------------------------------------------------------
# Stage gates — the sequencing rule
# ---------------------------------------------------------------------------
# A veteran operator's real contribution is refusing to work on stage N+1
# before stage N clears. Each gate lists the metrics that must be healthy
# before the next stage is worth funding.

STAGE_GATES: List[dict] = [
    {
        "key": "atomic_network",
        "name": "Atomic network",
        "goal": "Make one narrow slice of the market dense enough to work "
                "reliably — one category, one city, one scene.",
        "gates": [
            ("atomic_cell_brands", 5, "brands in the densest category cell"),
            ("atomic_cell_orders", 20, "orders in that same cell in the window"),
        ],
        "focus": "Concentrate every scrap of supply and demand into a single "
                 "cell. Breadth is the enemy here.",
        "stop": "Stop recruiting brands outside the densest cell, and stop "
                "spending on broad reach.",
    },
    {
        "key": "liquidity",
        "name": "Liquidity",
        "goal": "A listing reliably sells and a visit reliably ends in a "
                "purchase.",
        "gates": [
            ("sell_through_rate", BANDS["sell_through_rate"]["weak"], "sell-through"),
            ("view_to_order_rate", BANDS["view_to_order_rate"]["weak"], "view → order"),
        ],
        "focus": "Match-making: search, sizing, price guidance, and killing "
                 "listings that will never sell.",
        "stop": "Stop buying traffic. Traffic poured into an illiquid "
                "marketplace churns both sides at once.",
    },
    {
        "key": "retention",
        "name": "Retention",
        "goal": "Buyers come back without being paid for twice.",
        "gates": [
            ("repeat_buyer_rate", BANDS["repeat_buyer_rate"]["weak"], "repeat rate"),
        ],
        "focus": "Second-purchase mechanics: post-delivery follow-up, "
                 "wishlist restock alerts, saved sizes.",
        "stop": "Stop widening the top of the funnel until the second "
                "purchase is a habit.",
    },
    {
        "key": "density",
        "name": "Network density",
        "goal": "Buyers cross between brands, so the marketplace — not any "
                "one seller — owns the relationship.",
        "gates": [
            ("multi_brand_buyer_rate", BANDS["multi_brand_buyer_rate"]["weak"],
             "multi-brand buyers"),
        ],
        "focus": "Cross-brand discovery: 'others also bought', mixed-brand "
                 "edits, category browse over brand browse.",
        "stop": "Stop giving individual brands standalone storefront "
                "treatment that trains buyers to shop one brand only.",
    },
    {
        "key": "scale",
        "name": "Scale",
        "goal": "Pour fuel on a loop that already compounds.",
        "gates": [
            ("k_factor", BANDS["k_factor"]["weak"], "K-factor"),
            ("organic_share_of_new_buyers",
             BANDS["organic_share_of_new_buyers"]["weak"], "organic share"),
        ],
        "focus": "Paid acquisition against a proven LTV, referral programme "
                 "live, brand and PR.",
        "stop": "Nothing — this is the stage where spending is correct.",
    },
]


def rate(metric_key: str, value) -> str:
    """Grade a metric value against its band.

    Returns one of "weak", "developing", "healthy", or "unknown" when there
    is no value or no band for the key.
    """
    band = lookup_band(metric_key)
    if band is None or value is None:
        return "unknown"
    weak, healthy = band["weak"], band["healthy"]
    if band["higher_is_better"]:
        if value < weak:
            return "weak"
        return "healthy" if value >= healthy else "developing"
    # Lower is better (HHI, days-to-first-sale).
    if value > weak:
        return "weak"
    return "healthy" if value <= healthy else "developing"


def band_for(metric_key: str) -> Tuple[float, float]:
    band = BANDS[metric_key]
    return band["weak"], band["healthy"]
