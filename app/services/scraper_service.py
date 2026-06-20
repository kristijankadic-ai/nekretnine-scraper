import logging
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import or_
from app.filters.agency_filter import AgencyFilter
from app.models import Listing, ScrapeRun, db, utcnow
from app.scrapers.base import ScrapedListing
from app.scrapers.oglasi_rs import OglasiRsScraper
from app.scrapers.cetirizida import CetiriZidaScraper
from app.scrapers.halooglasi import HalooglasiScraper
from app.services.email_service import EmailService
from app.services.lead_service import LeadService

logger = logging.getLogger(__name__)

class ScraperService:
    def __init__(self):
        self.oglasi_rs = OglasiRsScraper()
        self.cetirizida = CetiriZidaScraper()
        self.halooglasi = HalooglasiScraper()
        self.agency_filter = AgencyFilter()
        self.email_service = EmailService()
        self.lead_service = LeadService(self.email_service)

    def run_full_scrape(self, send_notifications: bool = True) -> dict:
        summary = {"oglasi_rs": {}, "4zida": {}, "halooglasi": {}, "new_listings": 0}
        all_new_listings = []

        oglasi_result, new = self._scrape_source("oglasi_rs", self.oglasi_rs.scrape(), send_notifications)
        summary["oglasi_rs"] = oglasi_result
        all_new_listings.extend(new)

        zida_result, new = self._scrape_source("4zida", self.cetirizida.scrape(), send_notifications)
        summary["4zida"] = zida_result
        all_new_listings.extend(new)

        halo_result, new = self._scrape_source("halooglasi", self.halooglasi.scrape(), send_notifications)
        summary["halooglasi"] = halo_result
        all_new_listings.extend(new)

        summary["new_listings"] = oglasi_result["new_count"] + zida_result["new_count"] + halo_result["new_count"]

        if send_notifications and all_new_listings:
            summary["leads_notified"] = self.lead_service.notify_matching_leads(all_new_listings)

        return summary

    def _scrape_source(self, source_name, scraped, send_notifications):
        run = ScrapeRun(source=source_name, status="running")
        db.session.add(run)
        db.session.commit()
        owner_listings = self.agency_filter.filter_owner_listings(scraped)
        new_listings = []
        try:
            for item in owner_listings:
                listing, is_new = self._upsert_listing(item)
                if is_new:
                    new_listings.append(listing)
            if send_notifications and new_listings:
                self.email_service.send_new_listings_notification(new_listings)
            run.found_count = len(scraped)
            run.new_count = len(new_listings)
            run.status = "success"
            run.finished_at = utcnow()
            db.session.commit()
            return {"found": len(scraped), "owner_listings": len(owner_listings), "new_count": len(new_listings), "status": "success"}, new_listings
        except Exception as exc:
            logger.exception("Scrape failed for %s", source_name)
            run.status = "error"
            run.finished_at = utcnow()
            run.message = str(exc)
            db.session.commit()
            return {"found": 0, "owner_listings": 0, "new_count": 0, "status": "error"}, []

    def _upsert_listing(self, item):
        existing = Listing.query.filter_by(external_id=item.external_id).first()
        if existing:
            existing.title = item.title
            existing.url = item.url
            existing.price = item.price
            existing.price_text = item.price_text
            existing.area = item.area
            existing.rooms = item.rooms
            existing.location = item.location
            existing.description = item.description
            existing.image_url = item.image_url
            existing.is_agency = item.is_agency
            existing.scraped_at = utcnow()
            db.session.commit()
            return existing, False
        listing = Listing(
            external_id=item.external_id,
            source=item.source,
            title=item.title,
            url=item.url,
            price=item.price,
            price_text=item.price_text,
            area=item.area,
            rooms=item.rooms,
            location=item.location,
            description=item.description,
            image_url=item.image_url,
            is_agency=item.is_agency,
        )
        db.session.add(listing)
        db.session.commit()
        return listing, True

    def query_listings(self, source=None, min_price=None, max_price=None, min_area=None, max_area=None, min_rooms=None, max_rooms=None, location=None, search=None, owners_only=True, sort="scraped_at", order="desc", page=1, per_page=20):
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
            query = query.filter(or_(Listing.title.ilike(pattern), Listing.description.ilike(pattern), Listing.location.ilike(pattern)))
        sort_column = getattr(Listing, sort, Listing.scraped_at)
        if order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        return query.paginate(page=page, per_page=per_page, error_out=False)

    def get_stats(self):
        total = Listing.query.filter(Listing.is_agency.is_(False)).count()
        oglasi = Listing.query.filter(Listing.source == "oglasi_rs", Listing.is_agency.is_(False)).count()
        zida = Listing.query.filter(Listing.source == "4zida", Listing.is_agency.is_(False)).count()
        halo = Listing.query.filter(Listing.source == "halooglasi", Listing.is_agency.is_(False)).count()
        last_run = ScrapeRun.query.order_by(ScrapeRun.started_at.desc()).first()
        return {
            "total": total,
            "oglasi_rs": oglasi,
            "4zida": zida,
            "halooglasi": halo,
            "last_scrape": last_run.finished_at.isoformat() if last_run and last_run.finished_at else None,
            "last_scrape_status": last_run.status if last_run else None,
        }
