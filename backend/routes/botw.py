# Brand of the Week — weekly hybrid auto-rotation with a 24h admin veto window.
#
# CYCLE:
#   week_index % 4 == 3  →  performance-weighted pick (top scorer on recent
#                            orders/revenue/freshness/rating within cooldown)
#   otherwise            →  fair rotation (oldest last-featured wins)
#
# TIMELINE FOR ONE ROTATION:
#   T-24h : loop picks `next_brand_id`, notifies every admin. Admin has 24h
#           to veto/swap via POST /api/admin/botw/veto.
#   T=0   : loop demotes current BotW, promotes next, schedules next rotation.
#
# SINGLE-DOC STATE at db.botw_state._id="singleton". Kept in one doc so the
# whole feature can be reasoned about + wiped for tests in one call.
#
# ADMIN OVERRIDE: the legacy `POST /api/admin/brands/{id}/set-brand-of-week`
# still works. When admin uses it, the loop treats that brand as the current
# BotW and just reschedules the NEXT rotation from that moment.
from core import *  # noqa: F401,F403

import asyncio
from datetime import datetime, timedelta, timezone as _tz

# ---- Config ----
ROTATION_INTERVAL_DAYS = int(os.environ.get("BOTW_ROTATION_INTERVAL_DAYS", "7"))
VETO_WINDOW_HOURS = int(os.environ.get("BOTW_VETO_WINDOW_HOURS", "24"))
COOLDOWN_DAYS = int(os.environ.get("BOTW_COOLDOWN_DAYS", "56"))          # ~8 weeks
LOOP_INTERVAL_SECONDS = int(os.environ.get("BOTW_LOOP_INTERVAL_SECONDS", "3600"))
CYCLE_PERFORMANCE_STEP = 4   # every 4th cycle is performance-weighted

STATE_ID = "singleton"


# ============ ELIGIBILITY & SCORING ============

async def _list_eligible_brands(exclude_current_id: Optional[str] = None) -> List[dict]:
    """Approved brands that (a) have at least one published, in-stock product,
    (b) are outside the cooldown window, and (c) aren't the currently-featured
    brand. Returns a list of full brand docs (with `_id`)."""
    cooldown_cutoff = datetime.now(_tz.utc) - timedelta(days=COOLDOWN_DAYS)
    query: dict = {
        "$or": [
            {"botw_last_featured_at": {"$exists": False}},
            {"botw_last_featured_at": None},
            {"botw_last_featured_at": {"$lt": cooldown_cutoff}},
        ],
    }
    if exclude_current_id:
        try:
            query["_id"] = {"$ne": ObjectId(exclude_current_id)}
        except Exception:
            pass

    candidates: List[dict] = []
    async for brand in db.brands.find(query):
        # Must have at least one live, in-stock product to be worth featuring.
        has_stock = await db.products.count_documents({
            "brand_id": str(brand["_id"]),
            "status": {"$ne": "draft"},
            "moderation_status": {"$ne": "flagged"},
            "stock": {"$gt": 0},
        })
        if has_stock == 0:
            continue
        candidates.append(brand)
    return candidates


