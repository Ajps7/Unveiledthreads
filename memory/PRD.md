# Unveiled Threads - PRD

## Problem Statement
UK streetwear marketplace called "Unveiled Threads" for small/medium independent brands. Full marketplace with auth, brand applications, product management, purchases with platform fee, analytics, wishlists, and email notifications.

## Architecture
- Frontend: React + Tailwind + Shadcn UI (brutalist black/silver/neon green)
- Backend: FastAPI + MongoDB
- Payments: Stripe (boosts + product purchases with 10% platform fee)
- Auth: JWT httpOnly cookies
- Storage: Emergent Object Storage (product images, brand logos/banners)
- Emails: Resend (falls back to mock when no API key)

## All Implemented Features
- JWT auth (register, login, logout, refresh)
- Brand application → admin review/approval with email notifications
- Product CRUD with image upload
- Brand profiles with logo/banner upload
- Brand of the Week (admin-set)
- Boosted Brand promotions (Stripe checkout)
- Buyer purchase flow with 10% platform fee (Stripe)
- Order tracking for buyers and brands
- Buyer wishlist (heart icon on cards, /wishlist page)
- Brand analytics dashboard (views, orders, revenue, charts, top products, conversion rate)
- Product view tracking
- Email notifications via Resend (mock fallback)
- In-app notification bell with unread count
- Search and filter
- 8 clothing categories

## Remaining Backlog
### P1
- [ ] Reviews and ratings
- [ ] Shipping/delivery tracking

### P2
- [ ] Social sharing
- [ ] Buyer messaging to brands
- [ ] Multiple wishlists
