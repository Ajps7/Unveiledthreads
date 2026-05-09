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
- Shipping: Shippo — **LIVE** (test key `shippo_test_0e34...`). Returns real rates from Hermes UK / DPD UK and generates real PDF labels. Falls back to mock label on any error.

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
- 2026-02: **Stripe Connect (Phases 1 + 2)** + **Boost feature paused as Coming Soon**.
  - Backend: New endpoints `/api/connect/onboard`, `/api/connect/status`, `/api/connect/dashboard-link`. Express-account creation with GB/individual defaults. `/api/orders/checkout` now uses **destination charges** with `application_fee_amount = 4% of product price` and `transfer_data.destination = brand.stripe_account_id`. Webhook handles `account.updated` to sync `stripe_charges_enabled`/`stripe_payouts_enabled`. Buyer purchase blocked with friendly 400 if seller hasn't completed onboarding.
  - Boost: `/api/boost/checkout` returns 503 "coming soon" message. Frontend boost section replaced with Lock-icon "Coming Soon" tile.
  - Frontend: Brand Dashboard shows Stripe Connect panel (yellow when not connected, green when connected) with "Connect with Stripe" CTA, "Resume Onboarding" if partial, requirements list, and "Open Stripe Dashboard" button when fully connected. ProductDetail shows "Coming soon to checkout" banner + disables Buy button when seller's `stripe_charges_enabled=false`. Products list response now includes `seller_payments_ready`.
  - **⚠️ ACTION REQUIRED FROM USER**: Stripe blocked the first onboarding attempt with `Please review the responsibilities of managing losses for connected accounts at https://dashboard.stripe.com/settings/connect/platform-profile`. This is a one-time platform setup the Unveiled Threads admin must complete on the Stripe Dashboard before any brand can connect. Backend returns this URL in the friendly error message.
- 2026-02: Shippo live integration (Hermes UK £2.71 verified)
- Earlier: 4% platform fee, Instagram/website removed, T&Cs, advanced filters, community feed
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
