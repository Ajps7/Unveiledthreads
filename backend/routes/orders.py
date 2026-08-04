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

    is_preorder = bool(product.get("is_preorder"))

    # Stock rules diverge for pre-orders. Non-pre-order behaviour is unchanged.
    if not is_preorder:
        if product["stock"] <= 0:
            raise HTTPException(status_code=400, detail="Product is out of stock")
    else:
        # Pre-order: no stock check. Instead, enforce preorder_limit atomically
        # so a burst of concurrent buyers can't oversell the reserved run.
        preorder_limit = product.get("preorder_limit")
        if preorder_limit is not None:
            current_preorders = await db.orders.count_documents({
                "product_id": str(product["_id"]),
                "status": {"$in": ["preorder_paid", "shipped", "delivered", "initiated"]},
            })
            if current_preorders >= preorder_limit:
                raise HTTPException(status_code=409, detail="Pre-order sold out.")

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
    
    # Auto-apply available referral credit against the Buyer Protection fee (only when programme is live)
    credit_applied = 0.0
    if REFERRALS_ENABLED:
        referral = await db.referrals.find_one({"user_id": user["id"]})
        if referral:
            available = round(referral.get("credits_earned", 0) - referral.get("credits_used", 0), 2)
            if available > 0:
                credit_applied = round(min(available, platform_fee), 2)
    fee_charged = round(platform_fee - credit_applied, 2)
    total_price = round(product_price + fee_charged + shipping_cost, 2)
    
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
        "platform_fee": str(fee_charged),
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
    ]
    if fee_charged > 0:
        fee_desc = "5% + £0.49 (max £6): money-back guarantee, easy returns, and hand-vetted independent brands"
        if credit_applied > 0:
            fee_desc += f" (£{credit_applied:.2f} referral credit applied)"
        line_items.append({
            "price_data": {
                "currency": "gbp",
                "product_data": {"name": "Buyer Protection", "description": fee_desc},
                "unit_amount": int(round(fee_charged * 100)),
            },
            "quantity": 1,
        })
    if shipping_cost > 0:
        line_items.append({
            "price_data": {
                "currency": "gbp",
                "product_data": {"name": "Shipping"},
                "unit_amount": int(round(shipping_cost * 100)),
            },
            "quantity": 1,
        })
    
    payment_intent_data = {"metadata": metadata}
    fee_pence = int(round(fee_charged * 100))
    if fee_pence > 0:
        payment_intent_data["application_fee_amount"] = fee_pence
    
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
            payment_intent_data=payment_intent_data,
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
        "platform_fee": fee_charged,
        "credit_applied": credit_applied,
        "total_charged": total_price,
        "brand_payout": product_price + shipping_cost,
        "stripe_account_id": brand_doc["stripe_account_id"],
        "status": "initiated",
        "shipping_status": "confirmed",
        "tracking_number": None,
        "courier": None,
        "shipping_updates": [],
        "reviewed": False,
        # Pre-order flags (copied from product at checkout so the buyer's
        # commitment is preserved even if the seller later edits the product).
        "is_preorder": is_preorder,
        "preorder_ship_date": product.get("preorder_ship_date") if is_preorder else None,
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
        "credit_applied": order.get("credit_applied") or 0,
        "shipping_cost": order.get("shipping_cost"),
        "total_charged": order.get("total_charged"),
        "is_preorder": bool(order.get("is_preorder")),
        "preorder_ship_date": order.get("preorder_ship_date"),
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
    credit = order.get("credit_applied") or 0
    credit_row = (
        f'<tr><td style="{row_style}">Referral credit</td><td style="{val_style}">-£{credit:.2f}</td></tr>'
        if credit > 0 else ""
    )

    # Pre-order banner — added ONLY when the order is a pre-order so existing
    # in-stock receipts are unchanged. Escapes every user-provided value.
    preorder_block = ""
    if order.get("is_preorder"):
        ship_by = esc(order.get("preorder_ship_date") or "the confirmed date")
        preorder_block = f"""
            <div style="border:1px solid #39FF14;background:#0A0A0A;padding:16px;margin:0 0 20px;">
                <p style="color:#39FF14;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;margin:0 0 6px;">
                    Pre-order — ships by {ship_by}
                </p>
                <p style="color:#9CA3AF;font-size:13px;line-height:1.6;margin:0;">
                    You've been charged today. {esc(order.get('brand_name', ''))} will dispatch your item by
                    <strong style="color:#fff;">{ship_by}</strong>. If it hasn't shipped by then you're covered by
                    Buyer Protection and can request a full refund.
                </p>
            </div>
        """
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
        <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;">UNVEILED THREADS</h1>
        <hr style="border:1px solid #27272A;margin:16px 0;">
        <h2 style="color:#fff;font-size:20px;">Order confirmed — thank you!</h2>
        <p style="color:#9CA3AF;line-height:1.6;">
            You just supported an independent UK brand. <strong style="color:#fff;">{esc(order.get('brand_name', ''))}</strong> has been
            notified and will ship your order soon — track it any time from your Orders page.
        </p>
        {preorder_block}
        <div style="background:#0A0A0A;border:1px solid #27272A;padding:20px;margin:24px 0;">
            <p style="color:#9CA3AF;font-size:11px;text-transform:uppercase;letter-spacing:2px;margin:0 0 12px;">Receipt</p>
            <p style="color:#fff;font-weight:bold;margin:0 0 2px;">{esc(order.get('product_name', ''))}</p>
            <p style="color:#9CA3AF;font-size:12px;margin:0 0 16px;">{esc(order.get('brand_name', ''))} &middot; Size {esc(order.get('size', ''))}</p>
            <table style="width:100%;border-collapse:collapse;">
                <tr><td style="{row_style}">Item</td><td style="{val_style}">£{(order.get('price') or 0):.2f}</td></tr>
                <tr><td style="{row_style}">Buyer Protection</td><td style="{val_style}">£{(order.get('platform_fee') or 0):.2f}</td></tr>
                {credit_row}
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

