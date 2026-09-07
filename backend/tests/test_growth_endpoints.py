"""Integration tests for the Network Effects Command Center endpoints.

Like every other suite in this directory these run against a LIVE server at
REACT_APP_BACKEND_URL — they are not unit tests. The engine's formulas and
judgment are covered separately and hermetically in
`backend/growth/tests/`, which needs no server and no database.

Credentials are read from the environment (GROWTH_TEST_ADMIN_EMAIL /
GROWTH_TEST_ADMIN_PASSWORD, falling back to ADMIN_EMAIL / ADMIN_PASSWORD)
rather than hardcoded, so this file adds no new plaintext password to the
repository. The suite skips itself when they are absent.
"""
import os

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE = line.strip().split("=", 1)[1].rstrip("/")
                    break
    except OSError:
        BASE = ""

ADMIN_EMAIL = (os.environ.get("GROWTH_TEST_ADMIN_EMAIL")
               or os.environ.get("ADMIN_EMAIL", ""))
ADMIN_PASSWORD = (os.environ.get("GROWTH_TEST_ADMIN_PASSWORD")
                  or os.environ.get("ADMIN_PASSWORD", ""))

pytestmark = pytest.mark.skipif(
    not (BASE and ADMIN_EMAIL and ADMIN_PASSWORD),
    reason="Set REACT_APP_BACKEND_URL and admin credentials to run these.",
)


@pytest.fixture(scope="module")
def admin() -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def unauth() -> requests.Session:
    return requests.Session()


GET_ENDPOINTS = ["/api/growth/snapshot", "/api/growth/diagnosis",
                 "/api/growth/playbook", "/api/growth/cohorts",
                 "/api/growth/brief"]


class TestAccessControl:
    @pytest.mark.parametrize("path", GET_ENDPOINTS)
    def test_requires_authentication(self, unauth, path):
        assert unauth.get(f"{BASE}{path}", timeout=20).status_code == 401

    def test_simulate_requires_authentication(self, unauth):
        r = unauth.post(f"{BASE}/api/growth/simulate", json={"months": 12}, timeout=20)
        assert r.status_code == 401


class TestBrief:
    def test_returns_the_whole_command_center_payload(self, admin):
        r = admin.get(f"{BASE}/api/growth/brief?days=90", timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert {"metrics", "detail", "coverage", "diagnosis", "playbook",
                "memo", "simulator_defaults", "bands"} <= set(body)
        assert body["window_days"] == 90

    def test_diagnosis_carries_loops_stage_and_confidence(self, admin):
        d = admin.get(f"{BASE}/api/growth/brief", timeout=60).json()["diagnosis"]
        assert len(d["loops"]) == 6
        assert d["stage"]["current"]
        assert d["confidence"]["level"] in ("very_low", "low", "medium", "high")

    def test_memo_always_names_something_to_stop(self, admin):
        memo = admin.get(f"{BASE}/api/growth/brief", timeout=60).json()["memo"]
        assert memo["headline"]
        assert memo["stop_doing"]

    def test_window_is_clamped_rather_than_erroring(self, admin):
        assert admin.get(f"{BASE}/api/growth/snapshot?days=1",
                         timeout=60).json()["window_days"] == 7
        assert admin.get(f"{BASE}/api/growth/snapshot?days=99999",
                         timeout=60).json()["window_days"] == 365


class TestSimulate:
    def test_returns_base_scenario_and_delta(self, admin):
        r = admin.post(f"{BASE}/api/growth/simulate",
                       json={"months": 12, "k_factor": 0.3}, timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["scenario"]["series"]) == 12
        assert "ending_gmv" in body["scenario"]["summary"]
        assert "ending_gmv" in body["delta"]

    def test_seeds_the_baseline_from_measured_data(self, admin):
        body = admin.post(f"{BASE}/api/growth/simulate", json={"months": 6},
                          timeout=60).json()
        # With no overrides the scenario IS the baseline, so the delta is nil.
        assert body["delta"]["ending_gmv"] == 0
        assert body["baseline_params"]["take_rate"] > 0

    @pytest.mark.parametrize("payload", [
        {"months": 999},          # beyond the 60-month cap
        {"cac": -5},              # must be positive
        {"buyer_retention": 1.5},  # a probability
        {"k_factor": -1},
    ])
    def test_rejects_out_of_range_inputs(self, admin, payload):
        r = admin.post(f"{BASE}/api/growth/simulate", json=payload, timeout=30)
        assert r.status_code == 422, (payload, r.status_code)
