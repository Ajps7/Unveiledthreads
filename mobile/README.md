# Unveiled Threads — mobile app

A React Native (Expo) buyer client for the existing Unveiled Threads
marketplace. It talks to the same FastAPI backend as the web frontend — no
business logic is duplicated, and no backend changes were needed to build it.

## What's in it

The complete buyer journey:

| Area | Screens | API routes used |
|---|---|---|
| Auth | Sign in, register, forgot password | `/api/auth/login`, `/register`, `/forgot-password`, `/me`, `/refresh`, `/logout` |
| Shop | Product grid with search, category and sort | `/api/products`, `/api/categories` |
| Product | Detail, size picker, price breakdown, wishlist, buy, message brand | `/api/products/{id}`, `/api/wishlist/*`, `/api/orders/checkout` |
| Brands | Directory, brand profile with their pieces | `/api/brands`, `/api/brands/{id}` |
| Community | Feed, compose, likes, replies | `/api/community/posts`, `/posts/{id}/like`, `/posts/{id}/comments` |
| Wishlist | Saved pieces grid | `/api/wishlist` |
| Orders | List, detail, shipping timeline, courier tracking, receipt | `/api/orders/my-orders`, `/api/orders/status/{session_id}` |
| Messages | Conversations, thread, composer, new threads | `/api/conversations`, `/api/messages/send` |
| Notifications | List, mark read, tab badges | `/api/notifications`, `/notifications/poll` |
| Account | Profile, change password, GDPR export/delete, sign out | `/api/auth/change-password`, `/api/account/*` |

Seller tooling (listings, payouts, dispute handling) and brand applications are
deliberately **not** here — they stay on the web dashboard.

### Navigation shape

Five tabs: **SHOP · FEED · SAVED · INBOX · YOU**. Orders sit under YOU rather
than in the tab bar, matching how Depop and Vinted place purchases; the
post-checkout alert deep-links straight there, so the path that matters is
still one tap. Brands live inside the Shop stack, reachable from the shop
header or by tapping a brand name on any product.

Unread counts come from `/api/notifications/poll` (one request for both
badges) every 45s while the app is foregrounded, pausing entirely when
backgrounded and refreshing on resume. The web app polls every 10s, which
would be wasteful on a phone. Push notifications remain the right long-term
answer and are already on the backlog in `memory/PRD.md`.

### Starting a conversation

Conversations are between *users*, but a product only carries `brand_id`, so
"Message this brand" resolves the brand first to get its owning `user_id`. A
brand-new thread has no id yet — `ConversationScreen` accepts
`conversationId: null`, and adopts the `conversation_id` off the first sent
message, which is how the backend reports the thread it created.

## Running it

```bash
cd mobile
npm install
npm start          # then press i / a, or scan with Expo Go
npm run typecheck  # tsc --noEmit
```

Point it at a backend by editing `extra.apiBaseUrl` in `app.json`, or per-run:

```bash
EXPO_PUBLIC_API_BASE_URL=https://your-backend.example npm start
```

## Auth in a native client — read this first

The backend issues **httpOnly** `access_token` / `refresh_token` cookies
(`backend/routes/auth.py`). React Native keeps a native cookie jar on both
platforms, so those cookies are attached automatically and the app stores no
credentials of its own. That is the desirable arrangement: an httpOnly cookie
cannot be read by JavaScript, so there is no token for a compromised bundle to
exfiltrate.

Two consequences worth knowing:

1. **The app cannot inspect its own session.** "Am I signed in?" is answered by
   calling `/api/auth/me` on boot, which is what `AuthContext` does. On a 401
   the client spends exactly one `/api/auth/refresh` before dropping to the
   sign-in screen (`src/api/client.ts`).

2. **Cookies are `Secure`, so they need HTTPS.** Against a plain
   `http://localhost` backend the app will authenticate once and then behave as
   though signed out, because the cookie is never stored. Use an HTTPS tunnel
   for local development.

If you ever want token auth instead, `get_current_user` in `backend/core.py`
already accepts `Authorization: Bearer <token>`. The blocker is on the other
side: `login` returns the token only as a cookie, never in the response body,
so there is nothing for the app to capture. That would need a small backend
change first — a native-client login response, or a dedicated token endpoint.
This app does not depend on it.

## Checkout

Stripe Checkout is a hosted page and must open in a real browser surface, not
an embedded WebView — card autofill and 3-D Secure depend on it. `useCheckout`
opens the session URL with `expo-web-browser`, and when the sheet closes it
**does not assume payment succeeded**. Dismissal tells us nothing, so the hook
polls `/api/orders/status/{session_id}`, which re-checks Stripe server-side and
settles the order. That endpoint is the only authority on whether money moved.

`origin_url` on the checkout call is the **web** origin, not a deep link: the
backend builds Stripe's success and cancel redirects from it and they need to
land on real pages.

## Keeping in sync with the backend

Three files intentionally duplicate backend logic and will drift if the backend
changes without them:

- `src/lib/fees.ts` — Buyer Protection, `min(subtotal × 5% + £0.49, £6.00)`.
  Must match `calculate_buyer_fee()` in `backend/core.py` and `calcBuyerFee()`
  in `frontend/src/lib/fees.js`. This is for display only; the server computes
  what is actually charged.
- `src/lib/courierTracking.ts` — courier → tracking URL. Must match
  `frontend/src/lib/courierTracking.js` and `COURIER_TRACKING_URLS` in the
  backend.
- The 8-character minimum in `RegisterScreen` and `ChangePasswordScreen`. Must
  match `validate_password()` in `backend/core.py`. Client-side length is a
  courtesy for instant feedback; the server rejects common passwords and
  over-72-byte passwords that the app does not check for.

`src/theme.ts` mirrors `design_guidelines.json` — treat that JSON as the source
of truth for colour and type.

## Design notes

Square corners, 1px borders, uppercase type, `#39FF14` on near-black. The web
app uses Clash Display and Satoshi; rather than ship font binaries this uses
platform faces and carries the character through weight, tracking and case. Tab
icons are text glyphs — one fewer dependency, and soft rounded icons would
fight the brutalist grid.

## Verified

- `npx tsc --noEmit` — clean.
- `npx expo export --platform ios` — bundles (2.17 MB).

**Not** verified: nothing has run against a live backend or on a device or
simulator. Every screen is written against the API contract as read from the
route handlers, but no request in this app has actually been executed. Treat
the first run against a real backend as the real test.
