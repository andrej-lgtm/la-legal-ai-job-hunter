"""FastAPI local web dashboard backend."""

import logging
from pathlib import Path
from typing import List, Optional
from fastapi import BackgroundTasks, FastAPI, Query
from fastapi.responses import HTMLResponse
from src.config import load_config
from src.db.database import Database
from src.engine.scorer import score_job
from src.scrapers.aggregator import ScraperAggregator

logger = logging.getLogger(__name__)

app = FastAPI(title="Legal & AI Job Hunter Dashboard")
config = load_config("config.yaml")
db = Database(config.database.path)


def run_scrape_background():
    """Execute scraping pipeline in background task."""
    logger.info("Starting background scrape from dashboard trigger...")
    aggregator = ScraperAggregator()
    raw_jobs = aggregator.fetch_all(config)
    scored_jobs = []
    for job in raw_jobs:
        score_job(job, config)
        scored_jobs.append(job)
    db.save_jobs(scored_jobs)
    logger.info(f"Background scrape complete. Processed {len(scored_jobs)} jobs.")


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the dashboard UI."""
    template_path = Path(__file__).parent / "templates" / "index.html"
    with open(template_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/jobs")
async def get_jobs(
    status: Optional[str] = None,
    category: Optional[str] = None,
    min_score: int = 75,  # Threshold allowing both prime (85-100%) and 3-4y reach (75-84%)
    search: Optional[str] = None,
    limit: int = 100,
):
    """API endpoint to get filtered jobs."""
    effective_min_score = 0 if search else min_score
    jobs = db.get_jobs(status=status, category=category, min_score=effective_min_score, limit=limit)
    if search:
        s_lower = search.lower()
        jobs = [
            j
            for j in jobs
            if s_lower in j.title.lower()
            or s_lower in j.company.lower()
            or s_lower in j.description.lower()
        ]
    return jobs


@app.post("/api/jobs/{job_id}/status")
async def update_status(job_id: str, status: str = Query(...), notes: Optional[str] = None):
    """Update status of a job posting."""
    success = db.update_job_status(job_id, status, notes)
    return {"success": success}


@app.get("/api/stats")
async def get_stats():
    """Get dashboard metrics."""
    return db.get_stats()


@app.post("/api/trigger-scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    """Trigger manual scrape run."""
    background_tasks.add_task(run_scrape_background)
    return {"status": "Scrape task initiated in background"}
