# Unveiled Threads - PRD

## Problem Statement
Full-featured UK streetwear marketplace for independent brands with social commerce, messaging, and shipping.

## Architecture
- Frontend: React + Tailwind + Shadcn UI (brutalist black/silver/neon green #39FF14)
- Backend: FastAPI + MongoDB
- Payments: Stripe (boosts + purchases with 10% platform fee + shipping)
- Auth: JWT httpOnly cookies
- Storage: Emergent Object Storage
- Emails: Resend (LIVE with key re_UoJXHjws...)
- Shipping: Shippo (ready — add SHIPPO_API_KEY to activate, falls back to mock labels)

## Complete Feature List
- JWT auth (register, login, logout, refresh)
- Brand application → admin approval with real email notifications (Resend)
- Product CRUD with image upload + shipping cost per product
- Brand profiles with logo/banner upload
- Brand of the Week (admin-set)
- Boosted Brand promotions (Stripe)
- Buyer purchase flow with 10% platform fee + flat shipping (Stripe)
- Order tracking + Vinted-style shipping timeline
- Shipping labels (Shippo real labels when key set, mock printable labels otherwise)
- Reviews & Ratings (separate product + brand ratings)
- Buyer wishlist (heart icon + /wishlist page)
- Brand analytics dashboard (views, orders, revenue, charts)
- Referral system (unique codes, share X/WhatsApp, £5 credit)
- In-app messaging with automated content surveillance
- Real-time notification polling (10s interval)
- Notification bell + message badge in header
- Search, filter, 8 clothing categories
