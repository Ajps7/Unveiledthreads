"""Search-engine discovery: query bank in, brand candidates out.

Providers are pluggable so the pipeline can run against whichever search API the
deployment has a key for, and against a recorded fixture in tests. Nothing here
scrapes a search engine's HTML — that breaks their terms and is unreliable; use
an API key.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Optional, Protocol

import requests

from .filters import host_of, is_non_brand_host
from .models import NOT_FOUND, Lead

USER_AGENT = (
    "UnveiledThreadsLeadBot/1.0 (+https://unveiledthreads.com/about; "
    "independent UK brand discovery; contact: partnerships@unveiledthreads.com)"
)


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    query: str = ""


class SearchProvider(Protocol):
    def search(self, query: str, *, limit: int = 20) -> list[SearchResult]:
        ...


class SerpApiProvider:
    """Google results via SerpAPI. Set SERPAPI_KEY."""

    endpoint = "https://serpapi.com/search.json"

    def __init__(self, api_key: Optional[str] = None, *, gl: str = "uk", hl: str = "en"):
        self.api_key = api_key or os.environ.get("SERPAPI_KEY", "")
        self.gl, self.hl = gl, hl
        if not self.api_key:
            raise RuntimeError("SERPAPI_KEY is not set")

    def search(self, query: str, *, limit: int = 20) -> list[SearchResult]:
        resp = requests.get(
            self.endpoint,
            params={"q": query, "api_key": self.api_key, "num": limit,
                    "gl": self.gl, "hl": self.hl},
            timeout=30,
        )
        resp.raise_for_status()
        organic = resp.json().get("organic_results", []) or []
        return [
            SearchResult(title=r.get("title", ""), url=r.get("link", ""),
                         snippet=r.get("snippet", ""), query=query)
            for r in organic if r.get("link")
        ]


class BraveSearchProvider:
    """Brave Search API. Set BRAVE_SEARCH_API_KEY."""

    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: Optional[str] = None, *, country: str = "GB"):
        self.api_key = api_key or os.environ.get("BRAVE_SEARCH_API_KEY", "")
        self.country = country
        if not self.api_key:
            raise RuntimeError("BRAVE_SEARCH_API_KEY is not set")

    def search(self, query: str, *, limit: int = 20) -> list[SearchResult]:
        resp = requests.get(
            self.endpoint,
            headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
            params={"q": query, "count": min(limit, 20), "country": self.country},
            timeout=30,
        )
        resp.raise_for_status()
        results = (resp.json().get("web", {}) or {}).get("results", []) or []
        return [
            SearchResult(title=r.get("title", ""), url=r.get("url", ""),
                         snippet=r.get("description", ""), query=query)
            for r in results if r.get("url")
        ]


class StaticProvider:
    """Replay recorded results. Used by tests and for offline re-runs."""

    def __init__(self, results_by_query: dict[str, list[SearchResult]]):
        self._results = results_by_query

    def search(self, query: str, *, limit: int = 20) -> list[SearchResult]:
        return list(self._results.get(query, []))[:limit]


def build_provider() -> Optional[SearchProvider]:
    """Pick whichever provider has credentials configured."""
    for factory in (SerpApiProvider, BraveSearchProvider):
        try:
            return factory()
        except RuntimeError:
            continue
    return None


# --- candidate extraction -------------------------------------------------

_TITLE_SEPARATORS = re.compile(r"\s*[|–—\-•:]\s*")
_TRAILING_JUNK = re.compile(
    r"\b(official (web)?site|online store|shop now|home ?page|uk|home)\b\.?$",
    re.IGNORECASE,
)


def brand_name_from_result(result: SearchResult) -> str:
    """Best-effort brand name from a result title.

    Search titles are overwhelmingly "<Brand> | <tagline>", so the first segment
    is the brand far more often than not. This is a *candidate* name — the
    verification pass is what confirms it.
    """
    head = _TITLE_SEPARATORS.split(result.title.strip())[0].strip()
    head = _TRAILING_JUNK.sub("", head).strip(" -–—|")
    if not head or len(head) > 60:
        host = host_of(result.url)
        head = host.split(".")[0].replace("-", " ").title() if host else head
    return head


def candidates_from_results(results: Iterable[SearchResult]) -> list[Lead]:
    """Turn raw search results into unverified Lead stubs.

    Publisher/retailer/broker hosts are dropped here rather than later, so the
    expensive enrichment pass only ever touches plausible brand sites.
    """
    leads: list[Lead] = []
    for result in results:
        if not result.url or is_non_brand_host(result.url):
            continue
        host = host_of(result.url)
        if not host:
            continue
        website = f"https://{host}/"
        lead = Lead(brand_name=brand_name_from_result(result), website=website)
        lead.sources["website"] = result.url
        lead.evidence["website"] = "search"
        lead.notes = (result.snippet or "").strip()[:400]
        leads.append(lead)
    return leads


def discover(
    provider: SearchProvider,
    queries: list[str],
    *,
    limit_per_query: int = 20,
    delay_seconds: float = 1.0,
    on_query: Optional[Callable[[str, int], None]] = None,
) -> list[Lead]:
    """Run the query bank and return deduplicated-by-URL candidate stubs."""
    seen_urls: set[str] = set()
    candidates: list[Lead] = []

    for query in queries:
        try:
            results = provider.search(query, limit=limit_per_query)
        except Exception as exc:  # a dead query must not kill the whole run
            if on_query:
                on_query(f"{query} [FAILED: {exc}]", 0)
            continue

        fresh = [r for r in results if r.url not in seen_urls]
        seen_urls.update(r.url for r in results)
        new_leads = candidates_from_results(fresh)
        candidates.extend(new_leads)

        if on_query:
            on_query(query, len(new_leads))
        if delay_seconds:
            time.sleep(delay_seconds)

    return candidates
