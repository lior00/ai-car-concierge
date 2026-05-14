"""
Email automation tool.
Sends purchase confirmation emails via Mailtrap SMTP sandbox.
"""
import logging
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.config import EMAIL_FROM

logger = logging.getLogger(__name__)

MAILTRAP_HOST = "sandbox.smtp.mailtrap.io"
MAILTRAP_PORT = 2525


def _build_html(customer_name: str, vehicle_year: int, vehicle_make: str,
                vehicle_model: str, vehicle_price: float, vehicle_id: int) -> str:
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto;">
      <h2 style="color: #1a1a2e;">Thank you for your interest, {customer_name}!</h2>
      <p>We've received your interest in the following vehicle:</p>
      <table style="border-collapse: collapse; width: 100%;">
        <tr><td style="padding: 8px; font-weight: bold;">Vehicle</td>
            <td style="padding: 8px;">{vehicle_year} {vehicle_make} {vehicle_model}</td></tr>
        <tr style="background:#f9f9f9"><td style="padding: 8px; font-weight: bold;">Listing Price</td>
            <td style="padding: 8px;">${vehicle_price:,.0f}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Reference ID</td>
            <td style="padding: 8px;">#{vehicle_id}</td></tr>
      </table>
      <p style="margin-top: 24px;">A dedicated sales specialist will contact you within <strong>24 hours</strong>.</p>
      <p>Call us at <strong>1-800-PREMIUM-CAR</strong> or reply to this email.</p>
      <hr style="margin: 32px 0; border: none; border-top: 1px solid #eee;">
      <p style="font-size: 12px; color: #888;">Premium Car Dealership · 123 Auto Plaza Drive, Premium City, CA 90210</p>
    </body>
    </html>
    """


def send_purchase_email(
    customer_email: str,
    customer_name: str,
    vehicle_make: str,
    vehicle_model: str,
    vehicle_year: int,
    vehicle_id: int,
    vehicle_price: float,
) -> dict:
    mt_user = os.getenv("MAILTRAP_USERNAME")
    mt_pass = os.getenv("MAILTRAP_PASSWORD")

    if not mt_user or not mt_pass:
        logger.warning("Mailtrap credentials not configured.")
        return {"success": False, "message_id": None, "error": "Email service not configured."}

    subject = f"Your Interest in the {vehicle_year} {vehicle_make} {vehicle_model} — Premium Dealership"
    html_body = _build_html(customer_name, vehicle_year, vehicle_make, vehicle_model, vehicle_price, vehicle_id)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = customer_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(MAILTRAP_HOST, MAILTRAP_PORT) as server:
            server.starttls()
            server.login(mt_user, mt_pass)
            server.sendmail(EMAIL_FROM, [customer_email], msg.as_string())
        logger.info(f"Mailtrap SMTP email sent to {customer_email}")
        return {"success": True, "message_id": None, "error": None}
    except Exception as e:
        logger.error(f"Mailtrap SMTP failed: {e}")
        return {"success": False, "message_id": None, "error": str(e)}
