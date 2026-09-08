"""Enrichment: read a brand's own public pages and record what they publish.

Scope limits, taken straight from the brief and not negotiable in code:

* Public pages only. robots.txt is honoured, and a page behind a login is
  skipped rather than worked around.
* Emails are only accepted when the brand publishes them on their own site.
  No pattern guessing, no people-search brokers, no personal addresses.
* Instagram is treated as a link target. We record the handle and the public
  profile URL; we do not log in, and we do not read private accounts.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

from .discovery import USER_AGENT
from .models import NOT_FOUND, Lead

REQUEST_TIMEOUT = 20
CRAWL_DELAY = 1.5

CONTACT_PATHS = (
    "/pages/contact", "/pages/contact-us", "/contact", "/contact-us",
    "/pages/about", "/about", "/about-us", "/pages/stockists",
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_IG_RE = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9._]{1,30})/?", re.IGNORECASE)
_TIKTOK_RE = re.compile(
    r"(?:https?://)?(?:www\.)?tiktok\.com/@([A-Za-z0-9._]{1,30})", re.IGNORECASE)
_LINKEDIN_RE = re.compile(
    r"(?:https?://)?(?:[a-z]{2}\.)?linkedin\.com/in/([A-Za-z0-9\-%]{3,100})", re.IGNORECASE)
_GBP_RE = re.compile(r"£\s?(\d{1,4})(?:\.\d{2})?")
_TAG_RE = re.compile(r"<[^>]+>")

# Addresses that belong to a platform, a lawyer or an image host rather than the
# brand, plus the placeholders every Shopify theme ships with.
_EMAIL_NOISE = re.compile(
    r"(example\.|sentry\.|wixpress|@shopify\.com|@2x|\.png$|\.jpg$|\.jpeg$|"
    r"\.gif$|\.webp$|\.svg$|@sentry\.io|no-?reply@|@godaddy|@wix\.com)",
    re.IGNORECASE,
)

# Instagram/TikTok paths that are not a brand account.
_HANDLE_NOISE = frozenset({
    "p", "reel", "reels", "explore", "accounts", "stories", "tv", "share",
    "directory", "about", "legal", "privacy", "developer", "help",
})

MARKETPLACE_SIGNATURES = {
    "asos.com": "ASOS",
    "endclothing.com": "END.",
    "wolfandbadger.com": "Wolf & Badger",
    "etsy.com": "Etsy",
    "depop.com": "Depop",
    "notonthehighstreet.com": "Not On The High Street",
    "amazon.co.uk": "Amazon UK",
    "ebay.co.uk": "eBay UK",
    "silkfred.com": "SilkFred",
    "urbanoutfitters.com": "Urban Outfitters",
    "zalando.co.uk": "Zalando",
    "farfetch.com": "Farfetch",
    "vinted.co.uk": "Vinted",
    "flannels.com": "Flannels",
    "jdsports.co.uk": "JD Sports",
}

ECOMMERCE_MARKERS = (
    "add to cart", "add to bag", "add to basket", "/cart", "checkout",
    "shopify", "woocommerce", "bigcommerce", "squarespace-commerce",
)

INDEPENDENT_MARKERS = (
    "independent", "family run", "family-run", "self funded", "self-funded",
    "small batch", "small-batch", "founded by", "we are a small team",
    "independently owned", "indie brand",
)

BRANDING_MARKERS = (
    "lookbook", "campaign", "editorial", "collection", "ss2", "aw2", "capsule",
)


@dataclass
class PageFetch:
    url: str
    status: int
    html: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status == 200 and bool(self.html)


@dataclass
class SiteEvidence:
    """Everything a site visit established, with the URL that proves each item."""

    emails: list[str] = field(default_factory=list)
    instagram_handle: str = ""
    tiktok_handle: str = ""
    linkedin_urls: list[str] = field(default_factory=list)
    contact_page: str = ""
    has_ecommerce: Optional[bool] = None
    independent_language: bool = False
    strong_branding: bool = False
    prices_gbp: list[int] = field(default_factory=list)
    marketplaces: list[str] = field(default_factory=list)
    pages_seen: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)

    def price_range(self) -> Optional[tuple[int, int]]:
        # Trim outliers: gift cards at £5 and a one-off £900 coat both distort
        # the band the brief actually cares about.
        sane = sorted(p for p in self.prices_gbp if 5 <= p <= 2000)
        if len(sane) < 3:
            return None
        cut = max(1, len(sane) // 10)
        trimmed = sane[cut:-cut] or sane
        return (trimmed[0], trimmed[-1])


class Fetcher:
    """Polite HTTP client: identifies itself, obeys robots.txt, rate limits."""

    def __init__(self, *, user_agent: str = USER_AGENT, respect_robots: bool = True,
                 delay: float = CRAWL_DELAY):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-GB,en;q=0.9",
        })
        self.user_agent = user_agent
        self.respect_robots = respect_robots
        self.delay = delay
        self._robots: dict[str, Optional[RobotFileParser]] = {}
        self._last_call: dict[str, float] = {}

    def _robots_for(self, url: str) -> Optional[RobotFileParser]:
        origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        if origin not in self._robots:
            parser = RobotFileParser()
            parser.set_url(urljoin(origin, "/robots.txt"))
            try:
                parser.read()
            except Exception:
                parser = None  # unreadable robots.txt: fall back to allowed
            self._robots[origin] = parser
        return self._robots[origin]

    def allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        parser = self._robots_for(url)
        if parser is None:
            return True
        try:
            return parser.can_fetch(self.user_agent, url)
        except Exception:
            return True

    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc
        elapsed = time.monotonic() - self._last_call.get(host, 0.0)
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_call[host] = time.monotonic()

    def get(self, url: str) -> PageFetch:
        if not self.allowed(url):
            return PageFetch(url=url, status=0, error="disallowed by robots.txt")
        self._throttle(url)
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        except requests.RequestException as exc:
            return PageFetch(url=url, status=0, error=str(exc))
        if "text/html" not in resp.headers.get("Content-Type", ""):
            return PageFetch(url=resp.url, status=resp.status_code, error="not HTML")
        return PageFetch(url=resp.url, status=resp.status_code, html=resp.text)


def _visible_text(html: str) -> str:
    stripped = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html,
                      flags=re.IGNORECASE | re.DOTALL)
    return _TAG_RE.sub(" ", stripped)


def extract_emails(html: str) -> list[str]:
    """Published addresses only: mailto: links first, then body text."""
    found: list[str] = []
    for match in re.finditer(r'mailto:([^"\'>?\s]+)', html, re.IGNORECASE):
        found.append(match.group(1))
    found.extend(_EMAIL_RE.findall(_visible_text(html)))

    cleaned: list[str] = []
    for raw in found:
        addr = raw.strip().strip(".,;:()<>").lower()
        if not _EMAIL_RE.fullmatch(addr) or _EMAIL_NOISE.search(addr):
            continue
        if addr not in cleaned:
            cleaned.append(addr)
    return cleaned


def _first_handle(pattern: re.Pattern[str], html: str) -> str:
    for match in pattern.finditer(html):
        handle = match.group(1).strip("/").lower()
        if handle and handle not in _HANDLE_NOISE:
            return handle
    return ""


def parse_page(html: str, base_url: str, evidence: SiteEvidence) -> SiteEvidence:
    """Fold one page's findings into the accumulating evidence record."""
    lowered = html.lower()
    text = _visible_text(html)

    for addr in extract_emails(html):
        if addr not in evidence.emails:
            evidence.emails.append(addr)

    if not evidence.instagram_handle:
        evidence.instagram_handle = _first_handle(_IG_RE, html)
    if not evidence.tiktok_handle:
        evidence.tiktok_handle = _first_handle(_TIKTOK_RE, html)
    for match in _LINKEDIN_RE.finditer(html):
        url = f"https://www.linkedin.com/in/{match.group(1)}"
        if url not in evidence.linkedin_urls:
            evidence.linkedin_urls.append(url)

    if any(marker in lowered for marker in ECOMMERCE_MARKERS):
        evidence.has_ecommerce = True

    if any(marker in text.lower() for marker in INDEPENDENT_MARKERS):
        evidence.independent_language = True
    if any(marker in lowered for marker in BRANDING_MARKERS):
        evidence.strong_branding = True

    evidence.prices_gbp.extend(int(p) for p in _GBP_RE.findall(text))

    for host, label in MARKETPLACE_SIGNATURES.items():
        if host in lowered and label not in evidence.marketplaces:
            evidence.marketplaces.append(label)

    if base_url not in evidence.pages_seen:
        evidence.pages_seen.append(base_url)
    return evidence


