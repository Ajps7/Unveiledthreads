"""Tests for the judgment layer: scoring, failure modes and sequencing."""
import pytest

from growth.benchmarks import BANDS, STAGE_GATES, rate
from growth.diagnostics import (
    LOOPS, assess_confidence, assess_stage, detect_failure_modes, diagnose,
    score_metric,
)
from growth.metrics import compute_metrics
from growth.tests.factory import marketplace


def _findings(raw) -> set:
    return {f["key"] for f in detect_failure_modes(compute_metrics(raw))}


class TestScoring:
    def test_band_thresholds_anchor_at_40_and_80(self):
        weak, healthy = BANDS["sell_through_rate"]["weak"], BANDS["sell_through_rate"]["healthy"]
        assert score_metric("sell_through_rate", weak) == 40.0
        assert score_metric("sell_through_rate", healthy) == 80.0
        assert score_metric("sell_through_rate", 0.0) == 0.0

    def test_score_is_monotonic_for_higher_is_better(self):
        scores = [score_metric("repeat_buyer_rate", v)
                  for v in (0.0, 0.05, 0.12, 0.2, 0.3, 0.6)]
        assert scores == sorted(scores)

    def test_lower_is_better_metrics_are_inverted(self):
        # HHI: concentrated is bad, so a high value must score low.
        assert score_metric("gmv_hhi", 0.05) > score_metric("gmv_hhi", 0.5)
        assert score_metric("gmv_hhi", BANDS["gmv_hhi"]["healthy"]) == 80.0
        assert score_metric("gmv_hhi", BANDS["gmv_hhi"]["weak"]) == 40.0

    def test_overshoot_tapers_rather_than_running_away(self):
        # Twice healthy is worth far less than getting off the floor.
        assert score_metric("sell_through_rate", 5.0) <= 100.0
        assert score_metric("sell_through_rate", 0.7) < 101

    def test_unmeasurable_metrics_score_none_not_zero(self):
        assert score_metric("k_factor", None) is None
        assert score_metric("not_a_metric", 0.5) is None

    def test_rate_labels_match_the_bands(self):
        assert rate("sell_through_rate", 0.5) == "healthy"
        assert rate("sell_through_rate", 0.25) == "developing"
        assert rate("sell_through_rate", 0.05) == "weak"
        assert rate("sell_through_rate", None) == "unknown"
        # Lower-is-better inverts.
        assert rate("gmv_hhi", 0.10) == "healthy"
        assert rate("gmv_hhi", 0.40) == "weak"

    def test_loop_score_ignores_unmeasurable_metrics(self):
        # With referrals gated off there are no code-holders to divide by, so
        # K is unmeasurable — but "0% of new users were referred" IS a
        # measurement. The loop therefore scores off the metric it can see
        # and reports that it only weighed part of itself.
        raw = marketplace(brands=4, buyers=8, orders_per_buyer=1,
                          referral_codes=0, referral_uses=0)
        out = diagnose(compute_metrics(raw))
        referral = next(l for l in out["loops"] if l["key"] == "referral")
        assert referral["score"] == 0.0
        assert referral["measured_weight"] < 1.0
        k = next(p for p in referral["metrics"] if p["key"] == "k_factor")
        assert k["score"] is None and k["rating"] == "unknown"

    def test_loop_score_is_none_when_nothing_in_it_is_measurable(self):
        out = diagnose(compute_metrics({"window_days": 90}))
        density = next(l for l in out["loops"] if l["key"] == "density")
        assert density["score"] is None
        assert density["status"] == "unknown"

    def test_every_loop_metric_has_a_band(self):
        # A loop metric with no band silently drops out of its own score.
        from growth.benchmarks import lookup_band
        for loop in LOOPS:
            for key, _weight in loop["metrics"]:
                assert lookup_band(key) is not None, f"{key} has no band"

    def test_loop_weights_sum_to_one(self):
        for loop in LOOPS:
            assert sum(w for _k, w in loop["metrics"]) == pytest.approx(1.0)


