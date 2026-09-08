"""The Monday memo.

Dashboards get read; memos get acted on. This turns the diagnostic into the
five-part note a CMO would actually send: where we are, what is really
happening, what I would do in the next 30 days, what I would stop, and what
would change my mind.

Deterministic templating — no model calls, no randomness, so the same data
always produces the same memo and week-on-week diffs are meaningful.
"""

from typing import List, Optional


def _pct(v: Optional[float], places: int = 1) -> str:
    return "not measurable" if v is None else f"{v * 100:.{places}f}%"


def _num(v: Optional[float], places: int = 1) -> str:
    return "not measurable" if v is None else f"{v:,.{places}f}"


def build_memo(bundle: dict, diagnosis: dict, playbook: dict) -> dict:
    m = bundle["metrics"]
    stage = diagnosis["stage"]
    findings = diagnosis.get("findings", [])
    confidence = diagnosis.get("confidence", {})
    window_days = ((bundle.get("detail") or {}).get("window") or {}).get("days", 90)

    critical = [f for f in findings if f["severity"] == "critical"]
    high = [f for f in findings if f["severity"] == "high"]

    # ---- Headline ----------------------------------------------------------
    if not m.get("orders"):
        headline = ("There is no transaction base yet. Everything below is a "
                    "plan for manufacturing a first cohort of orders in one "
                    "narrow slice of the market, by hand if necessary.")
    elif critical:
        headline = (
            f"The binding constraint is {stage['current_name'].lower()}, and "
            f"the clearest symptom is '{critical[0]['name'].lower()}'. Work on "
            f"that and nothing beneath it in the stack."
        )
    elif high:
        headline = (
            f"Nothing is on fire, but {stage['current_name'].lower()} has not "
            f"cleared its gate — '{high[0]['name'].lower()}' is what is "
            f"holding it."
        )
    else:
        healthy_stages = [s['name'] for s in stage['stages'] if s['passed']]
        headline = (
            f"All measured gates through {(healthy_stages[-1] if healthy_stages else 'the first stage').lower()} "
            f"are clear. The job now is to press the advantage rather than to "
            f"fix anything."
        )

    # ---- Where we are ------------------------------------------------------
    where: List[str] = [
        f"Over the last {window_days} days: £{_num(m.get('gmv'), 0)} GMV across "
        f"{m.get('orders', 0)} orders, from {m.get('active_buyers', 0)} active "
        f"buyers and {m.get('selling_brands', 0)} brands that actually sold "
        f"something.",
        f"Stage: {stage['current_name']}. {stage['goal']}",
    ]
    if stage["blocking_checks"]:
        parts = []
        for c in stage["blocking_checks"]:
            got = "no reading" if c["value"] is None else _num(c["value"], 2)
            direction = "at least" if c["higher_is_better"] else "at most"
            parts.append(f"{c['label']} needs to be {direction} "
                         f"{_num(c['threshold'], 2)} — currently {got}")
        where.append("The gate is held by: " + "; ".join(parts) + ".")

    # ---- What is actually happening ---------------------------------------
    happening: List[dict] = [
        {
            "title": f["name"],
            "severity": f["severity"],
            "detail": f["what"],
            "why": f["why_it_matters"],
        }
        for f in findings[:4]
    ]

    # ---- Next 30 days ------------------------------------------------------
    do_next = [
        {
            "name": p["name"],
            "owner": p["owner"],
            "why": p["hypothesis"],
            "first_step": p["steps"][0] if p["steps"] else None,
            "expect": (
                f"{p['expected']['metric'].replace('_', ' ')} "
                f"{p['expected']['direction']} {p['expected']['magnitude']}, "
                f"visible in about {p['time_to_signal_days']} days"
            ),
        }
        for p in playbook.get("now", [])
    ]

    # ---- Stop doing --------------------------------------------------------
    stop: List[str] = [stage["stop"]]
    for p in playbook.get("not_yet", [])[:2]:
        if p.get("reason"):
            stop.append(f"Do not start '{p['name']}' yet. {p['reason']}")
    if m.get("oversupplied"):
        stop.append(
            f"Stop approving new brands. At "
            f"{_num(m.get('listings_per_active_buyer'), 1)} live listings per "
            f"active buyer, each new listing lowers every existing seller's "
            f"odds of a sale."
        )

    # ---- What would change my mind ----------------------------------------
    caveats: List[str] = [confidence.get("note", "")]
    for gap in confidence.get("gaps", [])[:3]:
        caveats.append(f"{gap['what']} {gap['consequence']}")

    return {
        "headline": headline,
        "where_we_are": where,
        "whats_happening": happening,
        "next_30_days": do_next,
        "stop_doing": [s for s in stop if s],
        "what_would_change_my_mind": [c for c in caveats if c],
    }