async def _score_brand_performance(brand_id: str) -> float:
    """Rolling 30-day performance score. Simple, transparent, easy to tune:

        score = 3 * orders_last_30d
              + 2 * revenue_last_30d / 100
              + 1 * new_products_last_30d
              + 0.5 * rolling_rating (5-star avg × 10, or 0 if none)

    Chosen so a brand with a single big sale doesn't wipe out a busy brand
    with lots of smaller ones."""
    since = datetime.now(_tz.utc) - timedelta(days=30)

    orders_count = 0
    revenue = 0.0
    async for order in db.orders.find({
        "brand_id": brand_id,
        "status": {"$in": SALE_STATUSES},
        "created_at": {"$gte": since},
    }, {"price": 1}):
        orders_count += 1
        revenue += float(order.get("price") or 0)

    new_products = await db.products.count_documents({
        "brand_id": brand_id,
        "status": {"$ne": "draft"},
        "created_at": {"$gte": since},
    })

    rating_agg = await db.reviews.aggregate([
        {"$match": {"brand_id": brand_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$brand_rating"}}},
    ]).to_list(1)
    avg_rating = float(rating_agg[0]["avg"]) if rating_agg else 0.0

    return (
        3.0 * orders_count
        + 2.0 * (revenue / 100.0)
        + 1.0 * new_products
        + 0.5 * (avg_rating * 10.0)
    )


async def _pick_next_brand(cycle_index: int, current_id: Optional[str]) -> Optional[dict]:
    """Choose the next BotW brand for the given cycle. Returns the brand doc
    or None if the pool is empty (e.g. brand-new install with nobody
    approved). Performance week if cycle_index % 4 == 3, else fair rotation."""
    eligible = await _list_eligible_brands(exclude_current_id=current_id)
    if not eligible:
        return None

    if cycle_index % CYCLE_PERFORMANCE_STEP == (CYCLE_PERFORMANCE_STEP - 1):
        # Performance-weighted: score them all, pick top. Ties broken by
        # oldest last_featured (or never featured) — same signal as fair.
        scored: List[Tuple[float, datetime, dict]] = []
        for b in eligible:
            score = await _score_brand_performance(str(b["_id"]))
            # Never-featured brands get datetime.min so ties favour newcomers.
            lf = b.get("botw_last_featured_at") or datetime.min.replace(tzinfo=_tz.utc)
            if lf.tzinfo is None:
                lf = lf.replace(tzinfo=_tz.utc)
            scored.append((-score, lf, b))
        scored.sort(key=lambda x: (x[0], x[1]))
        return scored[0][2]

    # Fair rotation: oldest last_featured_at (or never-featured) first.
    # Never-featured beats featured-a-year-ago, so ONLY newcomers win until
    # everyone's had a turn.
    def _key(b):
        lf = b.get("botw_last_featured_at")
        if lf is None:
            return datetime.min.replace(tzinfo=_tz.utc)
        if lf.tzinfo is None:
            return lf.replace(tzinfo=_tz.utc)
        return lf
    eligible.sort(key=_key)
    return eligible[0]


# ============ STATE HELPERS ============

async def _get_state() -> dict:
    state = await db.botw_state.find_one({"_id": STATE_ID})
    if state:
        return state
    # First-run: initialise a fresh state doc. `current_brand_id` is picked
    # from whatever is_brand_of_week already points at (so a human-set BotW
    # keeps its position when auto-rotation is switched on for the first
    # time). If nobody is BotW, we leave it null and the next tick fills it.
    now = datetime.now(_tz.utc)
    manual_current = await db.brands.find_one({"is_brand_of_week": True})
    current_id = str(manual_current["_id"]) if manual_current else None
    doc = {
        "_id": STATE_ID,
        "current_brand_id": current_id,
        "current_started_at": now if current_id else None,
        "next_brand_id": None,
        "next_queued_at": None,
        "next_scheduled_at": now + timedelta(days=ROTATION_INTERVAL_DAYS),
        "cycle_index": 0,
        "history": [],
        "updated_at": now,
    }
    await db.botw_state.insert_one(doc)
    return doc


async def _notify_admins_of_pick(next_brand: dict, scheduled_at: datetime) -> None:
    """Ping every admin so they see the queued pick in their notifications
    and have 24h to veto/swap before the rotation goes live."""
    async for admin in db.users.find({"role": "admin"}, {"_id": 1}):
        try:
            await create_notification(
                user_id=str(admin["_id"]),
                brand_id=str(next_brand["_id"]),
                notification_type="botw_queued",
                title="Brand of the Week queued",
                message=(
                    f"{next_brand.get('brand_name')} will become BotW at "
                    f"{scheduled_at.strftime('%a %d %b %H:%M')} UTC — veto within 24h if needed."
                ),
                metadata={"brand_id": str(next_brand["_id"])},
            )
        except Exception as e:
            logger.warning(f"[BOTW] Admin notify failed: {e}")


# ============ BRAND-FACING EMAILS ============

async def _brand_owner_email(brand: dict) -> Optional[Tuple[str, str]]:
    """Return (recipient_email, owner_name) for a brand, or None if not resolvable."""
    owner_id = brand.get("user_id")
    if not owner_id:
        return None
    try:
        user = await db.users.find_one({"_id": ObjectId(owner_id)}, {"email": 1, "name": 1})
    except Exception:
        return None
    if not user or not user.get("email"):
        return None
    return (user["email"], user.get("name") or brand.get("brand_name") or "there")


async def send_botw_queued_email(brand: dict, scheduled_at: datetime) -> None:
    """"You've been picked as next BotW — the slot goes live in ~24h" email.
    Sent whenever the loop or an admin sets `next_brand_id`. Never raises —
    email failures must not break the rotation loop."""
    resolved = await _brand_owner_email(brand)
    if not resolved:
        return
    recipient_email, owner_name = resolved

    if not (RESEND_API_KEY and SENDER_EMAIL):
        logger.info(f"[MOCK EMAIL — BOTW queued] To: {recipient_email} | brand={brand.get('brand_name')}")
        return

    brand_name = brand.get("brand_name") or "your brand"
    slug = brand.get("slug") or ""
    frontend_url = os.environ.get("FRONTEND_URL", "https://unveiledthreads.co.uk").rstrip("/")
    dashboard_url = f"{frontend_url}/brand/dashboard"
    storefront_url = f"{frontend_url}/@{slug}" if slug else frontend_url

    when = scheduled_at.strftime("%A %d %B at %H:%M UTC") if scheduled_at else "soon"

    html_content = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
            <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;letter-spacing:1px;">UNVEILED THREADS</h1>
            <hr style="border:1px solid #27272A;margin:16px 0;">
            <p style="color:#39FF14;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;margin:0 0 8px;">
                You're up next
            </p>
            <h2 style="color:#fff;font-size:22px;margin:0 0 12px;">You'll be Brand of the Week — {esc(when)}</h2>
            <p style="color:#9CA3AF;line-height:1.6;margin:0 0 16px;">
                Hey {esc(owner_name)}, we've queued <strong style="color:#fff;">{esc(brand_name)}</strong> to
                take the Brand of the Week slot at the top of Unveiled Threads.
                Your storefront will be the first thing every visitor sees for the whole week.
            </p>
            <div style="border:1px solid #39FF14;background:#0A0A0A;padding:20px;margin:24px 0;">
                <p style="color:#fff;font-size:15px;font-weight:bold;margin:0 0 12px;">Prep checklist</p>
                <ul style="color:#9CA3AF;font-size:13px;line-height:1.7;margin:0;padding-left:20px;">
                    <li>Stock levels — restock your bestsellers so they don't sell out day one</li>
                    <li>Freshest product photos on your hero image (submit one for admin approval)</li>
                    <li>Storefront tagline &amp; bio — this is prime shop-window real estate</li>
                    <li>Tell your community: post to your socials so your fans catch the moment</li>
                </ul>
            </div>
            <p style="color:#9CA3AF;line-height:1.6;margin:0 0 16px;">
                <a href="{dashboard_url}" style="color:#39FF14;text-decoration:none;font-weight:bold;">Open your dashboard →</a>
                &nbsp;·&nbsp;
                <a href="{storefront_url}" style="color:#39FF14;text-decoration:none;font-weight:bold;">View your storefront →</a>
            </p>
            <p style="color:#6B7280;font-size:12px;line-height:1.6;">
                Note: The Unveiled Threads admin team can veto or swap picks within a 24h window before the slot goes live.
                In the rare case that happens, we'll let you know.
            </p>
            <hr style="border:1px solid #27272A;margin:24px 0;">
            <p style="color:#9CA3AF;font-size:12px;">Unveiled Threads — UK's marketplace for independent streetwear</p>
        </div>
    """
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [recipient_email],
            "subject": "Unveiled Threads — You're up next as Brand of the Week",
            "html": html_content,
        })
        logger.info(f"[BOTW QUEUED EMAIL SENT] To: {recipient_email} | brand={brand_name}")
    except Exception as e:
        logger.warning(f"[BOTW QUEUED EMAIL FAILED] To: {recipient_email} | Error: {e}")


async def send_botw_promoted_email(brand: dict, ends_at: datetime) -> None:
    """"You're now Brand of the Week!" email. Sent at rotation time."""
    resolved = await _brand_owner_email(brand)
    if not resolved:
        return
    recipient_email, owner_name = resolved

    if not (RESEND_API_KEY and SENDER_EMAIL):
        logger.info(f"[MOCK EMAIL — BOTW live] To: {recipient_email} | brand={brand.get('brand_name')}")
        return

    brand_name = brand.get("brand_name") or "your brand"
    slug = brand.get("slug") or ""
    frontend_url = os.environ.get("FRONTEND_URL", "https://unveiledthreads.co.uk").rstrip("/")
    storefront_url = f"{frontend_url}/@{slug}" if slug else frontend_url
    dashboard_url = f"{frontend_url}/brand/dashboard"

    until = ends_at.strftime("%A %d %B") if ends_at else "next week"

    html_content = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
            <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;letter-spacing:1px;">UNVEILED THREADS</h1>
            <hr style="border:1px solid #27272A;margin:16px 0;">
            <p style="color:#39FF14;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;margin:0 0 8px;">
                Live now
            </p>
            <h2 style="color:#fff;font-size:26px;margin:0 0 12px;">{esc(brand_name)} is Brand of the Week</h2>
            <p style="color:#9CA3AF;line-height:1.6;margin:0 0 20px;">
                Congratulations {esc(owner_name)} — your storefront is now front-and-centre on Unveiled Threads
                until <strong style="color:#fff;">{esc(until)}</strong>. Every visitor to the homepage sees you first.
            </p>
            <div style="text-align:center;margin:24px 0;">
                <a href="{storefront_url}"
                    style="display:inline-block;background:#39FF14;color:#000;text-decoration:none;font-weight:bold;
                    padding:14px 28px;letter-spacing:0.1em;text-transform:uppercase;font-size:13px;">
                    View your storefront →
                </a>
            </div>
            <div style="border:1px solid #27272A;background:#0A0A0A;padding:20px;margin:24px 0;">
                <p style="color:#fff;font-size:15px;font-weight:bold;margin:0 0 12px;">Make the week count</p>
                <ul style="color:#9CA3AF;font-size:13px;line-height:1.7;margin:0;padding-left:20px;">
                    <li>Share the link — Instagram stories, TikTok, group chats. This is your week.</li>
                    <li>Watch stock — restock in real time before your bestsellers sell out.</li>
                    <li>Reply fast — buyers messaging you now are hot leads.</li>
                    <li>Check analytics in your dashboard to see what's converting.</li>
                </ul>
            </div>
            <p style="color:#9CA3AF;line-height:1.6;margin:0 0 8px;">
                <a href="{dashboard_url}" style="color:#39FF14;text-decoration:none;font-weight:bold;">Open your dashboard →</a>
            </p>
            <hr style="border:1px solid #27272A;margin:24px 0;">
            <p style="color:#9CA3AF;font-size:12px;">Unveiled Threads — UK's marketplace for independent streetwear</p>
        </div>
    """
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [recipient_email],
            "subject": "You're Unveiled Threads' Brand of the Week — go tell everyone",
            "html": html_content,
        })
        logger.info(f"[BOTW PROMOTED EMAIL SENT] To: {recipient_email} | brand={brand_name}")
    except Exception as e:
        logger.warning(f"[BOTW PROMOTED EMAIL FAILED] To: {recipient_email} | Error: {e}")


