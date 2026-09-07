"""Tests for the flywheel model — especially its feedback loops.

The point of these is that the model must behave like a marketplace, not
like a spreadsheet: supply must be able to collapse, depth must be able to
throttle conversion, and no input should be able to produce a negative
population.
"""
import pytest

from growth.metrics import compute_metrics
from growth.simulator import (
    DEFAULTS, TARGET_LISTINGS_PER_BUYER, compare, depth_multiplier,
    effective_take_rate, params_from_bundle, simulate,
)
from growth.tests.factory import marketplace


class TestTakeRate:
    def test_matches_the_buyer_protection_formula(self):
        # 5% + £0.49, capped at £6.
        assert effective_take_rate(45) == pytest.approx((45 * 0.05 + 0.49) / 45)

    def test_cap_bites_on_large_baskets(self):
        assert effective_take_rate(500) == pytest.approx(6.0 / 500)

    def test_take_rate_falls_as_basket_size_rises(self):
        rates = [effective_take_rate(v) for v in (20, 45, 100, 300, 600)]
        assert rates == sorted(rates, reverse=True)

    def test_zero_aov_is_zero_not_a_division_error(self):
        assert effective_take_rate(0) == 0.0


class TestDepthMultiplier:
    def test_is_neutral_at_the_target_depth(self):
        assert depth_multiplier(TARGET_LISTINGS_PER_BUYER) == pytest.approx(1.0)

    def test_thin_catalogue_throttles_conversion(self):
        assert depth_multiplier(0.5) < 1.0

    def test_returns_diminish_and_are_capped(self):
        assert depth_multiplier(1000) <= 1.35
        # Doubling depth well past target buys almost nothing.
        assert depth_multiplier(200) - depth_multiplier(100) < 0.05

    def test_elasticity_of_zero_disables_the_effect(self):
        assert depth_multiplier(0.1, elasticity=0.0) == pytest.approx(1.0)
        assert depth_multiplier(50, elasticity=0.0) == pytest.approx(1.0)

    def test_empty_catalogue_does_not_divide_by_zero(self):
        assert depth_multiplier(0) > 0


class TestSimulation:
    def test_produces_one_row_per_month(self):
        out = simulate({"months": 18})
        assert len(out["series"]) == 18
        assert [r["month"] for r in out["series"]] == list(range(1, 19))

    def test_months_are_clamped_to_a_sane_range(self):
        assert len(simulate({"months": 500})["series"]) == 60
        assert len(simulate({"months": 0})["series"]) == 1

    def test_populations_never_go_negative(self):
        out = simulate({"months": 36, "buyer_retention": 0.05,
                        "brand_retention": 0.1,
                        "baseline_organic_new_buyers": 0,
                        "brand_adds_per_month": 0})
        for row in out["series"]:
            assert row["active_buyers"] >= 0
            assert row["brands"] >= 0
            assert row["gmv"] >= 0

    def test_unknown_parameters_are_ignored(self):
        out = simulate({"months": 3, "not_a_real_lever": 999})
        assert "not_a_real_lever" not in out["params"]

    def test_none_values_fall_back_to_defaults(self):
        out = simulate({"months": 3, "aov": None})
        assert out["params"]["aov"] == DEFAULTS["aov"]


class TestFeedbackLoops:
    def test_oversupply_starves_brands_and_collapses_supply(self):
        # Far too many brands chasing far too little demand: GMV per brand is
        # tiny, so brands churn faster than they are replaced.
        out = simulate({"months": 12, "brands": 80, "listings_per_brand": 30,
                        "active_buyers": 60, "baseline_organic_new_buyers": 5})
        assert out["summary"]["ending_brands"] < 80 * 0.5
        assert out["summary"]["binding_constraint"] == "supply retention"

    def test_supply_churn_sensitivity_of_zero_disables_the_spiral(self):
        params = {"months": 12, "brands": 80, "listings_per_brand": 30,
                  "active_buyers": 60, "baseline_organic_new_buyers": 5}
        spiral = simulate(params)
        flat = simulate({**params, "supply_churn_sensitivity": 0.0})
        assert flat["summary"]["ending_brands"] > spiral["summary"]["ending_brands"]

    def test_thin_catalogue_is_named_as_the_binding_constraint(self):
        out = simulate({"months": 12, "brands": 3, "listings_per_brand": 2,
                        "active_buyers": 400})
        assert out["summary"]["binding_constraint"] == "catalogue depth"

    def test_referral_compounds_on_previous_month_acquisition(self):
        base = simulate({"months": 12, "k_factor": 0.0})
        viral = simulate({"months": 12, "k_factor": 0.4})
        assert viral["summary"]["ending_active_buyers"] > \
               base["summary"]["ending_active_buyers"]
        # The viral term must build over time, not apply as a flat uplift.
        early = viral["series"][1]["referral_new_buyers"]
        late = viral["series"][-1]["referral_new_buyers"]
        assert late > early

    def test_paid_spend_buys_buyers_at_the_stated_cac(self):
        out = simulate({"months": 1, "monthly_paid_spend": 1000, "cac": 20})
        assert out["series"][0]["paid_new_buyers"] == pytest.approx(50.0)

    def test_organic_acquisition_scales_with_catalogue_breadth(self):
        # Breadth is measured against the run's own starting catalogue, so
        # month 1 always equals the stated baseline.
        out = simulate({"months": 1, "baseline_organic_new_buyers": 40})
        assert out["series"][0]["organic_new_buyers"] == pytest.approx(40.0)


