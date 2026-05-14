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
- 2026-02: **Security hardening — critical fixes for public launch**:
  1. **Stripe webhook signature verification**: Replaced `Event.construct_from` (which accepted any payload) with `stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)`. Returns 400 on signature mismatch. Falls back to unsigned-with-warning mode when `STRIPE_WEBHOOK_SECRET` is empty (dev). Webhook handler now returns 500 on unexpected errors (was 200 — would silently drop real events) so Stripe retries. Webhook also now properly handles `checkout.session.completed` for direct charges.
  2. **Rate limiting via slowapi**: `/api/auth/login` 10/min, `/api/auth/register` 10/hour, `/api/auth/refresh` 30/min, `/api/connect/onboard` 10/min, `/api/orders/checkout` 20/min. Real client IP read from `X-Forwarded-For` (Kubernetes ingress proxy). Verified: 11th rapid login attempt → 429.
  3. **Email enumeration fixed**: `/api/auth/register` now returns generic "Could not register account" instead of exposing whether the email exists.
  - **⚠️ ACTION REQUIRED**: Before live launch, create a Stripe webhook at https://dashboard.stripe.com/webhooks pointing to `/api/webhook/stripe` (events: `account.updated`, `checkout.session.completed`, `payment_intent.succeeded`), copy the signing secret (`whsec_...`), and paste it into `STRIPE_WEBHOOK_SECRET` in `/app/backend/.env`. Without this, signature verification is bypassed (logged loudly).
- 2026-02: **Stripe Connect switched to Direct Charges** (seller-liable). Sellers process payments on their own connected accounts; platform takes 4% via `application_fee_amount`. Chargebacks land on the seller.
- 2026-02: **Shippo fully removed.** Vinted/Depop-style shipping. Brands ship via any carrier, enter tracking manually.
- 2026-02: **Stripe Connect (Phases 1 + 2)** + **Boost paused as Coming Soon**.
- 2026-02: Stripe live test keys configured (sk_test_... backend, pk_test_... frontend). E2E verified: boost checkout + product purchase checkout both create real `cs_test_...` sessions against Stripe, status polling returns correct unpaid/paid state.
- 2026-02: Fixed `emergentintegrations.get_checkout_status` Pydantic validation bug by bypassing the library for status polls and using direct Stripe SDK (`stripe.checkout.Session.retrieve` + `session.metadata.to_dict()`). Helper `get_stripe_session_status()` defined at top of server.py.
- 2026-02: Switched `load_dotenv()` to `load_dotenv(override=True)` so `.env` always wins over pod-inherited env vars (pod was silently overriding STRIPE_API_KEY with `sk_test_emergent`).
- 2026-02: Verified Referrals "Coming Soon" redirect page renders correctly
- Earlier: Platform fee set to 4%; Instagram & website removed from brand profiles; admin credentials updated; T&Cs; community + advanced filters

## Roadmap
### P1 (next)
- (none queued — user dropped product colour variants)

### P2 (backlog)
- Stripe Connect Phase 3 (Payouts widget on Brand Dashboard)
- Stripe Connect Phase 4 (refunds with `reverse_transfer=True`)
- Push notifications (currently short-polling)
- Refactor `server.py` into modular routes (it's ~3000 lines)

## Credentials
See `/app/memory/test_credentials.md`.

## Critical Rules
- DO NOT re-add Instagram / website links to brand profiles (anti off-app sales policy)
- DO NOT bypass / weaken content moderation in messages & comments
- Platform fee is 4% (env `PLATFORM_FEE_PERCENT=4`)
- User language: English (UK spelling)
