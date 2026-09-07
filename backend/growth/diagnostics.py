"""The judgment layer: loop scoring, named failure modes, and sequencing.

Metrics are not advice. This module turns the numbers into the three things
an operator actually needs from a CMO:

  1. Which of the growth loops is broken, and what the failure is *called*.
  2. Which stage the business is at, and therefore which single loop is worth
     working on now — plus, just as important, what to stop doing.
  3. How much to trust any of it, given how thin the data is.

Pure functions, stdlib only.
"""

from typing import Dict, List, Optional

from .benchmarks import (
    BANDS, OVERSUPPLY_LISTINGS_PER_BUYER, STAGE_GATES, lookup_band, rate,
)

# ---------------------------------------------------------------------------
# Loop definitions
# ---------------------------------------------------------------------------
# Weights are the share each metric carries in its loop's score. They encode
# a point of view: for the density loop, whether buyers cross brands matters
# more than how concentrated GMV is, because concentration is a symptom and
# crossing is the cause.

LOOPS: List[dict] = [
    {
        "key": "supply",
        "name": "Supply loop",
        "question": "Do brands that join go on to sell, fast enough to stay?",
        "mechanism": "Brand joins → lists → sells → earns → lists more → "
                     "tells other brands. Break any link and supply decays "
                     "silently, because unhappy sellers do not complain, "
                     "they just stop listing.",
        "metrics": [
            ("brand_activation_rate", 0.40),
            ("sell_through_rate", 0.40),
            ("days_to_first_sale", 0.20),
        ],
    },
    {
        "key": "demand",
        "name": "Demand loop",
        "question": "Does a visit reliably become a purchase?",
        "mechanism": "Buyer arrives → finds something in their size and taste "
                     "→ trusts the seller enough to pay. Conversion is a "
                     "match-making problem long before it is a traffic one.",
        "metrics": [
            ("view_to_order_rate", 0.45),
            ("listings_per_active_buyer", 0.30),
            ("wishlist_conversion_rate", 0.25),
        ],
    },
    {
        "key": "retention",
        "name": "Retention loop",
        "question": "Do buyers come back without being paid for twice?",
        "mechanism": "Good first order → remembered → returns unprompted. "
                     "Retention is the multiplier on every acquisition pound "
                     "you will ever spend; it is not a lifecycle-email "
                     "programme.",
        "metrics": [
            ("repeat_buyer_rate", 0.70),
            ("wishlist_conversion_rate", 0.30),
        ],
    },
    {
        "key": "density",
        "name": "Network density loop",
        "question": "Do buyers cross between brands — or is this a set of "
                    "separate shops sharing a checkout?",
        "mechanism": "Buyer discovers brand B while shopping brand A → the "
                     "marketplace, not the brand, owns the relationship → "
                     "each new brand raises the value of every buyer, and "
                     "vice versa. This is the network effect itself. Every "
                     "other loop is a feeder into it.",
        "metrics": [
            ("multi_brand_buyer_rate", 0.55),
            ("gmv_hhi", 0.25),
            ("brand_activation_rate", 0.20),
        ],
    },
    {
        "key": "referral",
        "name": "Referral loop",
        "question": "Does the marketplace grow itself?",
        "mechanism": "Buyer has a good experience → invites → invitee buys → "
                     "invites. Compounds only when retention already works; "
                     "a referral programme layered on a leaky bucket buys "
                     "churn at a discount.",
        "metrics": [
            ("k_factor", 0.60),
            ("referral_share_of_new_users", 0.40),
        ],
    },
    {
        "key": "content",
        "name": "Content / community loop",
        "question": "Does the community create reasons to return between "
                    "purchases?",
        "mechanism": "Post → seen → engaged with → poster returns and the "
                     "viewer discovers a brand. The only retention mechanism "
                     "that also generates supply-side discovery, and the "
                     "cheapest one a marketplace owns.",
        "metrics": [
            ("community_participation_rate", 0.50),
            ("engagement_per_post", 0.20),
            ("brand_tag_rate", 0.30),
        ],
    },
]

