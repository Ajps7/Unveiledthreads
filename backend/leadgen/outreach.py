"""Personalised outreach notes.

The brief asks for "one specific reason" per brand. Specific means grounded in
something we actually verified about *that* brand — its city, its founder story,
its follower band, its distribution. A note that would read identically for any
other brand has failed, so `generate_note` picks the strongest evidenced hook
rather than emitting a template.

Hand-written notes always win: `Lead.outreach_note`, once set, is left alone.
"""

from __future__ import annotations

import re

from .models import Lead, is_found

MARKETPLACE_NAME = "UnveiledThreads"

_PARENTHETICAL = re.compile(r"\s*\([^)]*\)?")


def _plain(value: str) -> str:
    """First clause of a field, with parenthetical asides removed.

    Fields carry qualifiers for the spreadsheet ("Glasgow (Glasgow Fort,
    Silverburn...)", "Armani Duke (trades as Armani TakeRisks)") that read badly
    mid-sentence and can leave an unclosed bracket once split on a comma.
    """
    return _PARENTHETICAL.sub("", value).split(",")[0].strip(" -–—")


def _followers_int(lead: Lead) -> int | None:
    if lead.signals.follower_count is not None:
        return lead.signals.follower_count
    if is_found(lead.instagram_followers):
        digits = lead.instagram_followers.replace("~", "").replace(",", "")
        if digits.isdigit():
            return int(digits)
    return None


def generate_note(lead: Lead) -> str:
    """Return a one- or two-sentence, evidence-grounded outreach hook."""
    name = _plain(lead.brand_name) or lead.brand_name
    city = _plain(lead.uk_location) if is_found(lead.uk_location) else ""
    followers = _followers_int(lead)
    s = lead.signals

    # Strongest hook first: a named founder plus a real city is the most
    # personal thing we can honestly say.
    if is_found(lead.founder_owner) and city:
        return (
            f"{name} is founder-led out of {city} — a direct approach to "
            f"{_plain(lead.founder_owner)} works better than a generic "
            f"brand inbox, and {MARKETPLACE_NAME} is being built specifically for "
            f"independent UK labels like this rather than as another general "
            f"fashion marketplace."
        )

    # No marketplace presence at all: the clearest value proposition we have.
    if s.marketplace_count == 0 and s.has_ecommerce:
        where = f" from {city}" if city else ""
        return (
            f"{name} currently sells only through its own site{where}, so "
            f"{MARKETPLACE_NAME} would add a new discovery channel without "
            f"competing against an existing marketplace relationship."
        )

    # Follower band is the criterion the brief weights most explicitly.
    if followers is not None and 1_000 <= followers <= 100_000:
        where = f" in {city}" if city else ""
        return (
            f"With roughly {followers:,} Instagram followers{where}, {name} sits in "
            f"the band where an audience already exists but discovery beyond "
            f"Instagram is the bottleneck — exactly the gap {MARKETPLACE_NAME} fills."
        )

    if followers is not None and followers > 100_000:
        return (
            f"{name} has built an audience of about {followers:,} on Instagram; a "
            f"curated UK-independent marketplace like {MARKETPLACE_NAME} is a "
            f"lower-risk retail channel than wholesale, and their scale would help "
            f"anchor the category for other brands."
        )

    if s.releases_collections and city:
        return (
            f"{name} releases new collections regularly out of {city}, which suits "
            f"{MARKETPLACE_NAME}'s drop-led merchandising better than a static "
            f"catalogue listing."
        )

    if city:
        return (
            f"{name} is an independent {city} label with its own storefront — the "
            f"kind of regional UK brand {MARKETPLACE_NAME} is being curated around, "
            f"rather than London-only coverage."
        )

    return (
        f"{name} positions itself as an independent UK label, which matches "
        f"{MARKETPLACE_NAME}'s curation criteria; worth confirming their current "
        f"stockist arrangements before approaching."
    )


def ensure_notes(leads: list[Lead]) -> list[Lead]:
    for lead in leads:
        if not lead.outreach_note.strip():
            lead.outreach_note = generate_note(lead)
    return leads
