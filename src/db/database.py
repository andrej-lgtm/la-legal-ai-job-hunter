"""SQLite database management for job storage, deduplication, and status tracking."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.scrapers.base import JobPosting, calculate_age_display

logger = logging.getLogger(__name__)


class Database:
    """Handles SQLite persistence for job postings."""

    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Create tables if they don't exist and run migrations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    is_remote INTEGER,
                    job_url TEXT NOT NULL,
                    source TEXT,
                    date_posted TEXT,
                    date_discovered TEXT NOT NULL,
                    age_display TEXT DEFAULT '',
                    salary_min REAL,
                    salary_max REAL,
                    salary_currency TEXT DEFAULT 'USD',
                    salary_interval TEXT DEFAULT 'yearly',
                    salary_display TEXT DEFAULT '',
                    description TEXT,
                    description_snippet TEXT,
                    jd_required INTEGER DEFAULT 0,
                    jd_notes TEXT,
                    exp_min INTEGER,
                    exp_max INTEGER,
                    exp_raw TEXT,
                    category TEXT DEFAULT 'General Legal',
                    is_legal_ai INTEGER DEFAULT 0,
                    match_score INTEGER DEFAULT 0,
                    match_reasons TEXT,
                    status TEXT DEFAULT 'new',
                    notes TEXT
                )
                """
            )
            try:
                cursor.execute("ALTER TABLE jobs ADD COLUMN age_display TEXT DEFAULT ''")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE jobs ADD COLUMN salary_display TEXT DEFAULT ''")
            except Exception:
                pass

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    jobs_scraped INTEGER DEFAULT 0,
                    jobs_qualified INTEGER DEFAULT 0,
                    new_jobs_found INTEGER DEFAULT 0
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_score ON jobs(match_score DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON jobs(category)")
            conn.commit()

    def save_job(self, job: JobPosting) -> bool:
        """Insert or update a single job posting."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, status FROM jobs WHERE id = ?", (job.id,))
            row = cursor.fetchone()

            reasons_json = json.dumps(job.match_reasons)
            if not job.age_display:
                job.age_display = calculate_age_display(job.date_posted, job.date_discovered)

            if row is None:
                cursor.execute(
                    """
                    INSERT INTO jobs (
                        id, title, company, location, is_remote, job_url, source,
                        date_posted, date_discovered, age_display, salary_min, salary_max,
                        salary_currency, salary_interval, salary_display,
                        description, description_snippet,
                        jd_required, jd_notes, exp_min, exp_max, exp_raw,
                        category, is_legal_ai, match_score, match_reasons, status
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        job.id,
                        job.title,
                        job.company,
                        job.location,
                        1 if job.is_remote else 0,
                        job.job_url,
                        job.source,
                        job.date_posted,
                        job.date_discovered,
                        job.age_display,
                        job.salary_min,
                        job.salary_max,
                        job.salary_currency,
                        job.salary_interval,
                        job.salary_display,
                        job.description,
                        job.description_snippet,
                        1 if job.jd_required else 0,
                        job.jd_notes,
                        job.exp_min,
                        job.exp_max,
                        job.exp_raw,
                        job.category,
                        1 if job.is_legal_ai else 0,
                        job.match_score,
                        reasons_json,
                        job.status,
                    ),
                )
                conn.commit()
                return True
            else:
                cursor.execute(
                    """
                    UPDATE jobs SET
                        title = ?,
                        company = ?,
                        location = ?,
                        is_remote = ?,
                        date_posted = ?,
                        age_display = ?,
                        salary_min = ?,
                        salary_max = ?,
                        salary_display = ?,
                        description = ?,
                        description_snippet = ?,
                        match_score = ?,
                        match_reasons = ?,
                        category = ?,
                        is_legal_ai = ?,
                        jd_required = ?,
                        jd_notes = ?,
                        exp_min = ?,
                        exp_max = ?,
                        exp_raw = ?
                    WHERE id = ?
                    """,
                    (
                        job.title,
                        job.company,
                        job.location,
                        1 if job.is_remote else 0,
                        job.date_posted,
                        job.age_display,
                        job.salary_min,
                        job.salary_max,
                        job.salary_display,
                        job.description,
                        job.description_snippet,
                        job.match_score,
                        reasons_json,
                        job.category,
                        1 if job.is_legal_ai else 0,
                        1 if job.jd_required else 0,
                        job.jd_notes,
                        job.exp_min,
                        job.exp_max,
                        job.exp_raw,
                        job.id,
                    ),
                )
                conn.commit()
                return False

    def save_jobs(self, jobs: List[JobPosting]) -> Tuple[int, int]:
        """Save a batch of jobs."""
        new_count = 0
        updated_count = 0
        for job in jobs:
            is_new = self.save_job(job)
            if is_new:
                new_count += 1
            else:
                updated_count += 1
        return new_count, updated_count

    def get_jobs(
        self,
        status: Optional[str] = None,
        min_score: int = 0,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[JobPosting]:
        """Fetch jobs based on status, score threshold, and category."""
        query = "SELECT * FROM jobs WHERE match_score >= ?"
        params: List[Any] = [min_score]

        if status:
            query += " AND status = ?"
            params.append(status)

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY match_score DESC, date_discovered DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_posting(r) for r in rows]

    def update_job_status(self, job_id: str, status: str, notes: Optional[str] = None) -> bool:
        """Update job status (e.g. 'applied', 'saved', 'dismissed')."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if notes is not None:
                cursor.execute(
                    "UPDATE jobs SET status = ?, notes = ? WHERE id = ?",
                    (status, notes, job_id),
                )
            else:
                cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics for dashboard."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM jobs")
            total_jobs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM jobs WHERE match_score >= 80")
            qualified_jobs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'applied'")
            applied_jobs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'saved'")
            saved_jobs = cursor.fetchone()[0]

            cursor.execute("SELECT category, COUNT(*) FROM jobs WHERE match_score >= 80 GROUP BY category")
            category_counts = dict(cursor.fetchall())

            return {
                "total_jobs": total_jobs,
                "qualified_jobs": qualified_jobs,
                "applied_jobs": applied_jobs,
                "saved_jobs": saved_jobs,
                "category_counts": category_counts,
            }

    def _row_to_posting(self, row: sqlite3.Row) -> JobPosting:
        reasons = []
        if row["match_reasons"]:
            try:
                reasons = json.loads(row["match_reasons"])
            except Exception:
                reasons = []

        salary_disp = ""
        try:
            salary_disp = row["salary_display"] or ""
        except Exception:
            pass

        age_disp = ""
        try:
            age_disp = row["age_display"] or ""
        except Exception:
            pass

        if not age_disp:
            age_disp = calculate_age_display(row["date_posted"], row["date_discovered"])

        return JobPosting(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            location=row["location"] or "Los Angeles, CA",
            is_remote=bool(row["is_remote"]),
            job_url=row["job_url"],
            source=row["source"] or "Unknown",
            date_posted=row["date_posted"],
            date_discovered=row["date_discovered"],
            age_display=age_disp,
            salary_min=row["salary_min"],
            salary_max=row["salary_max"],
            salary_currency=row["salary_currency"] or "USD",
            salary_interval=row["salary_interval"] or "yearly",
            salary_display=salary_disp,
            description=row["description"] or "",
            description_snippet=row["description_snippet"] or "",
            jd_required=bool(row["jd_required"]),
            jd_notes=row["jd_notes"] or "",
            exp_min=row["exp_min"],
            exp_max=row["exp_max"],
            exp_raw=row["exp_raw"] or "",
            category=row["category"] or "General Legal",
            is_legal_ai=bool(row["is_legal_ai"]),
            match_score=row["match_score"] or 0,
            match_reasons=reasons,
            status=row["status"] or "new",
        )
