"""Strict multi-tier scorer enforcing hard gates, strict JD requirement, and candidate-tailored resume scoring."""

import re
from typing import List, Tuple
from src.config import AppConfig
from src.engine.classifier import classify_role
from src.engine.exp_parser import extract_experience
from src.engine.jd_detector import detect_jd_requirement
from src.engine.resume_matcher import match_candidate_to_job
from src.engine.salary_parser import extract_salary
from src.scrapers.base import JobPosting, calculate_age_display

# Strict Los Angeles County Municipalities & Neighborhoods
LA_COUNTY_CITIES = [
    r"\b(los\s+angeles|la|greater\s+los\s+angeles|los\s+angeles\s+metropolitan\s+area|la\s+metro)\b",
    r"\b(beverly\s+hills|santa\s+monica|culver\s+city|century\s+city|westwood|west\s+hollywood|burbank|glendale|pasadena)\b",
    r"\b(playa\s+vista|venice|el\s+segundo|manhattan\s+beach|hermosa\s+beach|redondo\s+beach|torrance|long\s+beach)\b",
    r"\b(studio\s+city|universal\s+city|hollywood|woodland\s+hills|calabasas|sherman\s+oaks|encino|valencia|santa\s+clarita)\b",
    r"\b(downtown\s+los\s+angeles|dtla|marina\s+del\s+rey|culver|burbank|woodland\s+hills|hawthorne|commerce)\b",
]

NON_LA_COUNTY_PATTERNS = [
    r"\b(san\s+francisco|bay\s+area|silicon\s+valley|san\s+jose|palo\s+alto|mountain\s+view|sunnyvale|oakland|berkeley|menlo\s+park|redwood\s+city)\b",
    r"\b(orange\s+county|irvine|newport\s+beach|costa\s+mesa|anaheim)\b",
    r"\b(san\s+diego|la\s+jolla|carlsbad)\b",
    r"\b(new\s+york|ny|chicago|seattle|austin|boston|denver|london|miami|dallas|washington\s+d\.?c\.?|atlanta)\b",
]

DISQUALIFIED_TITLE_PATTERNS = [
    r"\b(facilities|property\s+manager|data\s+center|practice\s+manager|office\s+manager)\b",
    r"\b(floater|billing|administrator|manager,\s+recruiting)\b",
    r"\b(tax\s+manager|sales\s+director|account\s+executive|product\s+manager)\b",
    r"\b(software\s+engineer|devops|data\s+scientist|security\s+engineer|systems\s+engineer)\b",
    r"\b(driver|photographer|producer|editor|audio|camera|janitor|maintenance)\b",
    r"\b(paralegal|legal\s+assistant|legal\s+secretary|clerk|coordinator)\b",
    # Pure Litigation Roles Disqualification
    r"\b(litigation\s+associate|litigation\s+attorney|litigation\s+counsel|trial\s+attorney|defense\s+attorney|civil\s+litigation\s+associate)\b",
    r"\b(personal\s+injury|lemon\s+law|insurance\s+defense|workers\s+comp|workers'\s+comp|wage\s+and\s+hour|class\s+action\s+associate)\b",
    r"\b(complex\s+business\s+litigation|entertainment\s+litigation|appellate\s+associate|litigation\s+contract\s+attorney)\b",
]