def score_metric(metric_key: str, value: Optional[float]) -> Optional[float]:
    """Map a raw metric onto 0-100 against its band.

    The scale is deliberately non-linear: hitting the "weak" threshold scores
    40, hitting "healthy" scores 80, and everything above that earns a
    tapering bonus up to 100. Being twice as good as healthy is worth a lot
    less than getting off the floor.
    """
    if value is None:
        return None
    band = lookup_band(metric_key)
    if band is None:
        return None
    weak = float(band["weak"])
    healthy = float(band["healthy"])

    if band["higher_is_better"]:
        if value <= 0:
            return 0.0
        if value < weak:
            return round(40.0 * (value / weak), 1)
        if value < healthy:
            return round(40.0 + 40.0 * (value - weak) / (healthy - weak), 1)
        overshoot = min(1.0, (value - healthy) / max(healthy, 1e-9))
        return round(min(100.0, 80.0 + 20.0 * overshoot), 1)

    # Lower is better: `healthy` is the good ceiling, `weak` the bad floor.
    if value <= healthy:
        headroom = min(1.0, (healthy - value) / max(healthy, 1e-9))
        return round(min(100.0, 80.0 + 20.0 * headroom), 1)
    if value <= weak:
        return round(40.0 + 40.0 * (weak - value) / max(weak - healthy, 1e-9), 1)
    decay = min(1.0, (value - weak) / max(weak, 1e-9))
    return round(max(0.0, 40.0 * (1.0 - decay)), 1)


def _status_from_score(score: Optional[float]) -> str:
    if score is None:
        return "unknown"
    if score < 30:
        return "broken"
    if score < 55:
        return "leaking"
    if score < 80:
        return "working"
    return "compounding"


def score_loop(loop: dict, metrics: dict) -> dict:
    parts = []
    weighted_total = 0.0
    weight_used = 0.0
    for metric_key, weight in loop["metrics"]:
        value = metrics.get(metric_key)
        s = score_metric(metric_key, value)
        band = lookup_band(metric_key) or {}
        parts.append({
            "key": metric_key,
            "label": band.get("label", metric_key.replace("_", " ").capitalize()),
            "value": value,
            "unit": band.get("unit", "ratio"),
            "score": s,
            "rating": rate(metric_key, value),
            "weak": band.get("weak"),
            "healthy": band.get("healthy"),
            "higher_is_better": band.get("higher_is_better", True),
            "why": band.get("why"),
        })
        if s is not None:
            weighted_total += s * weight
            weight_used += weight

    score = round(weighted_total / weight_used, 1) if weight_used else None
    return {
        "key": loop["key"],
        "name": loop["name"],
        "question": loop["question"],
        "mechanism": loop["mechanism"],
        "score": score,
        "status": _status_from_score(score),
        # How much of the loop we could actually measure.
        "measured_weight": round(weight_used, 2),
        "metrics": parts,
    }


# ---------------------------------------------------------------------------
# Named failure modes
# ---------------------------------------------------------------------------
# A number tells you something is wrong. A name tells you what kind of wrong,
# and that is what makes it actionable. Each entry is (key, predicate) where
# the predicate reads the metric dict and returns a finding or None.


def _finding(key, name, severity, what, why, evidence, loop) -> dict:
    return {
        "key": key, "name": name, "severity": severity, "what": what,
        "why_it_matters": why, "evidence": evidence, "loop": loop,
    }


