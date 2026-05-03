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
- Shipping: Shippo (mock fallback active — add SHIPPO_API_KEY to go live)

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
- 2026-02: Stripe live test keys configured (sk_test_... backend, pk_test_... frontend)
- 2026-02: Verified Referrals "Coming Soon" redirect page renders correctly
- Earlier: Platform fee set to 4%; Instagram & website removed from brand profiles; admin credentials updated; T&Cs; community + advanced filters

## Roadmap
### P1 (next)
- Product colour variants (support multiple colours per product)

### P2 (backlog)
- Real Shippo API integration (awaiting user's Shippo API key)
- Push notifications (currently short-polling)
- Refactor `server.py` into modular routes (it's ~2700 lines)

## Credentials
See `/app/memory/test_credentials.md`.

## Critical Rules
- DO NOT re-add Instagram / website links to brand profiles (anti off-app sales policy)
- DO NOT bypass / weaken content moderation in messages & comments
- Platform fee is 4% (env `PLATFORM_FEE_PERCENT=4`)
- User language: English (UK spelling)
