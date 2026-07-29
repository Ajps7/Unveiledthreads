"""Exclusion rules — what must never reach the prospect database.

The brief asks for small-to-medium independents. The two failure modes worth
guarding against are (a) listicle noise: the same six global brands appear in
every "UK streetwear" article, and (b) domain noise: search results are mostly
magazines, retailers and marketplaces rather than brands.
"""

from __future__ import annotations

from urllib.parse import urlparse

from .models import Lead, is_found

# Global / high-street / heavily-distributed names. Present in nearly every
# "UK streetwear" listicle and never a fit for an independent marketplace.
MAJOR_BRANDS: frozenset[str] = frozenset({
    "corteiz", "palace", "palace skateboards", "trapstar", "syna world",
    "represent", "represent clothing", "bench", "hoodrich", "stone island",
    "burberry", "barbour", "fred perry", "ben sherman", "lyle and scott",
    "superdry", "jack wills", "asos", "boohoo", "prettylittlething", "shein",
    "topshop", "topman", "river island", "next", "primark", "marks and spencer",
    "new look", "george at asda", "matalan", "jd sports", "sports direct",
    "the couture club", "gymshark", "castore", "montirex", "berghaus",
    "nike", "adidas", "supreme", "carhartt", "carhartt wip", "stussy",
    "the north face", "patagonia", "vans", "dickies", "santa cruz",
    "jaded london", "vollebak", "aries", "maharishi", "burberry prorsum",
    "alexander mcqueen", "jw anderson", "paul smith", "vivienne westwood",
    "mulberry", "reiss", "ted baker", "allsaints", "cos", "arket", "uniqlo",
    "urban outfitters", "end clothing", "end.", "size?", "footasylum",
})

# Hosts that are publishers, retailers, marketplaces or data brokers — useful as
# *sources*, never as brand candidates.
NON_BRAND_HOSTS: frozenset[str] = frozenset({
    # editorial
    "hypebeast.com", "highsnobiety.com", "complex.com", "gq-magazine.co.uk",
    "esquire.com", "vogue.co.uk", "dazeddigital.com", "i-d.co", "nssmag.com",
    "pausemag.co.uk", "whowhatwear.com", "stylist.co.uk", "service95.com",
    "fashionbeans.com", "opumo.com", "themanc.com", "manchestersfinest.com",
    "bristol247.com", "365bristol.com", "glasgowworld.com", "vice.com",
    "drapersonline.com", "insidermedia.com", "trendhunter.com", "guap.co",
    "vanityteen.com", "kerrang.com", "sneakerjagers.com", "newwavemagazine.com",
    "basementapproved.com", "system.social", "shiftlondon.org", "fizzymag.com",
    "undiscoveredmag.com", "oculate.uk", "images-magazine.com", "lux-life.digital",
    "yorkshireeveningpost.co.uk", "barrheadnews.com", "sportindustry.co.uk",
    "versus.uk.com", "bcu.ac.uk", "1granary.substack.com",
    "apetogentleman.com", "forbes.com", "hellomagazine.com", "confidentials.com",
    "bestblogabout.com", "retailboss.co", "huptechweb.com", "12lunes.com",
    "goodmakertales.com", "document-bristol.com", "theupcoming.co.uk",
    "independentlife.co.uk", "fox61.com", "trinidadexpress.com", "spotern.com",
    # official records, tourism and shopping-centre listings
    "gov.uk", "find-and-update.company-information.service.gov.uk",
    "thegazette.co.uk", "insolvencyintel.co.uk", "visitleeds.co.uk",
    "visitglasgow.com", "whatsonglasgow.co.uk", "glasgowfort.com",
    "shopsilverburn.com", "braehead.co.uk", "frasersplusbraehead.co.uk",
    # reference / generic / social profile hosts
    "wikipedia.org", "en.wikipedia.org", "reddit.com", "quora.com",
    "pinterest.com", "youtube.com", "medium.com", "substack.com",
    "facebook.com", "x.com", "twitter.com", "tumblr.com", "tiktok.com",
    "linkedin.com", "instagram.com", "wordpress.com", "blogspot.com",
    "wearop.com",
    # retail / marketplace
    "endclothing.com", "asos.com", "amazon.co.uk", "ebay.co.uk", "etsy.com",
    "depop.com", "vinted.co.uk", "notonthehighstreet.com", "wolfandbadger.com",
    "silkfred.com", "crepslocker.com", "sevenstore.com", "impericon.com",
    "attitudeclothing.co.uk", "bluebanana.com", "emp.co.uk", "beserk.com.au",
    "urbanstaroma.com", "cooshti.com", "fatbuddhastore.com", "shop.app",
    "trustpilot.com", "wanderlog.com", "hipshops.com",
    # data brokers / email-guessing services — explicitly barred
    "rocketreach.co", "signalhire.com", "zoominfo.com", "contactout.com",
    "prospeo.io", "apollo.io", "hunter.io", "lusha.com", "endole.co.uk",
    "clearbit.com", "snov.io", "findthatlead.com",
})

