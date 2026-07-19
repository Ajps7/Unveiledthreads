# Unveiled Threads - PRD

## Problem Statement
Full-featured UK streetwear marketplace for independent/small-medium brands with social commerce, brand applications, boosted promotions, in-app messaging and shipping. Modern streetwear aesthetic (black / silver / neon green).

## Architecture
- Frontend: React + Tailwind + Shadcn UI (brutalist black/silver/neon green #39FF14)
- Backend: FastAPI + MongoDB (~2700 lines in server.py — candidate for refactor)
- Payments: Stripe (boosts + purchases with **Buyer Protection fee: 5% of subtotal + £0.49, capped £6.00/order** + shipping) — LIVE test keys set (sk_test_51TO33K...)
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
- Buyer purchase flow (Buyer Protection fee 5% + £0.49 capped £6 + shipping) via Stripe
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
- 2026-06: **Delivered email** — `send_order_delivered_email()` sends buyers a branded "your order has arrived — leave a review" email (LEAVE A REVIEW button → /orders) when a brand marks status `delivered` via `PUT /api/orders/{id}/shipping-status`. Once per order (`delivered_email_sent` flag, duplicate-guard verified); generic notification email suppressed for delivered status. Domain verification for Resend is a USER action (dashboard + DNS) — the API key is send-only restricted so it can't be checked programmatically. Once verified, set `SENDER_EMAIL=noreply@unveiledthreads.co.uk` in prod env + backend/.env.
- 2026-06: **Shipped email** — `send_order_shipped_email()` sends buyers a branded Resend email with tracking number + clickable "TRACK YOUR PARCEL" button when a brand marks an order shipped (`PUT /api/orders/{id}/ship`). Backend `COURIER_TRACKING_URLS` mirrors `frontend/src/lib/courierTracking.js` (Royal Mail / Evri / DPD / Yodel / UPS / FedEx). `create_notification()` gained a `send_email` flag — ship flow passes `send_email=False` so the buyer gets ONE branded email, not a duplicate generic one. Verified delivered to owner's gmail. Demo order is now in "shipped" state with tracking AB123456789GB.
- 2026-06: **Email receipts + payout history + low-stock digest** — (1) `send_order_receipt_email()` sends buyers a branded Resend receipt (Item / Buyer Protection / Shipping / Total) when an order settles as paid in `get_order_status`, guarded by `receipt_email_sent` flag. (2) `/api/connect/payouts` now returns a `history` list (last 20 payouts); BrandDashboard payouts widget renders a scrollable Payout History with status badges. (3) Weekly low-stock digest: `send_low_stock_digests()` (best sellers with stock ≤ LOW_STOCK_THRESHOLD and ≥1 sale in 30d, max 5 items, per-brand 7-day guard via `brands.low_stock_digest_sent_at`), runs from a startup `low_stock_digest_loop()` every 6h; admin manual trigger `POST /api/admin/low-stock-digest/run` returns a send report. Both email types verified delivered to the owner's gmail in dev.
- 2026-06: **Fee line everywhere + Payouts widget** — `GET /api/orders/status/{session_id}` now returns an `order` receipt object (price / platform_fee / shipping / total); OrderSuccess page shows a full receipt card; MyOrders expanded view shows a Receipt breakdown with a "Buyer Protection" line. New `GET /api/connect/payouts` (Stripe Balance + Account schedule + Payout list on the connected account) powers a Payouts widget on BrandDashboard (Available / Pending / Next payout / Last payout); returns `{connected:false}` gracefully and the widget hides when the brand has no Stripe account. A seeded paid demo order (`session_id=cs_test_receipt_demo_123`, buyer demo@threadandbone.uk, £65 + £3.74 BP + £4.99 ship = £73.73) remains in the dev DB for receipt testing.
- 2026-06: **Buyer fee restructure** — flat 4% replaced by "Buyer Protection" fee: `min(subtotal*0.05 + 0.49, 6.00)` paid by buyer, once per order, on item subtotal only (not shipping). Sellers unchanged (receive 100% of price + shipping). `calculate_buyer_fee()` in server.py; frontend shared config `/app/frontend/src/lib/fees.js`. Stripe checkout now shows 3 line items (product / Buyer Protection / shipping); `application_fee_amount` uses new fee in pence. Copy updated: ProductDetail (with info tooltip), AddProduct "Buyer sees" preview, BrandDashboard, Terms §6.1/6.2/liability cap, BuyerProtection page. Note: orders are single-item, so "once per order" is trivially true; if a multi-item basket is ever added, fee must be computed once on combined subtotal.
- Earlier: Instagram & website removed from brand profiles; admin credentials updated; T&Cs; community + advanced filters

## Roadmap
### P1 (next)
- (none queued — user dropped product colour variants)

### P2 (backlog)
- Push notifications (currently short-polling)
- Refactor `server.py` into modular routes (it's ~3500 lines)
- **GDPR Hardening Pass 2**: Admin 2FA (TOTP), field-level encryption for shipping addresses at rest, log redaction middleware, ICO registration reminder in admin panel, DPA template links for Stripe/Resend/Atlas.

## Credentials
See `/app/memory/test_credentials.md`.

## Critical Rules
- DO NOT re-add Instagram / website links to brand profiles (anti off-app sales policy)
- DO NOT bypass / weaken content moderation in messages & comments
- Buyer fee is "Buyer Protection": min(subtotal×0.05 + £0.49, £6.00), buyer-paid, sellers keep 100% of price + shipping (env overrides: PLATFORM_FEE_RATE / PLATFORM_FEE_FIXED / PLATFORM_FEE_CAP)
- User language: English (UK spelling)
errides: PLATFORM_FEE_RATE / PLATFORM_FEE_FIXED / PLATFORM_FEE_CAP)
- User language: English (UK spelling)
