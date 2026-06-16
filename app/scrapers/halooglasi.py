import html
import json
import logging
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

import cloudscraper
from bs4 import BeautifulSoup

from app.scrapers.base import ScrapedListing
from config import Config

logger = logging.getLogger(__name__)

SERVER_LIST_DATA_PATTERN = re.compile(r"serverListData\s*=\s*(\{.*?\});", re.DOTALL)


class HalooglasiScraper:
    SOURCE = "halooglasi"

    def __init__(self, timeout: int = None):
        self.timeout = timeout or Config.REQUEST_TIMEOUT
        self.scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        self.base_url = Config.HALOOGLASI_BASE_URL

    def scrape(self, max_pages: int = None) -> List[ScrapedListing]:
        max_pages = max_pages or Config.MAX_HALOOGLASI_PAGES
        listings: List[ScrapedListing] = []
        seen_ids = set()

        for page in range(1, max_pages + 1):
            page_listings, total_pages = self._scrape_page(page)
            for listing in page_listings:
                if listing.external_id not in seen_ids:
                    seen_ids.add(listing.external_id)
                    listings.append(listing)

            if not page_listings or page >= total_pages:
                break

        logger.info("Halooglasi: scraped %d unique listings", len(listings))
        return listings

    def _scrape_page(self, page: int) -> tuple[List[ScrapedListing], int]:
        url = Config.HALOOGLASI_OWNER_URL
        if page > 1:
            url = f"{url}?page={page}"

        try:
            response = self.scraper.get(url, timeout=self.timeout)
            response.raise_for_status()
        except Exception as exc:
            logger.error("Halooglasi fetch failed (page %d): %s", page, exc)
            return [], 1

        total_pages = 1
        ads = []

        match = SERVER_LIST_DATA_PATTERN.search(response.text)
        if match:
            try:
                data = json.loads(match.group(1))
                ads = data.get("Ads", [])
                total_pages = int(data.get("TotalPages") or 1)
            except json.JSONDecodeError as exc:
                logger.warning("Failed to parse serverListData: %s", exc)

        if not ads:
            ads = self._fallback_parse_html(response.text)

        listings = [self._parse_ad(ad) for ad in ads]
        listings = [item for item in listings if item is not None]
        return listings, total_pages

    def _fallback_parse_html(self, html_content: str) -> list:
        soup = BeautifulSoup(html_content, "html.parser")
        items = soup.select(".product-item[data-id]")
        ads = []
        for item in items:
            ad_id = item.get("data-id")
            if not ad_id:
                continue
            title_el = item.select_one(".product-title a")
            ads.append(
                {
                    "Id": ad_id,
                    "Title": title_el.get_text(strip=True) if title_el else "",
                    "RelativeUrl": title_el.get("href", "") if title_el else "",
                    "ListHTML": str(item),
                }
            )
        return ads

    def _parse_ad(self, ad: dict) -> Optional[ScrapedListing]:
        ad_id = str(ad.get("Id", ""))
        if not ad_id:
            return None

        title = ad.get("Title", "").strip()
        relative_url = ad.get("RelativeUrl", "")
        url = urljoin(self.base_url, relative_url) if relative_url else ""

        list_html = html.unescape(ad.get("ListHTML", "") or "")
        parsed = self._parse_list_html(list_html)

        advertiser_type = parsed.get("advertiser_type")
        if not advertiser_type and ad.get("OtherFields"):
            for field in ad["OtherFields"]:
                if field.get("Name") == "oglasivac_nekretnine_s":
                    advertiser_type = field.get("Value")

        description = ad.get("Text", "") or ad.get("PrintText", "")
        image_url = None
        image_urls = ad.get("ImageURLs") or []
        if image_urls:
            image_url = image_urls[0] if isinstance(image_urls[0], str) else image_urls[0].get("Url")

        published_at = parsed.get("published_at") or ad.get("ValidFromForDisplay")

        return ScrapedListing(
            external_id=f"halo-{ad_id}",
            source=self.SOURCE,
            title=title or parsed.get("title", "Bez naslova"),
            url=url,
            price=parsed.get("price"),
            price_text=parsed.get("price_text"),
            area=parsed.get("area"),
            rooms=parsed.get("rooms"),
            floor=parsed.get("floor"),
            location=parsed.get("location"),
            advertiser_type=advertiser_type,
            description=description,
            image_url=image_url,
            published_at=published_at,
            raw_text=f"{title} {description} {parsed.get('location', '')}",
        )

    def _parse_list_html(self, list_html: str) -> dict:
        if not list_html:
            return {}

        soup = BeautifulSoup(list_html, "html.parser")
        result = {}

        price_el = soup.select_one(".central-feature [data-value]")
        if price_el:
            price_val = price_el.get("data-value", "")
            result["price_text"] = price_el.get_text(strip=True)
            try:
                result["price"] = float(price_val.replace(".", "").replace(",", "."))
            except (ValueError, AttributeError):
                pass

        title_el = soup.select_one(".product-title")
        if title_el:
            result["title"] = title_el.get_text(strip=True)

        locations = [li.get_text(strip=True) for li in soup.select(".subtitle-places li")]
        if locations:
            result["location"] = " / ".join(locations)

        for feature in soup.select(".product-features li"):
            legend = feature.select_one(".legend")
            value = feature.select_one(".value-wrapper")
            if not legend or not value:
                continue
            label = legend.get_text(strip=True).lower()
            text = value.get_text(" ", strip=True)
            if "kvadratura" in label:
                area_match = re.search(r"([\d.,]+)", text)
                if area_match:
                    try:
                        result["area"] = float(area_match.group(1).replace(",", "."))
                    except ValueError:
                        pass
            elif "soba" in label:
                room_match = re.search(r"([\d.,]+)", text)
                if room_match:
                    try:
                        result["rooms"] = float(room_match.group(1).replace(",", "."))
                    except ValueError:
                        pass
            elif "sprat" in label:
                result["floor"] = text.split()[0] if text else None

        advertiser_el = soup.select_one('[data-field-name="oglasivac_nekretnine_s"]')
        if advertiser_el:
            result["advertiser_type"] = advertiser_el.get("data-field-value") or advertiser_el.get_text(strip=True)

        date_el = soup.select_one(".publish-date")
        if date_el:
            result["published_at"] = self._parse_date(date_el.get_text(strip=True))

        return result

    @staticmethod
    def _parse_date(date_str: str) -> Optional[str]:
        for fmt in ("%d.%m.%Y.", "%d.%m.%Y"):
            try:
                return datetime.strptime(date_str.strip(), fmt).isoformat()
            except ValueError:
                continue
        return date_str or None