def score_job(job: JobPosting, config: AppConfig) -> Tuple[int, List[str], bool]:
    """
    Score a job posting by first enforcing hard criteria gates (including strict JD requirement),
    then applying personalized candidate resume matching (Harrison Wheeler).

    Returns:
        (score, reasons, is_qualified)
    """
    title_lower = job.title.lower()
    loc_lower = job.location.lower()
    combined_lower = f"{job.title}\n{job.location}\n{job.description}".lower()

    # Calculate exact age display and diff_days
    age_disp, diff_days = calculate_age_display(job.date_posted, job.date_discovered)
    job.age_display = age_disp

    # -------------------------------------------------------------
    # 1. HARD 30-DAY AGE CUTOFF GATE
    # -------------------------------------------------------------
    if diff_days > 30:
        job.match_score = 0
        job.match_reasons = [f"🚫 Job posting is {age_disp.replace('🕒 ', '')} ({diff_days} days old, exceeds 30-day limit)"]
        return 0, job.match_reasons, False

    # Extract Salary Range
    sal_min, sal_max, sal_int, sal_disp = extract_salary(f"{job.title}\n{job.description}")
    if sal_disp:
        job.salary_min = sal_min
        job.salary_max = sal_max
        job.salary_interval = sal_int
        job.salary_display = sal_disp

    # -------------------------------------------------------------
    # 2. HARD GEOGRAPHIC GATE (STRICT LA COUNTY ONLY)
    # -------------------------------------------------------------
    is_explicit_non_la = any(re.search(pat, loc_lower, re.IGNORECASE) for pat in NON_LA_COUNTY_PATTERNS)
    is_la_county = any(re.search(pat, loc_lower, re.IGNORECASE) for pat in LA_COUNTY_CITIES) or "los angeles" in combined_lower

    if is_explicit_non_la and not is_la_county:
        job.match_score = 0
        job.match_reasons = [f"🚫 Location not in Los Angeles County: '{job.location}'"]
        return 0, job.match_reasons, False

    if not is_la_county:
        job.match_score = 0
        job.match_reasons = [f"🚫 Location not in Los Angeles County: '{job.location}'"]
        return 0, job.match_reasons, False

    # -------------------------------------------------------------
    # 2B. HARD JURISDICTION & CA STATE BAR GATE
    # -------------------------------------------------------------
    # Check for foreign/UK qualification (Solicitor / Barrister)
    if bool(re.search(r"\b(solicitor\s+or\s+barrister|qualified\s+as\s+solicitor|sra\s+regulated)\b", combined_lower)) and "california" not in combined_lower:
        job.match_score = 0
        job.match_reasons = ["🚫 Requires UK/Foreign legal qualification (Solicitor/Barrister)"]
        return 0, job.match_reasons, False

    # Check for out-of-state office requirement (e.g. New York HQ / Bristol CT)
    has_out_of_state_office = bool(
        re.search(r"\b(based\s+out\s+of\s+(?:the\s+)?[a-z\s]*new\s+york|location:\s*bristol|office\s+in\s+bristol|must\s+reside\s+in\s+new\s+york|headquarters\s+in\s+new\s+york)\b", combined_lower)
    )
    if has_out_of_state_office and ("ascap new york" in combined_lower or "location: bristol" in combined_lower):
        job.match_score = 0
        job.match_reasons = ["🚫 Office requirement is based outside California (e.g. New York HQ / Bristol CT)"]
        return 0, job.match_reasons, False

    # Check for explicit Out-of-State Bar only
    has_ny_bar_only = bool(re.search(r"\b(practice\s+law\s+in\s+new\s+york\s+state|licensed\s+in\s+new\s+york\s+state|new\s+york\s+state\s+bar\s+required|admission\s+to\s+connecticut\s+state\s+bar\s+or\s+new\s+york\s+state\s+bar)\b", combined_lower))
    allows_ca_or_any = bool(re.search(r"\b(california|ca\s+bar|any\s+(?:u\.?s\.?\s+)?state\s+bar|at\s+least\s+one\s+(?:u\.?s\.?\s+)?(?:state\s+)?bar|other\s+(?:u\.?s\.?\s+)?state\s+bar|another\s+(?:u\.?s\.?\s+)?state\s+bar|in-house\s+counsel\s+registration|or\s+california|or\s+other\b)\b", combined_lower))

    if has_ny_bar_only and not allows_ca_or_any:
        job.match_score = 0
        job.match_reasons = ["🚫 Requires New York State Bar admission (Candidate holds State Bar of California license)"]
        return 0, job.match_reasons, False

    # -------------------------------------------------------------
    # 3. PURE LITIGATION DISQUALIFICATION
    # -------------------------------------------------------------
    is_pure_litigation = any(re.search(pat, title_lower, re.IGNORECASE) for pat in [
        r"\b(litigation\s+associate|litigation\s+attorney|litigation\s+counsel|trial\s+attorney|defense\s+attorney|civil\s+litigation)\b",
        r"\b(personal\s+injury|lemon\s+law|insurance\s+defense|workers\s+comp|wage\s+and\s+hour|class\s+action)\b",
        r"\b(complex\s+business\s+litigation|entertainment\s+litigation|contract\s+attorney\s+complex\s+business\s+litigation)\b",
    ])
    if is_pure_litigation:
        job.match_score = 0
        job.match_reasons = [f"🚫 Pure litigation role excluded: '{job.title}' (Focus: In-House, Tech/AI, Corporate & Entertainment)"]
        return 0, job.match_reasons, False

    if any(re.search(pat, title_lower, re.IGNORECASE) for pat in DISQUALIFIED_TITLE_PATTERNS):
        job.match_score = 0
        job.match_reasons = [f"🚫 Disqualified role/title: '{job.title}'"]
        return 0, job.match_reasons, False

    # -------------------------------------------------------------
    # 4. STRICT HARD JD & BAR REQUIREMENT GATE (USER DIRECTIVE)
    # -------------------------------------------------------------
    has_jd, is_jd_req, jd_notes = detect_jd_requirement(job.description, job.title)
    job.jd_required = is_jd_req
    job.jd_notes = jd_notes

    if not is_jd_req:
        job.match_score = 0
        job.match_reasons = [f"🚫 JD / CA Bar not required ({jd_notes})"]
        return 0, job.match_reasons, False

    # Classify role
    cat, is_ai = classify_role(job.title, job.description)
    job.category = cat
    job.is_legal_ai = is_ai

    # Experience check
    exp_min, exp_max, exp_raw, is_exp_match, is_ideal, exp_reason = extract_experience(
        job.description, job.title, min_target=config.filters.min_experience_years, max_target=config.filters.max_experience_years
    )
    job.exp_min = exp_min
    job.exp_max = exp_max
    job.exp_raw = exp_raw

    # -------------------------------------------------------------
    # GRADED MATCHING TIERS FOR JD ROLES (20% to 100%)
    # -------------------------------------------------------------

    # TIER 1: Prime & Reach Target JD Roles (75% - 100%)
    if is_exp_match:
        total_score, match_reasons, is_qualified = match_candidate_to_job(job)
        job.match_score = total_score
        job.match_reasons = match_reasons
        return total_score, match_reasons, is_qualified

    # TIER 2: Senior / Stretch Legal Roles in LA (55% - 74%)
    reasons = []
    if exp_min and exp_min >= 5:
        reasons.append(f"⚠️ Requires {exp_min}+ years experience")
    elif "Senior role detected in title" in exp_reason:
        reasons.append(f"⚠️ {exp_reason}")
    else:
        reasons.append(f"📋 {exp_reason}")

    reasons.append("🎓 JD / CA Bar Required")

    if "business affairs" in title_lower or "business and legal" in title_lower or "entertainment" in combined_lower:
        reasons.append("🎬 Entertainment & Media Business Affairs in LA")
    elif is_ai or "ai" in title_lower or "legal innovation" in title_lower:
        reasons.append("🤖 Legal AI & Technology Operations")
    elif "contracts" in title_lower or "licensing" in title_lower:
        reasons.append("📑 Commercial Contracts & Licensing in LA")
    else:
        reasons.append("🏢 Corporate & Commercial Legal in LA")

    score = 55
    if "counsel" in title_lower or "business affairs" in title_lower or "corporate" in title_lower:
        score += 10
    if any(co in combined_lower for co in ["nbc", "disney", "paramount", "amazon", "sony", "warner", "fox", "netflix"]):
        score += 5

    job.match_score = score
    job.match_reasons = reasons
    return score, reasons, True
