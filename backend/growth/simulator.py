"""Flywheel simulator — a marketplace growth model with the loops wired in.

A spreadsheet projects each line independently and always shows a hockey
stick. This model closes three feedback loops that decide whether a
marketplace compounds or quietly dies:

  1. Catalogue depth → buyer conversion. More listings per buyer raises
     orders per buyer, with strongly diminishing returns and a ceiling.
  2. GMV per brand → supply retention. Brands that do not sell leave, which
     thins the catalogue, which lowers conversion, which lowers GMV per
     brand. This is the death spiral, and it is why marketplaces fail from
     the supply side while the demand chart still looks fine.
  3. New buyers → referral children → new buyers. The viral term.

The model is deliberately simple and legible: every coefficient is named,
bounded, and exposed to the caller. It is a thinking tool for ranking
scenarios, not a forecast — treat the shape as signal and the absolute
numbers as illustrative.
"""

from math import log, sqrt
from typing import Dict, List, Optional

# Listings per active buyer at which catalogue depth stops being the binding
# constraint on conversion. Matches the healthy band in benchmarks.py, which
# is calibrated for a curated brand marketplace rather than C2C resale.
TARGET_LISTINGS_PER_BUYER = 6.0

# Monthly GMV per brand at which a brand is clearly making money and stays.
# Deliberately modest: for an independent brand with no listing fee, a few
# hundred pounds a month is enough to keep restocking. Raise it and the model
# churns supply aggressively; that is the lever to test, not to hide.
TARGET_GMV_PER_BRAND = 250.0

DEFAULTS: Dict[str, float] = {
    "months": 12,
    # Starting state
    "active_buyers": 150.0,
    "brands": 12.0,
    "listings_per_brand": 30.0,
    "aov": 45.0,
    "orders_per_buyer_month": 0.35,
    # Retention
    "buyer_retention": 0.55,          # monthly, of active buyers
    "brand_retention": 0.90,          # monthly, before the GMV feedback
    # Acquisition
    "monthly_paid_spend": 0.0,
    "cac": 18.0,
    "baseline_organic_new_buyers": 60.0,
    "k_factor": 0.0,
    # Supply acquisition
    "brand_adds_per_month": 4.0,
    "brand_add_elasticity": 0.8,      # how strongly brand adds follow GMV/brand
    # Economics
    "take_rate": 0.06,                # effective platform revenue / GMV
    "variable_cost_per_order": 0.60,  # payment + support + comms
    "fixed_monthly_cost": 0.0,
    # Model behaviour
    "depth_elasticity": 1.0,          # 0 = depth does not affect conversion
    "supply_churn_sensitivity": 0.25,  # 0 = brands never churn on poor sales
}


def effective_take_rate(aov: float, fee_rate: float = 0.05,
                        fee_fixed: float = 0.49, fee_cap: float = 6.0) -> float:
    """Platform revenue as a share of GMV, from the real fee formula.

    Unveiled Threads charges the buyer min(subtotal x rate + fixed, cap) and
    passes the whole item price to the seller, so the effective take rate is
    not a flat percentage — it falls as basket size rises and the cap bites.
    Modelling it as a flat 9% would overstate revenue on every high-AOV
    scenario.
    """
    if aov <= 0:
        return 0.0
    return min(aov * fee_rate + fee_fixed, fee_cap) / aov


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def depth_multiplier(listings_per_buyer: float, elasticity: float = 1.0) -> float:
    """Effect of catalogue depth on orders per buyer.

    Logarithmic: going from 1 to 6 listings per buyer matters enormously,
    from 40 to 80 barely at all. Capped at 1.35 because no amount of choice
    turns a browser into a repeat buyer on its own — and past the oversupply
    point extra listings simply go unseen.
    """
    if listings_per_buyer <= 0:
        return 0.2
    raw = log(1.0 + listings_per_buyer) / log(1.0 + TARGET_LISTINGS_PER_BUYER)
    capped = _clamp(raw, 0.2, 1.35)
    # elasticity of 0 flattens the effect to neutral, 1 applies it fully
    return 1.0 + (capped - 1.0) * _clamp(elasticity, 0.0, 2.0)


