# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ PRODUCT PURCHASE / ORDERS ============

@api_router.post("/orders/checkout")
@limiter.limit("20/minute")
async def create_order_checkout(purchase: ProductPurchaseRequest, request: Request):
    user = await get_current_user(request)
    
    product = await db.products.find_one({"_id": ObjectId(purchase.product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product["stock"] <= 0:
        raise HTTPException(status_code=400, detail="Product is out of stock")
    
    if purchase.size not in product["sizes"]:
        raise HTTPException(status_code=400, detail="Selected size is not available")
    
    # Verify brand has completed Stripe Connect onboarding (required for split payments)
    brand_doc = await db.brands.find_one({"_id": ObjectId(product["brand_id"])})
    if not brand_doc:
        raise HTTPException(status_code=404, detail="Brand not found")
    if not brand_doc.get("stripe_account_id") or not brand_doc.get("stripe_charges_enabled"):
        raise HTTPException(
            status_code=400,
            detail="This brand hasn't completed Stripe payment onboarding yet. Please check back soon.",
        )
    
    # Calculate Buyer Protection fee (once per order, on the combined subtotal) and shipping
    product_price = product["price"]
    shipping_cost = product.get("shipping_cost", 0)
    platform_fee = calculate_buyer_fee(product_price)
    total_price = round(product_price + platform_fee + shipping_cost, 2)
    
    api_key = os.environ.get("STRIPE_API_KEY")
    stripe_sdk.api_key = api_key
    
    success_url = f"{purchase.origin_url}/order/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{purchase.origin_url}/products/{purchase.product_id}"
    
    metadata = {
        "type": "product_purchase",
        "user_id": user["id"],
        "product_id": str(product["_id"]),
        "brand_id": product["brand_id"],
        "size": purchase.size,
        "product_price": str(product_price),
        "platform_fee": str(platform_fee),
        "shipping_cost": str(shipping_cost),
    }
    
    line_items = [
        {
            "price_data": {
                "currency": "gbp",
                "product_data": {
                    "name": f"{product['name']} (Size: {purchase.size})",
                    "description": f"Sold by {product['brand_name']} via Unveiled Threads",
                },
                "unit_amount": int(round(product_price * 100)),
            },
            "quantity": 1,
        },
        {
            "price_data": {
                "currency": "gbp",
                "product_data": {
                    "name": "Buyer Protection",
                    "description": "5% + £0.49 (max £6): money-back guarantee, easy returns, and hand-vetted independent brands",
                },
                "unit_amount": int(round(platform_fee * 100)),
            },
            "quantity": 1,
        },
    ]
    if shipping_cost > 0:
        line_items.append({
            "price_data": {
                "currency": "gbp",
                "product_data": {"name": "Shipping"},
                "unit_amount": int(round(shipping_cost * 100)),
            },
            "quantity": 1,
        })
    
    try:
        # Direct charge: payment is processed on the seller's connected account
        # (passed via stripe_account header). The seller is liable for chargebacks.
        # Platform takes the Buyer Protection fee (5% + £0.49, max £6) via `application_fee_amount`.
        session = await asyncio.to_thread(
            stripe_sdk.checkout.Session.create,
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
            payment_intent_data={
                "application_fee_amount": int(round(platform_fee * 100)),
                "metadata": metadata,
            },
            stripe_account=brand_doc["stripe_account_id"],
        )
    except Exception as e:
        logger.error(f"Stripe direct charge checkout failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    
    # Create order record
    order_doc = {
        "session_id": session.id,
        "buyer_id": user["id"],
        "buyer_email": user["email"],
        "buyer_name": user["name"],
        "product_id": str(product["_id"]),
        "product_name": product["name"],
        "brand_id": product["brand_id"],
        "brand_name": product["brand_name"],
        "size": purchase.size,
        "price": product_price,
        "shipping_cost": shipping_cost,
        "platform_fee": platform_fee,
        "total_charged": total_price,
        "brand_payout": product_price + shipping_cost,
        "stripe_account_id": brand_doc["stripe_account_id"],
        "status": "initiated",
        "shipping_status": "confirmed",
        "tracking_number": None,
        "courier": None,
        "shipping_updates": [],
        "reviewed": False,
        "created_at": datetime.now(timezone.utc)
    }
    await db.orders.insert_one(order_doc)
    
    # Also add to payment_transactions
    await db.payment_transactions.insert_one({
        "session_id": session.id,
        "user_id": user["id"],
        "type": "product_purchase",
        "amount": total_price,
        "currency": "gbp",
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"url": session.url, "session_id": session.id}

def _order_receipt(order: dict) -> dict:
    return {
        "product_name": order.get("product_name"),
        "brand_name": order.get("brand_name"),
        "size": order.get("size"),
        "price": order.get("price"),
        "platform_fee": order.get("platform_fee"),
        "shipping_cost": order.get("shipping_cost"),
        "total_charged": order.get("total_charged"),
    }

async def send_order_receipt_email(order: dict):
    """Branded order confirmation email to the buyer with the full fee breakdown."""
    buyer_email = order.get("buyer_email")
    if not buyer_email:
        return
    shipping = order.get("shipping_cost") or 0
    shipping_str = f"£{shipping:.2f}" if shipping > 0 else "Free"
    frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
    row_style = "padding:8px 0;border-bottom:1px solid #27272A;color:#9CA3AF;font-size:14px;"
    val_style = "padding:8px 0;border-bottom:1px solid #27272A;color:#FFFFFF;font-size:14px;text-align:right;"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
        <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;">UNVEILED THREADS</h1>
        <hr style="border:1px solid #27272A;margin:16px 0;">
        <h2 style="color:#fff;font-size:20px;">Order confirmed — thank you!</h2>
        <p style="color:#9CA3AF;line-height:1.6;">
            You just supported an independent UK brand. <strong style="color:#fff;">{order.get('brand_name', '')}</strong> has been
            notified and will ship your order soon — track it any time from your Orders page.
        </p>
        <div style="background:#0A0A0A;border:1px solid #27272A;padding:20px;margin:24px 0;">
            <p style="color:#9CA3AF;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 12px;">Receipt</p>
            <p style="color:#fff;font-weight:bold;margin:0 0 2px;">{order.get('product_name', '')}</p>
            <p style="color:#9CA3AF;font-size:12px;margin:0 0 16px;">{order.get('brand_name', '')} &middot; Size {order.get('size', '')}</p>
            <table style="width:100%;border-collapse:collapse;">
                <tr><td style="{row_style}">Item</td><td style="{val_style}">£{(order.get('price') or 0):.2f}</td></tr>
                <tr><td style="{row_style}">Buyer Protection</td><td style="{val_style}">£{(order.get('platform_fee') or 0):.2f}</td></tr>
                <tr><td style="{row_style}">Shipping</td><td style="{val_style}">{shipping_str}</td></tr>
                <tr><td style="padding:10px 0;color:#fff;font-weight:bold;font-size:15px;">Total</td>
                    <td style="padding:10px 0;color:#39FF14;font-weight:bold;font-size:15px;text-align:right;">£{(order.get('total_charged') or 0):.2f}</td></tr>
            </table>
        </div>
        <p style="color:#9CA3AF;font-size:12px;line-height:1.6;">
            Buyer Protection (5% + £0.49, max £6) covers your money-back guarantee, easy returns and hand-vetted
            independent brands — it's how we keep the platform commission-free for independent brands.
            {f'<a href="{frontend_url}/orders" style="color:#39FF14;">View your order</a> &middot; <a href="{frontend_url}/buyer-protection" style="color:#39FF14;">Buyer Protection policy</a>' if frontend_url else ''}
        </p>
        <hr style="border:1px solid #27272A;margin:24px 0;">
        <p style="color:#9CA3AF;font-size:12px;">Unveiled Threads — UK's marketplace for independent streetwear</p>
    </div>
    """
    if not RESEND_API_KEY:
        logger.info(f"[MOCK RECEIPT EMAIL] To: {buyer_email} | {order.get('product_name')}")
        return
    params = {
        "from": SENDER_EMAIL,
        "to": [buyer_email],
        "subject": f"Order confirmed — {order.get('product_name', 'your order')} | Unveiled Threads",
        "html": html,
    }
    try:
        await asyncio.to_thread(resend.Emails.send, params)
        await db.orders.update_one({"_id": order["_id"]}, {"$set": {"receipt_email_sent": True}})
        logger.info(f"[RECEIPT EMAIL SENT] To: {buyer_email} | {order.get('product_name')}")
    except Exception as e:
        logger.warning(f"[RECEIPT EMAIL FAILED] To: {buyer_email} | {e}")

@api_router.get("/orders/status/{session_id}")
async def get_order_status(session_id: str, request: Request):
    user = await get_current_user(request)
    
    order = await db.orders.find_one({"session_id": session_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["buyer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if order.get("status") == "paid":
        return {"status": "complete", "payment_status": "paid", "already_processed": True, "order": _order_receipt(order)}
    
    api_key = os.environ.get("STRIPE_API_KEY")
    
    try:
        # Direct charge: session lives on the seller's connected account
        status_data = get_stripe_session_status(
            session_id, api_key, stripe_account=order.get("stripe_account_id")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    
    await db.orders.update_one(
        {"session_id": session_id},
        {"$set": {"status": status_data["payment_status"]}}
    )
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status_data["payment_status"], "status": status_data["status"]}}
    )
    
    # If paid and not already processed
    if status_data["payment_status"] == "paid" and not order.get("stock_deducted"):
        # Deduct stock
        await db.products.update_one(
            {"_id": ObjectId(order["product_id"])},
            {"$inc": {"stock": -1}}
        )
        await db.orders.update_one(
            {"session_id": session_id},
            {"$set": {"stock_deducted": True}}
        )
        
        # Send notification to brand
        await create_notification(
            user_id=None,
            brand_id=order["brand_id"],
            notification_type="order_received",
            title="New Order Received!",
            message=f"New order for {order['product_name']} (Size: {order['size']}) from {order['buyer_name']}. Payout: £{order['brand_payout']:.2f}",
            metadata={"order_session_id": session_id}
        )
        
        # Email the buyer a branded receipt (once per order)
        if not order.get("receipt_email_sent"):
            await send_order_receipt_email(order)
    
    return {"status": status_data["status"], "payment_status": status_data["payment_status"], "order": _order_receipt(order)}

@api_router.get("/orders/my-orders")
async def get_my_orders(request: Request):
    user = await get_current_user(request)
    
    orders = await db.orders.find({"buyer_id": user["id"]}).sort("created_at", -1).to_list(50)
    result = []
    for order in orders:
        order["id"] = str(order["_id"])
        del order["_id"]
        result.append(order)
    return result

@api_router.get("/orders/brand-orders")
async def get_brand_orders(request: Request):
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    orders = await db.orders.find({"brand_id": str(brand["_id"])}).sort("created_at", -1).to_list(50)
    result = []
    for order in orders:
        order["id"] = str(order["_id"])
        del order["_id"]
        result.append(order)
    return result

