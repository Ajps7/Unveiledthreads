"""Tests for the lead-generation pipeline.

The tests that matter most here are the data-integrity ones: the whole value of
this dataset is that nothing in it is invented, so the guard rails against
unsourced values, broker-derived emails and non-UK/major brands are tested
directly rather than assumed.
"""

import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from leadgen import dedup, filters, outreach, queries, scoring, store  # noqa: E402
from leadgen.discovery import SearchResult, StaticProvider, candidates_from_results  # noqa: E402
from leadgen.extract import SiteEvidence, apply_evidence, extract_emails, parse_page  # noqa: E402
from leadgen.models import Lead, Signals, NOT_FOUND, load_leads  # noqa: E402
from leadgen.pipeline import FLAG_UK, RunReport, refine  # noqa: E402
from leadgen.seed import seed_leads  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "leadgen", "data")
LEADS_JSON = os.path.join(DATA_DIR, "leads.json")


# --------------------------------------------------------------------------
# Data integrity — the non-fabrication guarantees
# --------------------------------------------------------------------------

def test_shipped_dataset_validates():
    """Every asserted field in the shipped dataset carries a source URL."""
    problems = {l.brand_name: l.validate() for l in load_leads(LEADS_JSON)}
    assert not {k: v for k, v in problems.items() if v}


def test_seed_dataset_validates():
    assert not [p for l in seed_leads() for p in l.validate()]


def test_missing_data_is_not_found_never_blank_or_invented():
    for lead in load_leads(LEADS_JSON):
        for field in ("website", "instagram_handle", "contact_email", "founder_owner",
                      "uk_location", "instagram_followers", "contact_page"):
            value = getattr(lead, field)
            assert value, f"{lead.brand_name}.{field} is empty rather than '{NOT_FOUND}'"


def test_no_email_sourced_from_a_people_search_broker():
    """Broker-derived addresses are guesses; they must never reach the dataset."""
    for lead in load_leads(LEADS_JSON):
        source = lead.sources.get("contact_email", "")
        assert not filters.is_email_broker(source), (
            f"{lead.brand_name} sourced its email from a broker: {source}")


def test_validate_rejects_a_value_without_a_source():
    lead = Lead(brand_name="Ghost Brand", contact_email="hi@ghost.example")
    assert any("no source URL" in p for p in lead.validate())


def test_validate_rejects_a_malformed_email_and_mismatched_handle():
    lead = Lead(
        brand_name="Bad Data",
        contact_email="not-an-email",
        instagram_handle="@realhandle",
        instagram_url="https://www.instagram.com/differenthandle/",
        sources={"contact_email": "https://example.com", "instagram_handle": "https://x.co"},
    )
    problems = " ".join(lead.validate())
    assert "not a valid address" in problems
    assert "does not match" in problems


def test_follower_count_must_be_numeric_not_prose():
    lead = Lead(brand_name="Vague", instagram_followers="lots",
                sources={"instagram_followers": "https://example.com"})
    assert any("must be a number" in p for p in lead.validate())


# --------------------------------------------------------------------------
# Exclusions
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["Corteiz", "Palace", "ASOS", "Represent", "boohoo"])
def test_major_brands_are_excluded(name):
    excluded, reason = filters.evaluate_exclusions(
        Lead(brand_name=name, website="https://example.co.uk/"))
    assert excluded and "Major" in reason


def test_publisher_and_broker_hosts_are_not_treated_as_brands():
    for url in ("https://hypebeast.com/2023/8/feature",
                "https://en.wikipedia.org/wiki/Bench",
                "https://rocketreach.co/forty-clothing"):
        excluded, reason = filters.evaluate_exclusions(
            Lead(brand_name="Something", website=url, uk_location="London"))
        assert excluded, url
        assert "Not a brand site" in reason


