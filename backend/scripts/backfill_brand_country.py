"""Backfill `market` and `stripe_country` on brands that predate the
decoupled marketplace-vs-Stripe identity refactor (2026-08).

All existing brands operated as UK, registered in the UK, so the defaults
`market="UK"` + `stripe_country="GB"` match their real-world state and
won't break any downstream reads.

Safe to run repeatedly — only touches docs missing the field.
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")


async def go() -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    market_res = await db.brands.update_many(
        {"market": {"$exists": False}},
        {"$set": {"market": "UK"}},
    )
    country_res = await db.brands.update_many(
        {"stripe_country": {"$exists": False}},
        {"$set": {"stripe_country": "GB"}},
    )
    # Applications not yet approved should also get the fields so downstream
    # approval reads have consistent shape.
    app_market = await db.brand_applications.update_many(
        {"market": {"$exists": False}},
        {"$set": {"market": "UK"}},
    )
    app_country = await db.brand_applications.update_many(
        {"stripe_country": {"$exists": False}},
        {"$set": {"stripe_country": "GB"}},
    )

    print(
        f"brands: market={market_res.modified_count} stripe_country={country_res.modified_count} | "
        f"applications: market={app_market.modified_count} stripe_country={app_country.modified_count}"
    )


if __name__ == "__main__":
    asyncio.run(go())
