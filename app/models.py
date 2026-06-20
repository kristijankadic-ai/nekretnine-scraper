import secrets
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


def generate_token():
    return secrets.token_urlsafe(24)


class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    source = db.Column(db.String(32), nullable=False, index=True)
    title = db.Column(db.String(512), nullable=False)
    url = db.Column(db.String(1024), nullable=False)
    price = db.Column(db.Float, nullable=True)
    price_text = db.Column(db.String(64), nullable=True)
    area = db.Column(db.Float, nullable=True)
    rooms = db.Column(db.Float, nullable=True)
    floor = db.Column(db.String(32), nullable=True)
    location = db.Column(db.String(256), nullable=True)
    advertiser_type = db.Column(db.String(64), nullable=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(1024), nullable=True)
    is_agency = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_notified = db.Column(db.Boolean, default=False, nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)
    scraped_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "external_id": self.external_id,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "price": self.price,
            "price_text": self.price_text,
            "area": self.area,
            "rooms": self.rooms,
            "floor": self.floor,
            "location": self.location,
            "advertiser_type": self.advertiser_type,
            "description": self.description,
            "image_url": self.image_url,
            "is_agency": self.is_agency,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
        }


class BuyerLead(db.Model):
    __tablename__ = "buyer_leads"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(256), nullable=False, index=True)
    phone = db.Column(db.String(64), nullable=True)
    min_price = db.Column(db.Float, nullable=True)
    max_price = db.Column(db.Float, nullable=True)
    min_area = db.Column(db.Float, nullable=True)
    max_area = db.Column(db.Float, nullable=True)
    min_rooms = db.Column(db.Float, nullable=True)
    max_rooms = db.Column(db.Float, nullable=True)
    location = db.Column(db.String(256), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    unsubscribe_token = db.Column(db.String(64), unique=True, nullable=False, default=generate_token)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    last_matched_at = db.Column(db.DateTime, nullable=True)

    def matches(self, listing: "Listing") -> bool:
        if self.min_price is not None and (listing.price is None or listing.price < self.min_price):
            return False
        if self.max_price is not None and (listing.price is None or listing.price > self.max_price):
            return False
        if self.min_area is not None and (listing.area is None or listing.area < self.min_area):
            return False
        if self.max_area is not None and (listing.area is None or listing.area > self.max_area):
            return False
        if self.min_rooms is not None and (listing.rooms is None or listing.rooms < self.min_rooms):
            return False
        if self.max_rooms is not None and (listing.rooms is None or listing.rooms > self.max_rooms):
            return False
        if self.location:
            haystack = (listing.location or "") + " " + (listing.title or "")
            if self.location.lower() not in haystack.lower():
                return False
        return True


class ScrapeRun(db.Model):
    __tablename__ = "scrape_runs"

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)
    source = db.Column(db.String(32), nullable=False)
    found_count = db.Column(db.Integer, default=0)
    new_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default="running")
    message = db.Column(db.Text, nullable=True)
