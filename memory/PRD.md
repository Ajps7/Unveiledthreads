# Unveiled Threads - PRD

## Problem Statement
UK streetwear marketplace for small/medium independent brands. Full marketplace with auth, brand applications, product management, purchases with platform fee, reviews & ratings, shipping tracking, analytics, wishlists, and email notifications.

## Architecture
- Frontend: React + Tailwind + Shadcn UI (brutalist black/silver/neon green)
- Backend: FastAPI + MongoDB
- Payments: Stripe (boosts + product purchases with 10% platform fee + shipping)
- Auth: JWT httpOnly cookies
- Storage: Emergent Object Storage
- Emails: Resend (mock fallback)

## All Implemented Features
- JWT auth (register, login, logout, refresh)
- Brand application → admin review/approval with email notifications
- Product CRUD with image upload + shipping cost per product
- Brand profiles with logo/banner upload
- Brand of the Week (admin-set)
- Boosted Brand promotions (Stripe checkout)
- Buyer purchase flow with 10% platform fee + flat shipping cost (Stripe)
- Order tracking for buyers and brands
- **Reviews & Ratings**: Separate product rating (1-5) + brand rating (1-5) per order, averages displayed on product pages
- **Shipping/Delivery Tracking**: Vinted/Depop-style — brand marks shipped with tracking number + courier (Royal Mail, Evri, DPD, etc.), buyer sees status timeline (Confirmed → Shipped → In Transit → Out for Delivery → Delivered)
- Buyer wishlist (heart icon + /wishlist page)
- Brand analytics dashboard (views, orders, revenue, charts, top products)
- Product view tracking
- Email notifications via Resend (mock fallback)
- Notification bell with unread count
- Search and filter, 8 clothing categories

## Remaining Backlog
### P2
- [ ] Social sharing / referral system
- [ ] Buyer messaging to brands
- [ ] Multiple wishlists
