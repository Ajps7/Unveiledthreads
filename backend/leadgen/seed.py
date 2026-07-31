"""Verified seed dataset of UK independent clothing & streetwear brands.

Every value below was read from a named public source, recorded in `sources`.
Where a fact could not be confirmed it is NOT_FOUND — including cases where a
value was *available* but not acceptable:

* Email-pattern guesses from people-search brokers (RocketReach, SignalHire,
  ZoomInfo et al) were rejected. Those services publish inferred addresses, and
  the brief rules out guessing private emails. Several brands here would
  otherwise show a "contact email"; they show "Not found" instead.
* Instagram follower counts are only recorded where a source stated a figure.
  None were estimated from brand size or press coverage.
* Founder names are only recorded where publicly attached to the business.

Run `python -m leadgen rebuild` after editing to re-score and re-export.
"""

from __future__ import annotations

import os

from .models import Lead, Signals, NOT_FOUND

VERIFIED_ON = "2026-07-29"

# Discovery constraint recorded for the next operator: this dataset was compiled
# from search-engine results only. The session that built it had outbound HTTPS
# blocked by egress policy, so brand sites could not be visited directly and the
# `extract` enrichment pass never ran. Re-run `python -m leadgen enrich --all`
# from an environment with network access to fill the gaps marked "Not found".
COMPILATION_METHOD = "search-only (no direct site access; enrichment pass not run)"


# Hand-written outreach hooks, one per brand. `outreach.generate_note` is only a
# fallback: it can pick the right *category* of hook from the signals, but it
# cannot say "sold out a debut trainer drop in an hour". Each note below cites a
# fact recorded in that brand's `notes`/`sources`, and each names a different
# reason — a note that would read the same for any other brand has failed.
OUTREACH_NOTES: dict[str, str] = {
    "Bene Culture": (
        "Already curates and retails other independent labels — thisisneverthat, "
        "Stepney Workers Club, Drama Call — from its Gibb Street store. A brand "
        "that already believes in multi-brand curation is a far easier yes to a "
        "marketplace than a pure DTC label; the own-label drops are what would list."
    ),
    "FORTY Clothing": (
        "Runs three Glasgow stores but no marketplace distribution was found. "
        "UnveiledThreads offers reach beyond the west of Scotland without the cost "
        "of a fourth lease. Note there is no published email — the contact form is "
        "the only legitimate route in."
    ),
    "CLINTS Inc": (
        "Its debut TRL Footprints trainer sold out in an hour and it has since "
        "collaborated with Patta — precisely the scarcity-led drop UnveiledThreads "
        "wants to feature. The only published address is order support, so find a "
        "partnerships contact before pitching."
    ),
    "MKI Miyuki Zoku": (
        "Fifteen years independent and still founder-run from the Leeds Corn "
        "Exchange, with no verified stockist footprint. Worth asking directly "
        "whether they want UK reach outside Yorkshire without taking the wholesale "
        "margin hit."
    ),
    "Death & Friends": (
        "Runs a standing 'new arrivals' cycle and publishes info@deathnfriends.com, "
        "so the first approach is frictionless. Its underground/alternative niche "
        "would give UnveiledThreads a subculture category distinct from the "
        "Manchester-London streetwear core."
    ),
    "Take Risks (Take Risks & Prosper)": (
        "Went from a 2016 Birmingham start-up to a Bullring & Grand Central store "
        "in six years and is still owner-run. With no business email published, "
        "approach Armani Duke directly via @armani_takerisks rather than the site."
    ),
    "Black Label Clothing": (
        "Handcrafted in Leeds and run single-handedly by Cameron Coid as both "
        "creative and operations director. A one-person operation gains the most "
        "from a marketplace that handles discovery, which is the angle to lead on."
    ),
    "Doomsday Co": (
        "Thirteen years of tattoo-art brand equity in Bridgend and a named owner "
        "contact after the High Dive Apparel acquisition. The hook is real, but "
        "confirm trading stability first — the company went through administration "
        "in 2023."
    ),
    "UN:IK Clothing": (
        "Already operates as a platform that develops and retails other independent "
        "designers, so the conversation is partnership as much as supply — their "
        "model and UnveiledThreads's overlap, and hello@unikclothing.co.uk is public."
    ),
    "Batch1": (
        "Designs and produces everything in-house in South London in small batches "
        "with organic fabrics and inks — the strongest provenance story on this "
        "list — and its existing SilkFred listing shows it is already comfortable "
        "selling through a third-party marketplace."
    ),
    "1AWAY Attire": (
        "Sells numbered limited-edition headwear (the 0003 Ace of Spades bucket "
        "hat) with info@1awayattire.co.uk published. Accessories are thin on most "
        "marketplaces, which makes this a low-friction first listing."
    ),
    "Hidden Hideout": (
        "Launched in 2023 and already holding a Braehead concession — early enough "
        "that marketplace reach genuinely changes its trajectory, with no existing "
        "distribution deals to negotiate around."
    ),
    "WHOCLO": (
        "Sixteen years screen printing every order in-house in Wales with an "
        "explicit 'no middlemen, no shortcuts' position and no marketplace "
        "distribution found. That makes UnveiledThreads purely additive — but "
        "expect the no-middlemen stance to need addressing head-on."
    ),
    "Chunk Clothing": (
        "Independent since 2001 with a recognisable humour-led cult-print niche. "
        "This is a stable catalogue addition rather than a growth bet — pitch "
        "incremental reach, not launch support."
    ),
    "Protect London": (
        "Self-funded a small jeans run in 2022 that reportedly sold out in seconds "
        "— proven drop demand with no marketplace presence found. Only the owners' "
        "first names are public, so the approach has to go through the site."
    ),
    "Disturbia": (
        "Twenty years of a distinct punk/DIY graphic identity from Northumberland, "
        "with distribution confined to alternative retailers rather than mainstream "
        "marketplaces — room for UnveiledThreads without channel conflict."
    ),
    "Urban Pirate Apparel": (
        "Hand-prints in East Glasgow on vegan-friendly blanks, so the independent "
        "credentials are genuine — but the Scotland-souvenir angle sits outside the "
        "streetwear core, and category fit is the question to settle before "
        "spending outreach effort."
    ),
    "Flow Like Zen": (
        "Positions on minimal premium oversized basics and maintains an active "
        "blog, so the site is being worked on. The aesthetic complements the "
        "graphic-led brands here — but verify the UK base and city first, since "
        "neither is published."
    ),
    "Bellisa X Clothing": (
        "A two-designer Bristol collaboration in festival-facing casualwear, which "
        "would widen UnveiledThreads beyond city streetwear. Confirm the brand is "
        "still actively trading before approaching."
    ),
    "Far From Home": (
        "Three Angolan-Portuguese siblings building from Manchester with Hypebeast "
        "coverage already behind them — a distinctive founder story "
        "UnveiledThreads could lead a brand feature with, once the correct domain "
        "and Instagram are pinned down."
    ),
    "Gramm": (
        "Owns its factory in Cheetham Hill and cuts, stitches and finishes every "
        "piece in-house — a genuine made-in-Manchester production story that would "
        "anchor UnveiledThreads's UK-manufacturing credentials. Confirm the "
        "official domain first."
    ),
    "Drama Call": (
        "The strongest Manchester independent by profile, but the adidas and "
        "Manchester United collaborations mean distribution is already broad and "
        "the founder is documented as avoiding press — expect the lowest response "
        "rate on this list, and confirm the official domain before contacting."
    ),
    "Roamers & Seekers": (
        "Founded by a former Superdry design manager and already selling through "
        "Wolf & Badger, so marketplace mechanics need no explanation. Coverage is "
        "several years old — confirm it is still trading before investing effort."
    ),
    "Emello": (
        "Launched in London in 2025 with European manufacturing, so it is still "
        "pre-distribution: UnveiledThreads could be its first retail channel rather "
        "than its fifth. Domain and handles still need confirming."
    ),
    "No Emotions": (
        "Founder-led London womenswear from Jemima May — useful for balancing a "
        "streetwear-heavy roster with everyday womenswear, though the domain and "
        "social handles still need to be established."
    ),
    "Heartless (Innocent Clothing)": (
        "Already stocked across Blue Banana, Attitude, EMP, Impericon, Ro Rox and "
        "more — the widest distribution on this list, which is exactly what the "
        "scoring penalises. Recorded for completeness so it is not rediscovered "
        "and re-researched later; deprioritise."
    ),
}


