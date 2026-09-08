"""Core data model for the UnveiledThreads lead-generation pipeline.

Design rule that governs this whole package: **a field is either evidenced or it
is NOT_FOUND**. There is no third state, and nothing in the pipeline is allowed
to infer, pattern-guess or interpolate a value. Email-pattern services (the
"first@domain.com, used 63% of the time" kind of result) are specifically not an
acceptable source — that is guessing a private address, not collecting a
published one.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any, Optional

NOT_FOUND = "Not found"

# How a value came to be in the record. Used by the exporter so a human can see
# at a glance which cells are safe to act on.
EVIDENCE_DIRECT = "direct"        # read off the brand's own site/profile
EVIDENCE_SEARCH = "search"        # stated verbatim in a search result / article
EVIDENCE_EDITORIAL = "editorial"  # stated in a press/editorial piece
EVIDENCE_LEVELS = (EVIDENCE_DIRECT, EVIDENCE_SEARCH, EVIDENCE_EDITORIAL)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
_HANDLE_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")


def is_found(value: Optional[str]) -> bool:
    """True when a field carries a real value rather than the NOT_FOUND sentinel."""
    return bool(value) and value != NOT_FOUND


@dataclass
class Signals:
    """Observable facts used by the scorer.

    Every field is Optional and defaults to None meaning *unknown*. The scorer
    treats unknown as "no credit, but no penalty beyond that" — it never invents
    a favourable assumption to inflate a score.
    """

    instagram_active: Optional[bool] = None          # posting within ~90 days
    instagram_professional: Optional[bool] = None    # bio, link, coherent grid
    follower_count: Optional[int] = None
    releases_collections: Optional[bool] = None      # recurring drops/collections
    has_ecommerce: Optional[bool] = None             # own site takes orders
    independent_positioning: Optional[bool] = None   # self-describes as independent
    strong_visual_branding: Optional[bool] = None
    price_range_gbp: Optional[tuple[int, int]] = None
    marketplace_count: Optional[int] = None          # third-party marketplaces seen
    has_public_contact: Optional[bool] = None        # published email or contact form

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.price_range_gbp is not None:
            d["price_range_gbp"] = list(self.price_range_gbp)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Signals":
        d = dict(d or {})
        pr = d.get("price_range_gbp")
        if isinstance(pr, list):
            d["price_range_gbp"] = tuple(pr)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Lead:
    """One prospect brand.

    `sources` maps a field name to the URL that evidences it; `evidence` maps a
    field name to one of EVIDENCE_LEVELS. Both are keyed by the attribute name
    (e.g. "contact_email"), so the exporter can render provenance per cell.
    """

    brand_name: str
    website: str = NOT_FOUND
    instagram_handle: str = NOT_FOUND
    instagram_url: str = NOT_FOUND
    contact_email: str = NOT_FOUND
    founder_owner: str = NOT_FOUND
    founder_profile: str = NOT_FOUND
    uk_location: str = NOT_FOUND
    category: str = NOT_FOUND
    instagram_followers: str = NOT_FOUND
    sells_own_website: str = NOT_FOUND       # "Yes" / "No" / NOT_FOUND
    existing_marketplaces: str = NOT_FOUND
    contact_page: str = NOT_FOUND
    notes: str = ""
    outreach_note: str = ""

    signals: Signals = field(default_factory=Signals)
    sources: dict[str, str] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)

    # Populated by scoring.score_lead(); kept on the record so exports are stable.
    lead_score: Optional[int] = None
    priority: Optional[str] = None
    score_breakdown: dict[str, int] = field(default_factory=dict)

    last_verified: str = ""
    excluded: bool = False
    exclusion_reason: str = ""

    # ---- validation -------------------------------------------------------

    def validate(self) -> list[str]:
        """Return a list of data-integrity problems. Empty list means clean.

        This is the guard rail against fabricated data reaching the spreadsheet:
        anything that looks like a value must also carry a source URL.
        """
        problems: list[str] = []
        if not self.brand_name.strip():
            problems.append("brand_name is empty")

        if is_found(self.contact_email) and not _EMAIL_RE.match(self.contact_email):
            problems.append(f"contact_email is not a valid address: {self.contact_email!r}")

        if is_found(self.instagram_handle):
            handle = self.instagram_handle.lstrip("@")
            if not _HANDLE_RE.match(handle):
                problems.append(f"instagram_handle is malformed: {self.instagram_handle!r}")
            if is_found(self.instagram_url) and handle.lower() not in self.instagram_url.lower():
                problems.append("instagram_url does not match instagram_handle")

        for f in ("website", "instagram_url", "contact_page", "founder_profile"):
            v = getattr(self, f)
            if is_found(v) and not v.startswith(("http://", "https://")):
                problems.append(f"{f} is not an absolute URL: {v!r}")

        # Every asserted fact needs provenance.
        for f in ("website", "instagram_handle", "contact_email", "founder_owner",
                  "uk_location", "instagram_followers"):
            if is_found(getattr(self, f)) and not self.sources.get(f):
                problems.append(f"{f} has a value but no source URL")

        for f, level in self.evidence.items():
            if level not in EVIDENCE_LEVELS:
                problems.append(f"evidence[{f}] has unknown level {level!r}")

        if is_found(self.instagram_followers):
            if not re.match(r"^~?[\d,]+$", self.instagram_followers):
                problems.append(
                    f"instagram_followers must be a number, got {self.instagram_followers!r}")

        return problems

    # ---- serialisation ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["signals"] = self.signals.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Lead":
        d = dict(d)
        d["signals"] = Signals.from_dict(d.get("signals") or {})
        known = cls.__dataclass_fields__
        return cls(**{k: v for k, v in d.items() if k in known})

    def all_source_urls(self) -> list[str]:
        """Deduplicated source URLs, in first-seen order."""
        seen: list[str] = []
        for url in self.sources.values():
            if url and url not in seen:
                seen.append(url)
        return seen


def load_leads(path: str) -> list[Lead]:
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    records = payload["leads"] if isinstance(payload, dict) else payload
    return [Lead.from_dict(r) for r in records]


def dump_leads(leads: list[Lead], path: str, *, generated_on: Optional[str] = None) -> None:
    payload = {
        "generated_on": generated_on or date.today().isoformat(),
        "count": len(leads),
        "leads": [l.to_dict() for l in leads],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
