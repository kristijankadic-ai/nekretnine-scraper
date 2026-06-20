import logging
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.models import BuyerLead, ScrapeRun, db
from app.services.scraper_service import ScraperService
from app.services.lead_service import LeadService

bp = Blueprint("main", __name__)
scraper_service = ScraperService()
lead_service = LeadService(scraper_service.email_service)
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
            f"Halooglasi: {summary['halooglasi'].get('new_count', 0)}). "
            f"Obavešteno kupaca: {summary.get('leads_notified', 0)}",
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


@bp.route("/leads", methods=["GET", "POST"])
def leads_new():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()

        if not name or not email:
            flash("Ime i email su obavezni.", "error")
            return redirect(url_for("main.leads_new"))

        lead_service.create_lead(
            name=name,
            email=email,
            phone=(request.form.get("phone") or "").strip() or None,
            min_price=_parse_float(request.form.get("min_price")),
            max_price=_parse_float(request.form.get("max_price")),
            min_area=_parse_float(request.form.get("min_area")),
            max_area=_parse_float(request.form.get("max_area")),
            min_rooms=_parse_float(request.form.get("min_rooms")),
            max_rooms=_parse_float(request.form.get("max_rooms")),
            location=(request.form.get("location") or "").strip() or None,
            notes=(request.form.get("notes") or "").strip() or None,
        )
        flash("Prijava uspešna! Obavestićemo Vas mejlom kad se pojavi odgovarajući oglas.", "success")
        return redirect(url_for("main.leads_new"))

    return render_template("leads_new.html")


@bp.route("/leads/unsubscribe/<token>")
def leads_unsubscribe(token):
    if lead_service.unsubscribe(token):
        flash("Uspešno ste se odjavili sa obaveštenja.", "success")
    else:
        flash("Link za odjavu nije validan.", "error")
    return redirect(url_for("main.leads_new"))


@bp.route("/leads/admin")
def leads_admin():
    leads = BuyerLead.query.order_by(BuyerLead.created_at.desc()).all()
    return render_template("leads_admin.html", leads=leads)
