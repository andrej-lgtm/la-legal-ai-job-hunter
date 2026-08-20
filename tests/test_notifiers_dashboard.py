"""Test notifiers, HTML digest generation, and FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.dashboard.app import app
from src.notifiers.digest_html import generate_html_digest
from src.scrapers.base import JobPosting


def test_html_digest_generation(tmp_path):
    jobs = [
        JobPosting(
            title="Associate Corporate Counsel",
            company="Warner Bros Discovery",
            location="Burbank, CA",
            job_url="https://wbd.com/counsel",
            description="Negotiate TV production agreements. JD required, 2 years experience.",
            match_score=95,
            category="In-House Counsel",
            match_reasons=["🎓 JD required (+35 pts)", "⏳ 1-3 years exp (+30 pts)"],
        )
    ]
    digest_path = generate_html_digest(jobs, output_dir=str(tmp_path))
    assert digest_path.exists()
    content = digest_path.read_text(encoding="utf-8")
    assert "Warner Bros Discovery" in content
    assert "Associate Corporate Counsel" in content
    assert "95" in content


def test_dashboard_api():
    client = TestClient(app)

    # Test dashboard page
    res = client.get("/")
    assert res.status_code == 200
    assert "LA Legal & AI Jobs" in res.text

    # Test stats
    res_stats = client.get("/api/stats")
    assert res_stats.status_code == 200
    assert "total_jobs" in res_stats.json()

    # Test jobs API
    res_jobs = client.get("/api/jobs")
    assert res_jobs.status_code == 200
    assert isinstance(res_jobs.json(), list)