def test_foreign_cctld_is_excluded_but_uk_tld_is_kept():
    overseas = Lead(brand_name="Tokyo Label", website="https://example.jp/")
    assert filters.evaluate_exclusions(overseas)[0]

    british = Lead(brand_name="Real Label", website="https://example.co.uk/")
    assert not filters.evaluate_exclusions(british)[0]


def test_uk_location_rescues_a_dot_com_brand():
    lead = Lead(brand_name="Dot Com Label", website="https://example.com/",
                uk_location="Bristol")
    assert filters.uk_status(lead) == filters.UK_CONFIRMED
    assert not filters.evaluate_exclusions(lead)[0]


def test_unverified_dot_com_candidate_is_kept_and_flagged_not_silently_dropped():
    """Unverified is not the same as disproved — a fresh candidate on a generic
    TLD must survive to the enrichment pass, carrying a visible warning."""
    lead = Lead(brand_name="Unknown Origin", website="https://example.com/")
    assert filters.uk_status(lead) == filters.UK_UNCONFIRMED
    assert not filters.evaluate_exclusions(lead)[0]

    report = RunReport()
    kept = refine([lead], report=report)
    assert [l.brand_name for l in kept] == ["Unknown Origin"]
    assert FLAG_UK in kept[0].notes
    assert report.unconfirmed_uk == ["Unknown Origin"]


def test_uk_flag_is_not_appended_twice_across_reruns():
    lead = Lead(brand_name="Unknown Origin", website="https://example.com/")
    refine([lead])
    refine([lead])
    assert lead.notes.count(FLAG_UK) == 1


def test_inactive_and_over_distributed_brands_are_excluded():
    inactive = Lead(brand_name="Gone", website="https://gone.co.uk/",
                    signals=Signals(instagram_active=False, has_ecommerce=False))
    assert "Inactive" in filters.evaluate_exclusions(inactive)[1]

    saturated = Lead(brand_name="Everywhere", website="https://everywhere.co.uk/",
                     signals=Signals(marketplace_count=15))
    assert "wide marketplace distribution" in filters.evaluate_exclusions(saturated)[1]


def test_shipped_dataset_contains_no_excluded_brand():
    for lead in load_leads(LEADS_JSON):
        assert not filters.evaluate_exclusions(lead)[0], lead.brand_name


# --------------------------------------------------------------------------
# Deduplication
# --------------------------------------------------------------------------

def test_duplicates_merge_on_host_handle_and_name():
    records = [
        Lead(brand_name="MKI", website="https://www.mkistore.co.uk/"),
        Lead(brand_name="MKI MIYUKI ZOKU®", website="https://mkistore.co.uk/pages/contact",
             contact_email="info@mkistore.com",
             sources={"contact_email": "https://mkistore.co.uk/pages/contact"}),
        Lead(brand_name="Totally Different", website="https://other.co.uk/"),
    ]
    merged = dedup.deduplicate(records)
    assert len(merged) == 2
    assert merged[0].contact_email == "info@mkistore.com"
    # The fuller trading name wins.
    assert "MIYUKI" in merged[0].brand_name


def test_shopify_mirror_collapses_onto_the_brand_domain():
    assert dedup.normalise_host("https://forty.myshopify.com/") == "forty"
    assert dedup.normalise_host("https://fortyclothing.com/") == "fortyclothing"


def test_merge_never_overwrites_an_existing_evidenced_value():
    base = Lead(brand_name="A", contact_email="real@brand.co.uk",
                sources={"contact_email": "https://brand.co.uk/contact"})
    other = Lead(brand_name="A", contact_email="wrong@elsewhere.com",
                 sources={"contact_email": "https://elsewhere.com"})
    merged = dedup.merge(base, other)
    assert merged.contact_email == "real@brand.co.uk"
    assert merged.sources["contact_email"] == "https://brand.co.uk/contact"


def test_shipped_dataset_has_no_duplicates():
    leads = load_leads(LEADS_JSON)
    assert len(dedup.deduplicate(leads)) == len(leads)


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def test_weights_total_one_hundred():
    assert sum(scoring.WEIGHTS.values()) == 100


