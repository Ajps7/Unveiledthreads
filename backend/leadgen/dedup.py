"""Duplicate detection and record merging.

The same brand arrives repeatedly under slightly different names ("MKI",
"MKI Miyuki Zoku", "MKI MIYUKI ZOKU®") and different URLs (bare domain, /pages/
deep link, myshopify.com mirror). Identity is resolved on the strongest
available key: website host, then Instagram handle, then normalised name.
"""

from __future__ import annotations

import re
import unicodedata

from .filters import host_of
from .models import Lead, NOT_FOUND, is_found

_NOISE_WORDS = {
    "the", "ltd", "limited", "co", "company", "clothing", "apparel", "brand",
    "official", "store", "shop", "uk", "london", "studios", "studio", "inc",
}
_PUNCT_RE = re.compile(r"[^a-z0-9\s]")
_SPACE_RE = re.compile(r"\s+")


def normalise_name(name: str) -> str:
    """Aggressive name key: lowercase, strip accents/symbols and filler words."""
    decomposed = unicodedata.normalize("NFKD", name or "")
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    cleaned = _PUNCT_RE.sub(" ", ascii_only.lower())
    tokens = [t for t in _SPACE_RE.split(cleaned) if t and t not in _NOISE_WORDS]
    return "".join(tokens) or _SPACE_RE.sub("", cleaned)


def normalise_host(url: str) -> str:
    """Website identity key, with the Shopify mirror collapsed onto the brand."""
    host = host_of(url)
    if not host:
        return ""
    if host.endswith(".myshopify.com"):
        return host[: -len(".myshopify.com")]
    # Treat co.uk / com variants of the same label as one brand.
    parts = host.split(".")
    return parts[0] if len(parts) > 1 else host


def normalise_handle(handle: str) -> str:
    if not is_found(handle):
        return ""
    return handle.strip().lstrip("@").lower()


def identity_keys(lead: Lead) -> set[str]:
    keys = set()
    host = normalise_host(lead.website)
    if host:
        keys.add(f"host:{host}")
    handle = normalise_handle(lead.instagram_handle)
    if handle:
        keys.add(f"ig:{handle}")
    name = normalise_name(lead.brand_name)
    if name:
        keys.add(f"name:{name}")
    return keys


def _prefer(current: str, incoming: str) -> str:
    """Keep the existing value unless it is empty/NOT_FOUND."""
    if is_found(current):
        return current
    return incoming if is_found(incoming) else (current or NOT_FOUND)


def merge(base: Lead, other: Lead) -> Lead:
    """Fold `other` into `base`, filling gaps without overwriting evidenced data."""
    for f in ("website", "instagram_handle", "instagram_url", "contact_email",
              "founder_owner", "founder_profile", "uk_location", "category",
              "instagram_followers", "sells_own_website", "existing_marketplaces",
              "contact_page"):
        setattr(base, f, _prefer(getattr(base, f), getattr(other, f)))

    # Longer brand name usually carries the fuller trading name.
    if len(other.brand_name.strip()) > len(base.brand_name.strip()):
        base.brand_name = other.brand_name.strip()

    for f_name, url in other.sources.items():
        base.sources.setdefault(f_name, url)
    for f_name, level in other.evidence.items():
        base.evidence.setdefault(f_name, level)

    for f_name, value in other.signals.to_dict().items():
        if getattr(base.signals, f_name) is None and value is not None:
            if f_name == "price_range_gbp" and isinstance(value, list):
                value = tuple(value)
            setattr(base.signals, f_name, value)

    if other.notes and other.notes not in base.notes:
        base.notes = f"{base.notes} {other.notes}".strip()
    if not base.outreach_note:
        base.outreach_note = other.outreach_note
    if not base.last_verified:
        base.last_verified = other.last_verified

    return base


def deduplicate(leads: list[Lead]) -> list[Lead]:
    """Collapse duplicates, preserving first-seen order."""
    merged: list[Lead] = []
    index: dict[str, int] = {}

    for lead in leads:
        keys = identity_keys(lead)
        hit = next((index[k] for k in keys if k in index), None)
        if hit is None:
            merged.append(lead)
            position = len(merged) - 1
        else:
            merge(merged[hit], lead)
            position = hit
        # Re-key against the merged record so later aliases also resolve.
        for k in identity_keys(merged[position]) | keys:
            index.setdefault(k, position)

    return merged
