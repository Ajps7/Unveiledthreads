# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ AUTH ROUTES ============

@api_router.post("/auth/register")
@limiter.limit("10/hour")
async def register(user_data: UserCreate, request: Request, response: Response):
    # Validate the password BEFORE the duplicate-email lookup, so a weak
    # password fails identically whether the email exists or not (preserves
    # anti-enumeration behaviour).
    validate_password(user_data.password)

    email = user_data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists. Try logging in, or use forgot password if you don't remember it.",
        )
    
    hashed = hash_password(user_data.password)
    user_doc = {
        "email": email,
        "password_hash": hashed,
        "name": user_data.name,
        "role": "user",
        "created_at": datetime.now(timezone.utc)
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": email,
        "name": user_data.name,
        "role": "user",
        "created_at": user_doc["created_at"].isoformat()
    }

@api_router.post("/auth/login")
@limiter.limit("10/minute")
async def login(user_data: UserLogin, request: Request, response: Response):
    email = user_data.email.lower()
    user = await db.users.find_one({"email": email})
    
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "created_at": user["created_at"].isoformat() if isinstance(user["created_at"], datetime) else user["created_at"]
    }

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "created_at": user["created_at"].isoformat() if isinstance(user["created_at"], datetime) else user["created_at"]
    }

@api_router.post("/auth/refresh")
@limiter.limit("30/minute")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        user_id = str(user["_id"])
        access_token = create_access_token(user_id, user["email"])
        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="none", max_age=3600, path="/")
        
        return {"message": "Token refreshed"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# ============ PASSWORD RESET ============

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


def _hash_reset_token(raw_token: str) -> str:
    """SHA-256 the token before storage — we never persist the plaintext."""
    import hashlib
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@api_router.post("/auth/forgot-password")
@limiter.limit("5/hour")
async def forgot_password(payload: ForgotPasswordRequest, request: Request):
    """Send a password reset email if the account exists.
    Always returns the same generic response to prevent email enumeration."""
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    
    generic_response = {
        "message": "If an account exists for that email, a reset link is on the way."
    }
    
    if not user:
        return generic_response
    
    # Generate a single-use, 1-hour token
    import secrets
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_reset_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    await db.password_reset_tokens.insert_one({
        "user_id": str(user["_id"]),
        "token_hash": token_hash,
        "expires_at": expires_at,
        "used": False,
        "created_at": datetime.now(timezone.utc),
    })
    
    # Build reset URL — frontend reads ?token= from /reset-password
    frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
    reset_url = f"{frontend_url}/reset-password?token={raw_token}"
    
    # Send email via Resend
    if RESEND_API_KEY:
        try:
            html_content = f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
                <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;">UNVEILED THREADS</h1>
                <hr style="border:1px solid #27272A;margin:16px 0;">
                <h2 style="color:#fff;font-size:20px;">Reset your password</h2>
                <p style="color:#9CA3AF;line-height:1.6;">We received a request to reset the password for the account linked to <strong style="color:#fff;">{esc(email)}</strong>. Click the button below to set a new password. This link expires in 1 hour.</p>
                <p style="margin:32px 0;">
                    <a href="{reset_url}" style="display:inline-block;background:#39FF14;color:#000;padding:14px 28px;text-decoration:none;font-weight:bold;letter-spacing:1px;text-transform:uppercase;font-size:14px;">Reset Password</a>
                </p>
                <p style="color:#9CA3AF;font-size:12px;line-height:1.6;">If you didn't request this, you can safely ignore this email — your password won't be changed.</p>
                <p style="color:#9CA3AF;font-size:12px;line-height:1.6;word-break:break-all;">Or copy this link: {reset_url}</p>
                <hr style="border:1px solid #27272A;margin:24px 0;">
                <p style="color:#9CA3AF;font-size:12px;">Unveiled Threads — UK's marketplace for independent streetwear</p>
            </div>
            """
            params = {
                "from": SENDER_EMAIL,
                "to": [email],
                "subject": "Unveiled Threads — Reset your password",
                "html": html_content,
            }
            await asyncio.to_thread(resend.Emails.send, params)
            logger.info(f"[PASSWORD RESET] sent to {email}")
        except Exception as e:
            logger.error(f"Password reset email send failed: {e}")
    else:
        # Dev fallback: log link to console so we can still test without Resend
        logger.warning(f"[PASSWORD RESET — DEV] Token for {email}: {reset_url}")
    
    return generic_response


@api_router.post("/auth/reset-password")
@limiter.limit("10/hour")
async def reset_password(payload: ResetPasswordRequest, request: Request):
    """Consume a reset token and set the new password."""
    validate_password(payload.new_password)
    
    token_hash = _hash_reset_token(payload.token)
    token_doc = await db.password_reset_tokens.find_one({"token_hash": token_hash})
    
    if not token_doc:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has already been used.")
    if token_doc.get("used"):
        raise HTTPException(status_code=400, detail="This reset link has already been used. Request a new one.")
    
    expires_at = token_doc.get("expires_at")
    if isinstance(expires_at, datetime):
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="This reset link has expired. Request a new one.")
    
    # Update the user's password
    new_hash = hash_password(payload.new_password)
    await db.users.update_one(
        {"_id": ObjectId(token_doc["user_id"])},
        {"$set": {"password_hash": new_hash}},
    )
    
    # Mark this token used + invalidate any other outstanding tokens for the user
    await db.password_reset_tokens.update_many(
        {"user_id": token_doc["user_id"]},
        {"$set": {"used": True}},
    )
    
    return {"message": "Password updated. You can now log in with your new password."}


# ============ CHANGE PASSWORD (authenticated) ============

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@api_router.post("/auth/change-password")
@limiter.limit("5/hour")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
):
    """Let a logged-in user rotate their password without needing an email
    reset link. Verifies the current password, enforces the shared policy on
    the new one, and invalidates any outstanding reset tokens for the user."""
    user = await get_current_user(request)

    # Verify the current password first — 401 signals bad creds, not a policy fail.
    db_user = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not db_user or not verify_password(payload.current_password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    # New must differ from current.
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from your current one.",
        )

    # Apply the shared policy to the new password.
    validate_password(payload.new_password)

    new_hash = hash_password(payload.new_password)
    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {"password_hash": new_hash}},
    )

    # Invalidate any outstanding reset tokens — matches the reset flow's behaviour.
    await db.password_reset_tokens.delete_many({"user_id": user["id"]})

    return {"message": "Password updated successfully."}




# ============ CHANGE EMAIL ============
# Two-step flow, mirrors /auth/forgot-password + /auth/reset-password:
#   1) POST /auth/change-email/request  { new_email, current_password }
#      → re-authenticates, checks new_email is free, stores a hashed
#        single-use 1-hour token, mails the link to the NEW inbox, and
#        pings the OLD inbox as a security notice.
#   2) POST /auth/change-email/confirm  { token }
#      → validates + consumes the token, atomically flips the user's
#        email, deletes outstanding reset tokens so the account can't be
#        recovered to the old address, and invalidates the current session
#        cookie so a re-login is required (re-secures the account).

class ChangeEmailRequestPayload(BaseModel):
    new_email: EmailStr
    current_password: str


class ChangeEmailConfirmPayload(BaseModel):
    token: str


async def _send_change_email_verification(new_email: str, token_url: str):
    """Verification link to the NEW inbox — clicking confirms ownership."""
    if not RESEND_API_KEY:
        logger.warning(f"[CHANGE EMAIL — DEV] Verification link for {new_email}: {token_url}")
        return
    html_content = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
            <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;">UNVEILED THREADS</h1>
            <hr style="border:1px solid #27272A;margin:16px 0;">
            <h2 style="color:#fff;font-size:20px;">Confirm your new email</h2>
            <p style="color:#9CA3AF;line-height:1.6;">Confirm <strong style="color:#fff;">{esc(new_email)}</strong> as the address on your Unveiled Threads account. This link expires in 1 hour and can only be used once.</p>
            <p style="margin:32px 0;">
                <a href="{token_url}" style="display:inline-block;background:#39FF14;color:#000;padding:14px 28px;text-decoration:none;font-weight:bold;letter-spacing:1px;text-transform:uppercase;font-size:14px;">Confirm New Email</a>
            </p>
            <p style="color:#9CA3AF;font-size:12px;line-height:1.6;">If you didn't request this, you can safely ignore this email — nothing changes until you confirm.</p>
            <p style="color:#9CA3AF;font-size:12px;line-height:1.6;word-break:break-all;">Or copy this link: {token_url}</p>
        </div>
    """
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [new_email],
            "subject": "Unveiled Threads — Confirm your new email",
            "html": html_content,
        })
    except Exception as e:
        logger.warning(f"[CHANGE EMAIL] verification send failed for {new_email}: {e}")


