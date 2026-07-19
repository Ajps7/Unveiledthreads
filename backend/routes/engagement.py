# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ LOW-STOCK WEEKLY DIGEST ============

LOW_STOCK_DIGEST_DAYS = int(os.environ.get("LOW_STOCK_DIGEST_DAYS", "7"))

async def send_low_stock_digests() -> list:
    """Weekly email nudging brands to restock best sellers that are running low.
    Returns a report of what was sent (used by the admin trigger endpoint)."""
    threshold = int(os.environ.get("LOW_STOCK_THRESHOLD", "3"))
    now = datetime.now(timezone.utc)
    digest_cutoff = now - timedelta(days=LOW_STOCK_DIGEST_DAYS)
    sales_window = now - timedelta(days=30)
    frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
    report = []
    
    async for brand in db.brands.find({}):
        last_sent = brand.get("low_stock_digest_sent_at")
        if last_sent and last_sent.replace(tzinfo=timezone.utc) > digest_cutoff:
            continue
        brand_id = str(brand["_id"])
        low_stock = await db.products.find({
            "brand_id": brand_id,
            "is_dead_stock": {"$ne": True},
            "stock": {"$lte": threshold},
        }).to_list(100)
        if not low_stock:
            continue
        pids = [str(p["_id"]) for p in low_stock]
        pipeline = [
            {"$match": {"brand_id": brand_id, "status": "paid", "product_id": {"$in": pids}, "created_at": {"$gte": sales_window}}},
            {"$group": {"_id": "$product_id", "count": {"$sum": 1}}},
        ]
        sold = {d["_id"]: d["count"] async for d in db.orders.aggregate(pipeline)}
        # Best sellers only — no point nudging about products nobody buys
        items = sorted(
            [p for p in low_stock if sold.get(str(p["_id"]), 0) >= 1],
            key=lambda p: sold.get(str(p["_id"]), 0),
            reverse=True,
        )[:5]
        if not items:
            continue
        user_doc = await db.users.find_one({"_id": ObjectId(brand["user_id"])})
        recipient = user_doc.get("email") if user_doc else None
        if not recipient:
            continue
        
        rows = "".join(
            f"""<tr>
                <td style="padding:8px 0;border-bottom:1px solid #27272A;color:#fff;font-size:14px;">{p.get('name', 'Unknown')}</td>
                <td style="padding:8px 0;border-bottom:1px solid #27272A;color:#9CA3AF;font-size:14px;text-align:center;">{sold.get(str(p['_id']), 0)} sold (30d)</td>
                <td style="padding:8px 0;border-bottom:1px solid #27272A;color:{'#EF4444' if int(p.get('stock', 0) or 0) == 0 else '#FACC15'};font-size:14px;font-weight:bold;text-align:right;">{int(p.get('stock', 0) or 0)} left</td>
            </tr>"""
            for p in items
        )
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
            <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;">UNVEILED THREADS</h1>
            <hr style="border:1px solid #27272A;margin:16px 0;">
            <h2 style="color:#fff;font-size:20px;">Your best sellers are running low</h2>
            <p style="color:#9CA3AF;line-height:1.6;">
                Buyers are still landing on these listings — restock them so you don't miss sales, {brand.get('brand_name', 'there')}.
            </p>
            <div style="background:#0A0A0A;border:1px solid #27272A;padding:20px;margin:24px 0;">
                <table style="width:100%;border-collapse:collapse;">{rows}</table>
            </div>
            {f'<p><a href="{frontend_url}/brand/products" style="color:#000;background:#39FF14;padding:12px 24px;text-decoration:none;font-weight:bold;display:inline-block;">RESTOCK NOW</a></p>' if frontend_url else ''}
            <hr style="border:1px solid #27272A;margin:24px 0;">
            <p style="color:#9CA3AF;font-size:12px;">You get this digest at most once a week, only when best sellers run low.</p>
        </div>
        """
        entry = {"brand": brand.get("brand_name"), "email": recipient, "items": [p.get("name") for p in items], "sent": False}
        try:
            if RESEND_API_KEY:
                params = {
                    "from": SENDER_EMAIL,
                    "to": [recipient],
                    "subject": "Restock alert — your best sellers are running low | Unveiled Threads",
                    "html": html,
                }
                await asyncio.to_thread(resend.Emails.send, params)
                logger.info(f"[LOW-STOCK DIGEST SENT] To: {recipient} | {brand.get('brand_name')}")
            else:
                logger.info(f"[MOCK LOW-STOCK DIGEST] To: {recipient} | {brand.get('brand_name')} | {entry['items']}")
            entry["sent"] = True
            await db.brands.update_one({"_id": brand["_id"]}, {"$set": {"low_stock_digest_sent_at": now}})
        except Exception as e:
            entry["error"] = str(e)
            logger.warning(f"[LOW-STOCK DIGEST FAILED] To: {recipient} | {e}")
        report.append(entry)
    return report

async def low_stock_digest_loop():
    while True:
        try:
            await send_low_stock_digests()
        except Exception as e:
            logger.error(f"Low-stock digest loop error: {e}")
        await asyncio.sleep(6 * 3600)

@api_router.post("/admin/low-stock-digest/run")
async def run_low_stock_digest(request: Request):
    """Admin: manually trigger the weekly low-stock digest run."""
    await require_admin(request)
    report = await send_low_stock_digests()
    return {"processed": len(report), "report": report}

# ============ ABANDONED CHECKOUT WIN-BACK ============

ABANDONED_MIN_AGE_MINUTES = int(os.environ.get("ABANDONED_MIN_AGE_MINUTES", "60"))
ABANDONED_MAX_AGE_HOURS = int(os.environ.get("ABANDONED_MAX_AGE_HOURS", "48"))

async def send_abandoned_checkout_emails() -> list:
    """Win-back email for buyers who started checkout but never paid.
    One email per order, sent 1-48h after the checkout was initiated."""
    now = datetime.now(timezone.utc)
    newest = now - timedelta(minutes=ABANDONED_MIN_AGE_MINUTES)
    oldest = now - timedelta(hours=ABANDONED_MAX_AGE_HOURS)
    frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
    report = []
    
    cursor = db.orders.find({
        "status": {"$in": ["initiated", "unpaid", "expired"]},
        "abandoned_email_sent": {"$ne": True},
        "created_at": {"$gte": oldest, "$lte": newest},
    })
    async for order in cursor:
        buyer_email = order.get("buyer_email")
        if not buyer_email:
            continue
        # Skip if they completed the purchase in another session
        paid = await db.orders.find_one({
            "buyer_id": order["buyer_id"],
            "product_id": order["product_id"],
            "status": "paid",
        })
        if paid:
            await db.orders.update_one({"_id": order["_id"]}, {"$set": {"abandoned_email_sent": True}})
            continue
        # Skip if the product is gone or sold out
        product = await db.products.find_one({"_id": safe_object_id(order["product_id"])})
        if not product or int(product.get("stock", 0) or 0) <= 0:
            await db.orders.update_one({"_id": order["_id"]}, {"$set": {"abandoned_email_sent": True}})
            continue
        
        stock = int(product.get("stock", 0) or 0)
        scarcity = f'<p style="color:#FACC15;font-size:13px;margin:0 0 4px;">Only {stock} left in stock</p>' if stock <= 5 else ""
        product_url = f"{frontend_url}/products/{order['product_id']}" if frontend_url else ""
        cta = (
            f'<p style="margin:24px 0;"><a href="{product_url}" style="color:#000;background:#39FF14;padding:14px 28px;text-decoration:none;font-weight:bold;display:inline-block;">COMPLETE YOUR ORDER</a></p>'
            if product_url else ""
        )
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
            <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;">UNVEILED THREADS</h1>
            <hr style="border:1px solid #27272A;margin:16px 0;">
            <h2 style="color:#fff;font-size:20px;">You left something behind</h2>
            <p style="color:#9CA3AF;line-height:1.6;">
                Your <strong style="color:#fff;">{order.get('product_name', '')}</strong> (Size {order.get('size', '')}) from
                <strong style="color:#fff;">{order.get('brand_name', '')}</strong> is still waiting in checkout.
            </p>
            <div style="background:#0A0A0A;border:1px solid #27272A;padding:20px;margin:24px 0;">
                {scarcity}
                <p style="color:#fff;font-weight:bold;margin:0 0 2px;">{order.get('product_name', '')}</p>
                <p style="color:#9CA3AF;font-size:12px;margin:0 0 8px;">{order.get('brand_name', '')} &middot; Size {order.get('size', '')}</p>
                <p style="color:#C0C0C0;font-size:18px;font-weight:bold;margin:0;">£{(order.get('price') or 0):.2f}</p>
            </div>
            {cta}
            <p style="color:#9CA3AF;font-size:12px;line-height:1.6;">
                Independent drops don't restock like the big brands — once it's gone, it's gone.
                Every purchase is covered by Unveiled Threads Buyer Protection.
            </p>
            <hr style="border:1px solid #27272A;margin:24px 0;">
            <p style="color:#9CA3AF;font-size:12px;">Unveiled Threads — UK's marketplace for independent streetwear</p>
        </div>
        """
        entry = {"order_id": str(order["_id"]), "email": buyer_email, "product": order.get("product_name"), "sent": False}
        try:
            if RESEND_API_KEY:
                params = {
                    "from": SENDER_EMAIL,
                    "to": [buyer_email],
                    "subject": f"Still want it? {order.get('product_name', 'Your order')} is waiting | Unveiled Threads",
                    "html": html,
                }
                await asyncio.to_thread(resend.Emails.send, params)
                logger.info(f"[ABANDONED CHECKOUT EMAIL SENT] To: {buyer_email} | {order.get('product_name')}")
            else:
                logger.info(f"[MOCK ABANDONED CHECKOUT EMAIL] To: {buyer_email} | {order.get('product_name')}")
            entry["sent"] = True
            await db.orders.update_one({"_id": order["_id"]}, {"$set": {"abandoned_email_sent": True}})
        except Exception as e:
            entry["error"] = str(e)
            logger.warning(f"[ABANDONED CHECKOUT EMAIL FAILED] To: {buyer_email} | {e}")
        report.append(entry)
    return report

