# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403
from core import _finalise_approval, _seller_cap_reached, _seller_slots_used

# ============ BRAND APPLICATION ROUTES ============

@api_router.post("/brands/apply")
async def apply_for_brand(application: BrandApplicationCreate, request: Request):
    user = await get_current_user(request)
    
    # Check if user already has a pending/approved application
    existing = await db.brand_applications.find_one({
        "user_id": user["id"],
        "status": {"$in": ["pending", "approved"]}
    })
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending or approved brand application")
    
    # Hybrid auto-approval: compute risk score from application + applicant signals
    risk_score, risk_reasons = calculate_application_risk(application, user)
    cap_reached = await _seller_cap_reached()
    
    app_doc = {
        "user_id": user["id"],
        "brand_name": application.brand_name,
        "description": application.description,
        "instagram_handle": application.instagram_handle,
        "website": application.website,
        "location": application.location,
        "category": application.category,
        # Marketplace vs. Stripe are decoupled — see BrandApplicationCreate.
        "market": application.market or "UK",
        "stripe_country": application.stripe_country or "GB",
        "status": "waitlisted" if cap_reached else "pending",
        "risk_score": risk_score,
        "risk_reasons": risk_reasons,
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.brand_applications.insert_one(app_doc)
    application_id = str(result.inserted_id)
    
    # Auto-approve only if score is low AND cap isn't reached. Otherwise queue/waitlist.
    auto_approved = False
    if not cap_reached and risk_score < AUTO_APPROVE_RISK_THRESHOLD:
        await _finalise_approval(application_id, app_doc, origin_url=str(request.base_url).rstrip("/"))
        auto_approved = True

    # Confirmation email for pending + waitlisted paths only. Auto-approved
    # brands already receive the Stripe onboarding email via _finalise_approval.
    if not auto_approved:
        try:
            await send_application_received_email(
                recipient_email=user["email"],
                brand_name=application.brand_name,
                is_waitlisted=cap_reached,
            )
        except Exception as e:
            # Never let an email failure block an application submission.
            logger.warning(f"send_application_received_email failed: {e}")
    
    if cap_reached:
        message = (
            f"Thanks — you're on the waitlist. We're capping the platform at "
            f"{MAX_SELLER_ACCOUNTS} sellers during our MVP phase. We'll email you the moment a slot opens up."
        )
    elif auto_approved:
        message = "Application approved instantly — check your email to finish Stripe payout setup."
    else:
        message = "Application submitted. Our team will review it shortly."
    
    return {
        "id": application_id,
        "message": message,
        "auto_approved": auto_approved,
        "waitlisted": cap_reached,
        "risk_score": risk_score,
    }

@api_router.get("/brands/my-application")
async def get_my_application(request: Request):
    user = await get_current_user(request)
    
    application = await db.brand_applications.find_one(
        {"user_id": user["id"]},
        {"_id": 0}
    )
    
    # Also check if user has a brand profile directly (e.g. seeded brands)
    brand_profile = await db.brands.find_one({"user_id": user["id"]})
    if brand_profile:
        brand_profile["id"] = str(brand_profile["_id"])
        del brand_profile["_id"]
    
    if not application and not brand_profile:
        return None
    
    # If there's a brand profile but no application, synthesize one
    if not application and brand_profile:
        application = {
            "user_id": user["id"],
            "brand_name": brand_profile["brand_name"],
            "description": brand_profile["description"],
            "status": "approved"
        }
    
    return {
        "application": application,
        "brand_profile": brand_profile
    }

@api_router.get("/admin/applications")
async def get_all_applications(request: Request, status: Optional[str] = None):
    await require_admin(request)
    
    query = {}
    if status:
        query["status"] = status
    
    # Sort by risk score descending (highest risk first), then newest
    applications = await db.brand_applications.find(query).sort(
        [("risk_score", -1), ("created_at", -1)]
    ).to_list(100)
    
    result = []
    for app in applications:
        app["id"] = str(app["_id"])
        del app["_id"]
        # Get user info
        user = await db.users.find_one({"_id": ObjectId(app["user_id"])}, {"_id": 0, "password_hash": 0})
        app["user"] = user
        # Default scores for legacy applications submitted before risk scoring shipped
        app.setdefault("risk_score", 0)
        app.setdefault("risk_reasons", [])
        result.append(app)
    
    return result


@api_router.get("/admin/seller-cap")
async def get_seller_cap(request: Request):
    """MVP seller cap status — used by admin dashboard counter."""
    await require_admin(request)
    used = await _seller_slots_used()
    waitlisted = await db.brand_applications.count_documents({"status": "waitlisted"})
    return {
        "used": used,
        "max": MAX_SELLER_ACCOUNTS,
        "remaining": max(0, MAX_SELLER_ACCOUNTS - used),
        "cap_reached": used >= MAX_SELLER_ACCOUNTS,
        "waitlisted": waitlisted,
    }

@api_router.post("/admin/wipe-demo-data")
async def wipe_demo_data(request: Request):
    """One-shot endpoint to delete all products, brands, and brand applications.
    Used to clear seed/demo data before opening to real buyers.
    Keeps user accounts intact (former brand owners become regular users).
    
    REQUIRES admin authentication.
    """
    await require_admin(request)
    
    # Snapshot counts so the caller can verify
    products_count = await db.products.count_documents({})
    brands_count = await db.brands.count_documents({})
    apps_count = await db.brand_applications.count_documents({})
    
    # Refuse to nuke if there are any real paid orders — protects accidental data loss
    paid_order_count = await db.orders.count_documents(
        {"status": {"$in": SALE_STATUSES}}
    )
    if paid_order_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Refusing to wipe: {paid_order_count} real paid order(s) exist. Manual cleanup required.",
        )
    
    # Cascade delete: anything depending on brand/product IDs
    deleted_products = (await db.products.delete_many({})).deleted_count
    deleted_brands = (await db.brands.delete_many({})).deleted_count
    deleted_apps = (await db.brand_applications.delete_many({})).deleted_count
    deleted_reviews = (await db.reviews.delete_many({})).deleted_count if 'reviews' in await db.list_collection_names() else 0
    deleted_wishlists = (await db.wishlists.delete_many({})).deleted_count if 'wishlists' in await db.list_collection_names() else 0
    deleted_comments = (await db.product_comments.delete_many({})).deleted_count if 'product_comments' in await db.list_collection_names() else 0
    deleted_orders = (await db.orders.delete_many({})).deleted_count  # only initiated/unpaid by this point
    
    # Downgrade any users with role=brand back to regular user
    downgraded = (await db.users.update_many(
        {"role": "brand"},
        {"$set": {"role": "user"}},
    )).modified_count
    
    return {
        "wiped": {
            "products": deleted_products,
            "brands": deleted_brands,
            "brand_applications": deleted_apps,
            "reviews": deleted_reviews,
            "wishlists": deleted_wishlists,
            "product_comments": deleted_comments,
            "unpaid_orders": deleted_orders,
            "users_downgraded_to_buyer": downgraded,
        },
        "before": {
            "products": products_count,
            "brands": brands_count,
            "brand_applications": apps_count,
        },
        "message": "Demo data wiped. User accounts preserved (brand owners downgraded to buyer role).",
    }


