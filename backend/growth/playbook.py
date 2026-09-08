"""The play library — what a marketplace CMO would actually do next.

Each play carries a trigger (the metric condition that makes it relevant),
the mechanism (why it strengthens a network effect rather than just moving a
number), concrete steps, the metric it should move, and kill criteria. Plays
are ranked by ICE and then gated by stage, because the most common growth
mistake is running a correct play at the wrong time.

Pure: stdlib only, no I/O.
"""

from typing import Callable, Dict, List, Optional

from .benchmarks import OVERSUPPLY_LISTINGS_PER_BUYER, lookup_band

# ---------------------------------------------------------------------------
# Trigger helpers — every one is None-safe. A missing metric never silently
# reads as zero, because "we cannot measure this" and "this is bad" call for
# different plays.
# ---------------------------------------------------------------------------


def below(key: str, threshold: Optional[float] = None) -> Callable:
    limit = threshold if threshold is not None else lookup_band(key)["weak"]

    def _t(m, d, c):
        v = m.get(key)
        return v is not None and v < limit
    return _t


def above(key: str, threshold: Optional[float] = None) -> Callable:
    limit = threshold if threshold is not None else lookup_band(key)["weak"]

    def _t(m, d, c):
        v = m.get(key)
        return v is not None and v > limit
    return _t


def missing(key: str) -> Callable:
    def _t(m, d, c):
        return m.get(key) is None
    return _t


def any_of(*triggers: Callable) -> Callable:
    def _t(m, d, c):
        return any(t(m, d, c) for t in triggers)
    return _t


def all_of(*triggers: Callable) -> Callable:
    def _t(m, d, c):
        return all(t(m, d, c) for t in triggers)
    return _t


def always(m, d, c) -> bool:
    return True


def _thin_cell(m, d, c) -> bool:
    top = ((d.get("atomic_cell") or {}).get("top") or {})
    return (top.get("brands", 0) < 5) or (top.get("orders", 0) < 20)


def _has_stalled_brands(m, d, c) -> bool:
    return (d.get("stalled_brand_count") or 0) >= 3


def _oversupplied(m, d, c) -> bool:
    v = m.get("listings_per_active_buyer")
    return v is not None and v > OVERSUPPLY_LISTINGS_PER_BUYER


def _has_traffic(m, d, c) -> bool:
    return (c.get("views_in_window") or 0) >= 200


# ---------------------------------------------------------------------------
# The library
# ---------------------------------------------------------------------------
# impact: 1-10 expected effect on the constrained loop
# ease:   1-10 (10 = a week of one person's time, 1 = a quarter of the roadmap)
# confidence: 0-1, how sure the play works in *this* kind of marketplace

