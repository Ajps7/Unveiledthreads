"""Unit tests for the pure metric formulas."""
from datetime import timedelta

import pytest

from growth.metrics import (
    compute_metrics, cohort_retention, gini, hhi, safe_div, top_n_share,
    _shift_month,
)
from growth.tests.factory import NOW, days_ago, marketplace


class TestNumericHelpers:
    def test_safe_div_returns_none_not_zero_on_empty_denominator(self):
        # The distinction matters: 0.0 would be reported as a confident
        # "0% conversion" for a week that simply had no traffic.
        assert safe_div(0, 0) is None
        assert safe_div(5, 0) is None
        assert safe_div(0, 5) == 0.0

    def test_gini_of_perfectly_even_distribution_is_zero(self):
        assert gini([10, 10, 10, 10]) == 0.0

    def test_gini_rises_with_concentration(self):
        assert gini([1, 1, 1, 97]) > gini([10, 20, 30, 40])

    def test_gini_of_empty_or_zero_total_is_none(self):
        assert gini([]) is None
        assert gini([0, 0]) is None

    def test_gini_single_value_is_zero_not_one(self):
        # One brand is total concentration, but Gini is undefined for n=1;
        # returning 0.0 avoids a false "perfectly unequal" reading. HHI is
        # the metric that correctly reports 1.0 here.
        assert gini([50]) == 0.0
        assert hhi([50]) == 1.0

    def test_hhi_matches_known_values(self):
        assert hhi([50, 50]) == 0.5
        assert hhi([25, 25, 25, 25]) == 0.25
        assert hhi([100]) == 1.0

    def test_top_n_share(self):
        assert top_n_share([40, 30, 20, 10], 3) == 0.9
        assert top_n_share([], 3) is None

    def test_shift_month_crosses_year_boundary(self):
        assert _shift_month("2025-11", 3) == "2026-02"
        assert _shift_month("2025-12", 1) == "2026-01"
        assert _shift_month("2026-01", 0) == "2026-01"


class TestEmptyMarketplace:
    def test_no_data_yields_none_not_zero(self):
        out = compute_metrics({"now": NOW, "window_days": 90})
        m = out["metrics"]
        for key in ("sell_through_rate", "view_to_order_rate",
                    "repeat_buyer_rate", "multi_brand_buyer_rate", "gmv_hhi"):
            assert m[key] is None, f"{key} should be unmeasurable, not zero"
        assert m["gmv"] == 0
        assert out["coverage"]["gaps"], "an empty marketplace must report gaps"

    def test_attribution_gap_is_always_reported(self):
        # No schema field captures acquisition source, so this gap holds even
        # for a busy marketplace.
        out = compute_metrics(marketplace(buyers=500, orders_per_buyer=3))
        keys = {g["key"] for g in out["coverage"]["gaps"]}
        assert "acquisition_attribution" in keys


class TestLiquidity:
    def test_sell_through_counts_only_mature_listings(self):
        raw = marketplace(brands=2, listings_per_brand=10, buyers=4,
                          orders_per_buyer=1, listing_age_days=60)
        # Add 100 listings created yesterday: they have had no chance to sell
        # and must not drag sell-through down.
        raw["listings"] += [
            {"id": f"fresh{i}", "brand_id": "br0",
             "created_at": days_ago(1), "is_active": True}
            for i in range(100)
        ]
        out = compute_metrics(raw)
        # 20 mature listings, 4 of them sold.
        assert out["metrics"]["sell_through_rate"] == pytest.approx(4 / 20)

    def test_live_listings_excludes_inactive(self):
        raw = marketplace(brands=1, listings_per_brand=4, buyers=1)
        raw["listings"][0]["is_active"] = False
        out = compute_metrics(raw)
        assert out["metrics"]["live_listings"] == 3

    def test_view_to_order_rate(self):
        raw = marketplace(brands=2, buyers=10, orders_per_buyer=1,
                          views_per_order=50)
        out = compute_metrics(raw)
        # 10 orders, 500 views.
        assert out["metrics"]["view_to_order_rate"] == pytest.approx(0.02)

    def test_oversupply_flag_trips_past_the_ceiling(self):
        raw = marketplace(brands=10, listings_per_brand=100, buyers=2,
                          orders_per_buyer=1)
        assert compute_metrics(raw)["metrics"]["oversupplied"] is True
        raw2 = marketplace(brands=2, listings_per_brand=5, buyers=20,
                           orders_per_buyer=1)
        assert compute_metrics(raw2)["metrics"]["oversupplied"] is False


