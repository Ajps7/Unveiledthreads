"""End-to-end orchestration: discover → enrich → filter → dedupe → score → export."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

from . import dedup, filters, outreach, queries, scoring
from .discovery import SearchProvider, discover
from .extract import Fetcher, apply_evidence, gather_site_evidence
from .models import Lead
from .store import LeadStore, export_csv, export_markdown, export_xlsx

FLAG_UK = "[UK base unconfirmed — verify before outreach]"


@dataclass
class RunReport:
    queries_run: int = 0
    candidates_found: int = 0
    enriched: int = 0
    excluded: list[tuple[str, str]] = field(default_factory=list)
    kept: int = 0
    unconfirmed_uk: list[str] = field(default_factory=list)
    invalid: list[tuple[str, list[str]]] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def as_text(self) -> str:
        lines = [
            f"queries run       : {self.queries_run}",
            f"candidates found  : {self.candidates_found}",
            f"sites enriched    : {self.enriched}",
            f"excluded          : {len(self.excluded)}",
            f"kept              : {self.kept}",
        ]
        if self.summary:
            lines.append(
                f"scores            : avg {self.summary.get('average_score')} · "
                f"{self.summary.get('high')} high / {self.summary.get('medium')} med / "
                f"{self.summary.get('low')} low"
            )
        if self.unconfirmed_uk:
            lines.append(f"UK base unconfirmed: {len(self.unconfirmed_uk)} "
                         f"({', '.join(self.unconfirmed_uk[:8])})")
        if self.excluded:
            lines.append("\nexcluded:")
            lines += [f"  - {name}: {reason}" for name, reason in self.excluded[:40]]
        if self.invalid:
            lines.append("\nvalidation problems:")
            lines += [f"  - {name}: {'; '.join(probs)}" for name, probs in self.invalid]
        return "\n".join(lines)


def refine(leads: list[Lead], *, report: Optional[RunReport] = None) -> list[Lead]:
    """The network-free half of the pipeline.

    Deduplicate first so exclusion reasons are evaluated against the merged
    record — a stub missing its location would otherwise be dropped as non-UK
    before the sibling record that proves the location gets merged in.
    """
    report = report or RunReport()

    merged = dedup.deduplicate(leads)
    kept, dropped = filters.apply_exclusions(merged)
    report.excluded = [(l.brand_name, l.exclusion_reason) for l in dropped]

    # A candidate on a generic TLD with no location yet is kept, but the
    # operator must be able to see that its UK status is unverified rather than
    # assume it was checked.
    for lead in kept:
        if filters.uk_status(lead) == filters.UK_UNCONFIRMED and FLAG_UK not in lead.notes:
            lead.notes = f"{lead.notes} {FLAG_UK}".strip()
            report.unconfirmed_uk.append(lead.brand_name)

    scoring.score_all(kept)
    outreach.ensure_notes(kept)
    ranked = scoring.rank(kept)

    for lead in ranked:
        problems = lead.validate()
        if problems:
            report.invalid.append((lead.brand_name, problems))

    report.kept = len(ranked)
    report.summary = scoring.summarise(ranked)
    return ranked


def enrich(leads: list[Lead], *, fetcher: Optional[Fetcher] = None,
           on_lead: Optional[Callable[[Lead], None]] = None) -> list[Lead]:
    """Visit each candidate's public pages and fold in what they publish."""
    fetcher = fetcher or Fetcher()
    today = date.today().isoformat()
    for lead in leads:
        if not lead.website or lead.website == "Not found":
            continue
        try:
            evidence = gather_site_evidence(lead.website, fetcher)
        except Exception as exc:
            lead.notes = f"{lead.notes} [enrichment failed: {exc}]".strip()
            continue
        apply_evidence(lead, evidence)
        lead.last_verified = today
        if on_lead:
            on_lead(lead)
    return leads


def run(
    provider: SearchProvider,
    *,
    store_path: str,
    query_list: Optional[list[str]] = None,
    limit_per_query: int = 20,
    do_enrich: bool = True,
    fetcher: Optional[Fetcher] = None,
    verbose: bool = False,
) -> tuple[list[Lead], RunReport]:
    """Full run. Results are merged into the store, so runs accumulate."""
    report = RunReport()
    query_list = query_list or queries.all_queries()

    def _log_query(query: str, found: int) -> None:
        report.queries_run += 1
        if verbose:
            print(f"  [{report.queries_run}/{len(query_list)}] {query} → {found} new")

    candidates = discover(provider, query_list, limit_per_query=limit_per_query,
                          on_query=_log_query)
    report.candidates_found = len(candidates)

    candidates = dedup.deduplicate(candidates)
    if do_enrich:
        enrich(candidates, fetcher=fetcher)
        report.enriched = sum(1 for l in candidates if l.last_verified)

    store = LeadStore(store_path)
    combined = store.load() + candidates
    final = refine(combined, report=report)
    store.save(final)
    return final, report


def export_all(leads: list[Lead], out_dir: str) -> dict[str, Optional[str]]:
    """Write CSV (always), XLSX (if openpyxl present) and a Markdown review sheet."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    return {
        "csv": export_csv(leads, os.path.join(out_dir, "uk_independent_brand_leads.csv")),
        "xlsx": export_xlsx(leads, os.path.join(out_dir, "uk_independent_brand_leads.xlsx")),
        "markdown": export_markdown(leads, os.path.join(out_dir, "uk_independent_brand_leads.md")),
    }
