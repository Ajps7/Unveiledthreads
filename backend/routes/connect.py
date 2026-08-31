# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ STRIPE CONNECT (Express) ============

class ConnectOnboardRequest(BaseModel):
    origin_url: str

@api_router.post("/connect/onboard")
@limiter.limit("10/minute")
async def connect_onboard(payload: ConnectOnboardRequest, request: Request):
    """Create (or reuse) an Express connected account for the brand and return a hosted onboarding link."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_sdk.api_key = api_key
    
    account_id = brand.get("stripe_account_id")
    try:
        if not account_id:
            # Use the brand's registered/banking country — decoupled from
            # the marketplace "market" (which is always UK for curation).
            # Legacy brands without stripe_country get GB. Country is
            # IMMUTABLE on Stripe once the account is created, so this must
            # be right first time.
            stripe_country = (brand.get("stripe_country") or "GB").upper()
            if stripe_country not in STRIPE_SUPPORTED_COUNTRIES:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Stripe onboarding isn't supported in '{stripe_country}' on this platform. "
                        f"Update your registered country or contact support."
                    ),
                )
            account = await asyncio.to_thread(
                stripe_sdk.Account.create,
                type="express",
                country=stripe_country,
                email=user["email"],
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
                business_type="individual",
                business_profile={
                    "name": brand["brand_name"],
                    "product_description": brand.get("description", "Independent UK clothing brand"),
                },
                metadata={
                    "brand_id": str(brand["_id"]),
                    "user_id": user["id"],
                },
            )
            account_id = account.id
            await db.brands.update_one(
                {"_id": brand["_id"]},
                {"$set": {
                    "stripe_account_id": account_id,
                    "stripe_charges_enabled": False,
                    "stripe_payouts_enabled": False,
                    "stripe_onboarded_at": None,
                }},
            )
        
        # Create AccountLink for hosted onboarding
        account_link = await asyncio.to_thread(
            stripe_sdk.AccountLink.create,
            account=account_id,
            refresh_url=f"{payload.origin_url}/brand/dashboard?connect=refresh",
            return_url=f"{payload.origin_url}/brand/dashboard?connect=return",
            type="account_onboarding",
        )
        return {"url": account_link.url, "account_id": account_id}
    except stripe_sdk.error.InvalidRequestError as e:
        msg = str(e)
        if "platform-profile" in msg or "responsibilities of managing losses" in msg:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Stripe Connect platform setup required. The Unveiled Threads admin must "
                    "complete the one-time platform profile at "
                    "https://dashboard.stripe.com/settings/connect/platform-profile before brands "
                    "can onboard. Please contact support."
                ),
            )
        logger.error(f"Stripe Connect onboard failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe Connect error: {msg}")
    except Exception as e:
        logger.error(f"Stripe Connect onboard failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe Connect error: {str(e)}")

@api_router.get("/connect/status")
async def connect_status(request: Request):
    """Refresh and return the brand's Connect account state."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    account_id = brand.get("stripe_account_id")
    if not account_id:
        return {
            "stripe_account_id": None,
            "charges_enabled": False,
            "payouts_enabled": False,
            "details_submitted": False,
            "requirements_due": [],
        }
    
    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_sdk.api_key = api_key
    try:
        account = await asyncio.to_thread(stripe_sdk.Account.retrieve, account_id)
    except Exception as e:
        logger.error(f"Stripe Connect status fetch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    
    charges_enabled = bool(account.charges_enabled)
    payouts_enabled = bool(account.payouts_enabled)
    details_submitted = bool(account.details_submitted)
    requirements_due = list(getattr(account.requirements, "currently_due", []) or [])
    
    update_doc = {
        "stripe_charges_enabled": charges_enabled,
        "stripe_payouts_enabled": payouts_enabled,
        "stripe_details_submitted": details_submitted,
    }
    if charges_enabled and payouts_enabled and not brand.get("stripe_onboarded_at"):
        update_doc["stripe_onboarded_at"] = datetime.now(timezone.utc)
    await db.brands.update_one({"_id": brand["_id"]}, {"$set": update_doc})
    
    return {
        "stripe_account_id": account_id,
        "charges_enabled": charges_enabled,
        "payouts_enabled": payouts_enabled,
        "details_submitted": details_submitted,
        "requirements_due": requirements_due,
    }

@api_router.get("/connect/dashboard-link")
async def connect_dashboard_link(request: Request):
    """Return a one-time login link to the Express Dashboard for the brand."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand or not brand.get("stripe_account_id"):
        raise HTTPException(status_code=400, detail="Brand has not connected Stripe yet")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_sdk.api_key = api_key
    try:
        link = await asyncio.to_thread(
            stripe_sdk.Account.create_login_link, brand["stripe_account_id"]
        )
        return {"url": link.url}
    except Exception as e:
        logger.error(f"Stripe Connect login link failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

@api_router.get("/connect/payouts")
async def connect_payouts(request: Request):
    """Stripe balance + next payout info for the brand's connected account."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand or not brand.get("stripe_account_id"):
        return {"connected": False}
    
    account_id = brand["stripe_account_id"]
    stripe_sdk.api_key = os.environ.get("STRIPE_API_KEY")
    try:
        balance, account, payouts = await asyncio.gather(
            asyncio.to_thread(stripe_sdk.Balance.retrieve, stripe_account=account_id),
            asyncio.to_thread(stripe_sdk.Account.retrieve, account_id),
            asyncio.to_thread(stripe_sdk.Payout.list, limit=20, stripe_account=account_id),
        )
    except Exception as e:
        logger.error(f"Stripe payouts fetch failed: {e}")
        return {"connected": False, "error": "Could not reach Stripe"}
    
    def _sum_gbp(entries):
        return round(sum(e["amount"] for e in entries if e["currency"] == "gbp") / 100, 2)
    
    def _iso(ts):
        return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
    
    schedule = ((account.get("settings") or {}).get("payouts") or {}).get("schedule") or {}
    next_payout = None
    last_payout = None
    history = []
    for p in payouts.get("data", []):
        if next_payout is None and p["status"] in ("pending", "in_transit"):
            next_payout = {"amount": round(p["amount"] / 100, 2), "arrival_date": _iso(p["arrival_date"]), "status": p["status"]}
        if last_payout is None and p["status"] == "paid":
            last_payout = {"amount": round(p["amount"] / 100, 2), "arrival_date": _iso(p["arrival_date"])}
        history.append({
            "amount": round(p["amount"] / 100, 2),
            "currency": p["currency"],
            "arrival_date": _iso(p["arrival_date"]),
            "status": p["status"],
        })
    
    return {
        "connected": True,
        "payouts_enabled": bool(account.get("payouts_enabled")),
        "available": _sum_gbp(balance["available"]),
        "pending": _sum_gbp(balance["pending"]),
        "currency": "gbp",
        "schedule_interval": schedule.get("interval"),
        "schedule_delay_days": schedule.get("delay_days"),
        "next_payout": next_payout,
        "last_payout": last_payout,
        "history": history,
    }