async def abandoned_checkout_loop():
    while True:
        try:
            await send_abandoned_checkout_emails()
        except Exception as e:
            logger.error(f"Abandoned checkout loop error: {e}")
        await asyncio.sleep(30 * 60)

@api_router.post("/admin/abandoned-checkout/run")
async def run_abandoned_checkout(request: Request):
    """Admin: manually trigger the abandoned checkout win-back run."""
    await require_admin(request)
    report = await send_abandoned_checkout_emails()
    return {"processed": len(report), "report": report}

@api_router.get("/notifications")
async def get_notifications(request: Request):
    user = await get_current_user(request)
    
    query = {"$or": [{"user_id": user["id"]}]}
    
    # If user is a brand, also get brand notifications
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        query["$or"].append({"brand_id": str(brand["_id"])})
    
    notifications = await db.notifications.find(query).sort("created_at", -1).to_list(50)
    result = []
    for notif in notifications:
        notif["id"] = str(notif["_id"])
        del notif["_id"]
        result.append(notif)
    return result

@api_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, request: Request):
    await get_current_user(request)
    await db.notifications.update_one(
        {"_id": safe_object_id(notification_id)},
        {"$set": {"read": True}}
    )
    return {"message": "Marked as read"}

@api_router.get("/notifications/unread-count")
async def get_unread_count(request: Request):
    user = await get_current_user(request)
    
    query = {"read": False, "$or": [{"user_id": user["id"]}]}
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        query["$or"].append({"brand_id": str(brand["_id"])})
    
    count = await db.notifications.count_documents(query)
    return {"count": count}