async def settle_paid_order(order: dict, payment_intent_id: Optional[str] = None) -> bool:
    """Idempotent order settlement: atomically claims the order, deducts stock,
    grants referral credit, consumes applied credit, notifies the brand and
    emails the buyer's receipt. Safe to call from the buyer poll AND the
    reconciliation sweep — only the first caller settles.

    Pre-order path: status is set to `preorder_paid` (distinguishable from
    in-stock `paid` everywhere), no stock is decremented, and the oversell
    guard is skipped. Everything else — receipts, referral credit, brand
    notification — runs identically."""
    now = datetime.now(timezone.utc)
    is_preorder = bool(order.get("is_preorder"))
    settled_status = "preorder_paid" if is_preorder else "paid"
    update = {"status": settled_status, "stock_deducted": True, "settled_at": now}
    if payment_intent_id:
        update["payment_intent_id"] = payment_intent_id
    claim = await db.orders.update_one(
        {"_id": order["_id"], "stock_deducted": {"$ne": True}},
        {"$set": update}
    )
    if claim.modified_count == 0:
        return False
    
    if not is_preorder:
        # Oversell guard: only decrement if stock is still available.
        # Skipped for pre-orders — there is no live stock to decrement.
        stock_result = await db.products.update_one(
            {"_id": ObjectId(order["product_id"]), "stock": {"$gt": 0}},
            {"$inc": {"stock": -1}}
        )
        if stock_result.modified_count == 0:
            # Oversold — another buyer got the last unit. Flag for manual refund.
            await db.orders.update_one({"_id": order["_id"]}, {"$set": {"oversold": True}})
            logger.error(
                f"OVERSOLD: order settled but no stock remained — manual refund required "
                f"(order={order['_id']} product={order['product_id']})"
            )
            await create_notification(
                user_id=None,
                brand_id=order["brand_id"],
                notification_type="oversold_order",
                title="Action needed: oversold order",
                message=f"Order #{str(order['_id'])[-6:]} for {order['product_name']} settled after the last unit had already sold — the item sold twice. Please arrange a refund for this order via support.",
                metadata={"order_id": str(order["_id"]), "product_id": order["product_id"]},
            )
    
    # Referral: credit the referrer on the buyer's first paid order (atomic flag flip).
    # Gated behind REFERRALS_ENABLED — no credits accrue until the programme launches.
    ref_use = None
    if REFERRALS_ENABLED:
        ref_use = await db.referral_uses.find_one_and_update(
            {"user_id": order["buyer_id"], "credit_pending": True},
            {"$set": {"credit_pending": False, "credited_at": now}},
        )
    if ref_use:
        await db.referrals.update_one(
            {"user_id": ref_use["referrer_id"]},
            {"$inc": {"credits_earned": REFERRAL_CREDIT}, "$addToSet": {"referred_users": order["buyer_id"]}},
        )
        await create_notification(
            user_id=ref_use["referrer_id"],
            brand_id=None,
            notification_type="referral_credit",
            title="You've earned referral credit!",
            message=f"£{REFERRAL_CREDIT:.2f} credit added — someone you invited made their first purchase. It'll be applied to the Buyer Protection fee on your next order.",
            metadata={"order_id": str(order["_id"])},
        )
    
    # Consume any referral credit that was applied to this order at checkout
    credit_applied = order.get("credit_applied") or 0
    if credit_applied > 0:
        await db.referrals.update_one(
            {"user_id": order["buyer_id"]},
            {"$inc": {"credits_used": credit_applied}}
        )
    
    await create_notification(
        user_id=None,
        brand_id=order["brand_id"],
        notification_type="order_received",
        title="New Order Received!",
        message=f"New order for {order['product_name']} (Size: {order['size']}) from {order['buyer_name']}. Payout: £{order['brand_payout']:.2f}",
        metadata={"order_session_id": order["session_id"]}
    )
    
    if not order.get("receipt_email_sent"):
        await send_order_receipt_email(order)
    return True