def test_ideal_brand_scores_full_marks():
    ideal = Signals(
        instagram_active=True, instagram_professional=True, follower_count=25_000,
        releases_collections=True, has_ecommerce=True, independent_positioning=True,
        strong_visual_branding=True, price_range_gbp=(25, 180), marketplace_count=0,
        has_public_contact=True,
    )
    lead = Lead(brand_name="Ideal", contact_email="hi@ideal.co.uk",
                sources={"contact_email": "https://ideal.co.uk"}, signals=ideal)
    scoring.score_lead(lead)
    assert lead.lead_score == 100
    assert lead.priority == scoring.PRIORITY_HIGH


def test_unknown_scores_between_verified_bad_and_verified_good():
    def score(signals):
        return scoring.score_lead(Lead(brand_name="x", contact_page="https://x.co.uk/c",
                                       sources={}, signals=signals)).lead_score

    good = score(Signals(instagram_active=True, instagram_professional=True,
                         has_ecommerce=True, independent_positioning=True))
    unknown = score(Signals())
    bad = score(Signals(instagram_active=False, instagram_professional=False,
                        has_ecommerce=False, independent_positioning=False))
    assert bad < unknown < good


def test_follower_sweet_spot_beats_both_extremes():
    def follower_points(n):
        return scoring.score_breakdown(Signals(follower_count=n))["follower_fit"]

    assert follower_points(20_000) == scoring.WEIGHTS["follower_fit"]
    assert follower_points(20_000) > follower_points(500_000)
    assert follower_points(20_000) > follower_points(50)
    assert follower_points(150_000) < follower_points(20_000)


def test_marketplace_breadth_scores_inversely():
    points = lambda n: scoring.score_breakdown(  # noqa: E731
        Signals(marketplace_count=n))["marketplace_headroom"]
    assert points(0) > points(2) > points(4) > points(10)


def test_price_band_outside_twenty_to_two_hundred_scores_lower():
    inside = scoring.score_breakdown(Signals(price_range_gbp=(25, 150)))["price_fit"]
    outside = scoring.score_breakdown(Signals(price_range_gbp=(400, 900)))["price_fit"]
    assert inside == scoring.WEIGHTS["price_fit"]
    assert outside == 0


def test_uncontactable_lead_cannot_reach_high_priority():
    great = Signals(
        instagram_active=True, instagram_professional=True, follower_count=25_000,
        releases_collections=True, has_ecommerce=True, independent_positioning=True,
        strong_visual_branding=True, price_range_gbp=(25, 180), marketplace_count=0,
        has_public_contact=True,
    )
    lead = Lead(brand_name="Unreachable", signals=great)
    scoring.score_lead(lead)
    assert lead.lead_score <= 69
    assert lead.priority != scoring.PRIORITY_HIGH


def test_scores_stay_within_one_to_one_hundred():
    for lead in load_leads(LEADS_JSON):
        assert 1 <= lead.lead_score <= 100
        assert lead.priority in (scoring.PRIORITY_HIGH, scoring.PRIORITY_MEDIUM,
                                 scoring.PRIORITY_LOW)


def test_ranking_is_descending():
    leads = load_leads(LEADS_JSON)
    assert [l.lead_score for l in leads] == sorted(
        (l.lead_score for l in leads), reverse=True)


# --------------------------------------------------------------------------
# Discovery and extraction
# --------------------------------------------------------------------------

def test_candidates_skip_publisher_results_and_keep_brand_sites():
    results = [
        SearchResult(title="Best UK brands | Hypebeast",
                     url="https://hypebeast.com/2023/8/list"),
        SearchResult(title="FORTY Clothing | Glasgow Streetwear",
                     url="https://fortyclothing.com/pages/about"),
    ]
    candidates = candidates_from_results(results)
    assert [c.brand_name for c in candidates] == ["FORTY Clothing"]
    assert candidates[0].website == "https://fortyclothing.com/"


