import logging
from typing import List
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.models import BuyerLead, Listing
from config import Config

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.enabled = bool(Config.MAIL_USERNAME and Config.NOTIFICATION_RECIPIENT)

    def _send(self, to_email: str, subject: str, body: str) -> bool:
        try:
            sg = SendGridAPIClient(Config.SENDGRID_API_KEY)
            message = Mail(
                from_email=Config.MAIL_USERNAME,
                to_emails=to_email,
                subject=subject,
                plain_text_content=body,
            )
            sg.send(message)
            return True
        except Exception as e:
            logger.error("Email greska (%s): %s", to_email, e)
            return False

    @staticmethod
    def _format_listings(listings: List[Listing]) -> str:
        return "\n\n".join(
            f"{l.title}\n{l.price_text or 'Cena na upit'} | {l.location or ''}\n{l.url}"
            for l in listings
        )

    def send_new_listings_notification(self, listings: List[Listing]) -> bool:
        if not listings:
            return True
        ok = self._send(
            Config.NOTIFICATION_RECIPIENT,
            f"Novi oglasi nekretnina u Novom Sadu - {len(listings)} oglasa",
            self._format_listings(listings),
        )
        if ok:
            logger.info("Email poslat sa %d oglasa", len(listings))
        return ok

    def send_lead_match_notification(self, lead: BuyerLead, listings: List[Listing]) -> bool:
        if not listings:
            return True
        body = (
            f"Zdravo {lead.name},\n\n"
            f"Pronasli smo {len(listings)} novi(h) oglas(a) koji odgovaraju Vasoj pretrazi:\n\n"
            f"{self._format_listings(listings)}\n\n"
            "---\n"
            f"Da se odjavite sa ovih obavestenja, kliknite: "
            f"{Config.BASE_URL}/leads/unsubscribe/{lead.unsubscribe_token}"
        )
        ok = self._send(
            lead.email,
            f"Novi stanovi za Vas - {len(listings)} oglasa",
            body,
        )
        if ok:
            logger.info("Lead email poslat (%s) sa %d oglasa", lead.email, len(listings))
        return ok