class TestNetworkDensity:
    def test_single_brand_buyers_score_zero_multi_brand_rate(self):
        # Every buyer buys twice, always from the same brand: repeat rate is
        # perfect but there is no network effect at all.
        raw = marketplace(brands=6, buyers=12, orders_per_buyer=2,
                          brands_per_buyer=1)
        m = compute_metrics(raw)["metrics"]
        assert m["repeat_buyer_rate"] == 1.0
        assert m["multi_brand_buyer_rate"] == 0.0

    def test_cross_brand_buyers_score_full_multi_brand_rate(self):
        raw = marketplace(brands=6, buyers=12, orders_per_buyer=2,
                          brands_per_buyer=2)
        m = compute_metrics(raw)["metrics"]
        assert m["multi_brand_buyer_rate"] == 1.0
        assert m["avg_brands_per_repeat_buyer"] == 2.0

    def test_multi_brand_rate_ignores_single_order_buyers(self):
        # A buyer with one order cannot have crossed brands; including them
        # would make this metric a restatement of the repeat rate.
        raw = marketplace(brands=4, buyers=10, orders_per_buyer=1)
        m = compute_metrics(raw)["metrics"]
        assert m["repeat_buyer_rate"] == 0.0
        assert m["multi_brand_buyer_rate"] is None

    def test_concentration_detects_one_brand_marketplace(self):
        raw = marketplace(brands=5, buyers=10, orders_per_buyer=1,
                          selling_brands=1)
        m = compute_metrics(raw)["metrics"]
        assert m["gmv_hhi"] == 1.0
        assert m["top3_gmv_share"] == 1.0

    def test_deleted_buyers_do_not_collapse_into_one_repeat_buyer(self):
        raw = marketplace(brands=2, buyers=3, orders_per_buyer=1)
        for o in raw["orders"]:
            o["buyer_id"] = "deleted-user"
        m = compute_metrics(raw)["metrics"]
        assert m["active_buyers"] == 0
        assert m["repeat_buyer_rate"] is None


class TestSupplyActivation:
    def test_activation_rate_and_time_to_first_sale(self):
        raw = marketplace(brands=4, buyers=4, orders_per_buyer=1,
                          selling_brands=2, brand_age_days=200)
        m = compute_metrics(raw)["metrics"]
        assert m["brand_activation_rate"] == 0.5
        assert m["days_to_first_sale"] is not None

    def test_brands_too_new_to_judge_are_excluded(self):
        raw = marketplace(brands=2, buyers=2, orders_per_buyer=1,
                          selling_brands=2)
        raw["brands"] += [
            {"id": "brand-joined-yesterday", "name": "New",
             "created_at": days_ago(1), "market": "UK", "category": "tees"}
        ]
        m = compute_metrics(raw)["metrics"]
        # Still 100%: the day-old brand has not had a fair chance yet.
        assert m["brand_activation_rate"] == 1.0

    def test_stalled_brands_are_listed_for_follow_up(self):
        raw = marketplace(brands=6, buyers=2, orders_per_buyer=1,
                          selling_brands=1)
        detail = compute_metrics(raw)["detail"]
        assert detail["stalled_brand_count"] == 5
        assert all(b["days_since_join"] > 0 for b in detail["stalled_brands"])


