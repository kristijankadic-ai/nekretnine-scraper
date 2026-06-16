import logging
from typing import List
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.models import Listing
from config import Config

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.enabled = bool(Config.MAIL_USERNAME and Config.NOTIFICATION_RECIPIENT)

    def send_new_listings_notification(self, listings: List[Listing]) -> bool:
        if not listings:
            return True
        try:
            sg = SendGridAPIClient(Config.SENDGRID_API_KEY)
            message = Mail(
                from_email=Config.MAIL_USERNAME,
                to_emails=Config.NOTIFICATION_RECIPIENT,
                subject=f"Novi oglasi nekretnina u Novom Sadu - {len(listings)} oglasa",
                plain_text_content="\n".join([f"{l.title} - {l.url}" for l in listings])
            )
            sg.send(message)
            logger.info("Email poslat sa %d oglasa", len(listings))
            return True
        except Exception as e:
            logger.error("Email greska: %s", e)
            return False
