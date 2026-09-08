# Network Effects Command Center — admin-only growth intelligence endpoints.
#
# The heavy lifting lives in the pure `growth` package; this module is the
# thin adapter: authenticate as admin, pull a snapshot, run the engine, and
# serve JSON. Snapshots are cached briefly because the full read touches
# every collection and an admin refreshing a dashboard should not be able to
# hammer the database.
from core import *  # noqa: F401,F403

import time as _time

from growth import benchmarks as gb
from growth import collector as gcollector
from growth import diagnostics as gdiag
from growth import metrics as gmetrics
from growth import narrative as gnarrative
from growth import playbook as gplaybook
from growth import simulator as gsim

# Window bounds. Under 7 days nothing is measurable; over a year the rates
# describe a business that no longer exists.
MIN_WINDOW_DAYS = 7
MAX_WINDOW_DAYS = 365
DEFAULT_WINDOW_DAYS = 90

GROWTH_CACHE_TTL_SECONDS = int(os.environ.get("GROWTH_CACHE_TTL_SECONDS", "300"))

# Cohort table horizon, in months. Computed once into the cached bundle so the
# cohorts endpoint never triggers a second full read.
COHORT_MONTHS = 12

# {window_days: (expires_at_monotonic, bundle)}. Bounded because the window is
# a free query parameter: without a cap, an admin (or a loop) walking
# ?days=7..365 would pin 359 snapshots in memory.
_snapshot_cache: dict = {}
MAX_CACHED_SNAPSHOTS = 6


def _evict_expired_and_oldest(now: float) -> None:
    for key in [k for k, (expires, _b) in _snapshot_cache.items() if expires <= now]:
        _snapshot_cache.pop(key, None)
    while len(_snapshot_cache) >= MAX_CACHED_SNAPSHOTS:
        oldest = min(_snapshot_cache, key=lambda k: _snapshot_cache[k][0])
        _snapshot_cache.pop(oldest, None)


def _clamp_window(days: int) -> int:
    return max(MIN_WINDOW_DAYS, min(MAX_WINDOW_DAYS, int(days or DEFAULT_WINDOW_DAYS)))


async def _bundle(days: int, refresh: bool = False) -> dict:
    """Metrics bundle for a window, cached for GROWTH_CACHE_TTL_SECONDS."""
    days = _clamp_window(days)
    now = _time.monotonic()
    if not refresh:
        cached = _snapshot_cache.get(days)
        if cached and cached[0] > now:
            return cached[1]

    raw = await gcollector.collect(db, window_days=days, sale_statuses=SALE_STATUSES)
    raw["cohort_months"] = COHORT_MONTHS
    bundle = gmetrics.compute_metrics(raw)
    bundle["detail"]["truncated"] = raw.get("truncated", {})
    # `raw` holds up to 200k view documents; only the computed bundle is
    # retained so the cache stays small.
    _evict_expired_and_oldest(now)
    _snapshot_cache[days] = (now + GROWTH_CACHE_TTL_SECONDS, bundle)
    return bundle


def _fee_config() -> dict:
    return {
        "rate": PLATFORM_FEE_RATE,
        "fixed": PLATFORM_FEE_FIXED,
        "cap": PLATFORM_FEE_CAP,
    }


class SimulationRequest(BaseModel):
    """Simulator inputs.

    Every field is optional: omitted values are seeded from measured reality
    (`params_from_bundle`) and only then from the model defaults, so the
    simulator is useful before anyone has tuned a single number.
    """
    window_days: Optional[int] = None
    months: Optional[int] = Field(default=12, ge=1, le=60)
    # Starting state
    active_buyers: Optional[float] = Field(default=None, ge=0)
    brands: Optional[float] = Field(default=None, ge=0)
    listings_per_brand: Optional[float] = Field(default=None, ge=0)
    aov: Optional[float] = Field(default=None, ge=0)
    orders_per_buyer_month: Optional[float] = Field(default=None, ge=0, le=20)
    # Loops
    buyer_retention: Optional[float] = Field(default=None, ge=0, le=0.99)
    brand_retention: Optional[float] = Field(default=None, ge=0, le=0.99)
    k_factor: Optional[float] = Field(default=None, ge=0, le=5)
    baseline_organic_new_buyers: Optional[float] = Field(default=None, ge=0)
    brand_adds_per_month: Optional[float] = Field(default=None, ge=0)
    # Money
    monthly_paid_spend: Optional[float] = Field(default=None, ge=0)
    cac: Optional[float] = Field(default=None, gt=0)
    take_rate: Optional[float] = Field(default=None, ge=0, le=1)
    variable_cost_per_order: Optional[float] = Field(default=None, ge=0)
    fixed_monthly_cost: Optional[float] = Field(default=None, ge=0)
    # Model behaviour
    depth_elasticity: Optional[float] = Field(default=None, ge=0, le=2)
    supply_churn_sensitivity: Optional[float] = Field(default=None, ge=0, le=1)
    # When true, also run the untouched baseline and return the delta.
    compare_to_baseline: bool = True

    def overrides(self) -> dict:
        skip = {"window_days", "compare_to_baseline"}
        return {
            k: v for k, v in self.model_dump().items()
            if k not in skip and v is not None
        }