def simulate(params: Optional[dict] = None) -> dict:
    """Run the monthly model and return the series plus summary economics."""
    p = dict(DEFAULTS)
    if params:
        for k, v in params.items():
            if k in p and v is not None:
                p[k] = float(v)
    months = int(_clamp(p["months"], 1, 60))

    buyers = max(p["active_buyers"], 0.0)
    brands = max(p["brands"], 0.0)
    starting_brands = max(brands, 1.0)
    listings_per_brand = max(p["listings_per_brand"], 0.0)
    prev_new_buyers = 0.0

    series: List[dict] = []
    cumulative_contribution = 0.0
    cumulative_spend = 0.0
    total_new_buyers = 0.0
    total_unpaid_new_buyers = 0.0

    for month in range(1, months + 1):
        listings = brands * listings_per_brand
        lpb = listings / buyers if buyers > 0 else listings
        depth = depth_multiplier(lpb, p["depth_elasticity"])

        orders_per_buyer = p["orders_per_buyer_month"] * depth
        orders = buyers * orders_per_buyer
        gmv = orders * p["aov"]
        revenue = gmv * p["take_rate"]
        spend = p["monthly_paid_spend"]
        variable = orders * p["variable_cost_per_order"]
        contribution = revenue - spend - variable - p["fixed_monthly_cost"]

        cumulative_contribution += contribution
        cumulative_spend += spend

        # ---- Acquisition -------------------------------------------------
        paid_new = spend / p["cac"] if p["cac"] > 0 else 0.0
        referral_new = p["k_factor"] * prev_new_buyers
        # Word of mouth scales with catalogue breadth, sub-linearly: twice the
        # brands is not twice the reasons to mention you. Measured relative to
        # the starting catalogue, so the baseline input means "new buyers per
        # month at today's breadth".
        breadth = sqrt(brands / starting_brands) if brands > 0 else 0.0
        organic_new = p["baseline_organic_new_buyers"] * _clamp(breadth, 0.0, 3.0)
        new_buyers = paid_new + referral_new + organic_new

        total_new_buyers += new_buyers
        total_unpaid_new_buyers += referral_new + organic_new

        # ---- Supply side: the feedback that kills marketplaces ------------
        gmv_per_brand = gmv / brands if brands > 0 else 0.0
        attractiveness = _clamp(gmv_per_brand / TARGET_GMV_PER_BRAND, 0.0, 2.0)

        # Brands churn harder when they are not selling.
        churn_adj = 1.0 - p["supply_churn_sensitivity"] * (1.0 - attractiveness)
        effective_brand_retention = _clamp(
            p["brand_retention"] * churn_adj, 0.30, 0.995
        )
        # And new brands arrive faster when existing ones visibly make money.
        brand_adds = max(
            0.0,
            p["brand_adds_per_month"]
            * (1.0 + p["brand_add_elasticity"] * (attractiveness - 1.0)),
        )

        series.append({
            "month": month,
            "active_buyers": round(buyers, 1),
            "brands": round(brands, 1),
            "listings": round(listings, 0),
            "listings_per_buyer": round(lpb, 2),
            "depth_multiplier": round(depth, 3),
            "orders": round(orders, 1),
            "gmv": round(gmv, 2),
            "revenue": round(revenue, 2),
            "contribution": round(contribution, 2),
            "cumulative_contribution": round(cumulative_contribution, 2),
            "new_buyers": round(new_buyers, 1),
            "paid_new_buyers": round(paid_new, 1),
            "organic_new_buyers": round(organic_new, 1),
            "referral_new_buyers": round(referral_new, 1),
            "brand_adds": round(brand_adds, 2),
            "brand_retention_effective": round(effective_brand_retention, 3),
            "gmv_per_brand": round(gmv_per_brand, 2),
        })

        # ---- Advance -----------------------------------------------------
        buyers = buyers * _clamp(p["buyer_retention"], 0.0, 0.99) + new_buyers
        brands = brands * effective_brand_retention + brand_adds
        prev_new_buyers = new_buyers

    summary = _summarise(series, p, total_new_buyers, total_unpaid_new_buyers,
                         cumulative_spend)
    return {"params": p, "series": series, "summary": summary}


