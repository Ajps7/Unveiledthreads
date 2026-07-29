# UnveiledThreads — UK independent brand lead generation

Discovers independent UK clothing and streetwear brands, collects their
**publicly published** contact details, scores each brand 1-100 for fit with an
independent-UK-fashion marketplace, and exports a prospect spreadsheet.

## The one rule

**A field is either evidenced with a source URL, or it is `"Not found"`.**

Nothing is inferred, interpolated or pattern-guessed. Concretely:

- Email-pattern services (RocketReach, SignalHire, ZoomInfo, ContactOut,
  Hunter.io …) are blocklisted in `filters.EMAIL_BROKER_HOSTS` and asserted
  against in the tests. Those services sell *inferred* addresses; publishing one
  as a brand's contact email is guessing a private address.
- Follower counts are recorded only where a source states a figure.
- Founder names are recorded only where publicly attached to the business.
- `Lead.validate()` fails any record that asserts a value without a source URL,
  and `python -m leadgen validate` exits non-zero if the dataset drifts.

Only public pages are read. `extract.Fetcher` sends a self-identifying
User-Agent, honours `robots.txt` and rate-limits per host. Nothing logs in,
reads private accounts or works around an access control.

## Layout

| Module | Responsibility |
|---|---|
| `models.py` | `Lead` / `Signals`, the `Not found` sentinel, validation, JSON I/O |
| `queries.py` | Discovery query bank — the brief's queries plus city/category/platform expansions |
| `discovery.py` | Pluggable search providers (SerpAPI, Brave, static replay) → candidate stubs |
| `extract.py` | Polite fetcher + parser for emails, socials, ecommerce, prices, marketplaces |
| `filters.py` | Exclusions: major brands, publishers/retailers/brokers, non-UK, dropship, inactive |
| `dedup.py` | Identity resolution on host → Instagram handle → normalised name, plus merging |
| `scoring.py` | 1-100 score across nine weighted criteria, priority banding |
| `outreach.py` | Evidence-grounded personalised outreach note per brand |
| `store.py` | JSON store with idempotent upsert; CSV / XLSX / Markdown export |
| `pipeline.py` | Orchestration: discover → enrich → dedupe → exclude → score → export |
| `seed.py` | The verified starting dataset, with per-field provenance |

## Usage

```bash
cd backend

python -m leadgen stats                 # counts and score distribution
python -m leadgen validate              # non-zero exit if any field lacks a source
python -m leadgen rebuild               # re-score and re-export the stored leads
python -m leadgen export                # write CSV / XLSX / Markdown

# Live discovery — needs a search API key
export SERPAPI_KEY=...                  # or BRAVE_SEARCH_API_KEY
python -m leadgen discover --limit 20
python -m leadgen discover --core-only  # just the brief's 13 seed queries

# Re-visit brand sites to fill in "Not found" fields
python -m leadgen enrich --all
```

Runs accumulate: `LeadStore.upsert` merges new findings into the existing
records without overwriting anything already evidenced, so the database improves
over time rather than being rebuilt from scratch.

## Scoring

Weights total 100 and map onto the brief's criteria:

| Criterion | Weight |
|---|---|
| Professional, active Instagram | 15 |
| Follower band (~1k-100k is the sweet spot) | 15 |
| Functioning own-site ecommerce | 15 |
| Clear independent positioning | 12 |
| Regular new collections / drops | 10 |
| Marketplace headroom (scored **inversely**) | 10 |
| Strong visual branding | 8 |
| Price band ~£20-£200 | 8 |
| Published contact route | 7 |

Two calibrations worth knowing:

- **Unknown earns a third of the weight**, not zero. Scoring unverified
  criteria as zero would make the ranking a measure of our research effort
  rather than of brand fit. A brand we have not finished researching should sit
  below a verified-good brand and above a verified-bad one.
- **A brand with no contact route is capped at 69**, so it cannot reach HIGH
  PRIORITY however good it looks — it is not yet actionable.

Bands: **HIGH** ≥ 75 · **MEDIUM** 55-74 · **LOW** < 55.

## Output

`data/leads.json` is the database. Exports land next to it:

- `uk_independent_brand_leads.csv`
- `uk_independent_brand_leads.xlsx` (needs `openpyxl`; priority-colour-coded)
- `uk_independent_brand_leads.md` (human review sheet)

Columns are fixed by the brief and asserted in the tests, with `Outreach Note`
and `Last Verified` appended.

## Tests

```bash
cd backend && python -m pytest tests/test_leadgen.py -q
```

## Known gap in the shipped dataset

The seed dataset was compiled from **search-engine results only**. The session
that built it had outbound HTTPS blocked by egress policy, so brand sites could
not be visited and the `extract` enrichment pass never ran. That is why many
records show `Not found` for Instagram handles, follower counts and emails that
are very likely published on the brands' own contact pages.

Running `python -m leadgen enrich --all` from an environment with network access
will fill those gaps and materially raise several scores — most of the LOW
PRIORITY entries are low because of missing verification, not because the brand
is a poor fit. Each such record says so in its `Notes`.
