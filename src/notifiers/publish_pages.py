"""Generates a standalone, fully-interactive online dashboard for GitHub Pages / Cloud deployment."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Ensure root directory is on path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import load_config
from src.db.database import Database

logger = logging.getLogger(__name__)


def generate_published_site(output_dir: str = "docs") -> str:
    """Generate a standalone interactive web app into output_dir."""
    config = load_config(str(ROOT_DIR / "config.yaml"))
    db = Database(str(ROOT_DIR / config.database.path))

    # Fetch all active jobs (score >= 20, non-hidden)
    jobs = db.get_jobs(min_score=20, limit=500)
    jobs_data = [j.model_dump() for j in jobs]
    stats = db.get_stats()

    # Format timestamp
    now_str = datetime.now().strftime("Today at %I:%M %p PST")
    stats["last_scraped_at"] = now_str
    db.set_metadata("last_scraped_at", now_str)

    template_path = ROOT_DIR / "src" / "dashboard" / "templates" / "index.html"
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Inject embedded datasets for standalone static hosting (GitHub Pages)
    embedded_script = f"""
    <script>
        window.INITIAL_JOBS = {json.dumps(jobs_data, ensure_ascii=False)};
        window.INITIAL_STATS = {json.dumps(stats, ensure_ascii=False)};
        window.DASHBOARD_PASSCODE = "90038";
    </script>
    """

    # Inject right before </head>
    injected_html = html_content.replace("</head>", f"{embedded_script}\n</head>")

    out_path = ROOT_DIR / output_dir
    out_path.mkdir(parents=True, exist_ok=True)
    target_file = out_path / "index.html"

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(injected_html)

    print(f"Standalone online dashboard published to: {target_file}")
    return str(target_file)


if __name__ == "__main__":
    generate_published_site()