def test_static_provider_replays_recorded_results():
    provider = StaticProvider({"uk streetwear": [
        SearchResult(title="Brand | Shop", url="https://brand.co.uk/")]})
    assert len(provider.search("uk streetwear")) == 1
    assert provider.search("unseen query") == []


def test_extract_emails_ignores_placeholders_and_asset_filenames():
    html = """
      <a href="mailto:info@brand.co.uk">email us</a>
      <img src="logo@2x.png">
      <p>you@example.com and noreply@brand.co.uk</p>
    """
    assert extract_emails(html) == ["info@brand.co.uk"]


def test_parse_page_reads_instagram_ecommerce_prices_and_marketplaces():
    html = """
      <a href="https://www.instagram.com/p/abc123/">post</a>
      <a href="https://www.instagram.com/brandhandle/">follow us</a>
      <button>Add to cart</button>
      <span>£45.00</span><span>£90.00</span><span>£120.00</span><span>£65.00</span>
      <p>We are a small independent label. Also stocked at wolfandbadger.com</p>
    """
    evidence = parse_page(html, "https://brand.co.uk/", SiteEvidence())
    # /p/ is a post permalink, not the account handle.
    assert evidence.instagram_handle == "brandhandle"
    assert evidence.has_ecommerce is True
    assert evidence.independent_language is True
    assert "Wolf & Badger" in evidence.marketplaces
    assert evidence.price_range() is not None


def test_apply_evidence_prefers_a_role_address_on_the_brand_domain():
    evidence = SiteEvidence(
        emails=["someone@gmail.com", "info@brand.co.uk"],
        contact_page="https://brand.co.uk/pages/contact",
    )
    lead = Lead(brand_name="Brand", website="https://brand.co.uk/")
    apply_evidence(lead, evidence)
    assert lead.contact_email == "info@brand.co.uk"
    assert lead.evidence["contact_email"] == "direct"


def test_apply_evidence_does_not_overwrite_verified_fields():
    lead = Lead(brand_name="Brand", website="https://brand.co.uk/",
                contact_email="verified@brand.co.uk")
    apply_evidence(lead, SiteEvidence(emails=["other@brand.co.uk"]))
    assert lead.contact_email == "verified@brand.co.uk"


# --------------------------------------------------------------------------
# Queries
# --------------------------------------------------------------------------

def test_every_query_from_the_brief_is_in_the_bank():
    bank = queries.all_queries()
    for required in queries.CORE_QUERIES:
        assert required in bank


def test_query_bank_is_deduplicated_and_covers_the_named_cities():
    bank = queries.all_queries()
    assert len(bank) == len(set(bank))
    for city in ("London", "Manchester", "Birmingham", "Bristol", "Leeds"):
        assert any(city in q for q in bank)


def test_verification_queries_never_target_email_finding_services():
    joined = " ".join(queries.verification_queries("Some Brand", "brand.co.uk")).lower()
    for broker in ("rocketreach", "hunter.io", "signalhire", "email format"):
        assert broker not in joined


# --------------------------------------------------------------------------
# Outreach notes
# --------------------------------------------------------------------------

def test_every_lead_has_a_substantive_outreach_note():
    for lead in load_leads(LEADS_JSON):
        note = lead.outreach_note.strip()
        assert len(note) > 80, f"{lead.brand_name} has a stub outreach note"


def test_generated_notes_name_the_brand():
    """Generated notes stand alone, so they must identify the brand. Hand-written
    notes sit in the spreadsheet row beside the Brand Name column and do not."""
    lead = Lead(brand_name="Alpha Label", uk_location="Leeds")
    assert "Alpha Label" in outreach.generate_note(lead)


def test_every_outreach_note_is_unique():
    leads = load_leads(LEADS_JSON)
    assert len({l.outreach_note for l in leads}) == len(leads)