async def _load_brand_by_id(brand_id: str) -> Optional[dict]:
    try:
        return await db.brands.find_one({"_id": ObjectId(brand_id)})
    except Exception:
        return None


# ============ THE LOOP ============

async def _rotate(state: dict) -> dict:
    """Perform the actual rotation: demote current, promote next, log history,
    schedule the next cycle. Idempotent — call only when `now >= next_scheduled_at`."""
    now = datetime.now(_tz.utc)
    next_id = state.get("next_brand_id")

    # If nobody was queued (e.g. brand-new install), fall back to picking one
    # right now. Never leave the homepage without a BotW if any candidate exists.
    if not next_id:
        candidate = await _pick_next_brand(state.get("cycle_index", 0), state.get("current_brand_id"))
        if candidate:
            next_id = str(candidate["_id"])

    if not next_id:
        # No eligible brands at all — do nothing this cycle, retry next tick.
        logger.info("[BOTW] No eligible candidates at rotation time; deferring.")
        return state

    # Demote everyone else, promote the winner.
    await db.brands.update_many({"is_brand_of_week": True}, {"$set": {"is_brand_of_week": False}})
    await db.brands.update_one(
        {"_id": ObjectId(next_id)},
        {"$set": {
            "is_brand_of_week": True,
            "botw_last_featured_at": now,
        }, "$inc": {"botw_featured_count": 1}},
    )

    # Record history + schedule next cycle.
    history = list(state.get("history", []))
    if state.get("current_brand_id"):
        history.append({
            "brand_id": state["current_brand_id"],
            "started_at": state.get("current_started_at"),
            "ended_at": now,
        })
    history = history[-20:]  # keep last 20 rotations

    ends_at = now + timedelta(days=ROTATION_INTERVAL_DAYS)
    new_state = {
        "current_brand_id": next_id,
        "current_started_at": now,
        "next_brand_id": None,
        "next_queued_at": None,
        "next_scheduled_at": ends_at,
        "cycle_index": int(state.get("cycle_index", 0)) + 1,
        "history": history,
        "updated_at": now,
    }
    await db.botw_state.update_one({"_id": STATE_ID}, {"$set": new_state})
    logger.info(f"[BOTW] Rotated → brand={next_id}, cycle={new_state['cycle_index']}")

    # Notify the winning brand. Fire-and-forget — email hiccups must not
    # break the loop, so we swallow exceptions inside the helper.
    promoted = await _load_brand_by_id(next_id)
    if promoted:
        await send_botw_promoted_email(promoted, ends_at)

    return {"_id": STATE_ID, **new_state}


