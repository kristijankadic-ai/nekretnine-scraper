import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "listings.db"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email (SMTP)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
    NOTIFICATION_RECIPIENT = os.environ.get("NOTIFICATION_RECIPIENT", MAIL_USERNAME)

    # Google Custom Search (optional)
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
    GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")

    # Scraping
    SCRAPE_INTERVAL_MINUTES = int(os.environ.get("SCRAPE_INTERVAL_MINUTES", "60"))
    MAX_HALOOGLASI_PAGES = int(os.environ.get("MAX_HALOOGLASI_PAGES", "5"))
    REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30"))

    HALOOGLASI_OWNER_URL = (
        "https://www.halooglasi.com/nekretnine/prodaja-stanova-od-vlasnika-u-novom-sadu"
    )
    HALOOGLASI_BASE_URL = "https://www.halooglasi.com"

    GOOGLE_SEARCH_QUERIES = [
        "prodaja stan Novi Sad od vlasnika",
        "prodajem stan Novi Sad vlasnik",
        "stan Novi Sad direktno od vlasnika prodaja",
    ]

    DEFAULT_AGENCY_KEYWORDS = [
        "agencija",
        "agencije",
        "posrednik",
        "posrednici",
        "posredovanje",
        "nekretnine d.o.o",
        "nekretnine doo",
        "real estate",
        "estate agency",
        "immobilien",
        "od agencije",
        "preko agencije",
        "agency",
        "broker",
        "realtor",
        "kvadrat nekretnine",
        "city expert",
        "century 21",
        "remax",
        "direkt nekretnine",
        "beta nekretnine",
        "ekskluziv",
        "fortuna",
        "moj dom",
        "stan i vikendica",
    ]