def test_outreach_notes_are_specific_not_boilerplate():
    """No two notes may share their opening clause — that is the signature of a
    template being reused rather than a brand-specific reason."""
    openings = [l.outreach_note.split(",")[0].split(" — ")[0]
                for l in load_leads(LEADS_JSON)]
    assert len(set(openings)) == len(openings)


def test_every_seed_brand_has_a_hand_written_note():
    from leadgen.seed import OUTREACH_NOTES
    for lead in seed_leads():
        assert lead.brand_name in OUTREACH_NOTES, lead.brand_name


def test_generated_note_uses_the_strongest_available_hook():
    founder_led = Lead(brand_name="Alpha", founder_owner="Jo Smith", uk_location="Leeds")
    assert "Jo Smith" in outreach.generate_note(founder_led)

    no_marketplaces = Lead(brand_name="Beta", uk_location="Bristol",
                           signals=Signals(marketplace_count=0, has_ecommerce=True))
    assert "own site" in outreach.generate_note(no_marketplaces)


def test_hand_written_notes_survive_regeneration():
    lead = Lead(brand_name="Gamma", outreach_note="hand written")
    outreach.ensure_notes([lead])
    assert lead.outreach_note == "hand written"


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------

def test_csv_columns_match_the_brief_exactly_and_in_order():
    required = [
        "Brand Name", "Website", "Instagram Handle", "Instagram URL", "Contact Email",
        "Founder/Owner", "Founder Contact/Profile", "UK Location", "Category",
        "Instagram Followers", "Ecommerce Website", "Existing Marketplaces",
        "Lead Score", "Priority", "Contact Page", "Source URLs", "Notes",
    ]
    assert store.COLUMNS[:len(required)] == required
    assert "Outreach Note" in store.COLUMNS


def test_exported_csv_round_trips(tmp_path):
    leads = load_leads(LEADS_JSON)
    path = store.export_csv(leads, str(tmp_path / "out.csv"))
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(leads)
    assert list(rows[0]) == store.COLUMNS
    assert rows[0]["Brand Name"] == leads[0].brand_name
    for row in rows:
        assert row["Priority"] in ("HIGH PRIORITY", "MEDIUM PRIORITY", "LOW PRIORITY")
        assert row["Contact Email"]  # never blank; "Not found" when absent


def test_store_upsert_is_idempotent(tmp_path):
    path = str(tmp_path / "leads.json")
    lead_store = store.LeadStore(path)
    batch = [Lead(brand_name="Alpha", website="https://alpha.co.uk/")]
    lead_store.upsert(batch)
    lead_store.upsert([Lead(brand_name="Alpha", website="https://alpha.co.uk/")])
    assert len(lead_store.load()) == 1


def test_refine_deduplicates_before_excluding():
    """A stub missing its location must not be dropped as non-UK when a sibling
    record proves the location."""
    stub = Lead(brand_name="Split Brand", website="https://splitbrand.com/")
    detail = Lead(brand_name="Split Brand", website="https://splitbrand.com/",
                  uk_location="Sheffield",
                  sources={"uk_location": "https://splitbrand.com/about"})
    kept = refine([stub, detail])
    assert [l.brand_name for l in kept] == ["Split Brand"]


# --------------------------------------------------------------------------
# Dataset shape
# --------------------------------------------------------------------------

def test_dataset_covers_multiple_uk_regions():
    locations = " ".join(l.uk_location for l in load_leads(LEADS_JSON))
    for city in ("Birmingham", "Manchester", "Leeds", "Glasgow", "London", "Bristol"):
        assert city in locations


def test_dataset_includes_verified_emails_and_founders():
    leads = load_leads(LEADS_JSON)
    assert sum(1 for l in leads if l.contact_email != NOT_FOUND) >= 5
    assert sum(1 for l in leads if l.founder_owner != NOT_FOUND) >= 10
