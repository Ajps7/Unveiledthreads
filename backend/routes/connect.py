# ruff: noqa: F403, F405
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
        # Cross-border / EEA restrictions — Stripe says you can't create an
        # account in that country from this platform. Give the brand a
        # friendly message and log the full Stripe error for the admin.
        if ("country" in msg.lower() and ("not supported" in msg.lower() or "not available" in msg.lower())) \
           or "cross-border" in msg.lower():
            logger.warning(f"Stripe refused country for brand={brand['_id']} country={stripe_country}: {e}")
            raise HTTPException(
                status_code=400,
                detail=(
                    f"We can't currently onboard brands based in {stripe_country}. "
                    f"We're working on it — contact support@unveiledthreads.co.uk and we'll let "
                    f"you know when it opens up."
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
            "stripe_country": (brand.get("stripe_country") or "GB").upper(),
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
        "stripe_country": (brand.get("stripe_country") or "GB").upper(),
        "account_country": (getattr(account, "country", None) or "").upper() or None,
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
    
    # Balance can hold entries in multiple currencies (an EEA brand might
    # accumulate both EUR and the odd GBP transfer during cross-border edge
    # cases). We report the account's DEFAULT currency as the headline
    # figure but surface a per-currency breakdown too so the dashboard can
    # show any non-headline balances honestly.
    def _sum_for_currency(entries, currency):
        return round(sum(e["amount"] for e in entries if e["currency"] == currency) / 100, 2)

    def _per_currency(entries):
        totals = {}
        for e in entries:
            totals.setdefault(e["currency"], 0)
            totals[e["currency"]] += e["amount"]
        return {c: round(v / 100, 2) for c, v in totals.items()}

    def _iso(ts):
        return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()

    account_currency = (account.get("default_currency") or "gbp").lower()
    schedule = ((account.get("settings") or {}).get("payouts") or {}).get("schedule") or {}
    next_payout = None
    last_payout = None
    history = []
    for p in payouts.get("data", []):
        if next_payout is None and p["status"] in ("pending", "in_transit"):
            next_payout = {"amount": round(p["amount"] / 100, 2), "currency": p["currency"], "arrival_date": _iso(p["arrival_date"]), "status": p["status"]}
        if last_payout is None and p["status"] == "paid":
            last_payout = {"amount": round(p["amount"] / 100, 2), "currency": p["currency"], "arrival_date": _iso(p["arrival_date"])}
        history.append({
            "amount": round(p["amount"] / 100, 2),
            "currency": p["currency"],
            "arrival_date": _iso(p["arrival_date"]),
            "status": p["status"],
        })

    return {
        "connected": True,
        "payouts_enabled": bool(account.get("payouts_enabled")),
        "available": _sum_for_currency(balance["available"], account_currency),
        "pending": _sum_for_currency(balance["pending"], account_currency),
        "currency": account_currency,
        "available_by_currency": _per_currency(balance["available"]),
        "pending_by_currency": _per_currency(balance["pending"]),
        "schedule_interval": schedule.get("interval"),
        "schedule_delay_days": schedule.get("delay_days"),
        "next_payout": next_payout,
        "last_payout": last_payout,
        "history": history,
    }



class ConnectResetRequest(BaseModel):
    stripe_country: str


async def _reset_brand_stripe_account(brand: dict, new_country: str, *, actor_label: str):
    """Delete an INCOMPLETE Stripe connected account and reset the brand so
    they can start onboarding fresh in the correct country.

    Safety rails (any failed check aborts the delete):
      - The brand must have no onboarded Stripe account, OR
      - the connected account must have `details_submitted = false` AND
        `charges_enabled = false` (never delete a live, earning account).
      - The new country must be in STRIPE_SUPPORTED_COUNTRIES.
    """
    new_country = (new_country or "").strip().upper()
    if new_country not in STRIPE_SUPPORTED_COUNTRIES:
        raise HTTPException(
            status_code=400,
            detail=f"We don't support Stripe onboarding in '{new_country}' yet.",
        )

    account_id = brand.get("stripe_account_id")
    if account_id:
        stripe_sdk.api_key = os.environ.get("STRIPE_API_KEY")
        try:
            account = await asyncio.to_thread(stripe_sdk.Account.retrieve, account_id)
        except Exception as e:
            logger.warning(f"[CONNECT RESET] Could not fetch {account_id}: {e}. Clearing brand's reference anyway.")
            account = None
        if account:
            if account.get("details_submitted") or account.get("charges_enabled"):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "This Stripe account has already completed onboarding or is active. "
                        "We can't reset it — contact support if the country is wrong."
                    ),
                )
            try:
                await asyncio.to_thread(stripe_sdk.Account.delete, account_id)
                logger.info(f"[CONNECT RESET] by={actor_label} brand={brand['_id']} deleted {account_id}, new country={new_country}")
            except Exception as e:
                logger.error(f"[CONNECT RESET] Stripe delete failed for {account_id}: {e}")
                raise HTTPException(status_code=500, detail="Stripe couldn't delete the old account — try again shortly.")

    # Scrub the brand's Stripe state AND update stripe_country so the next
    # `/connect/onboard` call creates a fresh account in the right place.
    await db.brands.update_one(
        {"_id": brand["_id"]},
        {"$set": {
            "stripe_account_id": None,
            "stripe_charges_enabled": False,
            "stripe_payouts_enabled": False,
            "stripe_onboarded_at": None,
            "stripe_country": new_country,
        }},
    )
    return {"ok": True, "stripe_country": new_country}


@api_router.post("/connect/reset-account")
@limiter.limit("5/hour")
async def connect_reset_account(payload: ConnectResetRequest, request: Request):
    """Brand self-service: wipe an INCOMPLETE Stripe connected account and
    change the brand's registered country so they can onboard fresh.
    Rate-limited aggressively because it hits the Stripe API.
    """
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    return await _reset_brand_stripe_account(
        brand, payload.stripe_country, actor_label=f"brand-self:{user['id']}",
    )


@api_router.post("/admin/brands/{brand_id}/reset-stripe")
async def admin_reset_brand_stripe(brand_id: str, payload: ConnectResetRequest, request: Request):
    """Admin version of `/connect/reset-account` — fixes a brand stuck on
    the wrong country without needing the brand to trigger it themselves.
    Same safety rails apply (won't delete a live / onboarded account).
    """
    await require_admin(request)
    brand = await db.brands.find_one({"_id": safe_object_id(brand_id)})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    actor = await get_current_user(request)
    return await _reset_brand_stripe_account(
        brand, payload.stripe_country, actor_label=f"admin:{actor['id']}",
    )

