import re
from typing import Iterable, List

from app.scrapers.base import ScrapedListing
from config import Config


class AgencyFilter:
    """Filters out listings that appear to be from real estate agencies."""

    AGENCY_ADVERTISER_TYPES = {"agencija", "agency", "posrednik"}

    def __init__(self, keywords: Iterable[str] = None):
        self.keywords = [k.lower().strip() for k in (keywords or Config.DEFAULT_AGENCY_KEYWORDS) if k.strip()]

    def is_agency(self, listing: ScrapedListing) -> bool:
        if listing.is_agency:
            return True

        if listing.advertiser_type:
            adv = listing.advertiser_type.lower().strip()
            if adv in self.AGENCY_ADVERTISER_TYPES:
                return True
            if adv == "vlasnik" or adv == "owner":
                return False

        text = self._build_search_text(listing)
        return self._contains_agency_keyword(text)

    def filter_owner_listings(self, listings: List[ScrapedListing]) -> List[ScrapedListing]:
        owner_listings = []
        for listing in listings:
            listing.is_agency = self.is_agency(listing)
            if not listing.is_agency:
                owner_listings.append(listing)
        return owner_listings

    def mark_agency_flags(self, listings: List[ScrapedListing]) -> List[ScrapedListing]:
        for listing in listings:
            listing.is_agency = self.is_agency(listing)
        return listings

    def _build_search_text(self, listing: ScrapedListing) -> str:
        parts = [
            listing.title or "",
            listing.description or "",
            listing.advertiser_type or "",
            listing.location or "",
            listing.raw_text or "",
            listing.url or "",
        ]
        return " ".join(parts).lower()

    def _contains_agency_keyword(self, text: str) -> bool:
        normalized = re.sub(r"\s+", " ", text)
        for keyword in self.keywords:
            if keyword in normalized:
                return True
        return False

    def add_keyword(self, keyword: str) -> None:
        keyword = keyword.lower().strip()
        if keyword and keyword not in self.keywords:
            self.keywords.append(keyword)

    def get_keywords(self) -> List[str]:
        return list(self.keywords)
