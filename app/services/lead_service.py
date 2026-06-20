import logging
from typing import List

from app.models import BuyerLead, Listing, db, utcnow
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class LeadService:
    def __init__(self, email_service: EmailService = None):
        self.email_service = email_service or EmailService()

    def notify_matching_leads(self, new_listings: List[Listing]) -> int:
        """Finds leads whose criteria match newly scraped listings and emails
        the agent (never the buyer directly) a summary per matched lead."""
        if not new_listings:
            return 0

        leads = BuyerLead.query.filter_by(is_active=True).all()
        matches = []
        for lead in leads:
            matched_listings = [listing for listing in new_listings if lead.matches(listing)]
            if matched_listings:
                matches.append((lead, matched_listings))

        if not matches:
            return 0

        if self.email_service.send_lead_match_notification(matches):
            for lead, _ in matches:
                lead.last_matched_at = utcnow()
            db.session.commit()
        return len(matches)

    def create_lead(self, **kwargs) -> BuyerLead:
        lead = BuyerLead(**kwargs)
        db.session.add(lead)
        db.session.commit()
        self.email_service.send_new_lead_notification(lead)
        return lead

    def unsubscribe(self, token: str) -> bool:
        lead = BuyerLead.query.filter_by(unsubscribe_token=token).first()
        if not lead:
            return False
        lead.is_active = False
        db.session.commit()
        return True
