# Network Effects Command Center — the growth engine

Marketplace growth intelligence for Unveiled Threads, served at
`/admin/growth`. It answers three questions in order: **which loop is
broken**, **what to do about it**, and **what happens if you pull each
lever**.

## Why it is built this way

The engine is layered strictly so that judgment can be tested without
infrastructure. Everything except `collector.py` is stdlib-only and
side-effect free.

| Module | Job |
| --- | --- |
| `benchmarks.py` | Metric bands and stage gates, each with the reasoning behind the number. Argue with these first — they are the opinions. |
| `metrics.py` | Pure formulas over plain data: liquidity, cross-side balance, network density, concentration, K-factor, cohorts, atomic cell. |
| `diagnostics.py` | Six loop scores, named failure modes, stage sequencing, confidence. |
| `playbook.py` | The play library: triggers, mechanism, steps, expected impact, ICE, kill criteria — sequenced into now / next / not yet. |
| `simulator.py` | The flywheel model, with its feedback loops closed. |
| `narrative.py` | The executive memo. Deterministic, so week-on-week diffs mean something. |
| `collector.py` | The only module that touches Mongo. |

## Running the tests

No database, no server, no network:

```bash
cd backend && python -m pytest growth/tests -q
```

The suite builds synthetic marketplaces (`growth/tests/factory.py`) — "eight
brands where buyers never cross between them", "supply that outnumbers demand
forty to one" — and asserts the engine reaches the right diagnosis.

The endpoint tests in `backend/tests/test_growth_endpoints.py` are integration
tests and need a live server, like the rest of that directory.

## Two conventions worth keeping

**`None` is not zero.** A metric that cannot be measured returns `None` and
renders as an em dash. A dashboard that reports a confident `0%` conversion
for a week with no traffic is worse than one that admits it does not know —
and an unmeasurable stage gate never counts as passed.

**Sequencing is the product.** Any tool can rank plays by ICE. The value here
is refusing to recommend a stage-4 play to a stage-1 business, and saying out
loud what to stop doing. If you change one thing, change the bands in
`benchmarks.py` to match your own read of the market — not the gate order.

## Known limits

- **No acquisition attribution exists in the schema.** Organic-vs-paid share,
  blended CAC and channel LTV are therefore unmeasurable. The engine reports
  this as its top coverage gap rather than guessing.
- Benchmarks are calibrated for a **curated marketplace of independent
  brands**, not C2C resale. A peer-to-peer site where every user also lists
  carries roughly ten times the listings-per-buyer ratio.
- The simulator is a thinking tool, not a forecast. Read the shape and the
  ranking of scenarios; ignore the decimals.