@api_router.post("/admin/applications/{application_id}/approve")
async def approve_application(application_id: str, request: Request):
    await require_admin(request)
    
    application = await db.brand_applications.find_one({"_id": safe_object_id(application_id)})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Allow approval of both "pending" and "waitlisted" (admin promoting from waitlist
    # once a seller slot has freed up).
    if application["status"] not in ("pending", "waitlisted"):
        raise HTTPException(status_code=400, detail="Application already processed")
    
    brand_id = await _finalise_approval(application_id, application, origin_url=str(request.base_url).rstrip("/"))
    return {"message": "Application approved", "brand_id": brand_id}

@api_router.post("/admin/applications/{application_id}/reject")
async def reject_application(application_id: str, request: Request):
    await require_admin(request)
    
    application = await db.brand_applications.find_one({"_id": safe_object_id(application_id)})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application["status"] != "pending":
        raise HTTPException(status_code=400, detail="Application already processed")
    
    await db.brand_applications.update_one(
        {"_id": safe_object_id(application_id)},
        {"$set": {"status": "rejected", "rejected_at": datetime.now(timezone.utc)}}
    )
    
    # Send rejection notification
    await create_notification(
        user_id=application["user_id"],
        brand_id=None,
        notification_type="application_rejected",
        title="Application Update",
        message=f"Unfortunately, your brand application for '{application['brand_name']}' was not approved at this time. You're welcome to reapply with updated details.",
        metadata={}
    )
    
    return {"message": "Application rejected"}

