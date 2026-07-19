# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ STRIPE BOOST ROUTES ============

@api_router.get("/boost/packages")
async def get_boost_packages():
    return list(BOOST_PACKAGES.values())

@api_router.post("/boost/checkout")
async def create_boost_checkout(checkout_data: CheckoutRequest, request: Request):
    # Boost feature temporarily disabled — coming soon
    raise HTTPException(
        status_code=503,
        detail="Brand boost is coming soon. We're polishing this feature and it will be available shortly.",
    )
    user = await require_brand(request)
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")
    
    package = BOOST_PACKAGES.get(checkout_data.package_id)
    if not package:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    
    success_url = f"{checkout_data.origin_url}/boost/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{checkout_data.origin_url}/brand/dashboard"
    
    checkout_request = CheckoutSessionRequest(
        amount=package["price"],
        currency="gbp",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user["id"],
            "brand_id": str(brand["_id"]),
            "package_id": package["id"],
            "duration_days": str(package["duration_days"])
        }
    )
    
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": user["id"],
        "brand_id": str(brand["_id"]),
        "package_id": package["id"],
        "amount": package["price"],
        "currency": "gbp",
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/boost/status/{session_id}")
async def get_boost_status(session_id: str, request: Request):
    user = await require_brand(request)
    
    transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if already processed
    if transaction.get("payment_status") == "paid":
        return {"status": "complete", "payment_status": "paid", "already_processed": True}
    
    api_key = os.environ.get("STRIPE_API_KEY")
    
    try:
        status_data = get_stripe_session_status(session_id, api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    
    # Update transaction status
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status_data["payment_status"], "status": status_data["status"]}}
    )
    
    # If paid and not already processed, apply the boost
    if status_data["payment_status"] == "paid" and not transaction.get("boost_applied"):
        package_id = transaction["package_id"]
        package = BOOST_PACKAGES.get(package_id)
        if package:
            brand_doc = await db.brands.find_one({"_id": ObjectId(transaction["brand_id"])})
            now = datetime.now(timezone.utc)
            current_until = brand_doc.get("boosted_until") if brand_doc else None
            # Stack onto existing boost if it hasn't expired yet, else start from now
            base = current_until if (current_until and current_until > now) else now
            boosted_until = base + timedelta(days=package["duration_days"])
            await db.brands.update_one(
                {"_id": ObjectId(transaction["brand_id"])},
                {"$set": {"is_boosted": True, "boosted_until": boosted_until}}
            )
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"boost_applied": True}}
            )
    
    return {"status": status_data["status"], "payment_status": status_data["payment_status"]}

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    api_key = os.environ.get("STRIPE_API_KEY")
    # Two separate webhook endpoints are registered with Stripe:
    #   - STRIPE_WEBHOOK_SECRET         → account-level events (payments, refunds)
    #   - STRIPE_CONNECT_WEBHOOK_SECRET → Connect platform events (account.updated, payouts)
    # Both webhooks POST to the same endpoint; we try each secret until one verifies.
    webhook_secrets = [
        s for s in (
            os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip(),
            os.environ.get("STRIPE_CONNECT_WEBHOOK_SECRET", "").strip(),
        ) if s
    ]
    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
    
    stripe_sdk.api_key = api_key
    
    # Webhook signature is REQUIRED. Without it, anyone can POST a fake
    # "payment_intent.succeeded" event and flip orders / connect-account state.
    # In production we hard-fail. In dev we still warn loudly and accept
    # unsigned events for local Stripe CLI testing.
    raw_event = None
    if webhook_secrets:
        for secret in webhook_secrets:
            try:
                raw_event = stripe_sdk.Webhook.construct_event(
                    payload=body, sig_header=signature, secret=secret
                )
                break
            except stripe_sdk.error.SignatureVerificationError:
                continue
            except Exception as e:
                logger.error(f"Stripe webhook parse error: {e}")
                raise HTTPException(status_code=400, detail="Invalid payload")
        if raw_event is None:
            logger.warning("Stripe webhook signature verification FAILED against all configured secrets — rejecting event")
            raise HTTPException(status_code=400, detail="Invalid signature")
    elif environment == "production":
        logger.error(
            "REFUSING webhook: no Stripe webhook secret is set in production. "
            "Set STRIPE_WEBHOOK_SECRET and STRIPE_CONNECT_WEBHOOK_SECRET from "
            "https://dashboard.stripe.com/webhooks before any live traffic."
        )
        raise HTTPException(status_code=503, detail="Webhook verification not configured")
    else:
        logger.warning(
            "No Stripe webhook secret is set — webhook events are NOT being verified. "
            "Add STRIPE_WEBHOOK_SECRET (and STRIPE_CONNECT_WEBHOOK_SECRET for Connect) before going live."
        )
        try:
            raw_event = stripe_sdk.Event.construct_from(
                json.loads(body.decode("utf-8")), api_key
            )
        except Exception as e:
            logger.error(f"Webhook parse failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
    
    try:
        # Connect account lifecycle: keep brand connect-status fields in sync
        if raw_event.type == "account.updated":
            account = raw_event.data.object
            await db.brands.update_one(
                {"stripe_account_id": account.id},
                {"$set": {
                    "stripe_charges_enabled": bool(account.get("charges_enabled")),
                    "stripe_payouts_enabled": bool(account.get("payouts_enabled")),
                    "stripe_details_submitted": bool(account.get("details_submitted")),
                    "stripe_onboarded_at": datetime.now(timezone.utc) if account.get("charges_enabled") and account.get("payouts_enabled") else None,
                }},
            )
        
        # Checkout session completed: settle orders + (if boost) extend expiry
        if raw_event.type == "checkout.session.completed":
            session = raw_event.data.object
            session_id = session.id
            metadata = dict(session.metadata) if session.metadata else {}
            payment_status = session.payment_status
            
            # Update payment_transactions
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"payment_status": payment_status, "status": session.status}}
            )
            
            # Boost flow (if still applicable when boost is re-enabled)
            transaction = await db.payment_transactions.find_one({"session_id": session_id})
            if (
                payment_status == "paid"
                and transaction
                and not transaction.get("boost_applied")
                and metadata.get("package_id")
            ):
                package = BOOST_PACKAGES.get(metadata["package_id"])
                if package:
                    brand_doc = await db.brands.find_one({"_id": ObjectId(transaction["brand_id"])})
                    now = datetime.now(timezone.utc)
                    current_until = brand_doc.get("boosted_until") if brand_doc else None
                    base = current_until if (current_until and current_until > now) else now
                    boosted_until = base + timedelta(days=package["duration_days"])
                    await db.brands.update_one(
                        {"_id": ObjectId(transaction["brand_id"])},
                        {"$set": {"is_boosted": True, "boosted_until": boosted_until}}
                    )
                    await db.payment_transactions.update_one(
                        {"session_id": session_id},
                        {"$set": {"boost_applied": True, "payment_status": "paid"}}
                    )
        
        return {"received": True}
    except HTTPException:
        raise
    except Exception as e:
        # Return 500 so Stripe retries; the previous behaviour of swallowing errors
        # would silently drop genuinely paid events.
        logger.error(f"Webhook handler error for event {getattr(raw_event, 'id', '?')}: {e}")
        raise HTTPException(status_code=500, detail="Webhook handler error")

