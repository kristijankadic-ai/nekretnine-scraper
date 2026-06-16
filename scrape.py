"""Standalone script for manual or cron-based scraping."""

import argparse
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from app import create_app
from app.services.scraper_service import ScraperService


def main():
    parser = argparse.ArgumentParser(description="Scrape nekretnine listings in Novi Sad")
    parser.add_argument("--no-email", action="store_true", help="Skip email notifications")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        service = ScraperService()
        summary = service.run_full_scrape(send_notifications=not args.no_email)
        print(f"Done. New listings: {summary['new_listings']}")
        print(f"  Halooglasi: {summary['halooglasi']}")
        print(f"  Google: {summary['google']}")


if __name__ == "__main__":
    main()
