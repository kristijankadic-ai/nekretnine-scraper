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

    def send_new_lead_notification(self, lead: BuyerLead) -> bool:
        criteria = self._format_lead_criteria(lead)
        body = (
            f"Novi potencijalni kupac se prijavio:\n\n"
            f"Ime: {lead.full_name}\n"
            f"Email: {lead.email}\n"
            f"Telefon: {lead.phone}\n\n"
            f"Trazi:\n{criteria}\n\n"
            f"Napomena: {lead.notes or '-'}\n\n"
            f"Pregled svih leadova: {Config.BASE_URL}/leads/admin"
        )
        ok = self._send(
            Config.NOTIFICATION_RECIPIENT,
            f"Novi lead - {lead.full_name}",
            body,
        )
        if ok:
            logger.info("Notifikacija o novom leadu poslata agentu (%s)", lead.email)
        return ok

    def send_lead_match_notification(self, matches: List[tuple]) -> bool:
        """matches: list of (BuyerLead, list[Listing]) tuples to report to the agent."""
        if not matches:
            return True
        sections = []
        for lead, listings in matches:
            sections.append(
                f"=== {lead.full_name} ({lead.email}, {lead.phone}) ===\n"
                f"Trazi:\n{self._format_lead_criteria(lead)}\n\n"
                f"Novi odgovarajuci oglasi:\n{self._format_listings(listings)}"
            )
        body = "\n\n".join(sections)
        total_leads = len(matches)
        ok = self._send(
            Config.NOTIFICATION_RECIPIENT,
            f"Novi oglasi odgovaraju {total_leads} lead(ovima)",
            body,
        )
        if ok:
            logger.info("Lead match notifikacija poslata agentu za %d leadova", total_leads)
        return ok

    @staticmethod
    def _format_lead_criteria(lead: BuyerLead) -> str:
        parts = []
        if lead.location:
            parts.append(f"Lokacija: {lead.location}")
        if lead.min_price or lead.max_price:
            parts.append(f"Cena: {lead.min_price or 0} - {lead.max_price or '∞'} EUR")
        if lead.min_area or lead.max_area:
            parts.append(f"Povrsina: {lead.min_area or 0} - {lead.max_area or '∞'} m2")
        if lead.min_rooms or lead.max_rooms:
            parts.append(f"Sobe: {lead.min_rooms or 0} - {lead.max_rooms or '∞'}")
        return "\n".join(parts) if parts else "(bez konkretnih kriterijuma)"
