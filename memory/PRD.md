# Unveiled Threads - PRD

## Problem Statement
Build a UK streetwear marketplace called "Unveiled Threads" similar to Vinted/Depop, focusing on small/medium independent UK streetwear brands. Target new brand owners with a marketplace that promotes visibility. Includes brand of the week, boosted brand in-app purchase, all clothing categories, image uploads, buyer purchase flow with platform fee, and mock notifications.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI (brutalist streetwear aesthetic - black, silver, neon green #39FF14)
- **Backend**: FastAPI + MongoDB
- **Payments**: Stripe (emergentintegrations) for boosts + product purchases with 10% platform fee
- **Auth**: JWT with httpOnly cookies
- **Storage**: Emergent Object Storage for product images and brand profile images
- **Notifications**: Mock (stored in DB, logged to console)

## User Personas
1. **Buyer** - browses, discovers, and purchases from indie UK streetwear brands
2. **Brand Owner** - applies to sell, manages products with image uploads, boosts brand, views orders
3. **Admin** - reviews brand applications (triggers notifications), sets brand of the week, manages platform

## Core Requirements (All Implemented)
- JWT authentication (register, login, logout)
- Brand application form (website optional) → admin review & approval with notifications
- Product CRUD with image upload via object storage
- Brand profiles with logo/banner upload
- Brand of the Week section (admin-set)
- Boosted Brand promotions via Stripe checkout
- Buyer purchase flow with 10% platform fee via Stripe
- Order tracking for buyers and brands
- Mock email notifications on application status changes and new orders
- Clothing categories (Hoodies, T-Shirts, Jackets, Trousers, Shorts, Accessories, Footwear, Caps)
- Search and filter functionality

## What's Been Implemented (April 2026)
- Full backend API with all endpoints including image upload, purchase flow, notifications
- Homepage with hero, marquee, brand of week, boosted brands, categories, products
- Auth pages (login, register)
- Brand application form (website optional)
- Admin dashboard (stats, approve/reject with notifications, set brand of week)
- Brand dashboard (profile images upload, add/delete products with image upload, boost packages, orders)
- Products page with search/filter
- Product detail with size selection and buy now with platform fee
- Brand profile pages
- Stripe checkout for boosts + product purchases
- Order success page with payment polling
- My Orders page
- Seed data with fictional indie brands (Thread & Bone, Nocturne Studios, Concrete Poetry, Raw Stitch Co.)

## Prioritized Backlog
### P1
- [ ] Real email notifications (SendGrid/Resend)
- [ ] User favourites/wishlist
- [ ] Brand analytics dashboard

### P2
- [ ] Social sharing features
- [ ] Reviews and ratings
- [ ] Shipping/delivery tracking
- [ ] Buyer messaging to brands