PLAYS: List[dict] = [
    # ---------------- Atomic network / cold start ----------------
    {
        "key": "atomic_cell_focus",
        "name": "Pick one cell and over-serve it",
        "loop": "supply", "stage": "atomic_network",
        "owner": "Founder / Growth",
        "trigger": _thin_cell,
        "hypothesis": "Liquidity is a local property, not a global one. One "
                      "dense category-and-scene cell will convert far better "
                      "than the same volume spread across eight categories.",
        "mechanism": "Network effects switch on per cell, not per marketplace. "
                     "A buyer needs several credible options in their size and "
                     "taste *at once*; spreading the same supply across "
                     "categories keeps every cell below that threshold "
                     "indefinitely. Saturating one cell also makes the "
                     "marketplace legible — 'the place for X' — which is what "
                     "generates the first word of mouth.",
        "steps": [
            "Take the densest cell from the cold-start panel and declare it "
            "the only cell that matters this quarter.",
            "Set a hard target: 15+ active brands and 100+ orders in that "
            "cell before any expansion.",
            "Point the homepage, every social post and every recruitment "
            "conversation at that cell only.",
            "Recruit brands strictly inside it, even when good brands from "
            "adjacent categories apply — park them on a waitlist.",
            "Publish the cell's depth as a promise ('40+ UK-made heavyweight "
            "tees, every size') so buyers know what to expect.",
        ],
        "expected": {"metric": "sell_through_rate", "direction": "up",
                     "magnitude": "+10-20pts inside the chosen cell"},
        "impact": 9, "ease": 6, "confidence": 0.8,
        "time_to_signal_days": 45, "cost": "£0 — a focusing decision",
        "kill_criteria": "If the cell has 15+ active brands and sell-through "
                         "is still under 20% after 8 weeks, the cell is wrong "
                         "— pick a different one rather than widening.",
    },
    {
        "key": "supply_recruitment_pause",
        "name": "Stop recruiting brands",
        "loop": "supply", "stage": "atomic_network",
        "owner": "Supply",
        "trigger": _oversupplied,
        "hypothesis": "Adding supply to an oversupplied marketplace actively "
                      "harms it: it dilutes attention per listing and "
                      "manufactures disappointed sellers.",
        "mechanism": "Every listing competes for the same scarce buyer "
                     "attention. Past the saturation point the marginal "
                     "listing lowers the average listing's odds of selling, "
                     "which lowers seller-perceived quality, which churns "
                     "supply. The counter-intuitive move — refusing supply — "
                     "raises sell-through for everyone still on the platform.",
        "steps": [
            "Freeze brand approvals except inside the focus cell.",
            "Move the application flow to a waitlist with an honest message: "
            "'we onboard brands only as fast as we can sell for them'.",
            "Redirect the supply team's hours entirely onto activating the "
            "brands already here.",
            "Publish the waitlist position — scarcity makes acceptance feel "
            "earned and raises listing effort on day one.",
        ],
        "expected": {"metric": "sell_through_rate", "direction": "up",
                     "magnitude": "+5-15pts within one window"},
        "impact": 8, "ease": 9, "confidence": 0.75,
        "time_to_signal_days": 30, "cost": "£0",
        "kill_criteria": "If sell-through does not move within 6 weeks, the "
                         "constraint is demand-side conversion, not the "
                         "supply-to-demand ratio.",
    },
    {
        "key": "founding_brand_concierge",
        "name": "Concierge every brand to its first sale",
        "loop": "supply", "stage": "atomic_network",
        "owner": "Supply",
        "trigger": any_of(below("brand_activation_rate"),
                          above("days_to_first_sale"), _has_stalled_brands),
        "hypothesis": "A brand's first sale is the single event that predicts "
                      "whether it ever lists again. It should be manufactured, "
                      "not left to chance.",
        "mechanism": "Supply-side time-to-value governs supply retention, and "
                     "supply retention governs catalogue depth, which governs "
                     "buyer conversion. Manually forcing the first sale buys "
                     "the loop time to become self-sustaining. It does not "
                     "scale — that is the point; it is scaffolding you remove.",
        "steps": [
            "Define activation precisely: 5 live listings with 3+ photos "
            "each, and one sale, within 21 days of approval.",
            "Assign every new brand an owner with a 7/14/21-day check-in.",
            "Give each new brand one free week of boosted placement, timed to "
            "a drop rather than to their approval date.",
            "Feature every genuinely new brand in the community feed and "
            "newsletter in their first fortnight.",
            "Call, do not email, any brand at day 21 with no sale — the call "
            "usually surfaces a pricing or photography problem in minutes.",
        ],
        "expected": {"metric": "brand_activation_rate", "direction": "up",
                     "magnitude": "+15-25pts on the next brand cohort"},
        "impact": 9, "ease": 6, "confidence": 0.85,
        "time_to_signal_days": 30, "cost": "Low — staff time plus free boosts",
        "kill_criteria": "If concierged brands activate no better than the "
                         "unconcierged control, the problem is demand depth, "
                         "not onboarding.",
    },
    {
        "key": "brand_cohort_onboarding",
        "name": "Onboard brands in cohorts, not a trickle",
        "loop": "supply", "stage": "atomic_network",
        "owner": "Supply",
        "trigger": any_of(below("brand_activation_rate"), _thin_cell),
        "hypothesis": "Ten brands launching together is a moment worth "
                      "marketing; ten brands launching separately is "
                      "administration.",
        "mechanism": "Cohorts create a demand event large enough to justify "
                     "promotion, which gives every brand in the cohort a "
                     "first-week sale, which activates supply. It also lets "
                     "brands meet each other — brand-to-brand referral is the "
                     "most underused supply channel in every marketplace.",
        "steps": [
            "Batch approvals into a fortnightly 'new brands' drop.",
            "Run one launch email, one feed post and one homepage rail per "
            "cohort.",
            "Put the cohort in a group chat with the supply lead.",
            "Ask each brand in the cohort to nominate one other brand.",
        ],
        "expected": {"metric": "brand_activation_rate", "direction": "up",
                     "magnitude": "+10-20pts"},
        "impact": 7, "ease": 8, "confidence": 0.7,
        "time_to_signal_days": 30, "cost": "£0",
        "kill_criteria": "Drop if cohort launch weeks do not out-sell "
                         "equivalent non-launch weeks.",
    },
    {
        "key": "listing_quality_bar",
        "name": "Enforce a minimum listing standard",
        "loop": "supply", "stage": "liquidity",
        "owner": "Supply / Product",
        "trigger": any_of(below("sell_through_rate"), below("view_to_order_rate")),
        "hypothesis": "Most non-selling listings are not badly priced, they "
                      "are badly presented — one dark photo, no measurements, "
                      "no size guidance.",
        "mechanism": "Listing quality is the raw material of match-making. "
                     "Poor listings depress conversion, which depresses "
                     "sell-through, which churns the seller who wrote them — "
                     "a loop the seller experiences as 'this marketplace does "
                     "not work'. Raising the floor lifts every downstream "
                     "metric at once.",
        "steps": [
            "Require 3+ images, garment measurements and a fit descriptor "
            "before a listing can go live.",
            "Show sellers a live 'listing strength' score as they type, with "
            "the one change that would help most.",
            "Sweep the existing catalogue: rank live listings by views with "
            "zero orders and send each seller a specific fix.",
            "Publish a one-page photography guide using the best-performing "
            "listings on the platform as the examples.",
        ],
        "expected": {"metric": "view_to_order_rate", "direction": "up",
                     "magnitude": "+0.5-1.5pts"},
        "impact": 7, "ease": 6, "confidence": 0.8,
        "time_to_signal_days": 30, "cost": "Low — product work",
        "kill_criteria": "If upgraded listings convert no better than their "
                         "own prior baseline, presentation was not the "
                         "constraint.",
    },
    {
        "key": "restock_the_winners",
        "name": "Chase restocks on everything that sold",
        "loop": "supply", "stage": "liquidity",
        "owner": "Supply",
        "trigger": any_of(below("sell_through_rate"), below("listings_per_active_buyer")),
        "hypothesis": "The highest-converting inventory you can add is more of "
                      "what already sold out.",
        "mechanism": "Proven demand removes the guesswork from supply "
                     "acquisition. It is also the cheapest possible seller "
                     "conversation — 'this sold in two days, send more' — and "
                     "it compounds: a brand that restocks stays active, which "
                     "keeps the catalogue deep in the sizes buyers want.",
        "steps": [
            "Daily report: sold-out listings with above-median view counts.",
            "Automated seller nudge within 24 hours of a sell-out.",
            "Add a 'notify me' capture on sold-out listings and show the "
            "seller the waiting count — nothing motivates a restock like a "
            "queue.",
            "Prioritise restock requests by size demand, not by product.",
        ],
        "expected": {"metric": "sell_through_rate", "direction": "up",
                     "magnitude": "+3-8pts"},
        "impact": 6, "ease": 8, "confidence": 0.85,
        "time_to_signal_days": 21, "cost": "£0 — uses existing low-stock digest",
        "kill_criteria": "If fewer than a quarter of nudged sellers restock, "
                         "the constraint is seller production capacity.",
    },
    {
        "key": "dead_stock_liquidity_event",
        "name": "Turn dead stock into a scheduled liquidity event",
        "loop": "demand", "stage": "liquidity",
        "owner": "Growth",
        "trigger": any_of(below("sell_through_rate"), _oversupplied),
        "hypothesis": "Aged inventory that will never sell at full price will "
                      "sell at a discount, and the discount buys you first-time "
                      "buyers cheaper than paid media does.",
        "mechanism": "Clearance does three jobs at once: it clears the "
                     "catalogue so live listings compete for attention "
                     "against fewer dead ones, it pays a seller who had "
                     "written the stock off, and it acquires price-sensitive "
                     "first-time buyers at negative marginal cost. Those "
                     "buyers then enter the retention loop at full price.",
        "steps": [
            "Run a monthly 48-hour clearance moment across the dead-stock "
            "section rather than leaving it as a permanent, ignorable tab.",
            "Auto-suggest dead-stock status for listings past 90 days with "
            "views but no sales.",
            "Email the whole list once per event — scarcity plus a deadline "
            "is what makes it work.",
            "Track what share of clearance buyers place a second, full-price "
            "order within 60 days; that number decides whether to repeat it.",
        ],
        "expected": {"metric": "sell_through_rate", "direction": "up",
                     "magnitude": "+5-10pts in the event window"},
        "impact": 6, "ease": 8, "confidence": 0.75,
        "time_to_signal_days": 14, "cost": "£0",
        "kill_criteria": "Stop if clearance buyers never buy at full price — "
                         "you are training a discount audience.",
    },

    # ---------------- Demand / liquidity ----------------
    {
        "key": "size_first_discovery",
        "name": "Make size the first filter, not the last",
        "loop": "demand", "stage": "liquidity",
        "owner": "Product",
        "trigger": any_of(below("view_to_order_rate"), _oversupplied),
        "hypothesis": "A buyer's real catalogue is 'items in my size'. Showing "
                      "them everything else is showing them an out-of-stock "
                      "shop.",
        "mechanism": "Effective liquidity is per-buyer, not aggregate. "
                     "Filtering to the buyer's size converts a shallow "
                     "catalogue into a dense one from their point of view, "
                     "which is the only point of view that converts. It also "
                     "produces the size-demand data supply recruitment needs.",
        "steps": [
            "Capture size on first visit — one tap, before signup.",
            "Default every browse and search to that size, with an obvious "
            "escape hatch.",
            "Show 'in your size' counts on brand and category pages.",
            "Feed aggregate size gaps back to sellers as a restock brief.",
        ],
        "expected": {"metric": "view_to_order_rate", "direction": "up",
                     "magnitude": "+0.5-2pts"},
        "impact": 8, "ease": 7, "confidence": 0.8,
        "time_to_signal_days": 21, "cost": "Low — product work",
        "kill_criteria": "If size-filtered sessions convert no better, the "
                         "objection is price or trust, not fit.",
    },
    {
        "key": "zero_result_search_fix",
        "name": "Instrument and close zero-result searches",
        "loop": "demand", "stage": "liquidity",
        "owner": "Product / Growth",
        "trigger": any_of(below("view_to_order_rate"), always),
        "hypothesis": "Every empty search is a buyer telling you exactly what "
                      "supply to go and get, and most marketplaces throw that "
                      "away.",
        "mechanism": "Zero-result searches are the highest-signal demand data "
                     "a marketplace generates: unmet, specific and already "
                     "intent-qualified. Routing them into supply recruitment "
                     "closes the loop between the two sides — demand pulls "
                     "the exact supply that will convert.",
        "steps": [
            "Log every search with its result count and the filters applied.",
            "Weekly report of the top zero- and low-result queries.",
            "Never show an empty page: offer the nearest matches plus a "
            "'tell me when this lands' capture.",
            "Hand the top ten queries to supply as a recruitment brief each "
            "week.",
        ],
        "expected": {"metric": "view_to_order_rate", "direction": "up",
                     "magnitude": "+0.3-1pt, plus a supply-targeting list"},
        "impact": 7, "ease": 7, "confidence": 0.85,
        "time_to_signal_days": 30, "cost": "Low",
        "kill_criteria": "None — the instrumentation is worth keeping even if "
                         "the conversion lift is small.",
    },
    {
        "key": "paid_traffic_hold",
        "name": "Hold paid spend until the funnel converts",
        "loop": "demand", "stage": "liquidity",
        "owner": "Growth",
        "trigger": all_of(below("view_to_order_rate"), _has_traffic),
        "hypothesis": "Traffic is not the constraint. Buying more of it at "
                      "this conversion rate destroys cash and burns the "
                      "audience you will want later.",
        "mechanism": "Paid acquisition multiplies whatever the funnel already "
                     "does. Against a broken conversion rate it multiplies a "
                     "negative, and it does lasting damage: the people who "
                     "bounce are the same people you will re-target in six "
                     "months, now with a bad first impression.",
        "steps": [
            "Cap paid spend at a small learning budget until view→order "
            "clears the weak band.",
            "Reallocate the budget to supply activation and listing quality.",
            "Set the explicit restart condition in writing, with a date to "
            "review it.",
        ],
        "expected": {"metric": "view_to_order_rate", "direction": "up",
                     "magnitude": "protects cash; no direct lift"},
        "impact": 7, "ease": 10, "confidence": 0.8,
        "time_to_signal_days": 1, "cost": "Negative — saves budget",
        "kill_criteria": "Restart paid the day conversion clears the band and "
                         "LTV:CAC modelling supports it.",
    },
    {
        "key": "wishlist_restock_alerts",
        "name": "Turn the wishlist into a trigger, not a folder",
        "loop": "demand", "stage": "retention",
        "owner": "Product / Lifecycle",
        "trigger": any_of(below("wishlist_conversion_rate"), missing("wishlist_conversion_rate")),
        "hypothesis": "A wishlist entry is a buyer telling you they want a "
                      "specific item at a slightly different moment. Sitting "
                      "on that is the cheapest revenue in the business going "
                      "unclaimed.",
        "mechanism": "Declared intent converts several times better than cold "
                     "traffic and costs nothing to reach. It also gives the "
                     "seller a demand signal — 'nine people are waiting' — "
                     "which drives restocks, feeding the supply loop.",
        "steps": [
            "Alert on price drop, low stock and restock for wishlisted items.",
            "Show sellers the wishlist count on each of their listings.",
            "Weekly 'still available in your size' digest, capped so it never "
            "becomes noise.",
            "Nudge a wishlist save on any product page a buyer views twice.",
        ],
        "expected": {"metric": "wishlist_conversion_rate", "direction": "up",
                     "magnitude": "+5-15pts"},
        "impact": 7, "ease": 8, "confidence": 0.85,
        "time_to_signal_days": 21, "cost": "Low",
        "kill_criteria": "Cut the frequency if unsubscribes rise above "
                         "baseline; the asset is the permission, not the send.",
    },
    {
        "key": "trust_at_decision_point",
        "name": "Put buyer protection at the decision point",
        "loop": "demand", "stage": "liquidity",
        "owner": "Product",
        "trigger": below("view_to_order_rate"),
        "hypothesis": "Buyers hesitate on unknown small brands because of "
                      "delivery and authenticity risk, not price.",
        "mechanism": "In a marketplace of unfamiliar sellers the platform's "
                     "job is to underwrite trust so buyers do not have to "
                     "evaluate each seller. Trust is what lets a buyer cross "
                     "from a brand they know to one they do not — which is "
                     "the precondition for network density.",
        "steps": [
            "Surface the buyer-protection promise on the product page and in "
            "the checkout button area, not only on a policy page.",
            "Show seller dispatch time, review count and rating inline.",
            "State the returns and dispute route in one plain sentence.",
            "A/B the placement; measure add-to-basket → paid, not clicks.",
        ],
        "expected": {"metric": "view_to_order_rate", "direction": "up",
                     "magnitude": "+0.2-0.8pts"},
        "impact": 6, "ease": 8, "confidence": 0.7,
        "time_to_signal_days": 21, "cost": "£0",
        "kill_criteria": "Revert if the fee becomes more salient than the "
                         "protection and conversion drops.",
    },

    # ---------------- Retention ----------------
    {
        "key": "second_purchase_sprint",
        "name": "Engineer the second purchase",
        "loop": "retention", "stage": "retention",
        "owner": "Lifecycle",
        "trigger": below("repeat_buyer_rate"),
        "hypothesis": "The gap between the first and second order is where "
                      "the business is being lost, and it is a 30-day window "
                      "you can address directly.",
        "mechanism": "Second purchase is the habit threshold: buyers who "
                     "reach it retain at multiples of those who do not, "
                     "because the first order proved the platform works and "
                     "the second proves it works repeatably. Every pound of "
                     "acquisition is worth more once this rate rises, so this "
                     "play compounds with all the others.",
        "steps": [
            "Trigger on delivery, not on purchase: 'how did it fit?' plus "
            "three items from *different* brands in the same size.",
            "Give a small credit that expires in 21 days — deadlines convert, "
            "open-ended credits decorate.",
            "Instrument days-to-second-order as a tracked metric and watch "
            "the median, not the mean.",
            "Segment: buyers whose first order was a clearance item need a "
            "different offer from full-price buyers.",
        ],
        "expected": {"metric": "repeat_buyer_rate", "direction": "up",
                     "magnitude": "+5-12pts"},
        "impact": 9, "ease": 7, "confidence": 0.8,
        "time_to_signal_days": 45, "cost": "Low — credit cost only on success",
        "kill_criteria": "If second orders only ever happen with a credit, "
                         "you have bought a discount habit, not retention — "
                         "stop and fix the product experience instead.",
    },
    {
        "key": "first_order_teardown",
        "name": "Tear down the first-order experience, brand by brand",
        "loop": "retention", "stage": "retention",
        "owner": "Ops / Supply",
        "trigger": below("repeat_buyer_rate"),
        "hypothesis": "Low repeat rate in a marketplace is usually a few "
                      "sellers with slow dispatch and poor packaging, not a "
                      "platform-wide problem.",
        "mechanism": "Buyers do not distinguish between the marketplace and "
                     "the seller — one bad first order churns the buyer from "
                     "the whole platform, including from brands that did "
                     "nothing wrong. Enforcing a service floor is therefore a "
                     "network-level retention intervention, not seller "
                     "policing.",
        "steps": [
            "Rank brands by repeat rate of the buyers whose first order they "
            "fulfilled.",
            "Correlate against dispatch time, tracking entry and dispute rate.",
            "Set a published service floor: dispatch in 3 working days, "
            "tracking always entered.",
            "Coach the worst offenders; restrict placement for repeat "
            "offenders rather than removing them outright.",
        ],
        "expected": {"metric": "repeat_buyer_rate", "direction": "up",
                     "magnitude": "+3-8pts"},
        "impact": 8, "ease": 6, "confidence": 0.8,
        "time_to_signal_days": 45, "cost": "£0 — uses existing shipping data",
        "kill_criteria": "If repeat rate is flat across brands, the cause is "
                         "platform-level (assortment or price), not seller "
                         "service.",
    },
    {
        "key": "drop_calendar",
        "name": "Run a weekly drop moment",
        "loop": "retention", "stage": "retention",
        "owner": "Growth / Brand",
        "trigger": any_of(below("repeat_buyer_rate"),
                          below("community_participation_rate")),
        "hypothesis": "Streetwear buyers already have a drop habit. Owning a "
                      "weekly time slot converts browsing into a routine.",
        "mechanism": "Appointment retention: a fixed, anticipated moment "
                     "creates recurring visits that are not paid for, and it "
                     "concentrates demand into a window where sell-through "
                     "is highest — which makes sellers want to be in it, "
                     "which deepens supply. Both sides pull towards the same "
                     "moment.",
        "steps": [
            "Fix a slot — Thursday 6pm — and never move it.",
            "Curate 10-20 pieces across at least five brands per drop.",
            "One email, one push, one feed post; a countdown on the homepage.",
            "Let brands apply for drop slots; make inclusion a reward for "
            "listing quality and dispatch performance.",
        ],
        "expected": {"metric": "repeat_buyer_rate", "direction": "up",
                     "magnitude": "+3-10pts, plus a weekly GMV spike"},
        "impact": 8, "ease": 6, "confidence": 0.75,
        "time_to_signal_days": 45, "cost": "Low — curation time",
        "kill_criteria": "Kill after 6 drops if drop-day GMV is not clearly "
                         "above a normal day and buyers do not return "
                         "week-on-week.",
    },

    # ---------------- Network density: the network effect proper ----------------
    {
        "key": "cross_brand_rails",
        "name": "Put cross-brand recommendations where the buyer already is",
        "loop": "density", "stage": "density",
        "owner": "Product",
        "trigger": any_of(below("multi_brand_buyer_rate"),
                          missing("multi_brand_buyer_rate")),
        "hypothesis": "Buyers stay inside the brand that brought them because "
                      "nothing ever shows them a second one at a moment they "
                      "care.",
        "mechanism": "This is the core network-effect intervention. Every "
                     "cross-brand purchase converts a brand's customer into "
                     "the marketplace's customer: it raises the value of the "
                     "catalogue to that buyer, makes each additional brand "
                     "worth more to every existing buyer, and makes the "
                     "marketplace the thing that is hard to leave. Without "
                     "it, adding brands adds nothing but choice fatigue.",
        "steps": [
            "'Others also bought' rail on the product page, restricted to "
            "*other* brands and the buyer's size.",
            "Order-confirmation and delivery emails carry three items from "
            "brands the buyer has never bought.",
            "'Complete the fit' rail on the basket, deliberately mixing "
            "brands.",
            "Track the cross-brand rate as a first-class metric on the "
            "weekly review, not as an analytics curiosity.",
        ],
        "expected": {"metric": "multi_brand_buyer_rate", "direction": "up",
                     "magnitude": "+10-20pts"},
        "impact": 10, "ease": 6, "confidence": 0.8,
        "time_to_signal_days": 45, "cost": "Low — product work",
        "kill_criteria": "If cross-brand rails cannibalise rather than add "
                         "(orders flat, brand mix shifts only), narrow the "
                         "rail to complementary categories.",
    },
    {
        "key": "category_first_navigation",
        "name": "Lead with category and edit, not brand storefronts",
        "loop": "density", "stage": "density",
        "owner": "Product / Brand",
        "trigger": below("multi_brand_buyer_rate"),
        "hypothesis": "A navigation built around brand storefronts trains "
                      "single-brand shopping and quietly prevents the network "
                      "effect from forming.",
        "mechanism": "Information architecture determines shopping behaviour. "
                     "Brand-first navigation makes the marketplace a hosting "
                     "service; category- and edit-first navigation forces "
                     "comparison across brands, which is where cross-brand "
                     "discovery — and therefore switching cost — comes from.",
        "steps": [
            "Make category and curated edits the primary navigation; keep "
            "brand pages one level down.",
            "Every homepage rail must contain at least three brands.",
            "Curate edits by theme — 'Heavyweight Tees', 'Olive Everything' — "
            "rather than by brand.",
            "Keep brand pages excellent; just stop making them the default "
            "entry point.",
        ],
        "expected": {"metric": "multi_brand_buyer_rate", "direction": "up",
                     "magnitude": "+5-15pts"},
        "impact": 8, "ease": 6, "confidence": 0.7,
        "time_to_signal_days": 45, "cost": "Low",
        "kill_criteria": "Watch brand sentiment: if strong brands feel "
                         "de-emphasised and threaten to leave, rebalance with "
                         "brand-led edits instead of reverting.",
    },
    {
        "key": "brand_collab_drops",
        "name": "Commission cross-brand collaboration drops",
        "loop": "density", "stage": "density",
        "owner": "Brand",
        "trigger": any_of(below("multi_brand_buyer_rate"), above("gmv_hhi")),
        "hypothesis": "Two brands sharing one drop introduce each other's "
                      "audiences and give the marketplace inventory nobody "
                      "else can list.",
        "mechanism": "A collaboration is a cross-brand purchase engineered at "
                     "the supply layer: it merges two audiences, produces "
                     "exclusive inventory that only exists because the "
                     "marketplace exists, and gives buyers a reason to see "
                     "the platform — not the brand — as the source of the "
                     "product. That exclusivity is the one defence against "
                     "brands disintermediating you.",
        "steps": [
            "Pair a high-GMV brand with a promising smaller one each month.",
            "Fund a small production run or underwrite the sample cost.",
            "Sell exclusively on-platform for two weeks.",
            "Measure how many buyers of the collab go on to buy from either "
            "brand separately.",
        ],
        "expected": {"metric": "multi_brand_buyer_rate", "direction": "up",
                     "magnitude": "+5-10pts, plus supply-side pull"},
        "impact": 8, "ease": 4, "confidence": 0.65,
        "time_to_signal_days": 60, "cost": "Medium — production underwriting",
        "kill_criteria": "Stop if collabs sell out but generate no follow-on "
                         "cross-brand purchases; then it is merchandising, "
                         "not network building.",
    },
    {
        "key": "concentration_derisk",
        "name": "Deliberately grow the long tail",
        "loop": "density", "stage": "density",
        "owner": "Supply / Growth",
        "trigger": above("gmv_hhi"),
        "hypothesis": "Concentration this high means the marketplace's "
                      "numbers are one brand's numbers, and its leverage over "
                      "you grows every month.",
        "mechanism": "Concentration is both a commercial risk and a "
                     "measurement problem: the dominant brand's customers "
                     "flatter every retention and AOV figure you report. "
                     "Broadening GMV share makes the network genuinely "
                     "multi-sided and makes your own metrics mean something.",
        "steps": [
            "Set an explicit ceiling — no brand above ~20% of GMV — and "
            "manage placement to it.",
            "Reserve homepage and drop slots for brands ranked 4-15.",
            "Report every headline metric twice: with and without the top "
            "brand, so you can see the underlying business.",
            "Recruit direct substitutes for the top brand's best sellers.",
        ],
        "expected": {"metric": "gmv_hhi", "direction": "down",
                     "magnitude": "-0.05 to -0.15"},
        "impact": 7, "ease": 6, "confidence": 0.7,
        "time_to_signal_days": 60, "cost": "£0 — placement reallocation",
        "kill_criteria": "Do not starve the top brand: if total GMV falls "
                         "more than the diversification is worth, rebalance.",
    },

    # ---------------- Referral ----------------
    {
        "key": "referral_launch",
        "name": "Launch the referral programme — once retention clears",
        "loop": "referral", "stage": "scale",
        "owner": "Growth",
        "trigger": any_of(missing("k_factor"), below("k_factor")),
        "hypothesis": "The referral machinery already exists and is gated "
                      "off. Streetwear is a recommendation category, so this "
                      "is a real channel — but only on top of retention that "
                      "works.",
        "mechanism": "Referral converts satisfied buyers into an acquisition "
                     "channel with near-zero marginal cost, and referred "
                     "buyers typically retain better because they arrive with "
                     "a personal recommendation attached. Launched over a "
                     "leaky bucket, though, it simply buys churn at a "
                     "discount — hence the sequencing.",
        "steps": [
            "Flip REFERRALS_ENABLED once the repeat-rate gate clears.",
            "Make it two-sided: credit for both referrer and referred.",
            "Place the ask at delivery and after a positive review — the "
            "moment of peak satisfaction, never at signup.",
            "Report K weekly, split by placement, and treat a fall as a "
            "product-experience signal.",
        ],
        "expected": {"metric": "k_factor", "direction": "up",
                     "magnitude": "0.15-0.40 observed K"},
        "impact": 7, "ease": 8, "confidence": 0.7,
        "time_to_signal_days": 45, "cost": "Low — credit cost on conversion",
        "kill_criteria": "If K stays under 0.1 after 8 weeks with the ask in "
                         "the right place, the experience is not "
                         "recommendable yet; go back to retention.",
    },
    {
        "key": "seller_side_referral",
        "name": "Let brands recruit brands",
        "loop": "referral", "stage": "atomic_network",
        "owner": "Supply",
        "trigger": any_of(below("brand_activation_rate"), _thin_cell,
                          missing("k_factor")),
        "hypothesis": "Independent brands know every other independent brand "
                      "in their scene, and a peer's recommendation converts "
                      "far better than cold outreach.",
        "mechanism": "Supply-side virality is the most underused loop in "
                     "marketplaces because everyone models referral as a "
                     "consumer mechanic. A brand that refers another has also "
                     "publicly endorsed you, which raises the referred "
                     "brand's activation odds — the loop improves its own "
                     "conversion rate as it runs.",
        "steps": [
            "Ask every brand that makes its first sale to nominate two peers, "
            "while the good news is fresh.",
            "Reward with fee relief or boosted placement rather than cash.",
            "Fast-track referred brands through approval and say so.",
            "Track referred-brand activation separately — it should beat "
            "cold-recruited brands, and if it does, this becomes the primary "
            "supply channel.",
        ],
        "expected": {"metric": "brand_activation_rate", "direction": "up",
                     "magnitude": "cheaper supply; +10pts activation on "
                                  "referred brands"},
        "impact": 7, "ease": 9, "confidence": 0.75,
        "time_to_signal_days": 30, "cost": "Low — fee relief",
        "kill_criteria": "Stop if referred brands activate no better than "
                         "cold ones; the referral is then just a discount.",
    },
    {
        "key": "shareable_product_cards",
        "name": "Make every listing worth screenshotting",
        "loop": "referral", "stage": "density",
        "owner": "Product / Brand",
        "trigger": any_of(below("k_factor"), missing("k_factor")),
        "hypothesis": "Streetwear finds already get shared in group chats — "
                      "as screenshots, with no link back to you.",
        "mechanism": "Dark-social sharing is happening whether or not you "
                     "instrument it. Making the shared artefact carry your "
                     "brand and a working link converts existing behaviour "
                     "into attributable acquisition without asking anyone to "
                     "do anything new — the cheapest possible loop.",
        "steps": [
            "Generate a branded share image per listing with price, brand and "
            "a short link.",
            "One-tap share to WhatsApp, Instagram Stories and iMessage on the "
            "product page.",
            "Give every listing a short, memorable URL.",
            "Track share → visit → purchase as its own funnel.",
        ],
        "expected": {"metric": "k_factor", "direction": "up",
                     "magnitude": "+0.05-0.15"},
        "impact": 6, "ease": 7, "confidence": 0.65,
        "time_to_signal_days": 30, "cost": "Low",
        "kill_criteria": "Drop if share rate stays under 1% of product views "
                         "after placement testing.",
    },

    # ---------------- Content / community ----------------
    {
        "key": "seed_the_feed",
        "name": "Seed the feed or hide it",
        "loop": "content", "stage": "retention",
        "owner": "Brand / Community",
        "trigger": below("community_participation_rate"),
        "hypothesis": "An empty feed advertises that nobody is here, at "
                      "exactly the moment a buyer is deciding whether to "
                      "trust you.",
        "mechanism": "Social proof is a conversion input, not a vanity "
                     "surface. A visibly active community both retains "
                     "existing buyers between purchases and reassures new "
                     "ones — and posts tagged to brands double as free "
                     "cross-brand discovery. An empty one does the reverse of "
                     "all three.",
        "steps": [
            "Commit to a fixed editorial cadence — three posts a week, "
            "published by the platform.",
            "Make one post per drop a condition of a brand's drop slot.",
            "Prompt a fit pic at the review step and cross-post it, with "
            "permission, to the feed.",
            "If the cadence cannot be held for six weeks, hide the feed "
            "rather than shipping an empty room.",
        ],
        "expected": {"metric": "community_participation_rate",
                     "direction": "up", "magnitude": "+3-8pts"},
        "impact": 6, "ease": 7, "confidence": 0.7,
        "time_to_signal_days": 45, "cost": "Low — editorial time",
        "kill_criteria": "Hide the feed if participation is still under 3% "
                         "after six weeks of consistent seeding.",
    },
    {
        "key": "fit_pic_ugc",
        "name": "Tie fit pics to the review moment",
        "loop": "content", "stage": "retention",
        "owner": "Lifecycle / Community",
        "trigger": any_of(below("community_participation_rate"),
                          below("brand_tag_rate")),
        "hypothesis": "The best moment to ask for content is the moment the "
                      "parcel is opened, and the review flow is already there.",
        "mechanism": "User photos solve the fit-and-authenticity objection "
                     "that suppresses conversion on unfamiliar brands, and "
                     "they are created by the buyer's own enthusiasm rather "
                     "than by a budget. Each one is simultaneously retention "
                     "content, a trust signal, and cross-brand discovery.",
        "steps": [
            "Add an optional photo to the existing review flow, with the "
            "buyer's height and size shown next to it.",
            "Display fit pics on the product page under the seller images.",
            "Feature the best weekly in the feed and the newsletter.",
            "Small credit for the first photo review a buyer leaves.",
        ],
        "expected": {"metric": "community_participation_rate",
                     "direction": "up", "magnitude": "+5-10pts"},
        "impact": 7, "ease": 7, "confidence": 0.75,
        "time_to_signal_days": 45, "cost": "Low",
        "kill_criteria": "If photo reviews do not lift product-page "
                         "conversion, keep them for the feed only and stop "
                         "paying for them.",
    },
    {
        "key": "botw_as_campaign",
        "name": "Make Brand of the Week an actual campaign",
        "loop": "content", "stage": "retention",
        "owner": "Brand",
        "trigger": any_of(below("community_participation_rate"),
                          below("brand_activation_rate")),
        "hypothesis": "The Brand of the Week slot exists and rotates. As a "
                      "badge it does little; as a weekly campaign with a "
                      "story it does a lot.",
        "mechanism": "A recurring editorial moment gives buyers a reason to "
                     "return on a schedule and gives brands a reason to bring "
                     "their own audience to your platform — brand-supplied "
                     "demand is the cheapest acquisition a marketplace gets, "
                     "and it lands those visitors in a catalogue full of "
                     "*other* brands.",
        "steps": [
            "Pair each slot with a short interview and behind-the-scenes "
            "photos.",
            "Require the featured brand to post it to their own channels — "
            "make that the price of the slot.",
            "Bundle an exclusive piece or an early drop with the feature.",
            "Measure new buyers attributable to each feature week.",
        ],
        "expected": {"metric": "community_participation_rate",
                     "direction": "up", "magnitude": "+2-6pts, plus "
                     "brand-supplied traffic"},
        "impact": 6, "ease": 8, "confidence": 0.7,
        "time_to_signal_days": 30, "cost": "Low — editorial time",
        "kill_criteria": "If featured brands will not promote the feature, "
                         "the slot is not valuable enough — raise what it "
                         "includes or drop it.",
    },

    # ---------------- Instrumentation ----------------
    {
        "key": "acquisition_attribution",
        "name": "Capture where buyers actually come from",
        "loop": "referral", "stage": "atomic_network",
        "owner": "Growth / Engineering",
        "trigger": always,
        "hypothesis": "There is no acquisition-source field anywhere in the "
                      "schema, so channel mix, blended CAC and organic share "
                      "are all guesses.",
        "mechanism": "Without attribution you cannot tell a compounding "
                     "network from a paid-traffic business, which means you "
                     "cannot tell whether growth is real. It is also the "
                     "prerequisite for every later decision about where to "
                     "spend — one small schema change unlocks the whole "
                     "class.",
        "steps": [
            "Persist first-touch source, medium, campaign and referral code "
            "on the user document at registration.",
            "Store landing page and UTM parameters in a first-party cookie "
            "before signup, and carry them through.",
            "Add channel to the admin funnel view and report new buyers by "
            "channel weekly.",
            "Backfill what you can from referral codes and existing email "
            "sends so the series does not start from zero.",
        ],
        "expected": {"metric": "organic_share_of_new_buyers",
                     "direction": "up", "magnitude": "makes it measurable at "
                     "all"},
        "impact": 8, "ease": 8, "confidence": 0.95,
        "time_to_signal_days": 14, "cost": "Low — one schema change",
        "kill_criteria": "None. This is table stakes for every decision above.",
    },
    {
        "key": "north_star_cross_brand",
        "name": "Adopt weekly cross-brand active buyers as the north star",
        "loop": "density", "stage": "atomic_network",
        "owner": "Founder / Growth",
        "trigger": always,
        "hypothesis": "GMV can rise while the network gets weaker. A metric "
                      "that only moves when the *network* works stops that "
                      "from happening quietly.",
        "mechanism": "The metric a team reports weekly is the metric it "
                     "optimises. Cross-brand active buyers cannot be improved "
                     "by leaning harder on one big seller, by discounting, or "
                     "by buying traffic that does not convert — it only rises "
                     "when both sides genuinely get denser. It is the closest "
                     "single number to 'the network effect is working'.",
        "steps": [
            "Define it: buyers who purchased from 2+ distinct brands in the "
            "last 90 days.",
            "Put it at the top of the weekly review, above GMV.",
            "Set a quarterly target and hold each play against it.",
            "Report GMV both with and without the largest brand alongside it.",
        ],
        "expected": {"metric": "multi_brand_buyer_rate", "direction": "up",
                     "magnitude": "focusing effect; no direct lift"},
        "impact": 7, "ease": 10, "confidence": 0.8,
        "time_to_signal_days": 7, "cost": "£0",
        "kill_criteria": "None — replace only if a better single measure of "
                         "network health emerges.",
    },
]

