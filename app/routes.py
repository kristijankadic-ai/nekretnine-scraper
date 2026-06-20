import logging
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.models import ScrapeRun, db
from app.services.scraper_service import ScraperService

bp = Blueprint("main", __name__)
scraper_service = ScraperService()
logger = logging.getLogger(__name__)


def _parse_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value, default=1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@bp.route("/")
def index():
    filters = {
        "source": request.args.get("source", ""),
        "min_price": request.args.get("min_price", ""),
        "max_price": request.args.get("max_price", ""),
        "min_area": request.args.get("min_area", ""),
        "max_area": request.args.get("max_area", ""),
        "min_rooms": request.args.get("min_rooms", ""),
        "max_rooms": request.args.get("max_rooms", ""),
        "location": request.args.get("location", ""),
        "search": request.args.get("search", ""),
        "owners_only": request.args.get("owners_only", "1") == "1",
        "sort": request.args.get("sort", "scraped_at"),
        "order": request.args.get("order", "desc"),
    }

    pagination = scraper_service.query_listings(
        source=filters["source"] or None,
        min_price=_parse_float(filters["min_price"]),
        max_price=_parse_float(filters["max_price"]),
        min_area=_parse_float(filters["min_area"]),
        max_area=_parse_float(filters["max_area"]),
        min_rooms=_parse_float(filters["min_rooms"]),
        max_rooms=_parse_float(filters["max_rooms"]),
        location=filters["location"] or None,
        search=filters["search"] or None,
        owners_only=filters["owners_only"],
        sort=filters["sort"],
        order=filters["order"],
        page=_parse_int(request.args.get("page"), 1),
        per_page=_parse_int(request.args.get("per_page"), 20),
    )

    stats = scraper_service.get_stats()
    recent_runs = ScrapeRun.query.order_by(ScrapeRun.started_at.desc()).limit(5).all()

    return render_template(
        "index.html",
        listings=pagination.items,
        pagination=pagination,
        filters=filters,
        stats=stats,
        recent_runs=recent_runs,
        agency_keywords=scraper_service.agency_filter.get_keywords(),
    )


@bp.route("/scrape", methods=["POST"])
def scrape():
    try:
        summary = scraper_service.run_full_scrape(send_notifications=True)
        flash(
            f"Scraping završen. Novih oglasa: {summary['new_listings']} "
            f"(Oglasi.rs: {summary['oglasi_rs'].get('new_count', 0)}, "
            f"4zida: {summary['4zida'].get('new_count', 0)}, "
            f"Halooglasi: {summary['halooglasi'].get('new_count', 0)})",
            "success",
        )
    except Exception as exc:
        logger.exception("Manual scrape failed")
        flash(f"Greška pri scrapingu: {exc}", "error")

    return redirect(url_for("main.index"))


@bp.route("/api/listings")
def api_listings():
    pagination = scraper_service.query_listings(
        source=request.args.get("source") or None,
        min_price=_parse_float(request.args.get("min_price")),
        max_price=_parse_float(request.args.get("max_price")),
        min_area=_parse_float(request.args.get("min_area")),
        max_area=_parse_float(request.args.get("max_area")),
        min_rooms=_parse_float(request.args.get("min_rooms")),
        max_rooms=_parse_float(request.args.get("max_rooms")),
        location=request.args.get("location") or None,
        search=request.args.get("search") or None,
        owners_only=request.args.get("owners_only", "1") == "1",
        page=_parse_int(request.args.get("page"), 1),
        per_page=_parse_int(request.args.get("per_page"), 20),
    )

    return jsonify(
        {
            "items": [item.to_dict() for item in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "page": pagination.page,
        }
    )


@bp.route("/api/stats")
def api_stats():
    return jsonify(scraper_service.get_stats())
