"""Re-evaluate existing listings against the fixed agency filter and remove agency rows.

Run on Railway against the production DB with:
    railway run python cleanup_agencies.py
or locally:
    python cleanup_agencies.py
"""

import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from app import create_app
from app.filters.agency_filter import AgencyFilter
from app.models import Listing, db
from app.scrapers.base import ScrapedListing
from app.scrapers.oglasi_rs import OglasiRsScraper


def listing_to_scraped(listing: Listing) -> ScrapedListing:
    return ScrapedListing(
        external_id=listing.external_id,
        source=listing.source,
        title=listing.title,
        url=listing.url,
        description=listing.description,
        advertiser_type=listing.advertiser_type,
        is_agency=False,
        raw_text=f"{listing.title or ''} {listing.description or ''} {listing.advertiser_type or ''}",
    )


def main():
    app = create_app()
    scraper = OglasiRsScraper()
    agency_filter = AgencyFilter()

    with app.app_context():
        rows = Listing.query.all()
        logger.info("Provera %d postojecih oglasa", len(rows))

        deleted = 0
        flagged = 0
        for row in rows:
            scraped = listing_to_scraped(row)

            # Use the dedicated cite-based heuristic when available (oglasi_rs).
            if row.source == "oglasi_rs" and row.advertiser_type:
                scraped.is_agency = scraper._je_agencija(row.advertiser_type)

            is_agency = agency_filter.is_agency(scraped)

            if is_agency:
                flagged += 1
                db.session.delete(row)
                deleted += 1

        db.session.commit()
        logger.info("Obrisano %d agencijskih oglasa (od %d pregledanih, flagged=%d)", deleted, len(rows), flagged)


if __name__ == "__main__":
    main()