async def _queue_next_if_due(state: dict) -> dict:
    """If we're inside the veto window and no candidate is queued yet, pick
    one and notify admins. No-op otherwise."""
    now = datetime.now(_tz.utc)
    scheduled = state.get("next_scheduled_at")
    if not scheduled:
        return state
    # scheduled may come back from Mongo without tzinfo — normalise.
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=_tz.utc)

    if state.get("next_brand_id"):
        return state
    if now < scheduled - timedelta(hours=VETO_WINDOW_HOURS):
        return state

    candidate = await _pick_next_brand(state.get("cycle_index", 0), state.get("current_brand_id"))
    if not candidate:
        return state

    update = {
        "next_brand_id": str(candidate["_id"]),
        "next_queued_at": now,
        "updated_at": now,
    }
    await db.botw_state.update_one({"_id": STATE_ID}, {"$set": update})
    await _notify_admins_of_pick(candidate, scheduled)
    await send_botw_queued_email(candidate, scheduled)
    logger.info(f"[BOTW] Queued next → brand={candidate['_id']} at {now.isoformat()}")
    return {**state, **update}


async def botw_rotation_tick() -> dict:
    """One iteration of the loop. Exposed so an admin endpoint can force it
    (useful for testing without waiting an hour)."""
    state = await _get_state()

    now = datetime.now(_tz.utc)
    scheduled = state.get("next_scheduled_at")
    if scheduled and scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=_tz.utc)

    if scheduled and now >= scheduled:
        state = await _rotate(state)
    else:
        state = await _queue_next_if_due(state)
    return state