# Hosts whose data must never be used as evidence for a contact email, because
# they publish inferred/pattern-derived addresses rather than published ones.
EMAIL_BROKER_HOSTS: frozenset[str] = frozenset({
    "rocketreach.co", "signalhire.com", "zoominfo.com", "contactout.com",
    "prospeo.io", "apollo.io", "hunter.io", "lusha.com", "clearbit.com",
    "snov.io", "findthatlead.com", "voilanorbert.com", "anymailfinder.com",
})

# Signals that a store is a generic dropship front rather than a brand.
DROPSHIP_MARKERS: frozenset[str] = frozenset({
    "aliexpress", "dropship", "print on demand storefront", "cj dropshipping",
    "14-30 business days delivery", "no brand identity",
})

# ccTLDs that positively indicate the business operates elsewhere. A generic TLD
# (.com/.shop/.store) proves nothing either way and must not be read as foreign.
FOREIGN_TLDS: tuple[str, ...] = (
    ".jp", ".de", ".fr", ".it", ".es", ".nl", ".se", ".no", ".dk", ".fi",
    ".pl", ".pt", ".gr", ".ch", ".at", ".be", ".ie", ".au", ".nz", ".ca",
    ".us", ".cn", ".kr", ".in", ".br", ".mx", ".za", ".ru", ".tr",
)

UK_HINTS: frozenset[str] = frozenset({
    "united kingdom", "uk", "england", "scotland", "wales", "northern ireland",
    "london", "manchester", "birmingham", "bristol", "leeds", "glasgow",
    "edinburgh", "liverpool", "newcastle", "nottingham", "sheffield",
    "cardiff", "brighton", "belfast", "leicester", "bridgend", "shrewsbury",
    "cramlington", "horwich", "yorkshire", "midlands", "gb",
})


def host_of(url: str) -> str:
    if not url or not is_found(url):
        return ""
    netloc = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def is_non_brand_host(url: str) -> bool:
    host = host_of(url)
    if not host:
        return False
    return any(host == h or host.endswith("." + h) for h in NON_BRAND_HOSTS)


def is_email_broker(url: str) -> bool:
    host = host_of(url)
    return any(host == h or host.endswith("." + h) for h in EMAIL_BROKER_HOSTS)


def is_major_brand(name: str) -> bool:
    return name.strip().lower().rstrip(".") in MAJOR_BRANDS


UK_CONFIRMED = "confirmed"
UK_UNCONFIRMED = "unconfirmed"
UK_FOREIGN = "foreign"


def uk_status(lead: Lead) -> str:
    """Three-way UK check: confirmed, unconfirmed, or positively foreign.

    The distinction matters because a freshly discovered candidate has no
    location yet. Treating "we have not checked" the same as "we checked and it
    is not UK" would silently bin real UK brands on .com domains before the
    enrichment pass ever runs.
    """
    host = host_of(lead.website)
    if host.endswith((".co.uk", ".uk", ".scot", ".wales", ".cymru")):
        return UK_CONFIRMED

    haystack = f"{lead.uk_location} {lead.notes}".lower()
    if any(hint in haystack.split() or hint in haystack for hint in UK_HINTS):
        return UK_CONFIRMED

    if host.endswith(FOREIGN_TLDS):
        return UK_FOREIGN

    return UK_UNCONFIRMED


def looks_uk(lead: Lead) -> bool:
    """True unless we have positive evidence the brand operates outside the UK."""
    return uk_status(lead) != UK_FOREIGN


def evaluate_exclusions(lead: Lead) -> tuple[bool, str]:
    """Return (excluded, reason). Reason is "" when the lead is kept."""
    if is_major_brand(lead.brand_name):
        return True, "Major/global or high-street brand — not an independent prospect"

    if is_non_brand_host(lead.website):
        return True, f"Not a brand site ({host_of(lead.website)} is a publisher/retailer/broker)"

    if uk_status(lead) == UK_FOREIGN:
        return True, f"Operates outside the UK ({host_of(lead.website)})"

    blob = f"{lead.notes} {lead.category}".lower()
    if any(marker in blob for marker in DROPSHIP_MARKERS):
        return True, "Dropshipping storefront with no identifiable brand presence"

    if lead.signals.instagram_active is False and lead.signals.has_ecommerce is False:
        return True, "Inactive — no recent posting and no working storefront"

    if lead.signals.marketplace_count is not None and lead.signals.marketplace_count >= 12:
        return True, "Already has very wide marketplace distribution"

    return False, ""


def apply_exclusions(leads: list[Lead]) -> tuple[list[Lead], list[Lead]]:
    """Split leads into (kept, excluded), tagging each excluded lead's reason."""
    kept: list[Lead] = []
    dropped: list[Lead] = []
    for lead in leads:
        excluded, reason = evaluate_exclusions(lead)
        lead.excluded = excluded
        lead.exclusion_reason = reason
        (dropped if excluded else kept).append(lead)
    return kept, dropped
