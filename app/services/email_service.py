import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from app.models import Listing
from config import Config

logger = logging.getLogger(__name__)

SOURCE_LABELS = {
    "halooglasi": "Halooglasi",
    "google": "Google pretraga",
}


class EmailService:
    def __init__(self):
        self.enabled = bool(Config.MAIL_USERNAME and Config.NOTIFICATION_RECIPIENT)

    def send_new_listings_notification(self, listings: List[Listing]) -> bool:
        if not listings:
            return True

        if not self.enabled:
            logger.warning("Email nije podešen — preskačem notifikaciju za %d oglasa", len(listings))
            return False

        count = len(listings)
        if count == 1:
            subject = "Novi oglas nekretnine u Novom Sadu (od vlasnika)"
        else:
            subject = f"Novi oglasi nekretnina u Novom Sadu — {count} oglasa (od vlasnika)"

        html_body = self._build_html(listings)
        text_body = self._build_text(listings)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = Config.MAIL_DEFAULT_SENDER
        msg["To"] = Config.NOTIFICATION_RECIPIENT
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
                if Config.MAIL_USE_TLS:
                    server.starttls()
                if Config.MAIL_PASSWORD:
                    server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
                server.sendmail(Config.MAIL_DEFAULT_SENDER, [Config.NOTIFICATION_RECIPIENT], msg.as_string())
            logger.info("Poslat email sa %d novih oglasa na %s", count, Config.NOTIFICATION_RECIPIENT)
            return True
        except Exception as exc:
            logger.error("Slanje emaila nije uspelo: %s", exc)
            return False

    def _format_price(self, item: Listing) -> str:
        if item.price_text:
            return item.price_text
        if item.price:
            return f"{item.price:,.0f} €".replace(",", ".")
        return "Cena na upit"

    def _format_source(self, source: str) -> str:
        return SOURCE_LABELS.get(source, source)

    def _build_html(self, listings: List[Listing]) -> str:
        count = len(listings)
        intro = (
            "Pronađen je 1 novi oglas od vlasnika u Novom Sadu:"
            if count == 1
            else f"Pronađeno je {count} novih oglasa od vlasnika u Novom Sadu:"
        )

        rows = []
        for item in listings:
            price = self._format_price(item)
            area = f"{item.area:.0f} m²" if item.area else "—"
            rooms = f"{item.rooms:.0f}" if item.rooms else "—"
            location = item.location or "—"
            rows.append(
                f"""
                <tr>
                    <td style="padding:8px;border-bottom:1px solid #eee;">
                        <a href="{html.escape(item.url)}">{html.escape(item.title)}</a>
                    </td>
                    <td style="padding:8px;border-bottom:1px solid #eee;">{html.escape(price)}</td>
                    <td style="padding:8px;border-bottom:1px solid #eee;">{html.escape(area)}</td>
                    <td style="padding:8px;border-bottom:1px solid #eee;">{html.escape(rooms)}</td>
                    <td style="padding:8px;border-bottom:1px solid #eee;">{html.escape(location)}</td>
                    <td style="padding:8px;border-bottom:1px solid #eee;">{html.escape(self._format_source(item.source))}</td>
                </tr>
                """
            )

        return f"""
        <html>
        <body style="font-family:Arial,sans-serif;color:#333;">
            <h2>Nekretnine Novi Sad — obaveštenje o novim oglasima</h2>
            <p>{intro}</p>
            <p style="color:#666;font-size:14px;">Oglasi agencija su automatski isfiltrirani.</p>
            <table style="border-collapse:collapse;width:100%;max-width:900px;">
                <thead>
                    <tr style="background:#f5f5f5;">
                        <th style="padding:8px;text-align:left;">Naslov</th>
                        <th style="padding:8px;text-align:left;">Cena</th>
                        <th style="padding:8px;text-align:left;">Površina</th>
                        <th style="padding:8px;text-align:left;">Sobe</th>
                        <th style="padding:8px;text-align:left;">Lokacija</th>
                        <th style="padding:8px;text-align:left;">Izvor</th>
                    </tr>
                </thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
            <p style="margin-top:16px;font-size:13px;color:#888;">
                Ovaj email je automatski poslat iz aplikacije Nekretnine Scraper.
            </p>
        </body>
        </html>
        """

    def _build_text(self, listings: List[Listing]) -> str:
        count = len(listings)
        if count == 1:
            header = "Nekretnine Novi Sad — 1 novi oglas od vlasnika\n"
        else:
            header = f"Nekretnine Novi Sad — {count} nova oglasa od vlasnika\n"

        lines = [header, "Oglasi agencija su automatski isfiltrirani.\n"]
        for index, item in enumerate(listings, start=1):
            price = self._format_price(item)
            area = f"{item.area:.0f} m²" if item.area else "nije navedeno"
            rooms = f"{item.rooms:.0f}" if item.rooms else "nije navedeno"
            location = item.location or "nije navedeno"
            lines.append(f"{index}. {item.title}")
            lines.append(f"   Cena: {price}")
            lines.append(f"   Površina: {area} | Sobe: {rooms}")
            lines.append(f"   Lokacija: {location}")
            lines.append(f"   Izvor: {self._format_source(item.source)}")
            lines.append(f"   Link: {item.url}\n")

        lines.append("—")
        lines.append("Automatsko obaveštenje iz aplikacije Nekretnine Scraper.")
        return "\n".join(lines)