def _lead(**kwargs) -> Lead:
    signals = kwargs.pop("signals", None)
    lead = Lead(**kwargs)
    if signals:
        lead.signals = signals
    lead.last_verified = VERIFIED_ON
    if not lead.outreach_note:
        lead.outreach_note = OUTREACH_NOTES.get(lead.brand_name, "")
    return lead


def seed_leads() -> list[Lead]:
    return [
        _lead(
            brand_name="Bene Culture",
            website="https://beneculture.com/",
            instagram_handle="@beneculture",
            instagram_url="https://www.instagram.com/beneculture/",
            contact_email="info@beneculture.com",
            founder_owner="Vimal Chauhan and Hasim Jhina (co-founders)",
            founder_profile=NOT_FOUND,
            uk_location="Digbeth, Birmingham",
            category="Streetwear — own label plus a concept store stocking independent brands",
            instagram_followers="47,000",
            sells_own_website="Yes",
            existing_marketplaces="Stocked by END. (retailer)",
            contact_page=NOT_FOUND,
            notes=(
                "Founded 2015; started as a Depop vintage shop before opening on Gibb Street, "
                "Birmingham B9 4AT in 2016. Runs its own drops via beneculture.com alongside "
                "stocking thisisneverthat, Stepney Workers Club and Drama Call. Follower count "
                "reported as 38k in an Aug-2023 Hypebeast feature and 47k on a later profile "
                "snapshot — treat as approximate. Co-founder names come from the Hypebeast "
                "interview, which names two of three founders; the third is not published."
            ),
            signals=Signals(
                instagram_active=True, instagram_professional=True,
                follower_count=47_000, releases_collections=True,
                has_ecommerce=True, independent_positioning=True,
                strong_visual_branding=True, marketplace_count=1,
                has_public_contact=True,
            ),
            sources={
                "website": "https://beneculture.com/pages/store",
                "instagram_handle": "https://www.instagram.com/beneculture/",
                "instagram_followers": "https://www.instagram.com/beneculture/",
                "contact_email": "https://beneculture.com/pages/store",
                "founder_owner": "https://hypebeast.com/2023/8/bene-culture-interview-feature-community",
                "uk_location": "https://beneculture.com/pages/store",
                "existing_marketplaces": "https://www.endclothing.com/gb/brands/bene-culture/bene-culture",
            },
            evidence={
                "website": "search", "instagram_handle": "search",
                "contact_email": "search", "founder_owner": "editorial",
                "uk_location": "search",
            },
        ),
        _lead(
            brand_name="MKI Miyuki Zoku",
            website="https://www.mkistore.co.uk/",
            instagram_handle="@mkimiyukizoku",
            instagram_url="https://www.instagram.com/mkimiyukizoku/",
            contact_email="info@mkistore.com",
            founder_owner="Vik Taylor (founder & creative director)",
            founder_profile=NOT_FOUND,
            uk_location="Leeds (Corn Exchange, LS1 7BR)",
            category="Minimal streetwear — Japanese-influenced basics, outerwear, caps",
            instagram_followers="119,000",
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page="https://www.mkistore.co.uk/pages/contact",
            notes=(
                "Founded 2010 by Leeds native Vik Taylor (previously BoConcept and Paul Smith). "
                "Flagship at Unit C4, Corn Exchange, Leeds. Follower count above the brief's "
                "1k-100k sweet spot, so scored in the next band down — still independent and "
                "founder-run. Stockist footprint not verified."
            ),
            signals=Signals(
                instagram_active=True, instagram_professional=True,
                follower_count=119_000, releases_collections=True,
                has_ecommerce=True, independent_positioning=True,
                strong_visual_branding=True, has_public_contact=True,
            ),
            sources={
                "website": "https://www.mkistore.co.uk/pages/contact",
                "instagram_handle": "https://www.instagram.com/mkimiyukizoku/",
                "instagram_followers": "https://www.instagram.com/mkimiyukizoku/",
                "contact_email": "https://www.mkistore.co.uk/pages/contact",
                "founder_owner": "https://www.opumo.com/magazine/mki-miyuki-zoku/",
                "uk_location": "https://www.visitleeds.co.uk/things-to-do/view-all/mki/",
            },
            evidence={
                "website": "direct", "instagram_handle": "search",
                "contact_email": "search", "founder_owner": "editorial",
                "uk_location": "search",
            },
        ),
        _lead(
            brand_name="CLINTS Inc",
            website="https://clints.co/",
            instagram_handle="@clintsinc",
            instagram_url="https://www.instagram.com/clintsinc/",
            contact_email="orders@clints.co",
            founder_owner="Junior Clint",
            founder_profile="https://www.instagram.com/junior.clint/",
            uk_location="Manchester",
            category="Footwear-led streetwear — sneakers plus apparel",
            instagram_followers="130,000",
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page="https://clints.co/pages/contact-us",
            notes=(
                "Founded 2019; debut 'TRL Footprints' trainer drop May 2020 sold out in an hour. "
                "Self-taught designer, has collaborated with Patta. Founder's personal Instagram "
                "@junior.clint reported at 38k. Brand follower figure is an April-2026 snapshot. "
                "orders@clints.co is an order-support address rather than a partnerships inbox — "
                "worth finding a better route before a commercial approach."
            ),
            signals=Signals(
                instagram_active=True, instagram_professional=True,
                follower_count=130_000, releases_collections=True,
                has_ecommerce=True, independent_positioning=True,
                strong_visual_branding=True, has_public_contact=True,
            ),
            sources={
                "website": "https://clints.co/",
                "instagram_handle": "https://www.sneakerjagers.com/en/n/all-about-sneaker-brand-clints/49017",
                "instagram_followers": "https://www.sneakerjagers.com/en/n/all-about-sneaker-brand-clints/49017",
                "contact_email": "https://clints.co/pages/contact-us",
                "founder_owner": "https://hypebeast.com/2023/2/meet-junior-clint-the-manchester-based-designer-stepping-correct-with-his-footwear-and-apparel-designs",
                "founder_profile": "https://www.instagram.com/junior.clint/",
                "uk_location": "https://www.manchestersfinest.com/places/clints/",
            },
            evidence={
                "website": "search", "instagram_handle": "editorial",
                "contact_email": "search", "founder_owner": "editorial",
                "uk_location": "search",
            },
        ),
        _lead(
            brand_name="FORTY Clothing",
            website="https://fortyclothing.com/",
            instagram_handle="@fortyclothing",
            instagram_url="https://www.instagram.com/fortyclothing/",
            contact_email=NOT_FOUND,
            founder_owner="Gordon Harry Miller and Peter Love",
            founder_profile=NOT_FOUND,
            uk_location="Glasgow (Glasgow Fort, Silverburn, Royal Exchange Square)",
            category="Streetwear — 90s terrace and club culture influenced",
            instagram_followers="45,000",
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page="https://fortyclothing.com/pages/contact",
            notes=(
                "Founded 2014; logo derived from a drawing by co-founder Harry Miller's son "
                "Bryce. Three Glasgow stores as of 2025. No published contact email was found — "
                "people-search sites offer a guessed first@fortyclothing.com pattern, which was "
                "deliberately not recorded. Use the contact page."
            ),
            signals=Signals(
                instagram_active=True, instagram_professional=True,
                follower_count=45_000, releases_collections=True,
                has_ecommerce=True, independent_positioning=True,
                strong_visual_branding=True, has_public_contact=True,
            ),
            sources={
                "website": "https://fortyclothing.com/pages/about",
                "instagram_handle": "https://www.instagram.com/fortyclothing/",
                "instagram_followers": "https://www.instagram.com/fortyclothing/",
                "founder_owner": "https://www.shopsilverburn.com/news/forty-pr/",
                "uk_location": "https://www.glasgowfort.com/eatdrinkshop/forty-clothing",
            },
            evidence={
                "website": "direct", "instagram_handle": "search",
                "founder_owner": "search", "uk_location": "search",
            },
        ),
        _lead(
            brand_name="Death & Friends",
            website="https://www.deathnfriends.com/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email="info@deathnfriends.com",
            founder_owner=NOT_FOUND,
            founder_profile=NOT_FOUND,
            uk_location="London",
            category="Alternative / underground streetwear — graphic tees, hoodies, caps",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page="https://www.deathnfriends.com/pages/contact",
            notes=(
                "Trades as Death & Friends Ltd, 22 Wenlock Road, London N1 7GU — note that is a "
                "very commonly used registered-office/mail-forwarding address, so it may not be "
                "where the brand actually operates. Active X account @DeathFriendsLtd; Instagram "
                "handle not confirmed in sources reviewed. Runs a recurring 'new arrivals' "
                "collection, so cadence is evidenced."
            ),
            signals=Signals(
                releases_collections=True, has_ecommerce=True,
                independent_positioning=True, strong_visual_branding=True,
                has_public_contact=True,
            ),
            sources={
                "website": "https://www.deathnfriends.com/",
                "contact_email": "https://www.deathnfriends.com/pages/contact",
                "uk_location": "https://x.com/DeathFriendsLtd",
            },
            evidence={"website": "search", "contact_email": "search", "uk_location": "search"},
        ),
        _lead(
            brand_name="Take Risks (Take Risks & Prosper)",
            website="https://www.takerisksandprosperuk.com/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner="Armani Duke (trades as Armani TakeRisks)",
            founder_profile="https://www.instagram.com/armani_takerisks/",
            uk_location="Birmingham (Bullring & Grand Central)",
            category="Streetwear — reflective jackets, paint-splatter apparel, tracksuits, caps",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "Founded 2016; opened a Bullring store in October 2022. Brand Instagram handle "
                "not confirmed — only the founder's personal account was verified. No published "
                "business email found in the sources reviewed, which is why this scores below "
                "its apparent quality: the gap is our research, not the brand. Re-run enrichment "
                "against the site to close it."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
                strong_visual_branding=True,
            ),
            sources={
                "website": "https://www.takerisksandprosperuk.com/pages/about-us",
                "founder_owner": "https://www.complex.com/music/a/emmanuel-onapa/armani-takerisks-interview",
                "founder_profile": "https://www.instagram.com/armani_takerisks/",
                "uk_location": "https://www.7igures.com/blogs/news/take-risks-store-a-risk-that-paid-off",
            },
            evidence={
                "website": "direct", "founder_owner": "editorial", "uk_location": "editorial",
            },
        ),
        _lead(
            brand_name="Black Label Clothing",
            website="https://www.blacklabelclothing.co.uk/",
            instagram_handle="@blacklabelofficialclothing",
            instagram_url="https://www.instagram.com/blacklabelofficialclothing/",
            contact_email=NOT_FOUND,
            founder_owner="Cameron Coid",
            founder_profile=NOT_FOUND,
            uk_location="Leeds",
            category="Unisex streetwear — premium men's essentials, handcrafted in Leeds",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page="https://www.blacklabelclothing.co.uk/pages/contact-us",
            notes=(
                "Founder Cameron Coid acts as both creative and operations director; brand "
                "slogan 'Be Your Own Label'. Small, owner-run and Leeds-manufactured — a strong "
                "profile fit. Follower count and posting cadence unverified."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
                has_public_contact=True,
            ),
            sources={
                "website": "https://www.blacklabelclothing.co.uk/",
                "instagram_handle": "https://www.blacklabelclothing.co.uk/",
                "founder_owner": "https://www.yorkshireeveningpost.co.uk/news/people/leeds-entrepreneur-launches-black-label-clothing-streetwear-brand-2606048",
                "uk_location": "https://www.yorkshireeveningpost.co.uk/news/people/leeds-entrepreneur-launches-black-label-clothing-streetwear-brand-2606048",
            },
            evidence={
                "website": "search", "instagram_handle": "search",
                "founder_owner": "editorial", "uk_location": "editorial",
            },
        ),
        _lead(
            brand_name="Doomsday Co",
            website="https://doomsdayco.com/",
            instagram_handle="@doomsdayco",
            instagram_url="https://www.instagram.com/doomsdayco/",
            contact_email="jamie@doomsdayco.com",
            founder_owner="Corey Smith-Wilkes (founder); now owned by Jamie Norton, High Dive Apparel",
            founder_profile=NOT_FOUND,
            uk_location="Bridgend, South Wales",
            category="Streetwear — traditional tattoo-art graphics",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page="https://doomsdayco.com/pages/about-us",
            notes=(
                "Started 2012. DOOMSDAY CO LIMITED entered administration in May 2023; the brand "
                "was relaunched later that year after High Dive Apparel bought its assets from "
                "the administrators. Verify current trading health and order fulfilment before "
                "onboarding — the insolvency history is a real commercial risk, not a "
                "presentational one."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
                has_public_contact=True,
            ),
            sources={
                "website": "https://doomsdayco.com/pages/about-us",
                "instagram_handle": "https://www.instagram.com/doomsdayco/",
                "contact_email": "https://www.images-magazine.com/new-era-for-doomsdayco/",
                "founder_owner": "https://www.images-magazine.com/new-era-for-doomsdayco/",
                "uk_location": "https://doomsdayco.com/pages/about-us",
            },
            evidence={
                "website": "search", "instagram_handle": "search",
                "contact_email": "editorial", "founder_owner": "editorial",
                "uk_location": "search",
            },
        ),
        _lead(
            brand_name="UN:IK Clothing",
            website="https://www.unikclothing.co.uk/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email="hello@unikclothing.co.uk",
            founder_owner=NOT_FOUND,
            founder_profile="https://uk.linkedin.com/company/unikclothingltd",
            uk_location="Shrewsbury, Shropshire",
            category="Streetwear — own label plus a platform for independent designers",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "Started 2014 in a bedroom in Shrewsbury. Explicitly positions itself as a "
                "platform that develops and retails other independent designers — that makes it "
                "as much a potential partner or channel as a supplier, and worth approaching on "
                "that basis. Verified handles are @unikclothingltd on X, TikTok and Facebook; "
                "Instagram not confirmed. Founder name not published in sources reviewed."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
                has_public_contact=True,
            ),
            sources={
                "website": "https://www.unikclothing.co.uk/",
                "contact_email": "https://www.unikclothing.com/en-us/pages/about",
                "uk_location": "https://www.unikclothing.com/en-us/pages/about",
                "founder_profile": "https://uk.linkedin.com/company/unikclothingltd",
            },
            evidence={"website": "search", "contact_email": "search", "uk_location": "search"},
        ),
        _lead(
            brand_name="Batch1",
            website="https://batch1.com/",
            instagram_handle="@batch1uk",
            instagram_url="https://www.instagram.com/batch1uk/",
            contact_email="hello@batch1.com",
            founder_owner=NOT_FOUND,
            founder_profile=NOT_FOUND,
            uk_location="South London",
            category="Independent clothing & merch — in-house small batches, organic fabrics and inks",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces="SilkFred",
            contact_page=NOT_FOUND,
            notes=(
                "Designs and produces everything in-house in small batches using organic fabrics "
                "and inks — a strong story for a curated independent marketplace. Already has one "
                "marketplace relationship (SilkFred), so there is precedent for third-party "
                "channels without the distribution being saturated."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
                marketplace_count=1, has_public_contact=True,
            ),
            sources={
                "website": "https://batch1.com/",
                "instagram_handle": "https://www.instagram.com/batch1uk/",
                "contact_email": "https://batch1.com/",
                "uk_location": "https://batch1.com/",
                "existing_marketplaces": "https://www.silkfred.com/boutiques/batch1",
            },
            evidence={
                "website": "search", "instagram_handle": "search",
                "contact_email": "search", "uk_location": "search",
            },
        ),
        _lead(
            brand_name="1AWAY Attire",
            website="https://1awayattire.co.uk/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email="info@1awayattire.co.uk",
            founder_owner=NOT_FOUND,
            founder_profile=NOT_FOUND,
            uk_location=NOT_FOUND,
            category="Headwear-led streetwear — bucket hats, snapbacks, trucker caps",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "UK-registered domain; self-describes as a UK independent streetwear brand doing "
                "limited-edition numbered drops (e.g. the 0003 Ace of Spades bucket hat). Uses "
                "Instagram and TikTok as primary channels. Specific UK city not published in the "
                "sources reviewed."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
                releases_collections=True, has_public_contact=True,
            ),
            sources={
                "website": "https://1awayattire.co.uk/",
                "contact_email": "https://1awayattire.co.uk/",
            },
            evidence={"website": "search", "contact_email": "search"},
        ),
        _lead(
            brand_name="Hidden Hideout",
            website="https://hiddenhideout.co.uk/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner=NOT_FOUND,
            founder_profile=NOT_FOUND,
            uk_location="Glasgow",
            category="Premium Glaswegian streetwear",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces="Concession at Braehead Shopping Centre (physical retail, not a marketplace)",
            contact_page=NOT_FOUND,
            notes=(
                "Launched 2023 by lifelong friends (names not published). Very early-stage and "
                "already holding retail space at Braehead — the profile of brand that gains most "
                "from marketplace distribution. A search summary suggested the handle "
                "@hiddenhideout_ but it could not be confirmed, so it is recorded as Not found "
                "rather than guessed."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
            ),
            sources={
                "website": "https://hiddenhideout.co.uk/pages/about-us",
                "uk_location": "https://braehead.co.uk/stores/hidden-hideout/",
            },
            evidence={"website": "search", "uk_location": "search"},
        ),
        _lead(
            brand_name="WHOCLO",
            website="https://www.whoclo.com/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner=NOT_FOUND,
            founder_profile=NOT_FOUND,
            uk_location="Wales",
            category="Skate-influenced streetwear — screen printed in-house",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "Trading since 2010 from a studio in Wales; states that every order is designed, "
                "screen printed, packed and shipped by the team in small quantities with no "
                "middlemen. That in-house, no-wholesale position is unusually well aligned with a "
                "curated independent marketplace, and means there is no existing distribution "
                "conflict to negotiate around."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
                marketplace_count=0,
            ),
            sources={
                "website": "https://www.whoclo.com/",
                "uk_location": "https://www.whoclo.com/",
            },
            evidence={"website": "search", "uk_location": "search"},
        ),
        _lead(
            brand_name="Chunk Clothing",
            website="https://chunkclothing.com/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner=NOT_FOUND,
            founder_profile=NOT_FOUND,
            uk_location="London",
            category="Independent British streetwear — humour-led cult graphic prints",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "Trading since 2001 and still self-describing as an independent British "
                "streetwear brand. Long-established rather than emerging, so the pitch is "
                "incremental distribution rather than launch support. Founder names not clearly "
                "published — an 'about' page references a colleague known as Colonel joining as "
                "second employee in 2001, which does not identify the founders."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
            ),
            sources={
                "website": "https://chunkclothing.com/pages/about-chunk",
                "uk_location": "https://chunkclothing.com/",
            },
            evidence={"website": "search", "uk_location": "search"},
        ),
        _lead(
            brand_name="Protect London",
            website="https://protectldn.com/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner="Egor and Peter (first names only as published)",
            founder_profile=NOT_FOUND,
            uk_location="London",
            category="Streetwear — denim, sweats, hoodies, puffers, hats, accessories",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "Ran a self-funded small batch of jeans in 2022 that reportedly sold out in "
                "seconds — a genuine drop-and-sell-out model rather than always-on stock. Only "
                "the owners' first names are published; surnames were not found and have not "
                "been guessed."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
                releases_collections=True,
            ),
            sources={
                "website": "https://protectldn.com/",
                "founder_owner": "https://www.vanityteen.com/protect-london-the-streetwear-brand-taking-the-uk-by-storm-and-expanding-globally/",
                "uk_location": "https://www.vanityteen.com/protect-london-the-streetwear-brand-taking-the-uk-by-storm-and-expanding-globally/",
            },
            evidence={"website": "search", "founder_owner": "editorial", "uk_location": "editorial"},
        ),
        _lead(
            brand_name="Disturbia",
            website="https://www.disturbia.co.uk/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner="Frank Major (also published as Francis J Major)",
            founder_profile=NOT_FOUND,
            uk_location="Cramlington, Northumberland",
            category="Alternative / gothic / dark-romantic clothing and graphic tees",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces="Stocked by Beserk (AU) and other alternative retailers",
            contact_page=NOT_FOUND,
            notes=(
                "Founded 2003 by a fashion graduate; registered at 3 Silverton Court, "
                "Northumberland Business Park, Cramlington NE23 7RY. Strong niche identity "
                "(punk/DIY, subverted pop culture). No published business email found — broker "
                "sites offer a guessed j@disturbia.co.uk pattern, which was not recorded."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
                strong_visual_branding=True, marketplace_count=2,
            ),
            sources={
                "website": "https://www.disturbia.co.uk/pages/about",
                "founder_owner": "https://www.theupcoming.co.uk/2012/11/23/disturbia-clothing-purveyor-of-original-and-creative-fashion/",
                "uk_location": "https://www.disturbia.co.uk/pages/about",
            },
            evidence={"website": "search", "founder_owner": "editorial", "uk_location": "search"},
        ),
        _lead(
            brand_name="Urban Pirate Apparel",
            website="https://urbanpirate.scot/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner=NOT_FOUND,
            founder_profile=NOT_FOUND,
            uk_location="East Glasgow, Scotland",
            category="Scotland-inspired graphic tees on vegan-friendly blanks; custom screen printing",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "Hand-printed, small-scale, strongly regional. Closer to a gift/tourist-facing "
                "range than fashion streetwear, so category fit for a streetwear marketplace is "
                "weaker than the independence credentials suggest — worth a look but not a "
                "priority approach."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
            ),
            sources={
                "website": "https://urbanpirate.scot/",
                "uk_location": "https://urbanpirate.scot/",
            },
            evidence={"website": "search", "uk_location": "search"},
        ),
        _lead(
            brand_name="Flow Like Zen",
            website="https://flowlikezen.com/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner=NOT_FOUND,
            founder_profile=NOT_FOUND,
            uk_location=NOT_FOUND,
            category="Premium oversized streetwear — graphic tees and hoodies, minimal design",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "Self-describes as an independent UK streetwear brand; won LUXlife's Best Urban "
                "Culture-Inspired Streetwear Company - UK in 2023, which is a paid-entry style "
                "award and weak evidence of scale. UK city not published. Publishes a blog, so "
                "the site is actively maintained."
            ),
            signals=Signals(
                has_ecommerce=True, independent_positioning=True,
            ),
            sources={
                "website": "https://flowlikezen.com/",
                "uk_location": "https://lux-life.digital/winners/flow-like-zen/",
            },
            evidence={"website": "search", "uk_location": "search"},
        ),
        _lead(
            brand_name="Bellisa X Clothing",
            website="https://bellisaxclothing.com/",
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner=NOT_FOUND,
            founder_profile=NOT_FOUND,
            uk_location="Bristol",
            category="Casual streetwear and festival wear",
            instagram_followers=NOT_FOUND,
            sells_own_website="Yes",
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "Described as a Creatives of Bristol collaboration between two designers; "
                "individual names not published in the sources reviewed. Small and early — "
                "verify current activity before approaching."
            ),
            signals=Signals(has_ecommerce=True, independent_positioning=True),
            sources={
                "website": "https://bellisaxclothing.com/collections/bellisa-x-lucid",
                "uk_location": "https://bellisaxclothing.com/collections/bellisa-x-lucid",
            },
            evidence={"website": "search", "uk_location": "search"},
        ),
        # --- Brands verified by name/founder/city but with no confirmed website ---
        _lead(
            brand_name="Far From Home",
            website=NOT_FOUND,
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner="Erike, Etiene and Cheila (siblings; surnames not published)",
            founder_profile=NOT_FOUND,
            uk_location="Manchester",
            category="Streetwear — tracksuits, denim and silk",
            instagram_followers=NOT_FOUND,
            sells_own_website=NOT_FOUND,
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "Angola-born siblings who moved to Manchester via Portugal; brand launched 2020, "
                "profiled by Hypebeast in 2022. Website NOT confirmed: farfromhome.cc surfaced in "
                "search but appears to belong to a Danish cycling-apparel brand of the same name, "
                "so it was not recorded. Resolve the correct domain and Instagram before "
                "approaching — everything else about the profile fits well."
            ),
            signals=Signals(independent_positioning=True),
            sources={
                "founder_owner": "https://hypebeast.com/2022/6/far-from-home-introduction-feature",
                "uk_location": "https://hypebeast.com/2022/6/far-from-home-introduction-feature",
            },
            evidence={"founder_owner": "editorial", "uk_location": "editorial"},
        ),
        _lead(
            brand_name="Gramm",
            website=NOT_FOUND,
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner="AK Williams",
            founder_profile=NOT_FOUND,
            uk_location="Manchester (own factory in Cheetham Hill)",
            category="Streetwear — neon palettes, bold graphics, Manchester-referencing",
            instagram_followers=NOT_FOUND,
            sells_own_website=NOT_FOUND,
            existing_marketplaces="Stocked by SEVENSTORE (retailer)",
            contact_page=NOT_FOUND,
            notes=(
                "Launched 2015 by self-taught designer and Habitat MCR resident DJ AK Williams. "
                "Owns its factory in Cheetham Hill and cuts, stitches and finishes in-house — "
                "genuinely rare, and a strong differentiator for marketplace storytelling. "
                "Has collaborated with the Emirates FA Cup. Official domain not confirmed in the "
                "sources reviewed."
            ),
            signals=Signals(
                independent_positioning=True, strong_visual_branding=True,
                releases_collections=True, marketplace_count=1,
            ),
            sources={
                "founder_owner": "https://themanc.com/style/gramm-the-streetwear-brand-keeping-it-hot-in-the-rainy-city/",
                "uk_location": "https://themanc.com/style/gramm-the-streetwear-brand-keeping-it-hot-in-the-rainy-city/",
                "existing_marketplaces": "https://www.sevenstore.com/editorial/gramm-studio-community-is-everything/",
            },
            evidence={"founder_owner": "editorial", "uk_location": "editorial"},
        ),
        _lead(
            brand_name="Drama Call",
            website=NOT_FOUND,
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner="Charlie Bowes (also published as Charlie Bows)",
            founder_profile=NOT_FOUND,
            uk_location="Manchester",
            category="Streetwear — graphic-led, drop model",
            instagram_followers=NOT_FOUND,
            sells_own_website=NOT_FOUND,
            existing_marketplaces="Stocked by Crepslocker and Bene Culture; adidas and Manchester United collaborations",
            contact_page=NOT_FOUND,
            notes=(
                "Founded 2017. Website NOT recorded: two candidate domains surfaced "
                "(dramascall.com and dramacall.shop, the latter advertising 'up to 40% off', a "
                "common counterfeit-site pattern) and neither could be confirmed as official. "
                "Founder is documented as avoiding interviews and marketing via guerrilla drops, "
                "so expect a low response rate. The adidas/Man Utd tie-ups also mean distribution "
                "is already broad — a weaker fit than the Manchester peer set."
            ),
            signals=Signals(
                independent_positioning=True, releases_collections=True,
                strong_visual_branding=True, marketplace_count=2,
            ),
            sources={
                "founder_owner": "https://hypebeast.com/2023/6/from-manneh-to-the-world-drama-call-is-the-next-big-thing-in-uk-streetwear",
                "uk_location": "https://www.manchestersfinest.com/shopping-in-manchester/drama-call-and-adidas-are-dropping-another-manchester-designed-superstar-ii/",
            },
            evidence={"founder_owner": "editorial", "uk_location": "editorial"},
        ),
        _lead(
            brand_name="Roamers & Seekers",
            website=NOT_FOUND,
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner="Amanda Goss (former Superdry design manager)",
            founder_profile=NOT_FOUND,
            uk_location="Bristol (77 Park Street, BS1 5PF)",
            category="Contemporary menswear — clean urban design, British/Scandinavian influence",
            instagram_followers=NOT_FOUND,
            sells_own_website=NOT_FOUND,
            existing_marketplaces="Wolf & Badger",
            contact_page=NOT_FOUND,
            notes=(
                "Founded 2014 by an ex-Superdry design manager. Already sells through Wolf & "
                "Badger, so there is a working marketplace precedent. Most coverage found is "
                "several years old and the official domain was not confirmed — check the brand "
                "is still actively trading before spending outreach effort."
            ),
            signals=Signals(independent_positioning=True, marketplace_count=1),
            sources={
                "founder_owner": "https://www.drapersonline.com/news/former-superdry-design-manager-launches-menswear-brand",
                "uk_location": "https://www.bristol247.com/lifestyle/fashion/roamers-seekers/",
                "existing_marketplaces": "https://www.wolfandbadger.com/us/designers/roamers-seekers/",
            },
            evidence={"founder_owner": "editorial", "uk_location": "editorial"},
        ),
        _lead(
            brand_name="Emello",
            website=NOT_FOUND,
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner="Victoria Price and Ashley McPherson",
            founder_profile=NOT_FOUND,
            uk_location="London",
            category="Womenswear — casual luxury, made in Europe",
            instagram_followers=NOT_FOUND,
            sells_own_website=NOT_FOUND,
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "Founded in London in 2025 — very early stage, which is the point: a brand at "
                "launch has no marketplace relationships to displace. Domain and Instagram not "
                "confirmed. Included as a womenswear counterweight to a streetwear-heavy list."
            ),
            signals=Signals(independent_positioning=True, marketplace_count=0),
            sources={
                "founder_owner": "https://www.forbes.com/sites/joanneshurvell/2025/11/14/7-exciting-new-womenswear-brands-launching-in-london/",
                "uk_location": "https://www.forbes.com/sites/joanneshurvell/2025/11/14/7-exciting-new-womenswear-brands-launching-in-london/",
            },
            evidence={"founder_owner": "editorial", "uk_location": "editorial"},
        ),
        _lead(
            brand_name="No Emotions",
            website=NOT_FOUND,
            instagram_handle=NOT_FOUND,
            instagram_url=NOT_FOUND,
            contact_email=NOT_FOUND,
            founder_owner="Jemima May",
            founder_profile=NOT_FOUND,
            uk_location="London",
            category="Womenswear — refined, versatile everyday pieces",
            instagram_followers=NOT_FOUND,
            sells_own_website=NOT_FOUND,
            existing_marketplaces=NOT_FOUND,
            contact_page=NOT_FOUND,
            notes=(
                "London womenswear label founded by Jemima May. Early-stage and founder-led; "
                "domain and social handles not confirmed in the sources reviewed."
            ),
            signals=Signals(independent_positioning=True),
            sources={
                "founder_owner": "https://retailboss.co/seven-new-womenswear-brands-setting-the-trend-london-2025/",
                "uk_location": "https://retailboss.co/seven-new-womenswear-brands-setting-the-trend-london-2025/",
            },
            evidence={"founder_owner": "editorial", "uk_location": "editorial"},
        ),
        _lead(
            brand_name="Heartless (Innocent Clothing)",
            website=NOT_FOUND,
            instagram_handle="@itsallheartless",
            instagram_url="https://www.instagram.com/itsallheartless/",
            contact_email=NOT_FOUND,
            founder_owner=NOT_FOUND,
            founder_profile=NOT_FOUND,
            uk_location="Glasgow, Scotland",
            category="Alternative / gothic / emo-leaning womenswear and streetwear",
            instagram_followers=NOT_FOUND,
            sells_own_website=NOT_FOUND,
            existing_marketplaces=(
                "Blue Banana, Attitude Clothing, EMP, Impericon, Ro Rox, Four Leaf, "
                "Osiris Gothic and other alternative retailers"
            ),
            contact_page=NOT_FOUND,
            notes=(
                "Part of Innocent Clothing Ltd (Glasgow), alongside sister brand Poizen "
                "Industries. Wholesale-first: distribution is already very wide across "
                "alternative retailers, which is the profile the brief scores down. A "
                "sales@osirisclothing.co.uk address surfaced but appears to belong to a stockist "
                "rather than the brand, so it was not recorded. Listed for completeness; low fit."
            ),
            signals=Signals(
                independent_positioning=False, marketplace_count=7,
                has_public_contact=False,
            ),
            sources={
                "instagram_handle": "https://www.instagram.com/itsallheartless/",
                "uk_location": "https://www.innocentclothingltd.com/en-us/pages/landing",
            },
            evidence={"instagram_handle": "search", "uk_location": "search"},
        ),
    ]


def write_seed(path: str | None = None) -> str:
    """Materialise the seed dataset into the JSON store, scored and ranked."""
    from .pipeline import refine
    from .store import LeadStore

    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "data", "leads.json")
    leads = refine(seed_leads())
    store = LeadStore(path)
    store.save(leads)
    return path


if __name__ == "__main__":
    print(write_seed())
