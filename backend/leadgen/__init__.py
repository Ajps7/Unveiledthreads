"""UnveiledThreads lead generation — UK independent clothing & streetwear brands.

Pipeline: discovery (search) → enrichment (public pages) → exclusion filters →
deduplication → 1-100 scoring → prioritisation → spreadsheet export.

The governing rule is in `models`: every field is either evidenced with a source
URL or recorded as "Not found". Nothing is inferred.
"""

from .models import Lead, Signals, NOT_FOUND, load_leads, dump_leads
from .scoring import score_lead, score_all, rank, summarise, priority_for
from .store import LeadStore, COLUMNS, export_csv, export_xlsx, export_markdown
from .pipeline import RunReport, refine, enrich, run, export_all

__all__ = [
    "Lead", "Signals", "NOT_FOUND", "load_leads", "dump_leads",
    "score_lead", "score_all", "rank", "summarise", "priority_for",
    "LeadStore", "COLUMNS", "export_csv", "export_xlsx", "export_markdown",
    "RunReport", "refine", "enrich", "run", "export_all",
]
