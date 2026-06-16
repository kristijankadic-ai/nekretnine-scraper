import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.scraper_service import ScraperService
from config import Config

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def scheduled_scrape(app):
    with app.app_context():
        try:
            service = ScraperService()
            summary = service.run_full_scrape(send_notifications=True)
            logger.info("Scheduled scrape completed: %s", summary)
        except Exception:
            logger.exception("Scheduled scrape failed")


def init_scheduler(app):
    if scheduler.running:
        return scheduler

    interval = Config.SCRAPE_INTERVAL_MINUTES
    scheduler.add_job(
        func=lambda: scheduled_scrape(app),
        trigger="interval",
        minutes=interval,
        id="scrape_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — scraping every %d minutes", interval)
    return scheduler