@api_router.get("/notifications/poll")
async def poll_notifications(request: Request):
    """Combined poll endpoint for real-time in-app notifications. Returns all unread counts + latest notifications."""
    user = await get_current_user(request)
    
    # Notification count
    notif_query = {"read": False, "$or": [{"user_id": user["id"]}]}
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        notif_query["$or"].append({"brand_id": str(brand["_id"])})
    
    notif_count = await db.notifications.count_documents(notif_query)
    
    # Unread messages count
    convos = await db.conversations.find({
        "$or": [{"participant_1": user["id"]}, {"participant_2": user["id"]}]
    }, {"_id": 1}).to_list(100)
    convo_ids = [str(c["_id"]) for c in convos]
    
    msg_count = 0
    if convo_ids:
        msg_count = await db.messages.count_documents({
            "conversation_id": {"$in": convo_ids},
            "sender_id": {"$ne": user["id"]},
            "read": False
        })
    
    # Latest 3 unread notifications
    latest = []
    latest_notifs = await db.notifications.find(notif_query).sort("created_at", -1).limit(3).to_list(3)
    for n in latest_notifs:
        n["id"] = str(n["_id"])
        del n["_id"]
        if isinstance(n.get("created_at"), datetime):
            n["created_at"] = n["created_at"].isoformat()
        latest.append(n)
    
    return {
        "notifications": notif_count,
        "messages": msg_count,
        "total": notif_count + msg_count,
        "latest": latest
    }