@api_router.get("/growth/snapshot")
async def growth_snapshot(request: Request, days: int = DEFAULT_WINDOW_DAYS,
                          refresh: bool = False):
    """Raw computed metrics, supporting detail and data-coverage flags."""
    await require_admin(request)
    bundle = await _bundle(days, refresh=refresh)
    return {
        "window_days": _clamp_window(days),
        "cache_ttl_seconds": GROWTH_CACHE_TTL_SECONDS,
        **bundle,
    }


@api_router.get("/growth/diagnosis")
async def growth_diagnosis(request: Request, days: int = DEFAULT_WINDOW_DAYS,
                           refresh: bool = False):
    """Loop scores, named failure modes, stage gates and confidence."""
    await require_admin(request)
    bundle = await _bundle(days, refresh=refresh)
    return {"window_days": _clamp_window(days), **gdiag.diagnose(bundle)}


@api_router.get("/growth/playbook")
async def growth_playbook(request: Request, days: int = DEFAULT_WINDOW_DAYS,
                          refresh: bool = False):
    """Triggered plays, ranked by ICE and sequenced by stage."""
    await require_admin(request)
    bundle = await _bundle(days, refresh=refresh)
    diagnosis = gdiag.diagnose(bundle)
    return {
        "window_days": _clamp_window(days),
        **gplaybook.build_playbook(bundle, diagnosis),
    }


@api_router.get("/growth/cohorts")
async def growth_cohorts(request: Request, months: int = 6,
                         days: int = DEFAULT_WINDOW_DAYS):
    """Monthly buyer cohorts with repeat-purchase retention.

    Cohorts are built from the full order history regardless of the dashboard
    window, and are computed once into the cached snapshot — so asking for a
    shorter horizon narrows the table rather than re-reading the database.
    """
    await require_admin(request)
    months = max(1, min(COHORT_MONTHS, int(months or 6)))
    bundle = await _bundle(days)
    cohorts = (bundle.get("detail") or {}).get("cohorts") or {"months": [], "rows": []}
    rows = cohorts.get("rows", [])[-months:]
    return {
        "months": months,
        "offsets": cohorts.get("months", []),
        "rows": rows,
        "repeat_buyer_rate": bundle["metrics"].get("repeat_buyer_rate"),
    }


@api_router.get("/growth/brief")
async def growth_brief(request: Request, days: int = DEFAULT_WINDOW_DAYS,
                       refresh: bool = False):
    """Everything the command centre needs in one call.

    The dashboard renders five panels off one round trip rather than five,
    which also guarantees every panel describes the same snapshot — panels
    that disagree with each other destroy trust in the whole tool.
    """
    await require_admin(request)
    window = _clamp_window(days)
    bundle = await _bundle(window, refresh=refresh)
    diagnosis = gdiag.diagnose(bundle)
    plays = gplaybook.build_playbook(bundle, diagnosis)
    memo = gnarrative.build_memo(bundle, diagnosis, plays)
    baseline_params = gsim.params_from_bundle(bundle, fee_config=_fee_config())

    return {
        "window_days": window,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": bundle["metrics"],
        "detail": bundle["detail"],
        "coverage": bundle["coverage"],
        "diagnosis": diagnosis,
        "playbook": plays,
        "memo": memo,
        "simulator_defaults": baseline_params,
        "bands": gb.BANDS,
    }


@api_router.post("/growth/simulate")
@limiter.limit("60/minute")
async def growth_simulate(payload: SimulationRequest, request: Request):
    """Project the flywheel forward, optionally against the untouched baseline.

    The baseline is seeded from measured data, so the delta answers the
    question an operator actually asks: what does this change buy me over
    doing nothing?
    """
    await require_admin(request)
    window = _clamp_window(payload.window_days or DEFAULT_WINDOW_DAYS)
    bundle = await _bundle(window)
    fee = _fee_config()

    baseline = gsim.params_from_bundle(bundle, fee_config=fee)
    baseline["months"] = float(payload.months or 12)
    scenario = gsim.params_from_bundle(bundle, overrides=payload.overrides(),
                                       fee_config=fee)

    if payload.compare_to_baseline:
        result = gsim.compare(baseline, scenario)
        return {"window_days": window, "baseline_params": baseline, **result}

    run = gsim.simulate(scenario)
    return {"window_days": window, "baseline_params": baseline, "scenario": run}