class TestReferralAndCommunity:
    def test_k_factor_is_referrals_per_code_holder(self):
        raw = marketplace(brands=2, buyers=4, referral_codes=10,
                          referral_uses=3)
        m = compute_metrics(raw)["metrics"]
        assert m["k_factor"] == pytest.approx(0.3)

    def test_k_factor_none_when_programme_is_off(self):
        raw = marketplace(brands=2, buyers=4, referral_codes=0, referral_uses=0)
        assert compute_metrics(raw)["metrics"]["k_factor"] is None

    def test_community_participation_counts_likers_not_just_posters(self):
        raw = marketplace(brands=2, buyers=10, orders_per_buyer=1, posts=4)
        m = compute_metrics(raw)["metrics"]
        assert m["community_participation_rate"] > 0
        assert m["engagement_per_post"] == pytest.approx(2.0)  # 1 like + 1 comment
        assert m["brand_tag_rate"] == pytest.approx(0.5)

    def test_wishlist_conversion(self):
        raw = marketplace(brands=2, buyers=10, orders_per_buyer=1,
                          wishlist_items=10, wishlist_converted=3)
        m = compute_metrics(raw)["metrics"]
        assert m["wishlist_conversion_rate"] == pytest.approx(0.3)


class TestAtomicCell:
    def test_finds_the_densest_category_market_cell(self):
        raw = marketplace(brands=3, buyers=9, orders_per_buyer=1,
                          category="tees", market="UK")
        raw["brands"] += [
            {"id": "br-hoodie", "name": "Hoodie Co",
             "created_at": days_ago(200), "market": "UK", "category": "hoodies"}
        ]
        raw["orders"] += [
            {"buyer_id": "u99", "brand_id": "br-hoodie", "product_id": "h1",
             "gmv": 60.0, "created_at": days_ago(5)}
        ]
        cell = compute_metrics(raw)["detail"]["atomic_cell"]
        assert cell["found"] is True
        assert cell["top"]["category"] == "tees"
        assert len(cell["cells"]) == 2

    def test_no_orders_means_no_cell(self):
        raw = marketplace(brands=3, buyers=0, orders_per_buyer=0)
        assert compute_metrics(raw)["detail"]["atomic_cell"]["found"] is False


class TestCohorts:
    def test_cohort_rows_track_repeat_purchase_by_month(self):
        orders = [
            # Two buyers first buy in March; only one comes back in April.
            {"buyer_id": "a", "brand_id": "br0", "product_id": "p",
             "gmv": 40, "created_at": NOW - timedelta(days=90)},
            {"buyer_id": "b", "brand_id": "br0", "product_id": "p",
             "gmv": 40, "created_at": NOW - timedelta(days=90)},
            {"buyer_id": "a", "brand_id": "br1", "product_id": "p2",
             "gmv": 40, "created_at": NOW - timedelta(days=60)},
        ]
        out = cohort_retention(orders, months=6, now=NOW)
        row = next(r for r in out["rows"] if r["size"] == 2)
        assert row["values"][0]["retained"] == 1
        assert row["values"][0]["rate"] == 0.5

    def test_empty_history_is_empty_not_an_error(self):
        assert cohort_retention([], months=6, now=NOW) == {"months": [], "rows": []}


class TestWindowing:
    def test_orders_outside_the_window_are_excluded_from_rates(self):
        raw = marketplace(brands=2, buyers=5, orders_per_buyer=1,
                          window_days=30)
        raw["orders"] += [
            {"buyer_id": "ancient", "brand_id": "br0", "product_id": "old",
             "gmv": 999.0, "created_at": days_ago(400)}
        ]
        m = compute_metrics(raw)["metrics"]
        assert m["gmv"] < 999
        assert "ancient" not in [o["buyer_id"] for o in raw["orders"][:5]]

    def test_prior_window_powers_growth_deltas(self):
        raw = marketplace(brands=2, buyers=4, orders_per_buyer=1,
                          window_days=30)
        raw["orders"] += [
            {"buyer_id": "old1", "brand_id": "br0", "product_id": "x",
             "gmv": 45.0, "created_at": days_ago(40)}
        ]
        out = compute_metrics(raw)
        assert out["detail"]["prior_window"]["gmv"] == 45.0
        assert out["metrics"]["gmv_growth"] is not None
