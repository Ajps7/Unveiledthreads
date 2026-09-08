"""Command line entry point.

    python -m leadgen rebuild            # re-score + re-export the stored leads
    python -m leadgen discover           # live run (needs a search API key)
    python -m leadgen enrich             # re-visit stored brands' public pages
    python -m leadgen export              # write CSV / XLSX / Markdown
    python -m leadgen stats              # counts and score distribution
    python -m leadgen validate           # fail if any record has unsourced data
"""

from __future__ import annotations

import argparse
import os
import sys

from . import pipeline, queries
from .discovery import build_provider
from .models import NOT_FOUND
from .store import LeadStore

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STORE = os.path.join(HERE, "data", "leads.json")
DEFAULT_OUT = os.path.join(HERE, "data")


def _print_exports(paths: dict) -> None:
    for kind, path in paths.items():
        if path:
            print(f"  {kind:9s} {path}")
        else:
            print(f"  {kind:9s} skipped (install openpyxl to enable)")


def cmd_rebuild(args: argparse.Namespace) -> int:
    store = LeadStore(args.store)
    leads = store.load()
    if not leads:
        print(f"No leads in {args.store}", file=sys.stderr)
        return 1
    report = pipeline.RunReport()
    final = pipeline.refine(leads, report=report)
    store.save(final)
    _print_exports(pipeline.export_all(final, args.out))
    print(report.as_text())
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    provider = build_provider()
    if provider is None:
        print(
            "No search provider configured. Set SERPAPI_KEY or BRAVE_SEARCH_API_KEY.",
            file=sys.stderr,
        )
        return 2
    query_list = queries.CORE_QUERIES if args.core_only else queries.all_queries()
    if args.max_queries:
        query_list = query_list[: args.max_queries]

    print(f"Running {len(query_list)} discovery queries via "
          f"{type(provider).__name__}...")
    final, report = pipeline.run(
        provider,
        store_path=args.store,
        query_list=query_list,
        limit_per_query=args.limit,
        do_enrich=not args.no_enrich,
        verbose=True,
    )
    print(report.as_text())
    _print_exports(pipeline.export_all(final, args.out))
    return 0


def cmd_enrich(args: argparse.Namespace) -> int:
    store = LeadStore(args.store)
    leads = store.load()
    if not leads:
        print(f"No leads in {args.store}", file=sys.stderr)
        return 1
    targets = [l for l in leads if args.all or l.contact_email == NOT_FOUND]
    print(f"Re-visiting {len(targets)} brand sites...")
    pipeline.enrich(targets, on_lead=lambda l: print(f"  {l.brand_name}: "
                                                     f"{l.contact_email}"))
    final = pipeline.refine(leads)
    store.save(final)
    _print_exports(pipeline.export_all(final, args.out))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    leads = LeadStore(args.store).load()
    if not leads:
        print(f"No leads in {args.store}", file=sys.stderr)
        return 1
    _print_exports(pipeline.export_all(leads, args.out))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    stats = LeadStore(args.store).stats()
    width = max(len(k) for k in stats)
    for key, value in stats.items():
        print(f"{key.replace('_', ' '):<{width}} : {value}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    leads = LeadStore(args.store).load()
    problems = [(l.brand_name, l.validate()) for l in leads]
    problems = [(name, p) for name, p in problems if p]
    if not problems:
        print(f"OK — {len(leads)} leads, every asserted field carries a source.")
        return 0
    for name, issues in problems:
        print(f"{name}:")
        for issue in issues:
            print(f"  - {issue}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="leadgen", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--store", default=DEFAULT_STORE, help="lead JSON store path")
    parser.add_argument("--out", default=DEFAULT_OUT, help="export directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("rebuild", help="re-score and re-export stored leads").set_defaults(
        func=cmd_rebuild)

    p_discover = sub.add_parser("discover", help="live search run")
    p_discover.add_argument("--limit", type=int, default=20, help="results per query")
    p_discover.add_argument("--max-queries", type=int, default=0,
                            help="cap the query bank (0 = no cap)")
    p_discover.add_argument("--core-only", action="store_true",
                            help="run only the brief's core queries")
    p_discover.add_argument("--no-enrich", action="store_true",
                            help="skip visiting brand sites")
    p_discover.set_defaults(func=cmd_discover)

    p_enrich = sub.add_parser("enrich", help="re-visit stored brands' public pages")
    p_enrich.add_argument("--all", action="store_true",
                          help="re-visit every lead, not just those missing an email")
    p_enrich.set_defaults(func=cmd_enrich)

    sub.add_parser("export", help="write CSV/XLSX/Markdown").set_defaults(func=cmd_export)
    sub.add_parser("stats", help="counts and score distribution").set_defaults(func=cmd_stats)
    sub.add_parser("validate", help="fail on unsourced data").set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
