# Unveiled Threads - PRD

## Problem Statement
Full-featured UK streetwear marketplace for independent brands with social commerce features.

## Architecture
- Frontend: React + Tailwind + Shadcn UI (brutalist black/silver/neon green)
- Backend: FastAPI + MongoDB
- Payments: Stripe (boosts + purchases with 10% platform fee + shipping)
- Auth: JWT httpOnly cookies
- Storage: Emergent Object Storage
- Emails: Resend (mock fallback)

## Complete Feature List
- JWT auth (register, login, logout, refresh)
- Brand application → admin review/approval with email notifications
- Product CRUD with image upload + shipping cost per product
- Brand profiles with logo/banner upload
- Brand of the Week (admin-set)
- Boosted Brand promotions (Stripe checkout)
- Buyer purchase flow with 10% platform fee + flat shipping (Stripe)
- Order tracking + shipping timeline (Confirmed → Shipped → In Transit → Delivered)
- Shipping labels (printable mock labels)
- Reviews & Ratings (separate product + brand ratings per order)
- Buyer wishlist (heart icon + /wishlist page)
- Brand analytics dashboard (views, orders, revenue, charts)
- Referral system (unique codes, share on X/WhatsApp, £5 credit)
- In-app messaging (Vinted-style chat)
- Automated message surveillance (blocks phone, email, PayPal, URLs, WhatsApp mentions)
- Email notifications via Resend (mock fallback)
- Notification bell with unread count
- Search and filter, 8 clothing categories
