"""Tests for database storage and deduplication."""

import pytest
from src.db.database import Database
from src.scrapers.base import JobPosting


def test_database_crud(tmp_path):
    db_file = tmp_path / "test_jobs.db"
    db = Database(str(db_file))

    job1 = JobPosting(
        title="Associate Counsel",
        company="Riot Games",
        location="Los Angeles, CA",
        job_url="https://riotgames.com/jobs/counsel",
        description="Legal role requiring JD and 2 years experience.",
        match_score=90,
        category="In-House Counsel",
        status="new",
    )

    # 1. Insert
    is_new = db.save_job(job1)
    assert is_new is True

    # 2. Duplicate Insert should update, not fail
    is_new2 = db.save_job(job1)
    assert is_new2 is False

    # 3. Query jobs
    jobs = db.get_jobs(min_score=80)
    assert len(jobs) == 1
    assert jobs[0].company == "Riot Games"
    assert jobs[0].match_score == 90

    # 4. Update status
    db.update_job_status(job1.id, "applied", notes="Applied on company portal")
    updated = db.get_jobs(status="applied")
    assert len(updated) == 1

    # 5. Stats
    stats = db.get_stats()
    assert stats["total_jobs"] == 1
    assert stats["applied_jobs"] == 1
    assert stats["category_counts"]["In-House Counsel"] == 1
