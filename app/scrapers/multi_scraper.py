import logging
import requests
from bs4 import BeautifulSoup
from typing import List
from app.scrapers.base import ScrapedListing

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def scrape_site(name, url, base_url, article_tag, naslov_tag, link_tag_name, cena_class, opis_tag) -> List[ScrapedListing]:
    listings = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        kartice = soup.find_all(article_tag)
        logger.info("%s: pronasao %d kartica", name, len(kartice))
        for k in kartice:
            try:
                n = k.find(naslov_tag)
                l = k.find("a", href=True)
                c = k.find(class_=lambda x: x and cena_class in x.lower()) if cena_class else None
                o = k.find(opis_tag) if opis_tag else None

                naslov = n.get_text(strip=True) if n else ""
                link = l["href"] if l else ""
                if link and link.startswith("/"):
                    link = base_url + link
                cena = c.get_text(strip=True) if c else ""
                opis = o.get_text(strip=True) if o else ""

                if not naslov or not link:
                    continue

                listings.append(ScrapedListing(
                    external_id=f"{name}-{abs(hash(link))}",
                    source=name,
                    title=naslov,
                    url=link,
                    price_text=cena,
                    description=opis,
                    raw_text=naslov + " " + opis,
                ))
            except Exception as e:
                logger.warning("%s kartica greska: %s", name, e)
    except Exception as e:
        logger.error("%s scraping failed: %s", name, e)
    logger.info("%s: ukupno %d oglasa", name, len(listings))
    return listings


class MultiScraper:
    SOURCE = "multi"

    def scrape(self) -> List[ScrapedListing]:
        listings = []

        listings += scrape_site(
            "4zida",
            "https://www.4zida.rs/prodaja-stanova/novi-sad?od_vlasnika=1",
            "https://www.4zida.rs",
            "article", "h2", "a", "price", "p"
        )

        listings += scrape_site(
            "oglasi_rs",
            "https://www.oglasi.rs/nekretnine/stanovi/prodaja?lokacija=novi-sad&vlasnik=1",
            "https://www.oglasi.rs",
            "article", "h2", "a", "price", "p"
        )

        listings += scrape_site(
            "sasomange",
            "https://www.sasomange.rs/nekretnine/stanovi?grad=novi-sad&tip=prodaja&oglasivac=vlasnik",
            "https://www.sasomange.rs",
            "div", "h2", "a", "price", "p"
        )

        listings += scrape_site(
            "kupujemprodajem",
            "https://www.kupujemprodajem.com/nekretnine/stanovi/prodaja/novi-sad?oglasivaOglas=private",
            "https://www.kupujemprodajem.com",
            "article", "h2", "a", "price", "p"
        )

        return listings
