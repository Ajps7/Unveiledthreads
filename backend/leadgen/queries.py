"""The discovery query bank.

`CORE_QUERIES` are the seed searches named in the brief. The rest are
expansions: running the same intent across UK cities and product categories is
what actually surfaces small brands, because the generic national queries are
dominated by listicles about Corteiz and Palace.
"""

from __future__ import annotations

# Verbatim from the brief — kept as its own list so it is obvious they all run.
CORE_QUERIES: list[str] = [
    "UK independent streetwear brand",
    "independent clothing brands UK",
    "emerging UK streetwear brands",
    "British independent fashion brands",
    "UK clothing brand Instagram",
    "UK streetwear Shopify",
    "London independent streetwear brand",
    "Manchester streetwear brand",
    "Birmingham independent clothing brand",
    "Bristol streetwear brand",
    "Leeds independent fashion brand",
    'site:instagram.com "UK streetwear"',
    "site:myshopify.com UK clothing brand",
]

# Cities beyond the five in the brief. Regional scenes are where the
# under-marketed, not-yet-signed brands live.
CITIES: list[str] = [
    "London", "Manchester", "Birmingham", "Bristol", "Leeds",
    "Glasgow", "Edinburgh", "Liverpool", "Newcastle", "Nottingham",
    "Sheffield", "Cardiff", "Brighton", "Belfast", "Leicester",
]

CITY_TEMPLATES: list[str] = [
    "{city} independent streetwear brand",
    "{city} independent clothing label founder",
    "{city} clothing brand own website drops",
]

CATEGORY_QUERIES: list[str] = [
    "independent UK menswear brand small label",
    "independent UK womenswear brand small label",
    "UK unisex clothing brand independent",
    "UK startup fashion brand launched own website",
    "Instagram-first UK clothing brand drops",
    "UK skatewear brand independent",
    "UK alternative streetwear brand independent",
    "UK sustainable independent clothing brand",
    "UK knitwear independent brand small batch",
    "UK graphic tee brand independent screen printed",
]

# Platform / directory sweeps.
PLATFORM_QUERIES: list[str] = [
    "site:myshopify.com streetwear UK",
    'site:instagram.com "independent clothing brand" UK',
    'site:instagram.com "UK streetwear brand"',
    'site:tiktok.com "UK streetwear brand"',
    'site:linkedin.com/in "founder" "streetwear" UK',
    "UK independent fashion brand directory",
    "British independent brand marketplace stockists",
    'site:find-and-update.company-information.service.gov.uk "clothing" streetwear',
]

# Editorial sources that reliably profile small UK labels.
EDITORIAL_QUERIES: list[str] = [
    "best independent UK streetwear brands to know",
    "emerging British streetwear brands you should know",
    "UK independent fashion brands to support",
    "new UK clothing brand founder interview",
    "hypebeast UK emerging brand feature",
    "brands to watch UK streetwear scene",
]


def all_queries() -> list[str]:
    """Full, de-duplicated query bank in run order."""
    queries: list[str] = list(CORE_QUERIES)
    for template in CITY_TEMPLATES:
        for city in CITIES:
            queries.append(template.format(city=city))
    queries.extend(CATEGORY_QUERIES)
    queries.extend(PLATFORM_QUERIES)
    queries.extend(EDITORIAL_QUERIES)

    seen: set[str] = set()
    ordered: list[str] = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            ordered.append(q)
    return ordered


def verification_queries(brand_name: str, website: str = "") -> list[str]:
    """Follow-up searches used to confirm a candidate's details.

    Deliberately does *not* include any "find the email of X" people-search
    query — those services sell inferred personal addresses, which is exactly
    what the brief rules out.
    """
    domain = website.replace("https://", "").replace("http://", "").strip("/")
    queries = [
        f'"{brand_name}" UK clothing brand founder',
        f'"{brand_name}" instagram',
        f'"{brand_name}" contact',
        f'"{brand_name}" based in UK studio',
    ]
    if domain:
        queries.append(f"site:{domain} contact")
        queries.append(f'"{domain}" stockists')
    return queries
