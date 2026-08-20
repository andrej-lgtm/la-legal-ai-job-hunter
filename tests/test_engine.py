"""Unit tests for JD detector, experience parser, classifier, and scorer with real edge cases."""

import pytest
from src.config import load_config
from src.engine.classifier import classify_role
from src.engine.exp_parser import extract_experience
from src.engine.jd_detector import detect_jd_requirement
from src.engine.scorer import score_job
from src.scrapers.base import JobPosting


def test_jd_detection():
    # Strict JD & Bar
    has_jd, is_req, note = detect_jd_requirement(
        "Requirements: Juris Doctor (JD) degree from an accredited law school and active member of the California Bar.",
        "Corporate Counsel",
    )
    assert has_jd is True
    assert is_req is True

    # JD Preferred for Practice Manager
    has_jd, is_req, note = detect_jd_requirement(
        "Education: Bachelor's degree required; JD is a plus.", "Law Practice Manager"
    )
    assert is_req is False  # Non-lawyer admin role

    # JD Edwards false positive
    has_jd, is_req, note = detect_jd_requirement(
        "Experience with JD Edwards ERP system and inventory tracking.", "Operations Lead"
    )
    assert is_req is False


def test_experience_parser():
    # Explicit 1-3 years
    min_y, max_y, raw, match, explicit, reason = extract_experience(
        "Requires 1-3 years of legal experience.", "Associate Counsel"
    )
    assert match is True
    assert explicit is True

    # FedEx written word six (6) years
    min_y, max_y, raw, match, explicit, reason = extract_experience(
        "At least six (6) years of experience in corporate law.", "Sr Attorney I - Sr Counsel"
    )
    assert match is False
    assert "exceeds" in reason.lower() or "senior" in reason.lower()

    # Senior title
    min_y, max_y, raw, match, explicit, reason = extract_experience(
        "Lead corporate tax strategy.", "International Senior Tax Manager"
    )
    assert match is False


def test_false_positive_rejection():
    config = load_config("config.yaml")

    # 1. Senior Tax Manager -> DISQUALIFIED
    job_tax = JobPosting(
        title="[WEBTOON] International Senior Tax Manager",
        company="Webtoon",
        location="El Segundo, CA, US",
        job_url="https://webtoon.com/tax",
        description="Lead global tax and compliance reporting.",
    )
    score, reasons, qual = score_job(job_tax, config)
    assert score < 50
    assert qual is False

    # 2. Director, Production Finance -> DISQUALIFIED
    job_finance = JobPosting(
        title="Director, Production Finance",
        company="Tennis Channel",
        location="Santa Monica, CA",
        job_url="https://tennischannel.com/finance",
        description="Manage production budgeting and forecasting.",
    )
    score, reasons, qual = score_job(job_finance, config)
    assert score < 50
    assert qual is False

    # 3. FedEx Sr Attorney (6 yrs) -> DISQUALIFIED
    job_fedex = JobPosting(
        title="Sr Attorney I - Sr Counsel (multi-level)",
        company="FedEx",
        location="Irvine, CA",
        job_url="https://fedex.com/counsel",
        description="Juris Doctorate required. At least six (6) years of experience.",
    )
    score, reasons, qual = score_job(job_fedex, config)
    assert score < 60
    assert qual is False

    # 4. Real Match: AWS Associate Corporate Counsel (Santa Monica) -> QUALIFIED
    job_aws = JobPosting(
        title="Associate Corporate Counsel, AWS Legal",
        company="Amazon Web Services (AWS)",
        location="Santa Monica, CA",
        job_url="https://amazon.jobs/aws-counsel",
        description="JD required. Member of California Bar. 1-3 years experience in commercial transactions.",
    )
    score, reasons, qual = score_job(job_aws, config)
    assert score >= 90
    assert qual is True
    assert job_aws.category == "In-House Counsel"
