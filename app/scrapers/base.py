from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScrapedListing:
    external_id: str
    source: str
    title: str
    url: str
    price: Optional[float] = None
    price_text: Optional[str] = None
    area: Optional[float] = None
    rooms: Optional[float] = None
    floor: Optional[str] = None
    location: Optional[str] = None
    advertiser_type: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    published_at: Optional[str] = None
    is_agency: bool = False
    raw_text: str = field(default="", repr=False)
