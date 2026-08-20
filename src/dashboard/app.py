"""FastAPI local web dashboard for LA Legal & AI Job Hunter."""

import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from src.config import load_config
from src.db.database import Database
from src.engine.scorer import score_job
from src.scrapers.aggregator import ScraperAggregator

logger = logging.getLogger(__name__)

config = load_config()
db = Database(config.database.path)

app = FastAPI(
    title="LA Legal & AI Job Hunter",
    description="Local web dashboard to view and track legal & legal-AI opportunities in Los Angeles.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard UI."""
    template_path = Path(__file__).parent / "templates" / "index.html"
    with open(template_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/jobs")
async def get_jobs(
    status: Optional[str] = None,
    category: Optional[str] = None,
    min_score: int = 20,  # Display anything and everything with match score >= 20
    search: Optional[str] = None,
    limit: int = 250,
):
    """API endpoint to get filtered jobs (displaying everything with match score >= 20)."""
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
    """Update application tracking status for a job."""
    if status not in ["new", "saved", "applied", "interviewing", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    success = db.update_job_status(job_id, status, notes)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "success", "job_id": job_id, "new_status": status}


@app.get("/api/stats")
async def get_stats():
    """Get aggregate statistics for the dashboard."""
    return db.get_stats()


@app.post("/api/trigger-scrape")
async def trigger_scrape():
    """Trigger a manual scrape in the background and update database."""
    try:
        aggregator = ScraperAggregator()
        postings = aggregator.fetch_all(config)
        for p in postings:
            score_job(p, config)
            db.save_job(p)
        return {"status": "success", "new_jobs_found": len(postings)}
    except Exception as e:
        logger.error(f"Manual scrape error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
