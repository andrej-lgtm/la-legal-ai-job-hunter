"""Webhook notification module (Discord / Slack / Telegram)."""

import logging
from typing import List
import requests
from src.config import WebhookConfig
from src.scrapers.base import JobPosting

logger = logging.getLogger(__name__)


def send_webhook_alert(jobs: List[JobPosting], webhook_cfg: WebhookConfig) -> bool:
    """Send top matched jobs summary to Discord or Slack webhook."""
    if not webhook_cfg.enabled or not webhook_cfg.url:
        return False

    top_jobs = sorted([j for j in jobs if j.match_score >= 70], key=lambda x: x.match_score, reverse=True)[:5]
    if not top_jobs:
        return False

    url = webhook_cfg.url.strip()

    # Discord format
    if "discord.com" in url:
        embeds = []
        for j in top_jobs:
            embeds.append(
                {
                    "title": f"[{j.match_score}% Match] {j.title} @ {j.company}",
                    "url": j.job_url,
                    "description": f"**Location**: {j.location}\n**Category**: {j.category}\n**JD**: {j.jd_notes}\n{j.description_snippet[:150]}...",
                    "color": 0x4F46E5,
                }
            )

        payload = {
            "content": f"⚖️ **Found {len(jobs)} Legal & AI Job Matches in Los Angeles Today!**",
            "embeds": embeds,
        }
    else:
        # Standard Slack / generic webhook format
        text_lines = [f"*Found {len(jobs)} Legal & AI Job Matches in LA Today:*\n"]
        for j in top_jobs:
            text_lines.append(f"• *<{j.job_url}|{j.title} @ {j.company}>* ({j.match_score}% Match, {j.location})")
        payload = {"text": "\n".join(text_lines)}

    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code in [200, 204]
    except Exception as e:
        logger.error(f"Failed to send webhook: {e}")
        return False