def detect_failure_modes(bundle: dict) -> List[dict]:
    m = bundle["metrics"]
    d = bundle.get("detail", {})
    cov = bundle.get("coverage", {})
    out: List[dict] = []

    lpb = m.get("listings_per_active_buyer")
    st = m.get("sell_through_rate")
    v2o = m.get("view_to_order_rate")
    mbr = m.get("multi_brand_buyer_rate")
    rep = m.get("repeat_buyer_rate")
    hhi_v = m.get("gmv_hhi")
    act = m.get("brand_activation_rate")

    if lpb is not None and lpb > OVERSUPPLY_LISTINGS_PER_BUYER and (st is None or st < BANDS["sell_through_rate"]["weak"]):
        out.append(_finding(
            "ghost_town", "Ghost town", "critical",
            f"There are {lpb:.0f} live listings for every active buyer and "
            f"sell-through is {_pct(st)}.",
            "Sellers are the ones who feel this first. A brand that lists ten "
            "pieces and sells none concludes the marketplace is dead and "
            "stops restocking — and supply churn is far harder to reverse "
            "than demand churn, because a burned seller does not come back.",
            {"listings_per_active_buyer": lpb, "sell_through_rate": st},
            "demand",
        ))

    if lpb is not None and lpb < BANDS["listings_per_active_buyer"]["weak"]:
        out.append(_finding(
            "empty_shelves", "Empty shelves", "high",
            f"Only {lpb:.1f} live listings per active buyer.",
            "Buyers arrive, find nothing in their size or taste, and leave. "
            "Paid traffic against thin inventory is a refund you pay to "
            "Meta. Depth of choice in the buyer's actual size is the "
            "constraint, not listing count in aggregate.",
            {"listings_per_active_buyer": lpb},
            "supply",
        ))

    if mbr is not None and mbr < BANDS["multi_brand_buyer_rate"]["weak"]:
        out.append(_finding(
            "silo_marketplace", "Silo marketplace", "critical",
            f"Only {_pct(mbr)} of repeat buyers have bought from more than "
            "one brand.",
            "This is the diagnosis that matters most, and the one that never "
            "shows up in a revenue chart. If buyers only ever transact with "
            "the brand that brought them, you are hosting shops rather than "
            "running a network: brands carry their own demand, so they can "
            "leave for a lower fee at any time, and adding a brand adds "
            "nothing to any existing buyer. Cross-brand purchasing is the "
            "only thing that makes the marketplace worth more than the sum "
            "of its sellers.",
            {"multi_brand_buyer_rate": mbr},
            "density",
        ))

    if hhi_v is not None and hhi_v > BANDS["gmv_hhi"]["weak"]:
        top = (d.get("top_brands") or [{}])[0]
        out.append(_finding(
            "one_brand_marketplace", "One-brand marketplace", "high",
            f"GMV concentration (HHI) is {hhi_v:.2f}; the top three brands "
            f"take {_pct(m.get('top3_gmv_share'))} of GMV.",
            "Your growth chart is one brand's growth chart. That brand has "
            "all the leverage in any fee conversation and takes a third of "
            "the marketplace with it if it leaves. It also distorts every "
            "other metric here — cohort retention and AOV are really that "
            "brand's customers.",
            {"gmv_hhi": hhi_v, "top_brand": top.get("name"),
             "top_brand_share": top.get("gmv_share")},
            "density",
        ))

    if rep is not None and rep < BANDS["repeat_buyer_rate"]["weak"]:
        out.append(_finding(
            "leaky_bucket", "Leaky bucket", "critical",
            f"Repeat purchase rate is {_pct(rep)}.",
            "Under this rate, acquisition never compounds: every pound of "
            "growth has to be bought again next month. Scaling spend here "
            "does not build a business, it rents one. Fix the second "
            "purchase before widening the funnel.",
            {"repeat_buyer_rate": rep},
            "retention",
        ))

    if v2o is not None and v2o < BANDS["view_to_order_rate"]["weak"] and (cov.get("views_in_window") or 0) > 200:
        out.append(_finding(
            "discovery_breakdown", "Discovery breakdown", "high",
            f"View → order conversion is {_pct(v2o)} across "
            f"{cov.get('views_in_window')} views.",
            "There is demand arriving and it is not finding what it came "
            "for. With traffic this size the constraint is match-making — "
            "search, size filters, price legibility, trust signals — not the "
            "top of the funnel. Buying more traffic multiplies the leak.",
            {"view_to_order_rate": v2o, "views": cov.get("views_in_window")},
            "demand",
        ))

    if act is not None and act < BANDS["brand_activation_rate"]["weak"]:
        stalled = d.get("stalled_brand_count", 0)
        out.append(_finding(
            "supply_activation_failure", "Supply never activates", "high",
            f"Only {_pct(act)} of established brands have ever made a sale; "
            f"{stalled} have not.",
            "Recruiting brands you cannot make successful is negative work: "
            "it costs approval effort, it dilutes the catalogue with listings "
            "nobody sees, and each dormant brand is a person telling other "
            "brands the marketplace does not sell. Activation beats "
            "recruitment every time at this stage.",
            {"brand_activation_rate": act, "stalled_brands": stalled},
            "supply",
        ))

    k = m.get("k_factor")
    if k is None and (cov.get("referral_codes") or 0) == 0:
        out.append(_finding(
            "no_word_of_mouth", "No word-of-mouth loop", "medium",
            "The referral programme is gated off, so there is no measurable "
            "word-of-mouth loop at all.",
            "Streetwear is a recommendation category — the purchase is "
            "social by nature and people already share finds. Not capturing "
            "that is leaving the cheapest acquisition channel unbuilt and, "
            "worse, unmeasured. Note the sequencing though: a referral "
            "programme is only worth launching once repeat purchase works, "
            "or you will pay to import churn.",
            {"referral_codes": 0},
            "referral",
        ))
    elif k is not None and k < BANDS["k_factor"]["weak"]:
        out.append(_finding(
            "weak_virality", "Word of mouth is not a channel", "medium",
            f"Observed K is {k:.2f}.",
            "Below 0.15 the referral programme is a feature, not a channel. "
            "Either the incentive is too small to change behaviour, the ask "
            "lands at the wrong moment, or the underlying experience is not "
            "worth recommending — and the third cause is the most common.",
            {"k_factor": k},
            "referral",
        ))

    cp = m.get("community_participation_rate")
    if cp is not None and cp < BANDS["community_participation_rate"]["weak"]:
        out.append(_finding(
            "dead_feed", "Dead feed", "medium",
            f"Only {_pct(cp)} of active users engaged with the community.",
            "An empty feed is worse than no feed: it is a public signal that "
            "nobody is here, shown to every buyer at the moment they are "
            "deciding whether to trust you with money. Either seed it "
            "properly or hide it.",
            {"community_participation_rate": cp},
            "content",
        ))

    atomic = d.get("atomic_cell") or {}
    if atomic.get("found"):
        top = atomic.get("top") or {}
        if top.get("brands", 0) < 5 or top.get("orders", 0) < 20:
            out.append(_finding(
                "cold_start_unsolved", "Cold start not yet solved", "high",
                f"The densest cell ({top.get('category')} · {top.get('market')}) "
                f"has {top.get('brands')} brands and {top.get('orders')} orders.",
                "No slice of the market is yet dense enough to work "
                "reliably. Spreading thinly across categories and regions "
                "keeps every cell below the threshold where buyers find what "
                "they want. Pick one cell, over-serve it until it is "
                "obviously liquid, then repeat — breadth is what you earn, "
                "not what you start with.",
                {"cell": top},
                "supply",
            ))
    else:
        out.append(_finding(
            "no_transactions", "No transaction base", "critical",
            "There are no completed orders in the window to analyse.",
            "Every diagnosis below this line is unmeasurable until the first "
            "transactions land. The only job is a first cohort of real "
            "orders in one narrow cell, hand-assembled if necessary.",
            {}, "supply",
        ))

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    out.sort(key=lambda f: order.get(f["severity"], 9))
    return out


