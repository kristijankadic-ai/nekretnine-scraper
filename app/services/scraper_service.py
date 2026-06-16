import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import or_

from app.filters.agency_filter import AgencyFilter
from app.models import Listing, ScrapeRun, db, utcnow
from app.scrapers.base import ScrapedListing
from app.scrapers.google_search import GoogleSearchScraper
from app.scrapers.halooglasi import HalooglasiScraper
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class ScraperService:
    def __init__(self):
        self.halooglasi = HalooglasiScraper()
        self.google = GoogleSearchScraper()
        self.agency_filter = AgencyFilter()
        self.email_service = EmailService()

    def run_full_scrape(self, send_notifications: bool = True) -> dict:
        summary = {"halooglasi": {}, "google": {}, "new_listings": 0}

        halo_result = self._scrape_source("halooglasi", self.halooglasi.scrape(), send_notifications)
        summary["halooglasi"] = halo_result

        google_result = self._scrape_source("google", self.google.scrape(), send_notifications)
        summary["google"] = google_result

        summary["new_listings"] = halo_result["new_count"] + google_result["new_count"]
        return summary

    def _scrape_source(
        self,
        source_name: str,
        scraped: List[ScrapedListing],
        send_notifications: bool,
    ) -> dict:
        run = ScrapeRun(source=source_name, status="running")
        db.session.add(run)
        db.session.commit()

        owner_listings = self.agency_filter.filter_owner_listings(scraped)
        new_listings: List[Listing] = []

        try:
            for item in owner_listings:
                listing, is_new = self._upsert_listing(item)
                if is_new:
                    new_listings.append(listing)

            if send_notifications and new_listings:
                sent = self.email_service.send_new_listings_notification(new_listings)
                if sent:
                    for listing in new_listings:
                        listing.is_notified = True

            run.found_count = len(scraped)
            run.new_count = len(new_listings)
            run.status = "success"
            run.finished_at = utcnow()
            run.message = f"Filtered to {len(owner_listings)} owner listings"
            db.session.commit()

            return {
                "found": len(scraped),
                "owner_listings": len(owner_listings),
                "new_count": len(new_listings),
                "status": "success",
            }
        except Exception as exc:
            logger.exception("Scrape failed for %s", source_name)
            run.status = "error"
            run.finished_at = utcnow()
            run.message = str(exc)
            db.session.commit()
            return {"found": 0, "owner_listings": 0, "new_count": 0, "status": "error", "error": str(exc)}

    def _upsert_listing(self, item: ScrapedListing) -> Tuple[Listing, bool]:
        existing = Listing.query.filter_by(external_id=item.external_id).first()
        if existing:
            existing.title = item.title
            existing.url = item.url
            existing.price = item.price
            existing.price_text = item.price_text
            existing.area = item.area
            existing.rooms = item.rooms
            existing.floor = item.floor
            existing.location = item.location
            existing.advertiser_type = item.advertiser_type
            existing.description = item.description
            existing.image_url = item.image_url
            existing.is_agency = item.is_agency
            existing.scraped_at = utcnow()
            db.session.commit()
            return existing, False

        published_at = None
        if item.published_at:
            try:
                published_at = datetime.fromisoformat(item.published_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                published_at = None

        listing = Listing(
            external_id=item.external_id,
            source=item.source,
            title=item.title,
            url=item.url,
            price=item.price,
            price_text=item.price_text,
            area=item.area,
            rooms=item.rooms,
            floor=item.floor,
            location=item.location,
            advertiser_type=item.advertiser_type,
            description=item.description,
            image_url=item.image_url,
            is_agency=item.is_agency,
            published_at=published_at,
        )
        db.session.add(listing)
        db.session.commit()
        return listing, True

    def query_listings(
        self,
        source: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_area: Optional[float] = None,
        max_area: Optional[float] = None,
        min_rooms: Optional[float] = None,
        max_rooms: Optional[float] = None,
        location: Optional[str] = None,
        search: Optional[str] = None,
        owners_only: bool = True,
        sort: str = "scraped_at",
        order: str = "desc",
        page: int = 1,
        per_page: int = 20,
    ):
        query = Listing.query

        if owners_only:
            query = query.filter(Listing.is_agency.is_(False))

        if source:
            query = query.filter(Listing.source == source)

        if min_price is not None:
            query = query.filter(Listing.price >= min_price)
        if max_price is not None:
            query = query.filter(Listing.price <= max_price)
        if min_area is not None:
            query = query.filter(Listing.area >= min_area)
        if max_area is not None:
            query = query.filter(Listing.area <= max_area)
        if min_rooms is not None:
            query = query.filter(Listing.rooms >= min_rooms)
        if max_rooms is not None:
            query = query.filter(Listing.rooms <= max_rooms)
        if location:
            query = query.filter(Listing.location.ilike(f"%{location}%"))
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Listing.title.ilike(pattern),
                    Listing.description.ilike(pattern),
                    Listing.location.ilike(pattern),
                )
            )

        sort_column = getattr(Listing, sort, Listing.scraped_at)
        if order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        return query.paginate(page=page, per_page=per_page, error_out=False)

    def get_stats(self) -> dict:
        total = Listing.query.filter(Listing.is_agency.is_(False)).count()
        halo = Listing.query.filter(Listing.source == "halooglasi", Listing.is_agency.is_(False)).count()
        google = Listing.query.filter(Listing.source == "google", Listing.is_agency.is_(False)).count()
        last_run = ScrapeRun.query.order_by(ScrapeRun.started_at.desc()).first()
        return {
            "total": total,
            "halooglasi": halo,
            "google": google,
            "last_scrape": last_run.finished_at.isoformat() if last_run and last_run.finished_at else None,
            "last_scrape_status": last_run.status if last_run else None,
        }
