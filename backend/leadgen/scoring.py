"""Lead scoring, 1-100, against the UnveiledThreads fit criteria.

Weights sum to 100 and map one-to-one onto the criteria in the brief. Three
principles matter more than the exact numbers:

1. Unknown never scores like a positive, but it is not scored like a negative
   either. An unverified criterion earns roughly a third of its weight
   (`_unknown()`), so a brand we simply have not finished researching ranks
   below a verified-good brand and above a verified-bad one. Scoring unknown as
   zero would make the ranking a measure of our research effort rather than of
   brand fit.
2. Marketplace breadth scores *inversely*. A brand already on ten marketplaces
   is a poor prospect however good it looks.
3. A brand with no contact route is capped below HIGH regardless of fit — it is
   not yet actionable.
"""

from __future__ import annotations

from typing import Optional

from .models import Lead, Signals, is_found

WEIGHTS: dict[str, int] = {
    "instagram_presence": 15,   # professional, active account
    "follower_fit": 15,         # ~1k-100k is the sweet spot
    "ecommerce": 15,            # functioning own-site storefront
    "independence": 12,         # clearly positions as independent
    "release_cadence": 10,      # regularly drops new collections
    "marketplace_headroom": 10, # NOT already widely distributed
    "visual_branding": 8,       # strong, coherent visual identity
    "price_fit": 8,             # roughly £20-£200
    "contactability": 7,        # a published business contact route
}

HIGH_PRIORITY_MIN = 75
MEDIUM_PRIORITY_MIN = 55

PRIORITY_HIGH = "HIGH PRIORITY"
PRIORITY_MEDIUM = "MEDIUM PRIORITY"
PRIORITY_LOW = "LOW PRIORITY"


def _unknown(criterion: str) -> int:
    """Credit for an unverified criterion: one third of its weight."""
    return round(WEIGHTS[criterion] / 3)


def _instagram_presence(s: Signals) -> int:
    max_points = WEIGHTS["instagram_presence"]
    if s.instagram_professional is None and s.instagram_active is None:
        return _unknown("instagram_presence")
    points = 0
    if s.instagram_professional:
        points += 8
    if s.instagram_active:
        points += 7
    return min(points, max_points)


def _follower_fit(s: Signals) -> int:
    max_points = WEIGHTS["follower_fit"]
    n = s.follower_count
    if n is None:
        return _unknown("follower_fit")
    if 1_000 <= n <= 100_000:
        return max_points             # the target band
    if 100_000 < n <= 250_000:
        return 9                      # bigger than ideal, still approachable
    if 250_000 < n <= 750_000:
        return 5
    if n > 750_000:
        return 2                      # likely past needing a marketplace
    if 250 <= n < 1_000:
        return 7                      # early but real
    return 3                          # sub-250: too early to convert


def _ecommerce(s: Signals) -> int:
    if s.has_ecommerce is None:
        return _unknown("ecommerce")
    return WEIGHTS["ecommerce"] if s.has_ecommerce else 3


def _independence(s: Signals) -> int:
    if s.independent_positioning is None:
        return _unknown("independence")
    return WEIGHTS["independence"] if s.independent_positioning else 0


def _release_cadence(s: Signals) -> int:
    if s.releases_collections is None:
        return _unknown("release_cadence")
    return WEIGHTS["release_cadence"] if s.releases_collections else 2


def _marketplace_headroom(s: Signals) -> int:
    max_points = WEIGHTS["marketplace_headroom"]
    n = s.marketplace_count
    if n is None:
        return _unknown("marketplace_headroom")
    if n == 0:
        return max_points
    if n <= 2:
        return 7
    if n <= 5:
        return 4
    if n <= 11:
        return 1
    return 0


def _visual_branding(s: Signals) -> int:
    if s.strong_visual_branding is None:
        return _unknown("visual_branding")
    return WEIGHTS["visual_branding"] if s.strong_visual_branding else 2


def _price_fit(s: Signals) -> int:
    max_points = WEIGHTS["price_fit"]
    pr = s.price_range_gbp
    if not pr:
        return _unknown("price_fit")
    low, high = pr
    if low >= 20 and high <= 200:
        return max_points
    # Partial overlap with the £20-£200 band still counts for something.
    overlap = min(high, 200) - max(low, 20)
    if overlap <= 0:
        return 0
    return max(2, round(max_points * overlap / 180))


def _contactability(s: Signals) -> int:
    if s.has_public_contact is None:
        return _unknown("contactability")
    return WEIGHTS["contactability"] if s.has_public_contact else 0


_COMPONENTS = {
    "instagram_presence": _instagram_presence,
    "follower_fit": _follower_fit,
    "ecommerce": _ecommerce,
    "independence": _independence,
    "release_cadence": _release_cadence,
    "marketplace_headroom": _marketplace_headroom,
    "visual_branding": _visual_branding,
    "price_fit": _price_fit,
    "contactability": _contactability,
}


def score_breakdown(signals: Signals) -> dict[str, int]:
    return {name: fn(signals) for name, fn in _COMPONENTS.items()}


def priority_for(score: int) -> str:
    if score >= HIGH_PRIORITY_MIN:
        return PRIORITY_HIGH
    if score >= MEDIUM_PRIORITY_MIN:
        return PRIORITY_MEDIUM
    return PRIORITY_LOW


def score_lead(lead: Lead) -> Lead:
    """Compute and attach lead_score / priority / score_breakdown."""
    breakdown = score_breakdown(lead.signals)
    total = sum(breakdown.values())

    # A prospect we cannot contact at all is capped — it is not actionable
    # however attractive the brand looks.
    if not is_found(lead.contact_email) and not is_found(lead.contact_page):
        total = min(total, 69)

    lead.score_breakdown = breakdown
    lead.lead_score = max(1, min(100, total))
    lead.priority = priority_for(lead.lead_score)
    return lead


def score_all(leads: list[Lead]) -> list[Lead]:
    return [score_lead(l) for l in leads]


def rank(leads: list[Lead]) -> list[Lead]:
    """Highest score first; ties broken by brand name for stable output."""
    return sorted(leads, key=lambda l: (-(l.lead_score or 0), l.brand_name.lower()))


def summarise(leads: list[Lead]) -> dict[str, Optional[float]]:
    scored = [l for l in leads if l.lead_score is not None]
    if not scored:
        return {"count": 0, "average_score": None, "high": 0, "medium": 0, "low": 0}
    return {
        "count": len(scored),
        "average_score": round(sum(l.lead_score for l in scored) / len(scored), 1),
        "high": sum(1 for l in scored if l.priority == PRIORITY_HIGH),
        "medium": sum(1 for l in scored if l.priority == PRIORITY_MEDIUM),
        "low": sum(1 for l in scored if l.priority == PRIORITY_LOW),
    }
