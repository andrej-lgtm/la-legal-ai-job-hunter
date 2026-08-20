"""Generates a standalone, fully-interactive online dashboard for GitHub Pages / Cloud deployment."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Ensure root directory is on path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import load_config
from src.db.database import Database
from src.engine.scorer import score_job
from src.engine.salary_parser import extract_salary, format_salary_display
from src.engine.classifier import classify_role
from src.scrapers.base import normalize_company, normalize_title

logger = logging.getLogger(__name__)


def generate_published_site(output_dir: str = "docs") -> str:
    """Generate a standalone interactive web app into output_dir."""
    config = load_config(str(ROOT_DIR / "config.yaml"))
    db = Database(str(ROOT_DIR / config.database.path))

    # Rescore all jobs in database to guarantee latest scoring formula & salary display
    all_raw_jobs = db.get_jobs(limit=1000)
    for job in all_raw_jobs:
        # 1. Update salary with latest accurate parser
        if job.description:
            s_min, s_max, s_int, s_disp = extract_salary(f"{job.title}\n{job.description}")
            if s_disp:
                job.salary_min = s_min
                job.salary_max = s_max
                job.salary_interval = s_int
                job.salary_display = s_disp
            else:
                # Clear bogus old values
                job.salary_min = None
                job.salary_max = None
                job.salary_display = ""
        elif job.salary_min or job.salary_max:
            job.salary_display = format_salary_display(job.salary_min, job.salary_max, job.salary_interval)

        # 2. Re-classify category
        cat, is_ai = classify_role(job.title, job.description)
        job.category = cat
        job.is_legal_ai = is_ai

        # 3. Score
        score, reasons, is_qual = score_job(job, config)
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE jobs 
                   SET match_score = ?, match_reasons = ?, category = ?, is_legal_ai = ?, 
                       jd_required = ?, jd_notes = ?, salary_min = ?, salary_max = ?, 
                       salary_interval = ?, salary_display = ? 
                   WHERE id = ?""",
                (score, json.dumps(reasons), job.category, 1 if job.is_legal_ai else 0, 
                 1 if job.jd_required else 0, job.jd_notes, job.salary_min, job.salary_max, 
                 job.salary_interval, job.salary_display, job.id)
            )
            conn.commit()

    # Fetch all active jobs (score >= 20, non-hidden) and deduplicate
    raw_jobs = db.get_jobs(min_score=20, limit=500)
    
    # Deduplicate cluster by company + title
    seen_clusters = {}
    for j in raw_jobs:
        c_norm = normalize_company(j.company)
        t_norm = normalize_title(j.title)
        key = (c_norm, t_norm)
        if key not in seen_clusters:
            seen_clusters[key] = j
        else:
            existing = seen_clusters[key]
            # Keep the more informative posting
            if len(j.description or "") > len(existing.description or ""):
                seen_clusters[key] = j
            elif len(j.description or "") == len(existing.description or "") and j.match_score > existing.match_score:
                seen_clusters[key] = j
            elif not existing.salary_display and j.salary_display:
                existing.salary_display = j.salary_display
                existing.salary_min = j.salary_min
                existing.salary_max = j.salary_max

    jobs = list(seen_clusters.values())
    # Sort by match_score descending
    jobs.sort(key=lambda x: (x.match_score, len(x.description or "")), reverse=True)
    jobs_data = [j.model_dump() for j in jobs]
    stats = db.get_stats()

    # Format timestamp explicitly in Pacific Time (America/Los_Angeles)
    try:
        pacific_tz = ZoneInfo("America/Los_Angeles")
        now_pst = datetime.now(pacific_tz)
    except Exception:
        now_pst = datetime.now()

    # Format as e.g. "Today at 9:48 PM PST"
    hour_12 = now_pst.strftime("%I").lstrip("0") or "12"
    now_str = f"Today at {hour_12}:{now_pst.strftime('%M %p')} PST"
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
