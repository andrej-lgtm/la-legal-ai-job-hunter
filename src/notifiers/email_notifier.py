"""Email notifier sending daily HTML digest via SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from src.config import EmailConfig
from src.notifiers.digest_html import HTML_TEMPLATE, Template
from src.scrapers.base import JobPosting

logger = logging.getLogger(__name__)


def send_email_digest(jobs: List[JobPosting], email_cfg: EmailConfig) -> bool:
    """Send HTML email digest to the configured recipient."""
    if not email_cfg.enabled or not email_cfg.to_email or not email_cfg.smtp_user:
        return False

    try:
        template = Template(HTML_TEMPLATE)
        rendered_html = template.render(
            jobs=sorted(jobs, key=lambda x: x.match_score, reverse=True),
            date_str="Today's Briefing",
            in_house_count=sum(1 for j in jobs if j.category == "In-House Counsel"),
            legal_ai_count=sum(1 for j in jobs if j.category == "Legal AI" or j.is_legal_ai),
            legal_eng_count=sum(1 for j in jobs if j.category == "Legal Engineer"),
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"⚖️ Daily Legal & AI Job Briefing — {len(jobs)} LA Matches Found"
        msg["From"] = email_cfg.smtp_user
        msg["To"] = email_cfg.to_email

        msg.attach(MIMEText(rendered_html, "html"))

        with smtplib.SMTP(email_cfg.smtp_host, email_cfg.smtp_port) as server:
            server.starttls()
            server.login(email_cfg.smtp_user, email_cfg.smtp_password)
            server.send_message(msg)

        logger.info(f"Email digest sent successfully to {email_cfg.to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email digest: {e}")
        return False