class TestFailureModes:
    def test_silo_marketplace_fires_when_buyers_never_cross_brands(self):
        raw = marketplace(brands=8, buyers=20, orders_per_buyer=2,
                          brands_per_buyer=1)
        assert "silo_marketplace" in _findings(raw)

    def test_silo_marketplace_stays_quiet_when_buyers_do_cross(self):
        raw = marketplace(brands=8, buyers=20, orders_per_buyer=3,
                          brands_per_buyer=3)
        assert "silo_marketplace" not in _findings(raw)

    def test_one_brand_marketplace_fires_on_concentration(self):
        raw = marketplace(brands=8, buyers=20, orders_per_buyer=1,
                          selling_brands=1)
        assert "one_brand_marketplace" in _findings(raw)

    def test_ghost_town_fires_on_oversupply_with_no_sell_through(self):
        raw = marketplace(brands=20, listings_per_brand=100, buyers=3,
                          orders_per_buyer=1)
        assert "ghost_town" in _findings(raw)

    def test_empty_shelves_fires_on_undersupply(self):
        raw = marketplace(brands=1, listings_per_brand=1, buyers=40,
                          orders_per_buyer=1)
        assert "empty_shelves" in _findings(raw)

    def test_leaky_bucket_fires_on_low_repeat_rate(self):
        raw = marketplace(brands=5, buyers=50, orders_per_buyer=1)
        assert "leaky_bucket" in _findings(raw)

    def test_discovery_breakdown_needs_real_traffic_before_it_fires(self):
        # Same terrible conversion rate, but only a handful of views: with
        # this little traffic the honest answer is "we cannot tell".
        thin = marketplace(brands=3, buyers=1, orders_per_buyer=1,
                           views_per_order=20)
        assert "discovery_breakdown" not in _findings(thin)

        heavy = marketplace(brands=3, buyers=2, orders_per_buyer=1,
                            views_per_order=1000)
        assert "discovery_breakdown" in _findings(heavy)

    def test_supply_activation_failure_fires_when_most_brands_never_sell(self):
        raw = marketplace(brands=20, buyers=4, orders_per_buyer=1,
                          selling_brands=2)
        assert "supply_activation_failure" in _findings(raw)

    def test_no_word_of_mouth_fires_when_referrals_are_gated_off(self):
        raw = marketplace(brands=4, buyers=10, referral_codes=0)
        assert "no_word_of_mouth" in _findings(raw)

    def test_no_transactions_fires_on_an_empty_marketplace(self):
        raw = marketplace(brands=5, buyers=0, orders_per_buyer=0)
        assert "no_transactions" in _findings(raw)

    def test_findings_are_ordered_by_severity(self):
        raw = marketplace(brands=20, listings_per_brand=100, buyers=3,
                          orders_per_buyer=1)
        sev = [f["severity"] for f in detect_failure_modes(compute_metrics(raw))]
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        assert sev == sorted(sev, key=lambda s: order[s])

    def test_a_healthy_marketplace_fires_no_critical_findings(self):
        raw = marketplace(brands=12, listings_per_brand=12, buyers=40,
                          orders_per_buyer=3, brands_per_buyer=3,
                          views_per_order=30, posts=30, referral_codes=40,
                          referral_uses=20, wishlist_items=40,
                          wishlist_converted=12)
        findings = detect_failure_modes(compute_metrics(raw))
        assert not [f for f in findings if f["severity"] == "critical"]


class TestStageGates:
    def test_empty_marketplace_sits_at_the_first_gate(self):
        raw = marketplace(brands=3, buyers=0, orders_per_buyer=0)
        stage = assess_stage(compute_metrics(raw))
        assert stage["current"] == "atomic_network"
        assert stage["blocking_checks"]

    def test_stage_advances_once_earlier_gates_clear(self):
        raw = marketplace(brands=10, listings_per_brand=10, buyers=40,
                          orders_per_buyer=3, brands_per_buyer=3,
                          views_per_order=25)
        stage = assess_stage(compute_metrics(raw))
        assert stage["current"] != "atomic_network"

    def test_stage_is_the_first_failing_gate_not_the_last_passing_one(self):
        raw = marketplace(brands=10, listings_per_brand=10, buyers=40,
                          orders_per_buyer=3, brands_per_buyer=3,
                          views_per_order=25)
        stage = assess_stage(compute_metrics(raw))
        keys = [s["key"] for s in stage["stages"]]
        idx = keys.index(stage["current"])
        assert all(s["passed"] for s in stage["stages"][:idx])
        assert not stage["stages"][idx]["passed"]

    def test_an_unmeasurable_gate_does_not_pass_by_default(self):
        # Missing data must never be read as a cleared gate — that is how a
        # team talks itself into stage-4 spending on a stage-1 business.
        raw = marketplace(brands=5, buyers=0, orders_per_buyer=0)
        stage = assess_stage(compute_metrics(raw))
        assert not stage["stages"][0]["passed"]

    def test_every_stage_names_something_to_stop(self):
        for stage in STAGE_GATES:
            assert stage["stop"], f"{stage['key']} has no stop guidance"


class TestConfidence:
    def test_thin_data_is_flagged_as_low_confidence(self):
        raw = marketplace(brands=2, buyers=3, orders_per_buyer=1)
        conf = assess_confidence(compute_metrics(raw))
        assert conf["level"] in ("very_low", "low")

    def test_volume_raises_confidence(self):
        raw = marketplace(brands=20, buyers=200, orders_per_buyer=3,
                          views_per_order=30)
        conf = assess_confidence(compute_metrics(raw))
        assert conf["level"] in ("medium", "high")


class TestDiagnoseIntegration:
    def test_diagnose_returns_a_complete_shape(self):
        out = diagnose(compute_metrics(marketplace(brands=6, buyers=20,
                                                   orders_per_buyer=2)))
        assert set(out) >= {"overall_score", "grade", "loops", "weakest_loop",
                            "findings", "stage", "confidence"}
        assert len(out["loops"]) == len(LOOPS)

    def test_weakest_loop_is_the_lowest_scoring_one(self):
        out = diagnose(compute_metrics(marketplace(brands=8, buyers=20,
                                                   orders_per_buyer=2,
                                                   brands_per_buyer=1)))
        scored = [l for l in out["loops"] if l["score"] is not None]
        assert out["weakest_loop"] == min(scored, key=lambda l: l["score"])["key"]

    def test_grade_is_na_when_nothing_is_measurable(self):
        out = diagnose(compute_metrics({"window_days": 90}))
        assert out["grade"] == "n/a"
