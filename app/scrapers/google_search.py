import logging
import re
from typing import List, Optional
from urllib.parse import urlparse

from app.scrapers.base import ScrapedListing
from config import Config

logger = logging.getLogger(__name__)

REAL_ESTATE_DOMAINS = {
    "halooglasi.com",
    "nekretnine.rs",
    "4zida.rs",
    "cityexpert.rs",
    "nadjidom.com",
    "oglasi.rs",
    "beograd-apartments.com",
}


class GoogleSearchScraper:
    SOURCE = "google"

    def __init__(self, queries: List[str] = None):
        self.queries = queries or Config.GOOGLE_SEARCH_QUERIES

    def scrape(self) -> List[ScrapedListing]:
        listings: List[ScrapedListing] = []
        seen_urls = set()

        if Config.GOOGLE_API_KEY and Config.GOOGLE_CSE_ID:
            listings.extend(self._search_via_custom_search(seen_urls))

        listings.extend(self._search_via_duckduckgo(seen_urls))
        listings.extend(self._search_via_googlesearch(seen_urls))

        logger.info("Google search: found %d unique results", len(listings))
        return listings

    def _search_via_custom_search(self, seen_urls: set) -> List[ScrapedListing]:
        import requests

        results: List[ScrapedListing] = []
        for query in self.queries:
            try:
                response = requests.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": Config.GOOGLE_API_KEY,
                        "cx": Config.GOOGLE_CSE_ID,
                        "q": query,
                        "num": 10,
                        "gl": "rs",
                        "hl": "sr",
                    },
                    timeout=Config.REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                logger.warning("Google Custom Search failed for '%s': %s", query, exc)
                continue

            for item in data.get("items", []):
                listing = self._result_to_listing(item.get("link"), item.get("title"), item.get("snippet"), seen_urls)
                if listing:
                    results.append(listing)

        return results

    def _search_via_duckduckgo(self, seen_urls: set) -> List[ScrapedListing]:
        results: List[ScrapedListing] = []
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            ddgs = DDGS()
            for query in self.queries:
                try:
                    search_results = ddgs.text(
                        f"{query} Novi Sad nekretnine prodaja",
                        region="rs-rs",
                        max_results=15,
                    )
                    for item in search_results:
                        listing = self._result_to_listing(
                            item.get("href"),
                            item.get("title"),
                            item.get("body"),
                            seen_urls,
                        )
                        if listing:
                            results.append(listing)
                except Exception as exc:
                    logger.warning("DuckDuckGo search failed for '%s': %s", query, exc)
        except ImportError:
            logger.debug("ddgs / duckduckgo-search not available")

        return results

    def _search_via_googlesearch(self, seen_urls: set) -> List[ScrapedListing]:
        results: List[ScrapedListing] = []
        try:
            from googlesearch import search

            for query in self.queries:
                try:
                    for url in search(query, num_results=10, lang="sr"):
                        listing = self._result_to_listing(url, None, None, seen_urls)
                        if listing:
                            results.append(listing)
                except Exception as exc:
                    logger.warning("googlesearch failed for '%s': %s", query, exc)
        except ImportError:
            logger.debug("googlesearch-python not available")

        return results

    def _result_to_listing(
        self,
        url: Optional[str],
        title: Optional[str],
        snippet: Optional[str],
        seen_urls: set,
    ) -> Optional[ScrapedListing]:
        if not url or url in seen_urls:
            return None

        if not self._is_relevant_real_estate_url(url):
            return None

        seen_urls.add(url)
        domain = urlparse(url).netloc.replace("www.", "")
        external_id = f"google-{abs(hash(url))}"

        full_text = " ".join(filter(None, [title, snippet, url]))
        price = self._extract_price(full_text)

        return ScrapedListing(
            external_id=external_id,
            source=self.SOURCE,
            title=title or self._title_from_url(url),
            url=url,
            price=price,
            price_text=str(price) + " €" if price else None,
            description=snippet,
            raw_text=full_text,
        )

    def _is_relevant_real_estate_url(self, url: str) -> bool:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "").lower()
        path = parsed.path.lower()

        if any(d in domain for d in REAL_ESTATE_DOMAINS):
            return True

        keywords = ("stan", "nekretn", "prodaj", "oglasi", "apartman", "kuca", "kuca")
        return "novi-sad" in path or "novi_sad" in path or any(k in path for k in keywords)

    @staticmethod
    def _extract_price(text: str) -> Optional[float]:
        match = re.search(r"([\d\s.]{2,10})\s*€", text)
        if match:
            try:
                return float(match.group(1).replace(" ", "").replace(".", ""))
            except ValueError:
                pass
        return None

    @staticmethod
    def _title_from_url(url: str) -> str:
        path = urlparse(url).path.strip("/").split("/")[-1]
        return path.replace("-", " ").title() or url