# Stage order for sequencing decisions.
STAGE_ORDER = ["atomic_network", "liquidity", "retention", "density", "scale"]


def ice(play: dict) -> float:
    """ICE on a 0-100 scale: impact × confidence × ease."""
    return round(play["impact"] * play["confidence"] * play["ease"], 1)


def build_playbook(bundle: dict, diagnosis: dict, limit: int = 8) -> dict:
    """Select, score and sequence plays for the current state of the network.

    Ranking is ICE, then a stage multiplier. The multiplier is what turns a
    list of good ideas into advice: a play aimed two stages ahead is
    down-weighted hard, because doing it now is how teams spend a quarter
    making a stage-1 problem worse.
    """
    m = bundle["metrics"]
    d = bundle.get("detail", {})
    c = bundle.get("coverage", {})
    current_stage = diagnosis["stage"]["current"]
    current_idx = STAGE_ORDER.index(current_stage) if current_stage in STAGE_ORDER else 0
    weakest = diagnosis.get("weakest_loop")
    fired_loops = {f["loop"] for f in diagnosis.get("findings", [])}

    selected: List[dict] = []
    deferred: List[dict] = []

    for play in PLAYS:
        try:
            triggered = bool(play["trigger"](m, d, c))
        except Exception:  # a malformed metric must never break the playbook
            triggered = False
        if not triggered:
            continue

        play_idx = STAGE_ORDER.index(play["stage"]) if play["stage"] in STAGE_ORDER else 0
        distance = play_idx - current_idx
        if distance <= 0:
            # Current stage, or unfinished business from an earlier one.
            stage_weight = 1.0 if distance == 0 else 0.85
            stage_note = None
        elif distance == 1:
            stage_weight = 0.45
            stage_note = ("One stage ahead. Worth preparing, not worth "
                          "staffing until the current gate clears.")
        else:
            stage_weight = 0.2
            stage_note = (f"Belongs to the '{play['stage']}' stage. Running it "
                          f"now spends effort on a problem you do not have "
                          f"yet, while the real constraint stays put.")

        loop_weight = 1.15 if play["loop"] == weakest else (
            1.05 if play["loop"] in fired_loops else 1.0
        )

        row = {
            "key": play["key"],
            "name": play["name"],
            "loop": play["loop"],
            "stage": play["stage"],
            "owner": play["owner"],
            "hypothesis": play["hypothesis"],
            "mechanism": play["mechanism"],
            "steps": play["steps"],
            "expected": play["expected"],
            "impact": play["impact"],
            "ease": play["ease"],
            "confidence": play["confidence"],
            "ice": ice(play),
            "priority": round(ice(play) * stage_weight * loop_weight, 1),
            "time_to_signal_days": play["time_to_signal_days"],
            "cost": play["cost"],
            "kill_criteria": play["kill_criteria"],
            "stage_note": stage_note,
            "in_stage": distance <= 0,
        }
        (selected if distance <= 0 else deferred).append(row)

    selected.sort(key=lambda p: p["priority"], reverse=True)
    deferred.sort(key=lambda p: p["priority"], reverse=True)

    now = selected[:3]
    nxt = selected[3:limit]
    later = deferred[:6]

    return {
        "stage": current_stage,
        "now": now,
        "next": nxt,
        "later": later,
        "not_yet": [
            {
                "key": p["key"], "name": p["name"], "stage": p["stage"],
                "reason": p["stage_note"],
            }
            for p in deferred[:6]
        ],
        "counts": {
            "triggered": len(selected) + len(deferred),
            "in_stage": len(selected),
            "deferred": len(deferred),
        },
    }