def gather_site_evidence(website: str, fetcher: Optional[Fetcher] = None) -> SiteEvidence:
    """Fetch the homepage plus the usual contact/about paths and parse them."""
    fetcher = fetcher or Fetcher()
    evidence = SiteEvidence()

    home = fetcher.get(website)
    if home.error == "disallowed by robots.txt":
        evidence.blocked.append(website)
    if home.ok:
        parse_page(home.html, home.url, evidence)

    for path in CONTACT_PATHS:
        url = urljoin(website, path)
        page = fetcher.get(url)
        if page.error == "disallowed by robots.txt":
            evidence.blocked.append(url)
            continue
        if not page.ok:
            continue
        parse_page(page.html, page.url, evidence)
        if not evidence.contact_page and "contact" in path:
            evidence.contact_page = page.url

    return evidence


def _best_email(emails: list[str], website: str) -> str:
    """Prefer a role address on the brand's own domain."""
    if not emails:
        return NOT_FOUND
    domain = urlparse(website).netloc.lower().removeprefix("www.")
    on_domain = [e for e in emails if e.endswith("@" + domain)] or emails
    preferred = ("info@", "hello@", "contact@", "sales@", "hi@", "shop@",
                 "orders@", "support@", "press@", "wholesale@", "team@")
    for prefix in preferred:
        for addr in on_domain:
            if addr.startswith(prefix):
                return addr
    return on_domain[0]


