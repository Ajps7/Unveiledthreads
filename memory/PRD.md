# Unveiled Threads - PRD

## Problem Statement
Build a UK streetwear marketplace app called "Unveiled Threads" similar to Vinted/Depop, focusing on small/medium independent UK streetwear brands. The goal is to target new brand owners and introduce a marketplace that promotes visibility to independent/UK streetwear brands. Includes brand of the week, boosted brand in-app purchase, and all clothing categories.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI (brutalist streetwear aesthetic - black, silver, neon green #39FF14)
- **Backend**: FastAPI + MongoDB
- **Payments**: Stripe (emergentintegrations library) for boosted brand purchases
- **Auth**: JWT with httpOnly cookies

## User Personas
1. **Buyer** - browses and discovers independent UK streetwear brands
2. **Brand Owner** - applies to sell, manages products, can boost their brand for visibility
3. **Admin** - reviews brand applications, sets brand of the week, manages platform

## Core Requirements
- JWT authentication (register, login, logout)
- Brand application form → admin review & approval
- Product CRUD for approved brands
- Brand profiles with products
- Brand of the Week section (admin-set)
- Boosted Brand promotions via Stripe checkout
- Clothing categories (Hoodies, T-Shirts, Jackets, Trousers, Shorts, Accessories, Footwear, Caps)
- Search and filter functionality

## What's Been Implemented (April 2026)
- Full backend API with all endpoints
- Homepage with hero, marquee, brand of week, boosted brands, categories, products
- Auth pages (login, register) with JWT httpOnly cookies
- Brand application form
- Admin dashboard (stats, approve/reject applications, set brand of week)
- Brand dashboard (view profile, add/delete products, boost packages)
- Products page with search/filter
- Brand profile pages
- Stripe checkout for boost purchases
- Seed data with fictional indie brands (Thread & Bone, Nocturne Studios, Concrete Poetry, Raw Stitch Co.)

## Prioritized Backlog
### P0
- [x] Core marketplace functionality
- [x] Auth system
- [x] Brand application/approval flow
- [x] Brand of the Week

### P1
- [ ] Product image upload (object storage)
- [ ] Brand logo/banner upload
- [ ] Order/purchase flow (buyer can buy from brand)
- [ ] User favourites/wishlist

### P2
- [ ] Brand analytics dashboard
- [ ] Email notifications (application status, new followers)
- [ ] Social sharing features
- [ ] Reviews and ratings

## Next Tasks
- Add image upload functionality for products and brand profiles
- Build out buyer purchase flow
- Add wishlist/favourites feature
- Email notifications for application status changes