async def botw_rotation_loop():
    """Background task started at app boot. Ticks every hour."""
    await asyncio.sleep(30)  # let the app finish startup
    while True:
        try:
            await botw_rotation_tick()
        except Exception as e:
            logger.error(f"[BOTW] Loop error: {e}")
        await asyncio.sleep(LOOP_INTERVAL_SECONDS)


# ============ ADMIN ENDPOINTS ============

async def _state_with_brand_info(state: dict) -> dict:
    """Enrich a state doc with brand_name lookups for the admin UI."""
    ids = [b for b in [state.get("current_brand_id"), state.get("next_brand_id")] if b]
    name_by_id: dict = {}
    if ids:
        try:
            obj_ids = [ObjectId(x) for x in ids]
            async for b in db.brands.find({"_id": {"$in": obj_ids}}, {"brand_name": 1, "slug": 1}):
                name_by_id[str(b["_id"])] = {"brand_name": b.get("brand_name"), "slug": b.get("slug")}
        except Exception:
            pass
    out = {
        "current_brand_id": state.get("current_brand_id"),
        "current_brand": name_by_id.get(state.get("current_brand_id") or ""),
        "current_started_at": state.get("current_started_at"),
        "next_brand_id": state.get("next_brand_id"),
        "next_brand": name_by_id.get(state.get("next_brand_id") or ""),
        "next_queued_at": state.get("next_queued_at"),
        "next_scheduled_at": state.get("next_scheduled_at"),
        "cycle_index": state.get("cycle_index"),
        "will_be_performance_pick": (int(state.get("cycle_index", 0)) % CYCLE_PERFORMANCE_STEP) == (CYCLE_PERFORMANCE_STEP - 1),
        "veto_deadline": (
            state["next_scheduled_at"] if state.get("next_scheduled_at") else None
        ),
        "history": state.get("history", []),
    }
    return out