def apply_evidence(lead: Lead, evidence: SiteEvidence) -> Lead:
    """Write site evidence onto a Lead, never overwriting an existing value."""
    site = lead.website if lead.website != NOT_FOUND else ""

    if lead.contact_email == NOT_FOUND:
        email = _best_email(evidence.emails, site)
        if email != NOT_FOUND:
            lead.contact_email = email
            lead.sources["contact_email"] = evidence.contact_page or site
            lead.evidence["contact_email"] = "direct"

    if lead.instagram_handle == NOT_FOUND and evidence.instagram_handle:
        lead.instagram_handle = f"@{evidence.instagram_handle}"
        lead.instagram_url = f"https://www.instagram.com/{evidence.instagram_handle}/"
        lead.sources["instagram_handle"] = site
        lead.evidence["instagram_handle"] = "direct"

    if lead.contact_page == NOT_FOUND and evidence.contact_page:
        lead.contact_page = evidence.contact_page
        lead.sources["contact_page"] = evidence.contact_page
        lead.evidence["contact_page"] = "direct"

    if evidence.marketplaces and lead.existing_marketplaces == NOT_FOUND:
        lead.existing_marketplaces = ", ".join(evidence.marketplaces)
        lead.sources["existing_marketplaces"] = site

    s = lead.signals
    if evidence.has_ecommerce is not None and s.has_ecommerce is None:
        s.has_ecommerce = evidence.has_ecommerce
        lead.sells_own_website = "Yes" if evidence.has_ecommerce else "No"
    if s.independent_positioning is None and evidence.independent_language:
        s.independent_positioning = True
    if s.strong_visual_branding is None and evidence.strong_branding:
        s.strong_visual_branding = True
    if s.price_range_gbp is None:
        s.price_range_gbp = evidence.price_range()
    if s.marketplace_count is None:
        s.marketplace_count = len(evidence.marketplaces)
    if s.has_public_contact is None:
        s.has_public_contact = bool(evidence.emails or evidence.contact_page)

    return lead
