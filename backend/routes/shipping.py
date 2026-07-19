# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ SHIPPING / TRACKING ============

COURIER_TRACKING_URLS = {
    "royal mail": "https://www.royalmail.com/track-your-item#/tracking-results/{n}",
    "evri": "https://www.evri.com/track/parcel/{n}",
    "hermes": "https://www.evri.com/track/parcel/{n}",
    "hermes uk": "https://www.evri.com/track/parcel/{n}",
    "dpd": "https://track.dpd.co.uk/parcels/{n}",
    "dpd uk": "https://track.dpd.co.uk/parcels/{n}",
    "yodel": "https://www.yodel.co.uk/track/{n}",
    "ups": "https://www.ups.com/track?tracknum={n}",
    "fedex": "https://www.fedex.com/fedextrack/?tracknumbers={n}",
}

def get_tracking_url(courier: str, tracking_number: str) -> Optional[str]:
    if not courier or not tracking_number:
        return None
    template = COURIER_TRACKING_URLS.get(courier.strip().lower())
    return template.format(n=quote(tracking_number)) if template else None

async def send_order_shipped_email(order: dict, courier: str, tracking_number: str):
    """Branded shipped notification to the buyer with a clickable tracking link."""
    buyer_email = order.get("buyer_email")
    if not buyer_email:
        return
    tracking_url = get_tracking_url(courier, tracking_number)
    frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
    track_button = (
        f'<p style="margin:24px 0;"><a href="{tracking_url}" style="color:#000;background:#39FF14;padding:14px 28px;text-decoration:none;font-weight:bold;display:inline-block;">TRACK YOUR PARCEL</a></p>'
        if tracking_url else ""
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
        <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;">UNVEILED THREADS</h1>
        <hr style="border:1px solid #27272A;margin:16px 0;">
        <h2 style="color:#fff;font-size:20px;">Your order is on its way!</h2>
        <p style="color:#9CA3AF;line-height:1.6;">
            <strong style="color:#fff;">{order.get('brand_name', '')}</strong> has shipped your
            <strong style="color:#fff;">{order.get('product_name', '')}</strong> (Size {order.get('size', '')}) via
            <strong style="color:#fff;">{courier}</strong>.
        </p>
        <div style="background:#0A0A0A;border:1px solid #27272A;padding:20px;margin:24px 0;">
            <p style="color:#9CA3AF;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 8px;">Tracking number</p>
            <p style="color:#fff;font-family:monospace;font-size:16px;margin:0;">{tracking_number}</p>
            <p style="color:#9CA3AF;font-size:12px;margin:8px 0 0;">via {courier}</p>
        </div>
        {track_button}
        <p style="color:#9CA3AF;font-size:12px;line-height:1.6;">
            {f'You can also follow the delivery timeline on your <a href="{frontend_url}/orders" style="color:#39FF14;">Orders page</a>. ' if frontend_url else ''}Remember, every purchase is covered by Unveiled Threads Buyer Protection.
        </p>
        <hr style="border:1px solid #27272A;margin:24px 0;">
        <p style="color:#9CA3AF;font-size:12px;">Unveiled Threads — UK's marketplace for independent streetwear</p>
    </div>
    """
    if not RESEND_API_KEY:
        logger.info(f"[MOCK SHIPPED EMAIL] To: {buyer_email} | {order.get('product_name')} via {courier}")
        return
    params = {
        "from": SENDER_EMAIL,
        "to": [buyer_email],
        "subject": f"Shipped — {order.get('product_name', 'your order')} is on its way | Unveiled Threads",
        "html": html,
    }
    try:
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[SHIPPED EMAIL SENT] To: {buyer_email} | {order.get('product_name')} via {courier}")
    except Exception as e:
        logger.warning(f"[SHIPPED EMAIL FAILED] To: {buyer_email} | {e}")

async def send_order_delivered_email(order: dict):
    """Branded 'your order has arrived — leave a review' email to the buyer."""
    buyer_email = order.get("buyer_email")
    if not buyer_email:
        return
    frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
    review_button = (
        f'<p style="margin:24px 0;"><a href="{frontend_url}/orders" style="color:#000;background:#39FF14;padding:14px 28px;text-decoration:none;font-weight:bold;display:inline-block;">LEAVE A REVIEW</a></p>'
        if frontend_url else ""
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
        <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;">UNVEILED THREADS</h1>
        <hr style="border:1px solid #27272A;margin:16px 0;">
        <h2 style="color:#fff;font-size:20px;">Your order has arrived!</h2>
        <p style="color:#9CA3AF;line-height:1.6;">
            Your <strong style="color:#fff;">{order.get('product_name', '')}</strong> (Size {order.get('size', '')}) from
            <strong style="color:#fff;">{order.get('brand_name', '')}</strong> has been delivered. We hope you love it.
        </p>
        <p style="color:#9CA3AF;line-height:1.6;">
            Reviews are everything for independent brands — a quick rating helps
            <strong style="color:#fff;">{order.get('brand_name', '')}</strong> get discovered by more buyers like you.
        </p>
        {review_button}
        <p style="color:#9CA3AF;font-size:12px;line-height:1.6;">
            Something not right? Message the brand from your Orders page{f' or read our <a href="{frontend_url}/buyer-protection" style="color:#39FF14;">Buyer Protection policy</a>' if frontend_url else ''}.
        </p>
        <hr style="border:1px solid #27272A;margin:24px 0;">
        <p style="color:#9CA3AF;font-size:12px;">Unveiled Threads — UK's marketplace for independent streetwear</p>
    </div>
    """
    if not RESEND_API_KEY:
        logger.info(f"[MOCK DELIVERED EMAIL] To: {buyer_email} | {order.get('product_name')}")
        return
    params = {
        "from": SENDER_EMAIL,
        "to": [buyer_email],
        "subject": f"Delivered — how was your {order.get('product_name', 'order')}? | Unveiled Threads",
        "html": html,
    }
    try:
        await asyncio.to_thread(resend.Emails.send, params)
        await db.orders.update_one({"_id": order["_id"]}, {"$set": {"delivered_email_sent": True}})
        logger.info(f"[DELIVERED EMAIL SENT] To: {buyer_email} | {order.get('product_name')}")
    except Exception as e:
        logger.warning(f"[DELIVERED EMAIL FAILED] To: {buyer_email} | {e}")

@api_router.get("/shipping/couriers")
async def get_couriers():
    return UK_COURIERS

@api_router.put("/orders/{order_id}/ship")
async def ship_order(order_id: str, ship_data: ShipOrderRequest, request: Request):
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    order = await db.orders.find_one({"_id": safe_object_id(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["brand_id"] != str(brand["_id"]):
        raise HTTPException(status_code=403, detail="Not your order")
    if order.get("status") != "paid":
        raise HTTPException(status_code=400, detail="Order must be paid before shipping")
    
    now = datetime.now(timezone.utc)
    shipping_update = {
        "status": "shipped",
        "message": f"Shipped via {ship_data.courier}. Tracking: {ship_data.tracking_number}",
        "timestamp": now
    }
    
    await db.orders.update_one(
        {"_id": safe_object_id(order_id)},
        {
            "$set": {
                "shipping_status": "shipped",
                "tracking_number": ship_data.tracking_number,
                "courier": ship_data.courier,
                "shipped_at": now
            },
            "$push": {"shipping_updates": shipping_update}
        }
    )
    
    # Notify buyer (in-app only — the branded shipped email below replaces the generic one)
    await create_notification(
        user_id=order["buyer_id"],
        brand_id=None,
        notification_type="order_shipped",
        title="Your Order Has Been Shipped!",
        message=f"Your order for {order['product_name']} has been shipped via {ship_data.courier}. Tracking: {ship_data.tracking_number}",
        metadata={"order_id": order_id, "tracking_number": ship_data.tracking_number, "courier": ship_data.courier},
        send_email=False
    )
    
    # Branded shipped email with a clickable tracking link
    await send_order_shipped_email(order, ship_data.courier, ship_data.tracking_number)
    
    return {"message": "Order marked as shipped"}

@api_router.put("/orders/{order_id}/shipping-status")
async def update_shipping_status(order_id: str, status_data: UpdateShippingStatus, request: Request):
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    order = await db.orders.find_one({"_id": safe_object_id(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["brand_id"] != str(brand["_id"]):
        raise HTTPException(status_code=403, detail="Not your order")
    
    if status_data.status not in SHIPPING_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(SHIPPING_STATUSES)}")
    
    now = datetime.now(timezone.utc)
    status_messages = {
        "processing": "Order is being prepared",
        "shipped": "Order has been shipped",
        "in_transit": "Package is in transit",
        "out_for_delivery": "Package is out for delivery",
        "delivered": "Package has been delivered"
    }
    
    shipping_update = {
        "status": status_data.status,
        "message": status_messages.get(status_data.status, status_data.status),
        "timestamp": now
    }
    
    update_fields = {"shipping_status": status_data.status}
    if status_data.status == "delivered":
        update_fields["delivered_at"] = now
    
    await db.orders.update_one(
        {"_id": safe_object_id(order_id)},
        {"$set": update_fields, "$push": {"shipping_updates": shipping_update}}
    )
    
    # Notify buyer of status change (in-app only for delivered — branded email below)
    is_delivered = status_data.status == "delivered"
    await create_notification(
        user_id=order["buyer_id"],
        brand_id=None,
        notification_type="shipping_update",
        title=f"Shipping Update: {status_messages.get(status_data.status, status_data.status)}",
        message=f"Your order for {order['product_name']} — {status_messages.get(status_data.status, '')}",
        metadata={"order_id": order_id, "status": status_data.status},
        send_email=not is_delivered
    )
    
    # Branded "arrived — leave a review" email (once per order)
    if is_delivered and not order.get("delivered_email_sent"):
        await send_order_delivered_email(order)
    
    return {"message": f"Shipping status updated to {status_data.status}"}

@api_router.get("/orders/{order_id}")
async def get_order_detail(order_id: str, request: Request):
    user = await get_current_user(request)
    
    order = await db.orders.find_one({"_id": safe_object_id(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check access: buyer or brand owner
    brand = await db.brands.find_one({"user_id": user["id"]})
    is_buyer = order["buyer_id"] == user["id"]
    is_brand = brand and order["brand_id"] == str(brand["_id"])
    is_admin = user.get("role") == "admin"
    
    if not (is_buyer or is_brand or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    order["id"] = str(order["_id"])
    del order["_id"]
    
    # Convert datetime objects in shipping_updates
    if "shipping_updates" in order:
        for update in order["shipping_updates"]:
            if isinstance(update.get("timestamp"), datetime):
                update["timestamp"] = update["timestamp"].isoformat()
    
    for field in ["created_at", "shipped_at", "delivered_at"]:
        if field in order and isinstance(order[field], datetime):
            order[field] = order[field].isoformat()
    
    return order

