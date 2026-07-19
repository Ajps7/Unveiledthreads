# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ AUTH ROUTES ============

@api_router.post("/auth/register")
@limiter.limit("10/hour")
async def register(user_data: UserCreate, request: Request, response: Response):
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
                <p style="color:#9CA3AF;line-height:1.6;">We received a request to reset the password for the account linked to <strong style="color:#fff;">{email}</strong>. Click the button below to set a new password. This link expires in 1 hour.</p>
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
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
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


