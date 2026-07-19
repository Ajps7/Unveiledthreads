# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ GDPR: DATA EXPORT & ACCOUNT DELETION ============

class DeleteAccountRequest(BaseModel):
    password: str
    confirm: str  # Must equal "DELETE"


def _serialise_doc(doc: dict) -> dict:
    """Strip Mongo internals and convert ObjectId/datetime for JSON export."""
    if not doc:
        return doc
    out = {}
    for k, v in doc.items():
        if k in ("_id", "password_hash", "token_hash"):
            continue
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, list):
            out[k] = [_serialise_doc(i) if isinstance(i, dict) else (i.isoformat() if isinstance(i, datetime) else (str(i) if isinstance(i, ObjectId) else i)) for i in v]
        elif isinstance(v, dict):
            out[k] = _serialise_doc(v)
        else:
            out[k] = v
    return out


@api_router.get("/account/export")
@limiter.limit("3/hour")
async def export_my_data(request: Request):
    """GDPR Article 20 — Right to Data Portability.
    Returns every record we hold about the requesting user as a JSON document."""
    user = await get_current_user(request)
    user_id = user["id"]

    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    brand_doc = await db.brands.find_one({"user_id": user_id})
    brand_id = str(brand_doc["_id"]) if brand_doc else None
    applications = await db.brand_applications.find({"user_id": user_id}).to_list(1000)
    products = await db.products.find({"brand_id": brand_id}).to_list(1000) if brand_id else []
    orders_as_buyer = await db.orders.find({"buyer_id": user_id}).to_list(1000)
    orders_as_seller = await db.orders.find({"brand_id": brand_id}).to_list(1000) if brand_id else []
    conversations = await db.conversations.find({"participants": user_id}).to_list(1000)
    convo_ids = [str(c["_id"]) for c in conversations]
    messages = await db.messages.find({"conversation_id": {"$in": convo_ids}}).to_list(5000) if convo_ids else []
    notifications = await db.notifications.find({"user_id": user_id}).to_list(1000)
    wishlist = await db.wishlist.find({"user_id": user_id}).to_list(1000)
    reviews = await db.reviews.find({"buyer_id": user_id}).to_list(1000)
    community_posts = await db.community_posts.find({"user_id": user_id}).to_list(1000)
    community_comments = await db.community_comments.find({"user_id": user_id}).to_list(1000)
    product_comments = await db.product_comments.find({"user_id": user_id}).to_list(1000)
    referrals = await db.referrals.find({"user_id": user_id}).to_list(1000)
    payment_transactions = await db.payment_transactions.find({"$or": [{"user_id": user_id}, {"buyer_id": user_id}]}).to_list(1000)

    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "notice": "This is a copy of every record Unveiled Threads holds about your account. Financial KYC data (bank, ID) is held by Stripe and must be requested directly via your Stripe dashboard.",
        "account": _serialise_doc(user_doc),
        "brand_profile": _serialise_doc(brand_doc) if brand_doc else None,
        "brand_applications": [_serialise_doc(d) for d in applications],
        "listings": [_serialise_doc(d) for d in products],
        "orders_as_buyer": [_serialise_doc(d) for d in orders_as_buyer],
        "orders_as_seller": [_serialise_doc(d) for d in orders_as_seller],
        "conversations": [_serialise_doc(d) for d in conversations],
        "messages": [_serialise_doc(d) for d in messages],
        "notifications": [_serialise_doc(d) for d in notifications],
        "wishlist": [_serialise_doc(d) for d in wishlist],
        "reviews_left": [_serialise_doc(d) for d in reviews],
        "community_posts": [_serialise_doc(d) for d in community_posts],
        "community_comments": [_serialise_doc(d) for d in community_comments],
        "product_comments": [_serialise_doc(d) for d in product_comments],
        "referrals": [_serialise_doc(d) for d in referrals],
        "payment_transactions": [_serialise_doc(d) for d in payment_transactions],
    }
    headers = {"Content-Disposition": f'attachment; filename="unveiled-threads-export-{user_id}.json"'}
    return Response(content=json.dumps(export, indent=2), media_type="application/json", headers=headers)


@api_router.post("/account/delete")
@limiter.limit("3/hour")
async def delete_my_account(payload: DeleteAccountRequest, request: Request, response: Response):
    """GDPR Article 17 — Right to Erasure.
    Permanently removes the user and all personal data we hold across collections.
    Order records are anonymised (not deleted) to preserve tax / accounting obligations."""
    user = await get_current_user(request)
    user_id = user["id"]

    # Admins must not be able to nuke themselves and lock the platform out
    if user.get("role") == "admin":
        raise HTTPException(status_code=403, detail="Admin accounts cannot self-delete. Contact another admin to remove this account.")

    if payload.confirm != "DELETE":
        raise HTTPException(status_code=400, detail="Confirmation text must be exactly 'DELETE'")

    full_user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not full_user or not verify_password(payload.password, full_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Password incorrect")

    # Resolve brand id (if any) before we wipe the brand row
    brand_doc = await db.brands.find_one({"user_id": user_id})
    brand_id = brand_doc.get("id") if brand_doc else None

    # 1. Anonymise orders (we keep them for tax/accounting but strip PII)
    anon_buyer = {"$set": {"buyer_id": "deleted-user", "shipping_address": None, "buyer_email": None, "buyer_name": "Deleted User"}}
    await db.orders.update_many({"buyer_id": user_id}, anon_buyer)
    if brand_id:
        await db.orders.update_many({"brand_id": brand_id}, {"$set": {"brand_name_snapshot": "Deleted Brand"}})

    # 2. Hard delete everything personal
    await db.brand_applications.delete_many({"user_id": user_id})
    if brand_id:
        await db.products.delete_many({"brand_id": brand_id})
        await db.brands.delete_one({"id": brand_id})
    await db.wishlists.delete_many({"user_id": user_id})
    await db.notifications.delete_many({"user_id": user_id})
    await db.community_posts.delete_many({"user_id": user_id})
    await db.community_comments.delete_many({"user_id": user_id})
    await db.product_comments.delete_many({"user_id": user_id})
    await db.reviews.delete_many({"buyer_id": user_id})
    await db.referrals.delete_many({"user_id": user_id})
    await db.referral_uses.delete_many({"$or": [{"referrer_id": user_id}, {"referred_user_id": user_id}]})
    await db.password_reset_tokens.delete_many({"user_id": user_id})
    await db.product_views.delete_many({"user_id": user_id})

    # 3. Messages — anonymise sender content references (keep message bodies redacted)
    convs = await db.conversations.find({"participants": user_id}).to_list(1000)
    for c in convs:
        await db.messages.update_many(
            {"conversation_id": c.get("id"), "sender_id": user_id},
            {"$set": {"sender_id": "deleted-user", "content": "[message removed — account deleted]"}}
        )
    await db.conversations.update_many(
        {"participants": user_id},
        {"$pull": {"participants": user_id}}
    )

    # 4. Finally delete the user row itself
    await db.users.delete_one({"_id": ObjectId(user_id)})

    # 5. Kill the session cookies
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")

    return {"message": "Your account and all associated personal data have been permanently deleted."}


