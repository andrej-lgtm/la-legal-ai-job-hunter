"""Test configuration loading and base data models with deduplication."""

import pytest
from src.config import load_config
from src.scrapers.base import JobPosting, generate_job_id


def test_load_config():
    config = load_config("config.yaml")
    assert len(config.search.queries) > 0
    assert len(config.search.locations) > 0
    assert config.filters.require_jd is True
    assert config.filters.min_experience_years == 1
    assert config.filters.max_experience_years == 3


def test_job_posting_model():
    job = JobPosting(
        title="Associate Counsel",
        company="Snap Inc.",
        location="Santa Monica, CA",
        job_url="https://jobs.snap.com/associate-counsel",
        description="We are seeking an Associate Counsel with a JD and 2 years of experience.",
    )
    assert job.id != ""
    assert len(job.id) == 16
    assert job.company == "Snap Inc."
    assert "Associate Counsel" in job.title
    assert len(job.description_snippet) > 0


def test_job_id_deduplication():
    # Same company, title, location with different URLs or company suffixes
    id1 = generate_job_id("Amazon Web Services (AWS)", "Associate Corporate Counsel, AWS Legal", "Santa Monica, CA")
    id2 = generate_job_id("Amazon.com", "Associate Corporate Counsel, AWS Legal", "Santa Monica, California")
    assert id1 == id2  # Company aliases and location differences normalized
