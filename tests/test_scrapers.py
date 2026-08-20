"""Tests for scrapers."""

import pytest
from src.scrapers.ats_scraper import ATSScraper
from src.scrapers.base import JobPosting


def test_ats_scraper_initialization():
    scraper = ATSScraper()
    assert scraper.name == "ATS Direct (Greenhouse / Lever / Ashby)"


def test_job_posting_snippet_generation():
    posting = JobPosting(
        title="In-House Legal Counsel",
        company="Tech Corp",
        job_url="https://tech.corp/legal-counsel",
        description="Paragraph 1 with details.\n\nParagraph 2 with more details.",
    )
    assert len(posting.description_snippet) > 0
    assert "Paragraph 1" in posting.description_snippet