async def _send_change_email_notice_to_old(old_email: str, new_email: str):
    """Security ping to the OLD inbox so account takeover is visible."""
    if not RESEND_API_KEY:
        logger.warning(f"[CHANGE EMAIL — DEV] Old-inbox notice: {old_email} → {new_email}")
        return
    html_content = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#050505;color:#F3F4F6;padding:40px;">
            <h1 style="color:#39FF14;font-size:24px;margin-bottom:8px;">UNVEILED THREADS</h1>
            <hr style="border:1px solid #27272A;margin:16px 0;">
            <h2 style="color:#fff;font-size:20px;">Email change requested</h2>
            <p style="color:#9CA3AF;line-height:1.6;">Someone (hopefully you) asked to move your Unveiled Threads account from <strong style="color:#fff;">{esc(old_email)}</strong> to <strong style="color:#fff;">{esc(new_email)}</strong>.</p>
            <p style="color:#9CA3AF;line-height:1.6;">The change only completes when the link sent to the new address is clicked. If that wasn't you, change your password immediately — this address is still on your account until confirmation.</p>
        </div>
    """
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [old_email],
            "subject": "Unveiled Threads — Email change requested on your account",
            "html": html_content,
        })
    except Exception as e:
        logger.warning(f"[CHANGE EMAIL] old-inbox notice failed for {old_email}: {e}")


@api_router.post("/auth/change-email/request")
@limiter.limit("5/hour")
async def request_change_email(payload: ChangeEmailRequestPayload, request: Request):
    user = await get_current_user(request)
    db_user = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not db_user or not verify_password(payload.current_password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    new_email = payload.new_email.lower()
    if new_email == db_user["email"].lower():
        raise HTTPException(status_code=400, detail="New email is the same as your current one.")

    existing = await db.users.find_one({"email": new_email, "_id": {"$ne": db_user["_id"]}})
    if existing:
        raise HTTPException(status_code=409, detail="That email is already in use on another account.")

    import secrets
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_reset_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    # Wipe any prior pending change-email token for this user — only one
    # in-flight request at a time.
    await db.email_change_tokens.delete_many({"user_id": user["id"]})
    await db.email_change_tokens.insert_one({
        "user_id": user["id"],
        "old_email": db_user["email"],
        "new_email": new_email,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "used": False,
        "created_at": datetime.now(timezone.utc),
    })

    frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
    verify_url = f"{frontend_url}/verify-email-change?token={raw_token}"

    await _send_change_email_verification(new_email, verify_url)
    await _send_change_email_notice_to_old(db_user["email"], new_email)

    return {"message": "Check your new inbox to confirm the change."}


@api_router.post("/auth/change-email/confirm")
@limiter.limit("10/hour")
async def confirm_change_email(payload: ChangeEmailConfirmPayload, request: Request, response: Response):
    token_hash = _hash_reset_token(payload.token)
    token_doc = await db.email_change_tokens.find_one({"token_hash": token_hash})
    now = datetime.now(timezone.utc)
    if not token_doc:
        raise HTTPException(status_code=400, detail="This link is invalid or has already been used.")
    if token_doc.get("used"):
        raise HTTPException(status_code=400, detail="This link has already been used.")
    expires = token_doc["expires_at"]
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        raise HTTPException(status_code=400, detail="This link has expired. Start the change from your account settings.")

    # Race-guard: someone else may have claimed the new email between
    # request and confirm. Refuse rather than allow duplicates.
    conflict = await db.users.find_one({
        "email": token_doc["new_email"],
        "_id": {"$ne": ObjectId(token_doc["user_id"])},
    })
    if conflict:
        await db.email_change_tokens.update_one({"_id": token_doc["_id"]}, {"$set": {"used": True}})
        raise HTTPException(status_code=409, detail="That email is now in use on another account.")

    # Flip the email + burn every other outstanding recovery token for
    # this user so the change fully re-secures the account.
    await db.users.update_one(
        {"_id": ObjectId(token_doc["user_id"])},
        {"$set": {"email": token_doc["new_email"], "email_changed_at": now}},
    )
    await db.email_change_tokens.update_one({"_id": token_doc["_id"]}, {"$set": {"used": True}})
    await db.password_reset_tokens.delete_many({"user_id": token_doc["user_id"]})

    # Invalidate the current session cookie — user must sign back in with
    # the new address, closing any active session created on the old email.
    response.delete_cookie(key="access_token", path="/")

    return {"message": "Email updated. Please sign in with your new email."}
