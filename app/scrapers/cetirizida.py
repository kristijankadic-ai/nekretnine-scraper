import logging
import requests
from typing import List
from app.scrapers.base import ScrapedListing

logger = logging.getLogger(__name__)

class CetiriZidaScraper:
    SOURCE = "4zida"
    BASE_URL = "https://www.4zida.rs"
    API_URL = "https://api.4zida.rs/v6/search/apartments"
    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    def scrape(self) -> List[ScrapedListing]:
        listings = []
        for page in range(1, 6):
            try:
                params = {"city": "novi-sad", "for_sale": 1, "ownerType": "owner", "page": page, "limit": 20}
                r = requests.get(self.API_URL, headers=self.HEADERS, params=params, timeout=15)
                if r.status_code != 200:
                    break
                data = r.json()
                ads = data.get("ads", [])
                if not ads:
                    break
                for ad in ads:
                    listing = self._parse(ad)
                    if listing:
                        listings.append(listing)
            except Exception as e:
                logger.error("4zida greska: %s", e)
                break
        logger.info("4zida: ukupno %d oglasa", len(listings))
        return listings

    def _parse(self, ad):
        try:
            url_path = ad.get("urlPath", "")
            link = self.BASE_URL + url_path if url_path else ""
            if not link:
                return None
            cena = ad.get("price")
            m2 = ad.get("m2")
            sobe = ad.get("roomCount")
            naslov = ad.get("detailedTitle") or ad.get("title", "")
            opis = ad.get("description100", "")
            lokacija = ", ".join(ad.get("placeNames", []))
            slika = None
            image = ad.get("image", {})
            if image:
                search_imgs = image.get("search", {})
                slika = search_imgs.get("380x0_fill_0_jpeg")
            return ScrapedListing(
                external_id=f"4zida-{ad.get('id', abs(hash(link)))}",
                source=self.SOURCE,
                title=naslov,
                url=link,
                price=float(cena) if cena else None,
                price_text=f"{cena} EUR" if cena else None,
                area=float(m2) if m2 else None,
                rooms=float(sobe) if sobe else None,
                location=lokacija,
                description=opis,
                image_url=slika,
                is_agency=False,
                raw_text=naslov + " " + opis,
            )
        except Exception as e:
            logger.warning("4zida parse greska: %s", e)
            return None