def _pct(v: Optional[float]) -> str:
    return "unknown" if v is None else f"{v * 100:.1f}%"


# ---------------------------------------------------------------------------
# Stage gates
# ---------------------------------------------------------------------------


def assess_stage(bundle: dict) -> dict:
    """Find the first stage gate that does not clear. That is where you are.

    The point of a stage model is not the label — it is the permission to
    ignore everything above your current stage. Most marketplace growth
    failure is a stage-4 tactic applied to a stage-1 problem.
    """
    m = bundle["metrics"]
    atomic_top = ((bundle.get("detail") or {}).get("atomic_cell") or {}).get("top") or {}
    values = dict(m)
    values["atomic_cell_brands"] = atomic_top.get("brands")
    values["atomic_cell_orders"] = atomic_top.get("orders")

    stages = []
    current = None
    for stage in STAGE_GATES:
        checks = []
        passed = True
        for metric_key, threshold, label in stage["gates"]:
            value = values.get(metric_key)
            band = BANDS.get(metric_key, {})
            higher_better = band.get("higher_is_better", True)
            if value is None:
                ok = False
            elif higher_better:
                ok = value >= threshold
            else:
                ok = value <= threshold
            checks.append({
                "metric": metric_key, "label": label, "threshold": threshold,
                "value": value, "passed": ok,
                "higher_is_better": higher_better,
            })
            passed = passed and ok
        stages.append({
            "key": stage["key"], "name": stage["name"], "goal": stage["goal"],
            "focus": stage["focus"], "stop": stage["stop"],
            "passed": passed, "checks": checks,
        })
        if current is None and not passed:
            current = stage["key"]

    if current is None:
        current = STAGE_GATES[-1]["key"]

    current_stage = next(s for s in stages if s["key"] == current)
    return {
        "current": current,
        "current_name": current_stage["name"],
        "goal": current_stage["goal"],
        "focus": current_stage["focus"],
        "stop": current_stage["stop"],
        "blocking_checks": [c for c in current_stage["checks"] if not c["passed"]],
        "stages": stages,
    }


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def assess_confidence(bundle: dict) -> dict:
    """How much weight the numbers can bear.

    Stated plainly rather than buried, because the fastest way to destroy an
    operator's trust in a growth dashboard is to give a decisive answer off
    forty orders and be wrong.
    """
    cov = bundle.get("coverage", {})
    orders = cov.get("orders_in_window", 0)
    views = cov.get("views_in_window", 0)

    if orders >= 400 and views >= 5000:
        level, note = "high", "Enough volume for the rates here to be stable."
    elif orders >= 100:
        level, note = ("medium",
                       "Enough to trust direction and rank the problems; not "
                       "enough to trust small differences between periods.")
    elif orders >= 20:
        level, note = ("low",
                       "Small-sample territory. Read these as hypotheses to "
                       "test, not as measurements. A handful of orders moves "
                       "any of these rates by ten points.")
    else:
        level, note = ("very_low",
                       "Below the level where rates mean anything. The "
                       "qualitative diagnosis and the sequencing still hold; "
                       "the decimals do not.")

    return {
        "level": level,
        "note": note,
        "orders_in_window": orders,
        "views_in_window": views,
        "gaps": cov.get("gaps", []),
    }


def diagnose(bundle: dict) -> dict:
    """Full diagnostic: loops, failure modes, stage, overall grade."""
    metrics = bundle["metrics"]
    loops = [score_loop(loop, metrics) for loop in LOOPS]
    findings = detect_failure_modes(bundle)
    stage = assess_stage(bundle)
    confidence = assess_confidence(bundle)

    scored = [l["score"] for l in loops if l["score"] is not None]
    overall = round(sum(scored) / len(scored), 1) if scored else None

    weakest = None
    ranked = sorted(
        (l for l in loops if l["score"] is not None), key=lambda l: l["score"]
    )
    if ranked:
        weakest = ranked[0]["key"]

    return {
        "overall_score": overall,
        "grade": _grade(overall),
        "loops": loops,
        "weakest_loop": weakest,
        "findings": findings,
        "stage": stage,
        "confidence": confidence,
    }


def _grade(score: Optional[float]) -> str:
    if score is None:
        return "n/a"
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"
