import logging
import requests
import re
from bs4 import BeautifulSoup
from typing import List, Optional
from app.scrapers.base import ScrapedListing

logger = logging.getLogger(__name__)

class OglasiRsScraper:
    SOURCE = "oglasi_rs"
    BASE_URL = "https://www.oglasi.rs"
    URL = "https://www.oglasi.rs/nekretnine/prodaja-stanova/novi-sad?rt=vlasnik"
    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    AGENCIJA_KLJUCNE = [
        "doo", "d.o.o", "a.d.", "j.p.", "pj.",
        "reg. pos.", "reg.br", "reg.pos", "registar posrednika",
        "upisan u reg", "broj 711", "broj 182",
        "agencija", "agencijska", "agencijski",
        "nekretnine", "broker", "posrednik", "posredovanje",
        "licenca", "sifra", "šifra"
    ]

    def scrape(self) -> List[ScrapedListing]:
        listings = []
        for page in range(1, 6):
            try:
                url = f"{self.URL}&page={page}" if page > 1 else self.URL
                r = requests.get(url, headers=self.HEADERS, timeout=15)
                if r.status_code != 200:
                    break
                soup = BeautifulSoup(r.text, "html.parser")
                kartice = soup.find_all("article", itemprop="itemListElement")
                if not kartice:
                    break
                for k in kartice:
                    listing = self._parse(k)
                    if listing:
                        listings.append(listing)
            except Exception as e:
                logger.error("oglasi.rs greska str %d: %s", page, e)
                break
        logger.info("oglasi.rs: ukupno %d oglasa", len(listings))
        return listings

    def _je_agencija(self, oglasivac: str) -> bool:
        tekst = oglasivac.lower()
        return any(k.lower() in tekst for k in self.AGENCIJA_KLJUCNE)

    def _parse(self, k) -> Optional[ScrapedListing]:
        try:
            naslov_tag = k.find("h2", itemprop="name")
            link_tag = k.find("a", class_="fpogl-list-title")
            cena_tag = k.find("span", itemprop="price")
            valuta_tag = k.find("span", itemprop="priceCurrency")
            opis_tag = k.find("p", itemprop="description")
            oglasivac_tag = k.find("cite")

            naslov = naslov_tag.get_text(strip=True) if naslov_tag else ""
            link = self.BASE_URL + link_tag["href"] if link_tag else ""
            cena_broj = cena_tag.get("content", "") if cena_tag else ""
            valuta = valuta_tag.get("content", "EUR") if valuta_tag else "EUR"
            cena_text = f"{cena_broj} {valuta}" if cena_broj else ""
            opis = opis_tag.get_text(strip=True) if opis_tag else ""
            oglasivac = oglasivac_tag.get_text(strip=True) if oglasivac_tag else ""

            if not naslov or not link:
                return None

            je_agencija = self._je_agencija(oglasivac)

            try:
                cena_float = float(cena_broj.replace(",", ".")) if cena_broj else None
            except:
                cena_float = None

            return ScrapedListing(
                external_id=f"oglasi_rs-{abs(hash(link))}",
                source=self.SOURCE,
                title=naslov,
                url=link,
                price=cena_float,
                price_text=cena_text,
                description=opis,
                advertiser_type=oglasivac or None,
                is_agency=je_agencija,
                raw_text=naslov + " " + opis + " " + oglasivac,
            )
        except Exception as e:
            logger.warning("oglasi.rs parse greska: %s", e)
            return None
