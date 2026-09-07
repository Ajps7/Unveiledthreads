"""Tests for play selection, ICE ranking and stage sequencing."""
import pytest

from growth.diagnostics import diagnose
from growth.metrics import compute_metrics
from growth.narrative import build_memo
from growth.playbook import PLAYS, STAGE_ORDER, build_playbook, ice
from growth.tests.factory import marketplace


def _run(raw):
    bundle = compute_metrics(raw)
    diagnosis = diagnose(bundle)
    return bundle, diagnosis, build_playbook(bundle, diagnosis)


class TestLibraryIntegrity:
    def test_every_play_is_complete(self):
        required = {"key", "name", "loop", "stage", "owner", "trigger",
                    "hypothesis", "mechanism", "steps", "expected", "impact",
                    "ease", "confidence", "time_to_signal_days", "cost",
                    "kill_criteria"}
        for play in PLAYS:
            assert required <= set(play), f"{play.get('key')} is missing fields"
            assert play["steps"], f"{play['key']} has no steps"
            assert play["stage"] in STAGE_ORDER, f"{play['key']} has a bad stage"
            assert 1 <= play["impact"] <= 10
            assert 1 <= play["ease"] <= 10
            assert 0 < play["confidence"] <= 1

    def test_play_keys_are_unique(self):
        keys = [p["key"] for p in PLAYS]
        assert len(keys) == len(set(keys))

    def test_every_play_names_kill_criteria(self):
        # A play you cannot stop is a religion, not an experiment.
        for play in PLAYS:
            assert len(play["kill_criteria"]) > 20, play["key"]

    def test_ice_is_bounded(self):
        for play in PLAYS:
            assert 0 < ice(play) <= 100

    def test_every_loop_has_at_least_one_play(self):
        loops = {p["loop"] for p in PLAYS}
        assert loops >= {"supply", "demand", "retention", "density",
                         "referral", "content"}


class TestTriggering:
    def test_plays_are_selected_by_the_marketplace_state(self):
        siloed = marketplace(brands=10, buyers=30, orders_per_buyer=2,
                             brands_per_buyer=1, listings_per_brand=8,
                             views_per_order=25)
        _b, _d, pb = _run(siloed)
        keys = {p["key"] for p in pb["now"] + pb["next"] + pb["later"]}
        assert "cross_brand_rails" in keys, (
            "a siloed marketplace must be offered the cross-brand play"
        )

    def test_oversupply_triggers_the_recruitment_pause(self):
        _b, _d, pb = _run(marketplace(brands=30, listings_per_brand=100,
                                      buyers=3, orders_per_buyer=1))
        keys = {p["key"] for p in pb["now"] + pb["next"]}
        assert "supply_recruitment_pause" in keys

    def test_undersupply_does_not_trigger_the_recruitment_pause(self):
        _b, _d, pb = _run(marketplace(brands=2, listings_per_brand=1,
                                      buyers=50, orders_per_buyer=1))
        keys = {p["key"] for p in pb["now"] + pb["next"] + pb["later"]}
        assert "supply_recruitment_pause" not in keys

    def test_attribution_play_always_fires(self):
        # It is triggered by a schema gap, not by a metric, so it holds in
        # every state of the marketplace.
        for raw in (marketplace(brands=0, buyers=0, orders_per_buyer=0),
                    marketplace(brands=20, buyers=200, orders_per_buyer=4)):
            _b, _d, pb = _run(raw)
            keys = {p["key"] for p in pb["now"] + pb["next"] + pb["later"]}
            assert "acquisition_attribution" in keys

    def test_a_broken_trigger_cannot_break_the_playbook(self):
        import growth.playbook as pbmod

        def _explodes(m, d, c):
            raise ValueError("bad metric")

        original = pbmod.PLAYS[0]["trigger"]
        pbmod.PLAYS[0]["trigger"] = _explodes
        try:
            _b, _d, pb = _run(marketplace(brands=5, buyers=10))
            assert pb["counts"]["triggered"] >= 0
        finally:
            pbmod.PLAYS[0]["trigger"] = original


