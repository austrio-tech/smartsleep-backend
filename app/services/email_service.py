"""
Email delivery via Google Apps Script webhook.
Usage:
    from app.services.email_service import send_email, render_template
"""

import logging
from pathlib import Path
from typing import Optional

import requests
from app.config import settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"


def render_template(name: str, **kwargs) -> str:
    """Load an HTML template and replace {{KEY}} placeholders."""
    path = _TEMPLATE_DIR / name
    html = path.read_text(encoding="utf-8")
    for key, value in kwargs.items():
        html = html.replace(f"{{{{{key}}}}}", str(value) if value is not None else "")
    return html


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send email via Google Apps Script. Returns True on success."""
    if not settings.google_script_url or not settings.email_token:
        logger.warning("Email env vars not configured — skipping send.")
        return False

    payload = {
        "token": settings.email_token,
        "to": to,
        "subject": subject,
        "body": html_body,
        "name": settings.email_name,
        "attachments": [],
    }

    try:
        resp = requests.post(
            settings.google_script_url,
            json=payload,
            timeout=20,
            allow_redirects=True,
        )
        if resp.status_code in (200, 302) and ("Success" in resp.text or resp.status_code == 302):
            logger.info("Email sent to %s — subject: %s", to, subject)
            return True
        logger.warning("Email send failed: status=%s body=%s", resp.status_code, resp.text[:200])
        return False
    except Exception as exc:
        logger.error("Email send exception: %s", exc)
        return False
