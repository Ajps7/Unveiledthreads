# Unveiled Threads - PRD

## Problem Statement
Full-featured UK streetwear marketplace for independent/small-medium brands with social commerce, brand applications, boosted promotions, in-app messaging and shipping. Modern streetwear aesthetic (black / silver / neon green).

## Architecture
- Frontend: React + Tailwind + Shadcn UI (brutalist black/silver/neon green #39FF14)
- Backend: FastAPI + MongoDB (~2700 lines in server.py — candidate for refactor)
- Payments: Stripe (boosts + purchases with **4% platform fee** + shipping) — LIVE test keys set (sk_test_51TO33K...)
- Auth: JWT httpOnly cookies
- Storage: Emergent Object Storage
- Emails: Resend (LIVE)
- Shipping: **Brands handle their own shipping** (Vinted/Depop model). They print labels via Royal Mail / Hermes / etc on their own, then enter courier + tracking number into the app via "Mark as Shipped" form. Platform doesn't generate labels.

## Complete Feature List
- JWT auth (register, login, logout, refresh, 401 axios interceptor)
- Brand application → admin approval with Resend email notifications
- Product CRUD with image upload + per-product shipping cost
- Advanced product filters: size, colour, material, fit, gender, condition
- Brand profiles with logo/banner — **NO external links (Instagram/website removed)** to prevent off-app sales
- Brand of the Week (admin-set)
- Boosted Brand promotions (Stripe)
- Buyer purchase flow (4% platform fee + shipping) via Stripe
- Order tracking + Vinted-style shipping timeline
- Shipping labels (Shippo when key set, mock otherwise)
- Reviews & Ratings (product + brand)
- Wishlist
- Brand analytics dashboard
- Referrals — **currently hidden as "Coming Soon" placeholder** (user request)
- In-app messaging with strict automated content surveillance (emails / phones / URLs / PayPal / Venmo / WhatsApp blocked)
- Community feed + product comments
- Real-time notification polling (10s interval)
- Terms & Conditions page + acceptance checkboxes at registration/application
- 8+ clothing categories

## Changelog (recent)
- 2026-02: **Forgot-password / reset-password flow added**:
  - `POST /api/auth/forgot-password` (5/hour rate-limited) — accepts email, generates `secrets.token_urlsafe(48)` token, stores SHA-256 hash with 1-hour expiry in new `password_reset_tokens` collection. Always returns generic "If an account exists..." to prevent email enumeration. Sends branded HTML email via Resend with reset link.
  - `POST /api/auth/reset-password` (10/hour rate-limited) — consumes token + sets new bcrypt-hashed password, invalidates all other outstanding tokens for that user.
  - New pages: `/forgot-password` and `/reset-password?token=...`. "Forgot password?" link added to Login page. When register fails with "email already exists", the error block now shows "Sign in instead" + "Forgot password?" inline links.
  - Register error message softened from generic "Could not register account" to specific "An account with this email already exists" since we now offer a recovery path.
  - MongoDB TTL index on `password_reset_tokens.expires_at` auto-purges old tokens after 7 days.
  - **⚠️ Note**: Resend currently rejects sends to anyone other than `anthonygeorgiades2000@gmail.com` because no domain is verified. To go live, verify `unveiledthreads.co.uk` at https://resend.com/domains and update `SENDER_EMAIL` env var to e.g. `noreply@unveiledthreads.co.uk`. Until then password reset emails will fail to send for all users except the admin.
- 2026-02: **Production deployment fix** — `load_dotenv()` no longer overrides Kubernetes env vars + CORS now reads `CORS_ORIGINS` allowlist.
  1. **`load_dotenv()` no longer overrides Kubernetes env vars**. Previous `load_dotenv(override=True)` was forcing the local `.env` `MONGO_URL=mongodb://localhost:27017` over the production Atlas URL injected by Emergent → backend startup crashed with `ServerSelectionTimeoutError`. Now defaults to non-override behaviour: deployment env vars take precedence, `.env` only fills in vars the platform hasn't set.
  2. **CORS now respects `CORS_ORIGINS` env var properly**. Old code only read `FRONTEND_URL` and ignored `CORS_ORIGINS`. New logic: if `CORS_ORIGINS="*"`, uses `allow_origin_regex=".*"` (works with credentials), else exact origin allowlist from comma-separated env var.
  - **⚠️ ACTION REQUIRED IN EMERGENT DEPLOYMENT SETTINGS**: Ensure these env vars are set on the production deployment: `MONGO_URL` (Atlas), `DB_NAME`, `JWT_SECRET`, `STRIPE_API_KEY` (real live key), `STRIPE_WEBHOOK_SECRET`, `CORS_ORIGINS=https://unveiledthreads.co.uk`, `FRONTEND_URL=https://unveiledthreads.co.uk`, `EMERGENT_LLM_KEY`, `RESEND_API_KEY`, `SENDER_EMAIL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `PLATFORM_FEE_PERCENT=4`.
  - **⚠️ Side effect on preview**: In preview, the pod injects a placeholder `STRIPE_API_KEY=sk_test_emergent` which now wins over our `.env`. To test real Stripe in preview, set `STRIPE_API_KEY` via Emergent preview env settings (not `.env`).
- 2026-02: Hybrid auto-approval with risk scoring + auto Stripe Connect onboarding.
  - New `calculate_application_risk()` computes a 0-100 score from: protected brand-name terms (Supreme/Nike/etc → +50), counterfeit keywords in description (wholesale/1:1/Yupoo/etc → +40), throwaway email domains (+30), account age < 24h (+15), short description / short or digit-heavy brand name (+10 each).
  - Score < 20 (`AUTO_APPROVE_RISK_THRESHOLD`) → instant approval. Otherwise queued for admin.
  - New `_finalise_approval()` helper shared by auto-approval + manual admin approval. Auto-creates Stripe Express Connect account on approval, generates `AccountLink` onboarding URL, and emails it to the new brand owner via Resend so they can finish KYC with one click (no need to log back in).
  - Admin pending queue now sorted by risk score DESC. Each application shows a colour-coded badge (green/yellow/red) + a list of triggered risk flags. "Auto-approved" badge marks applications that bypassed manual review.
  - Brand application success page now branches: "You're approved — check your email for the Stripe setup link" vs "We'll review within 24h" depending on outcome.
- 2026-02: **Tracking links**: Buyer + brand order pages now show clickable "Track on Royal Mail / Evri / DPD..." links for known UK couriers. Lib at `/app/frontend/src/lib/courierTracking.js`.
- 2026-02: **Security hardening**: Stripe webhook signature verification, slowapi rate limiting on auth + checkout endpoints, generic error message on register to prevent email enumeration.
- 2026-02: **Stripe Connect Direct Charges** (seller-liable), Shippo removed, boost paused.
- 2026-02: Stripe live test keys configured (sk_test_... backend, pk_test_... frontend). E2E verified: boost checkout + product purchase checkout both create real `cs_test_...` sessions against Stripe, status polling returns correct unpaid/paid state.
- 2026-02: Fixed `emergentintegrations.get_checkout_status` Pydantic validation bug by bypassing the library for status polls and using direct Stripe SDK (`stripe.checkout.Session.retrieve` + `session.metadata.to_dict()`). Helper `get_stripe_session_status()` defined at top of server.py.
- 2026-02: Switched `load_dotenv()` to `load_dotenv(override=True)` so `.env` always wins over pod-inherited env vars (pod was silently overriding STRIPE_API_KEY with `sk_test_emergent`).
- 2026-02: Verified Referrals "Coming Soon" redirect page renders correctly
- 2026-02: **GDPR Compliance Pass 1** — added `/privacy` Privacy Policy page (UK GDPR/DPA 2018 compliant), `/account` settings page with self-service Data Export (Art. 20) and Account Deletion (Art. 17), and a strictly-necessary cookies banner. Backend: `GET /api/account/export` returns full JSON dump (excluding `_id`/`password_hash`), `POST /api/account/delete` requires password + "DELETE" confirmation, cascades across all collections, anonymises orders for HMRC retention.
- Earlier: Platform fee set to 4%; Instagram & website removed from brand profiles; admin credentials updated; T&Cs; community + advanced filters

## Roadmap
### P1 (next)
- (none queued — user dropped product colour variants)

### P2 (backlog)
- Stripe Connect Phase 3 (Payouts widget on Brand Dashboard)
- Stripe Connect Phase 4 (refunds with `reverse_transfer=True`)
- Push notifications (currently short-polling)
- Refactor `server.py` into modular routes (it's ~3500 lines)
- **GDPR Hardening Pass 2**: Admin 2FA (TOTP), field-level encryption for shipping addresses at rest, log redaction middleware, ICO registration reminder in admin panel, DPA template links for Stripe/Resend/Atlas.

## Credentials
See `/app/memory/test_credentials.md`.

## Critical Rules
- DO NOT re-add Instagram / website links to brand profiles (anti off-app sales policy)
- DO NOT bypass / weaken content moderation in messages & comments
- Platform fee is 4% (env `PLATFORM_FEE_PERCENT=4`)
- User language: English (UK spelling)