class TestSequencing:
    def test_later_stage_plays_are_deferred_not_recommended(self):
        # A marketplace with no transactions is at the atomic-network stage;
        # scaling plays must not appear in "now".
        _b, diagnosis, pb = _run(marketplace(brands=4, buyers=0,
                                             orders_per_buyer=0))
        assert diagnosis["stage"]["current"] == "atomic_network"
        current_idx = STAGE_ORDER.index("atomic_network")
        for play in pb["now"]:
            assert STAGE_ORDER.index(play["stage"]) <= current_idx

    def test_deferred_plays_explain_why_they_are_deferred(self):
        _b, _d, pb = _run(marketplace(brands=4, buyers=0, orders_per_buyer=0))
        for entry in pb["not_yet"]:
            assert entry["reason"], f"{entry['key']} deferred with no reason"

    def test_a_play_two_stages_ahead_ranks_below_one_stage_ahead(self):
        _b, _d, pb = _run(marketplace(brands=4, buyers=0, orders_per_buyer=0))
        by_key = {p["key"]: p for p in pb["later"]}
        near = [p for p in by_key.values()
                if STAGE_ORDER.index(p["stage"]) == 1]
        far = [p for p in by_key.values()
               if STAGE_ORDER.index(p["stage"]) >= 3]
        if near and far:
            # Compare the stage multiplier's effect at equal ICE.
            assert max(p["priority"] / p["ice"] for p in near) > \
                   max(p["priority"] / p["ice"] for p in far)

    def test_now_is_ranked_by_priority(self):
        _b, _d, pb = _run(marketplace(brands=8, buyers=25, orders_per_buyer=2,
                                      brands_per_buyer=1))
        priorities = [p["priority"] for p in pb["now"]]
        assert priorities == sorted(priorities, reverse=True)

    def test_now_is_capped_so_the_list_stays_actionable(self):
        _b, _d, pb = _run(marketplace(brands=30, listings_per_brand=60,
                                      buyers=4, orders_per_buyer=1))
        assert len(pb["now"]) <= 3

    def test_plays_in_the_weakest_loop_are_boosted(self):
        # Compare like with like: priority is ICE x stage weight x loop
        # weight, so only plays at the SAME stage can be compared directly.
        # A weakest-loop play can still rank below its own raw ICE if it is
        # remedial work from an earlier stage.
        bundle = compute_metrics(marketplace(brands=10, buyers=30,
                                             orders_per_buyer=2,
                                             brands_per_buyer=1))
        diagnosis = diagnose(bundle)
        pb = build_playbook(bundle, diagnosis)
        weakest = diagnosis["weakest_loop"]
        rows = pb["now"] + pb["next"] + pb["later"]

        by_stage = {}
        for play in rows:
            by_stage.setdefault(play["stage"], []).append(play)

        compared = 0
        for plays in by_stage.values():
            weak_loop = [p for p in plays if p["loop"] == weakest]
            other = [p for p in plays if p["loop"] != weakest]
            if not weak_loop or not other:
                continue
            compared += 1
            assert max(p["priority"] / p["ice"] for p in weak_loop) > \
                   min(p["priority"] / p["ice"] for p in other)
        assert compared, "no same-stage comparison was available"


class TestMemo:
    def test_memo_has_every_section(self):
        bundle, diagnosis, pb = _run(marketplace(brands=8, buyers=25,
                                                 orders_per_buyer=2))
        memo = build_memo(bundle, diagnosis, pb)
        assert memo["headline"]
        assert memo["where_we_are"]
        assert memo["next_30_days"]
        assert memo["stop_doing"]
        assert memo["what_would_change_my_mind"]

    def test_memo_is_deterministic(self):
        raw = marketplace(brands=8, buyers=25, orders_per_buyer=2)
        first = build_memo(*_run(raw))
        second = build_memo(*_run(raw))
        assert first == second

    def test_empty_marketplace_memo_says_so_plainly(self):
        bundle, diagnosis, pb = _run(marketplace(brands=5, buyers=0,
                                                 orders_per_buyer=0))
        memo = build_memo(bundle, diagnosis, pb)
        assert "no transaction base" in memo["headline"].lower()

    def test_memo_never_reports_none_as_a_number(self):
        bundle, diagnosis, pb = _run(marketplace(brands=2, buyers=1,
                                                 orders_per_buyer=1))
        memo = build_memo(bundle, diagnosis, pb)
        blob = repr(memo)
        assert "None" not in blob, "a None leaked into user-facing memo copy"