async def reconcile_pending_orders() -> list:
    """Settle paid-but-unreturned orders (buyer paid on Stripe then closed the tab)
    and expire dead sessions. Returns ids of orders settled this run."""
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        return []
    now = datetime.now(timezone.utc)
    settled = []
    cursor = db.orders.find({
        "status": {"$in": ["initiated", "unpaid"]},
        "created_at": {"$gte": now - timedelta(days=7), "$lte": now - timedelta(minutes=15)},
    })
    async for order in cursor:
        try:
            status_data = await asyncio.to_thread(
                get_stripe_session_status, order["session_id"], api_key,
                stripe_account=order.get("stripe_account_id"),
            )
        except Exception as e:
            logger.warning(f"Reconcile: session fetch failed for {order['session_id']}: {e}")
            continue
        if status_data["payment_status"] == "paid":
            if await settle_paid_order(order, payment_intent_id=status_data.get("payment_intent")):
                logger.info(f"[RECONCILED] Order {order['_id']} settled without buyer returning")
                settled.append(str(order["_id"]))
        elif status_data["status"] == "expired":
            await db.orders.update_one(
                {"_id": order["_id"], "status": {"$in": ["initiated", "unpaid"]}},
                {"$set": {"status": "expired"}}
            )
    return settled

async def order_reconciliation_loop():
    while True:
        try:
            await reconcile_pending_orders()
        except Exception as e:
            logger.error(f"Order reconciliation loop error: {e}")
        await asyncio.sleep(10 * 60)

@api_router.post("/admin/orders/reconcile")
async def run_order_reconciliation(request: Request):
    """Admin: manually trigger the paid-order reconciliation sweep."""
    await require_admin(request)
    settled = await reconcile_pending_orders()
    return {"settled": settled, "count": len(settled)}

@api_router.get("/orders/status/{session_id}")
async def get_order_status(session_id: str, request: Request):
    user = await get_current_user(request)
    
    order = await db.orders.find_one({"session_id": session_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["buyer_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if order.get("status") in ("paid", "preorder_paid"):
        return {"status": "complete", "payment_status": "paid", "already_processed": True, "order": _order_receipt(order)}
    
    api_key = os.environ.get("STRIPE_API_KEY")
    
    try:
        # Direct charge: session lives on the seller's connected account
        status_data = get_stripe_session_status(
            session_id, api_key, stripe_account=order.get("stripe_account_id")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status_data["payment_status"], "status": status_data["status"]}}
    )
    
    if status_data["payment_status"] == "paid":
        await settle_paid_order(order, payment_intent_id=status_data.get("payment_intent"))
    else:
        await db.orders.update_one(
            {"session_id": session_id, "stock_deducted": {"$ne": True}},
            {"$set": {"status": status_data["payment_status"]}}
        )
    
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

