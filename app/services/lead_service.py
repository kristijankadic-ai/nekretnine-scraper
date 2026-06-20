import logging
from typing import List

from app.models import BuyerLead, Listing, db, utcnow
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class LeadService:
    def __init__(self, email_service: EmailService = None):
        self.email_service = email_service or EmailService()

    def notify_matching_leads(self, new_listings: List[Listing]) -> int:
        if not new_listings:
            return 0

        leads = BuyerLead.query.filter_by(is_active=True).all()
        notified = 0
        for lead in leads:
            matches = [listing for listing in new_listings if lead.matches(listing)]
            if not matches:
                continue
            if self.email_service.send_lead_match_notification(lead, matches):
                lead.last_matched_at = utcnow()
                db.session.commit()
                notified += 1
        return notified

    def create_lead(self, **kwargs) -> BuyerLead:
        lead = BuyerLead(**kwargs)
        db.session.add(lead)
        db.session.commit()
        return lead

    def unsubscribe(self, token: str) -> bool:
        lead = BuyerLead.query.filter_by(unsubscribe_token=token).first()
        if not lead:
            return False
        lead.is_active = False
        db.session.commit()
        return True