def _summarise(series: List[dict], p: dict, total_new: float,
               total_unpaid: float, cumulative_spend: float) -> dict:
    first, last = series[0], series[-1]

    # Buyer lifetime value on the platform's own revenue, not GMV.
    retention = _clamp(p["buyer_retention"], 0.0, 0.98)
    expected_months = 1.0 / (1.0 - retention) if retention < 1 else 60.0
    monthly_contribution_per_buyer = (
        p["orders_per_buyer_month"] * p["aov"] * p["take_rate"]
        - p["orders_per_buyer_month"] * p["variable_cost_per_order"]
    )
    ltv = monthly_contribution_per_buyer * expected_months
    ltv_cac = (ltv / p["cac"]) if p["cac"] > 0 else None
    payback_months = (
        p["cac"] / monthly_contribution_per_buyer
        if monthly_contribution_per_buyer > 0 else None
    )

    organic_share = (total_unpaid / total_new) if total_new > 0 else None

    # Escape velocity: growing without paid carrying it, and supply not
    # shrinking. Both conditions matter — GMV growth on a collapsing brand
    # count is a countdown, not a trend.
    gmv_growing = last["gmv"] > first["gmv"] * 1.2
    supply_growing = last["brands"] >= first["brands"]
    escape = bool(
        gmv_growing and supply_growing
        and organic_share is not None and organic_share >= 0.5
    )

    # Name the binding constraint at the end state: whichever loop is holding
    # the model back is where the next quarter should go.
    if last["depth_multiplier"] < 0.85:
        constraint = ("catalogue depth", "Buyers do not have enough to choose "
                      "from, so conversion never lifts.")
    elif last["brands"] < first["brands"]:
        constraint = ("supply retention", "Brands are leaving faster than they "
                      "join — the catalogue is shrinking underneath the "
                      "demand you are buying.")
    elif retention < 0.5:
        constraint = ("buyer retention", "Buyers leak out faster than the "
                      "loops refill them, so growth needs constant spend.")
    elif organic_share is not None and organic_share < 0.4:
        constraint = ("acquisition dependence", "Most new buyers are bought. "
                      "Growth stops the month spend stops.")
    else:
        constraint = ("none binding", "No single loop is capping the model at "
                      "these inputs — the constraint is execution.")

    return {
        "months": len(series),
        "ending_gmv": last["gmv"],
        "ending_monthly_revenue": last["revenue"],
        "ending_active_buyers": last["active_buyers"],
        "ending_brands": last["brands"],
        "total_gmv": round(sum(s["gmv"] for s in series), 2),
        "total_revenue": round(sum(s["revenue"] for s in series), 2),
        "cumulative_contribution": last["cumulative_contribution"],
        "cumulative_spend": round(cumulative_spend, 2),
        "gmv_multiple": round(last["gmv"] / first["gmv"], 2) if first["gmv"] else None,
        "ltv": round(ltv, 2),
        "ltv_cac": round(ltv_cac, 2) if ltv_cac is not None else None,
        "payback_months": round(payback_months, 1) if payback_months is not None else None,
        "organic_share_of_new_buyers": round(organic_share, 4) if organic_share is not None else None,
        "escape_velocity": escape,
        "binding_constraint": constraint[0],
        "binding_constraint_note": constraint[1],
    }


def params_from_bundle(bundle: dict, overrides: Optional[dict] = None,
                       fee_config: Optional[dict] = None) -> dict:
    """Seed the model from measured reality, then apply the caller's overrides.

    Anything the marketplace has not measured falls back to the default, so
    the simulator is usable on day one and gets more honest as data arrives.
    """
    m = bundle.get("metrics", {})
    window_days = ((bundle.get("detail") or {}).get("window") or {}).get("days", 90)
    months_in_window = max(window_days / 30.0, 0.5)

    p = dict(DEFAULTS)
    if m.get("active_buyers"):
        p["active_buyers"] = float(m["active_buyers"])
    if m.get("selling_brands"):
        p["brands"] = float(m["selling_brands"])
    if m.get("live_listings") and m.get("selling_brands"):
        p["listings_per_brand"] = float(m["live_listings"]) / float(m["selling_brands"])
    if m.get("aov"):
        p["aov"] = float(m["aov"])
    # Derive the take rate from the live fee configuration at the measured AOV
    # rather than assuming a flat percentage.
    fee_config = fee_config or {}
    p["take_rate"] = round(effective_take_rate(
        p["aov"],
        float(fee_config.get("rate", 0.05)),
        float(fee_config.get("fixed", 0.49)),
        float(fee_config.get("cap", 6.0)),
    ), 4)
    if m.get("orders") and m.get("active_buyers"):
        p["orders_per_buyer_month"] = (
            float(m["orders"]) / float(m["active_buyers"]) / months_in_window
        )
    if m.get("repeat_buyer_rate") is not None:
        # Monthly retention approximated from the window's repeat rate. Crude
        # but grounded, and clearly better than a made-up 0.55.
        p["buyer_retention"] = _clamp(
            float(m["repeat_buyer_rate"]) ** (1.0 / months_in_window), 0.05, 0.9
        )
    if m.get("k_factor") is not None:
        p["k_factor"] = float(m["k_factor"])

    if overrides:
        for k, v in overrides.items():
            if k in p and v is not None:
                p[k] = float(v)
    return p


def compare(base_params: dict, scenario_params: dict) -> dict:
    """Run two scenarios and report the delta on the numbers that matter."""
    base = simulate(base_params)
    scenario = simulate(scenario_params)
    bs, ss = base["summary"], scenario["summary"]

    def delta(key):
        b, s = bs.get(key), ss.get(key)
        if b is None or s is None:
            return None
        return round(s - b, 2)

    return {
        "base": base,
        "scenario": scenario,
        "delta": {
            "ending_gmv": delta("ending_gmv"),
            "total_gmv": delta("total_gmv"),
            "cumulative_contribution": delta("cumulative_contribution"),
            "ending_active_buyers": delta("ending_active_buyers"),
            "ending_brands": delta("ending_brands"),
            "organic_share_of_new_buyers": delta("organic_share_of_new_buyers"),
        },
    }