@api_router.get("/admin/botw/queue")
async def admin_botw_queue(request: Request):
    """Current + next-queued BotW, plus a list of eligible brands the admin
    can swap into next_brand_id."""
    await require_admin(request)
    state = await _get_state()
    enriched = await _state_with_brand_info(state)

    # List eligible brands the admin can veto TO. Skip the currently-featured
    # brand (same-brand veto makes no sense) but INCLUDE brands still inside
    # cooldown so admin can override the cooldown if needed.
    eligible: List[dict] = []
    async for b in db.brands.find({}, {"brand_name": 1, "logo_url": 1, "slug": 1, "botw_last_featured_at": 1, "is_brand_of_week": 1}):
        if b.get("is_brand_of_week"):
            continue
        eligible.append({
            "id": str(b["_id"]),
            "brand_name": b.get("brand_name"),
            "slug": b.get("slug"),
            "logo_url": b.get("logo_url"),
            "botw_last_featured_at": b.get("botw_last_featured_at"),
        })
    def _sort_key(x):
        lf = x.get("botw_last_featured_at")
        if lf is None:
            lf = datetime.min.replace(tzinfo=_tz.utc)
        elif lf.tzinfo is None:
            # Legacy docs may have naive datetimes; treat as UTC so the
            # sort doesn't crash on mixed tz-aware / tz-naive values.
            lf = lf.replace(tzinfo=_tz.utc)
        return (lf, x["brand_name"] or "")
    eligible.sort(key=_sort_key)
    enriched["eligible_brands"] = eligible
    return enriched


class BotwVeto(BaseModel):
    brand_id: str


@api_router.post("/admin/botw/veto")
async def admin_botw_veto(payload: BotwVeto, request: Request):
    """Replace the queued next-BotW with the admin's choice. Doesn't touch
    the current BotW or the schedule — only the pick that'll go live at
    the next rotation."""
    await require_admin(request)
    try:
        brand_oid = ObjectId(payload.brand_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid brand_id")
    brand = await db.brands.find_one({"_id": brand_oid})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Skip the notify if admin is re-vetoing to the same brand — no point
    # spamming their inbox twice.
    prev_state = await _get_state()
    same_pick = prev_state.get("next_brand_id") == str(brand["_id"])

    now = datetime.now(_tz.utc)
    await db.botw_state.update_one(
        {"_id": STATE_ID},
        {"$set": {"next_brand_id": str(brand["_id"]), "next_queued_at": now, "updated_at": now}},
        upsert=True,
    )

    if not same_pick:
        scheduled = prev_state.get("next_scheduled_at") or (now + timedelta(days=ROTATION_INTERVAL_DAYS))
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=_tz.utc)
        await send_botw_queued_email(brand, scheduled)

    return {"next_brand_id": str(brand["_id"]), "brand_name": brand.get("brand_name")}


@api_router.post("/admin/botw/skip")
async def admin_botw_skip_pick(request: Request):
    """Clear the queued next-BotW and immediately recompute a new candidate.
    Useful when the automated pick doesn't sit right and the admin wants
    the algorithm to try again."""
    await require_admin(request)
    state = await _get_state()
    now = datetime.now(_tz.utc)
    prev_next = state.get("next_brand_id")
    await db.botw_state.update_one(
        {"_id": STATE_ID},
        {"$set": {"next_brand_id": None, "next_queued_at": None, "updated_at": now}},
    )
    # Force a fresh pick right now (bypasses the veto-window gate so the
    # admin sees an immediate update in the UI).
    candidate = await _pick_next_brand(state.get("cycle_index", 0), state.get("current_brand_id"))
    if not candidate:
        return {"next_brand_id": None, "message": "No eligible candidates"}
    await db.botw_state.update_one(
        {"_id": STATE_ID},
        {"$set": {"next_brand_id": str(candidate["_id"]), "next_queued_at": now, "updated_at": now}},
    )
    # Email the newly-queued brand (unless it happens to be the exact same
    # brand that was already queued — we already emailed them).
    if str(candidate["_id"]) != prev_next:
        scheduled = state.get("next_scheduled_at") or (now + timedelta(days=ROTATION_INTERVAL_DAYS))
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=_tz.utc)
        await send_botw_queued_email(candidate, scheduled)
    return {"next_brand_id": str(candidate["_id"]), "brand_name": candidate.get("brand_name")}


@api_router.post("/admin/botw/rotate-now")
async def admin_botw_rotate_now(request: Request):
    """Force an immediate rotation. Kept for admin recovery + testing —
    does NOT change the weekly schedule beyond `now + interval`."""
    await require_admin(request)
    state = await _get_state()
    state = await _rotate(state)
    return await _state_with_brand_info(state)