class TestEconomics:
    def test_ltv_cac_and_payback_are_consistent(self):
        # Use a scenario with a meaningful LTV: the summary rounds to 2dp, so
        # at sub-£2 lifetime values the rounding dominates the comparison.
        out = simulate({"months": 12, "cac": 10, "aov": 100.0,
                        "orders_per_buyer_month": 1.0,
                        "buyer_retention": 0.8})
        s = out["summary"]
        assert s["ltv_cac"] == pytest.approx(s["ltv"] / 10, rel=1e-2)
        assert s["payback_months"] > 0

    def test_unprofitable_unit_economics_report_no_payback(self):
        out = simulate({"months": 6, "take_rate": 0.0,
                        "variable_cost_per_order": 5.0})
        assert out["summary"]["payback_months"] is None

    def test_spend_shows_up_in_contribution(self):
        free = simulate({"months": 6, "monthly_paid_spend": 0})
        paid = simulate({"months": 6, "monthly_paid_spend": 5000})
        assert paid["summary"]["cumulative_contribution"] < \
               free["summary"]["cumulative_contribution"]

    def test_escape_velocity_requires_growth_supply_and_organic_share(self):
        # Growth bought entirely with paid money is not escape velocity.
        bought = simulate({"months": 12, "monthly_paid_spend": 20000,
                           "cac": 10, "baseline_organic_new_buyers": 1})
        assert bought["summary"]["organic_share_of_new_buyers"] < 0.5
        assert bought["summary"]["escape_velocity"] is False

    def test_a_working_flywheel_reaches_escape_velocity(self):
        out = simulate({"months": 18, "k_factor": 0.4, "buyer_retention": 0.7,
                        "brand_adds_per_month": 8,
                        "baseline_organic_new_buyers": 80})
        assert out["summary"]["escape_velocity"] is True


class TestSeedingFromRealData:
    def test_params_are_seeded_from_measured_metrics(self):
        bundle = compute_metrics(marketplace(brands=6, buyers=30,
                                             orders_per_buyer=2,
                                             listings_per_brand=10))
        p = params_from_bundle(bundle)
        assert p["active_buyers"] == bundle["metrics"]["active_buyers"]
        assert p["aov"] == pytest.approx(bundle["metrics"]["aov"])
        assert p["take_rate"] == pytest.approx(
            effective_take_rate(bundle["metrics"]["aov"]), rel=1e-3)

    def test_unmeasured_inputs_fall_back_to_defaults(self):
        bundle = compute_metrics({"window_days": 90})
        p = params_from_bundle(bundle)
        assert p["active_buyers"] == DEFAULTS["active_buyers"]

    def test_overrides_beat_measured_values(self):
        bundle = compute_metrics(marketplace(brands=6, buyers=30,
                                             orders_per_buyer=2))
        p = params_from_bundle(bundle, overrides={"active_buyers": 9999})
        assert p["active_buyers"] == 9999

    def test_fee_config_drives_the_take_rate(self):
        bundle = compute_metrics(marketplace(brands=4, buyers=10,
                                             orders_per_buyer=1,
                                             gmv_per_order=100.0))
        p = params_from_bundle(bundle, fee_config={"rate": 0.1, "fixed": 0.0,
                                                   "cap": 100.0})
        assert p["take_rate"] == pytest.approx(0.1)


class TestCompare:
    def test_compare_reports_the_delta_between_scenarios(self):
        out = compare({"months": 12}, {"months": 12, "k_factor": 0.4,
                                       "buyer_retention": 0.75})
        assert out["delta"]["ending_gmv"] > 0
        assert out["base"]["summary"]["ending_gmv"] < \
               out["scenario"]["summary"]["ending_gmv"]

    def test_identical_scenarios_have_a_zero_delta(self):
        out = compare({"months": 6}, {"months": 6})
        assert out["delta"]["ending_gmv"] == 0
