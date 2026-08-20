"""Personalized Resume Matcher matching job postings against Candidate Profile (Harrison Wheeler)."""

import re
from typing import List, Tuple
from src.engine.candidate_profile import CandidateProfile, HARRISON_WHEELER
from src.scrapers.base import JobPosting


def match_candidate_to_job(
    job: JobPosting,
    candidate: CandidateProfile = HARRISON_WHEELER,
) -> Tuple[int, List[str], bool]:
    """
    Score a job posting specifically tailored to Harrison Wheeler's resume:
    - Base Qualification: 50 pts for passing LA County, JD/CA Bar, 1-4 Yrs Exp, and <=30d Recency.
    - Dimension 1: Practice Area Alignment (+12 to +20 pts)
    - Dimension 2: Candidate Superpowers & Skills (+8 to +15 pts)
    - Dimension 3: Experience & Class Year Exact Match (1-3 yrs: +10 pts, 3-4 yrs reach: +5 pts)
    - Dimension 4: Employer & Studio Affinity Bonus (+3 to +5 pts)

    Returns:
        (total_score: int, personalized_reasons: List[str], is_qualified: bool)
    """
    reasons: List[str] = []
    combined_text = f"{job.title}\n{job.description}".lower()
    title_lower = job.title.lower()
    comp_lower = job.company.lower()

    # 1. Base Score for passing all eligibility gates
    score = 50
    reasons.append("✅ Hard Gates: Los Angeles County • CA Bar / JD Required • 1–4 Yrs Exp • Active (<30d)")

    # -------------------------------------------------------------------------
    # Dimension 1: Practice Area Alignment (Max 20 pts)
    # -------------------------------------------------------------------------
    has_ai_title = bool(re.search(r"\b(legal\s+engineer|associate\s*[-–—]\s*ai|ai\s+associate|ai\s+counsel|ai\s+attorney|prompt)\b", title_lower))
    is_entertainment_role = any(k in f"{comp_lower} {title_lower} {combined_text}" for k in ["entertainment", "studio", "studios", "mgm", "music", "prime video", "gaming", "media", "fox", "riot games", "sony", "live nation", "disney", "netflix", "warner", "paramount", "telemundo", "nbcu", "nbcuniversal"])
    is_inhouse_corp = any(k in title_lower for k in ["in-house", "corporate counsel", "commercial counsel", "product counsel", "privacy counsel", "legal counsel", "business affairs", "contract manager", "legal affairs"])
    is_firm_associate = any(k in title_lower for k in ["associate attorney", "corporate associate", "litigation associate", "associate"])

    if has_ai_title:
        score += 20
        reasons.append("🤖 Prime Match: Legal AI & Engineering role (matches your Harvey certification & LLM workflows)")
    elif is_entertainment_role:
        score += 20
        reasons.append("🎬 Prime Match: Entertainment & Media In-House legal (matches your MGM/AEG/Gaumont/NBCU background)")
    elif is_inhouse_corp:
        score += 18
        reasons.append("🏢 Strong Match: In-House Corporate / Commercial Counsel role (matches your contract & compliance background)")
    elif is_firm_associate:
        score += 16
        reasons.append("⚖️ Strong Match: Law Firm Associate role (matches your active litigation & CA Bar admission)")
    else:
        score += 12
        reasons.append("📄 General Legal practice match")

    # -------------------------------------------------------------------------
    # Dimension 2: Candidate Superpower & Skill Overlap (Max 15 pts)
    # -------------------------------------------------------------------------
    skill_pts = 0

    # 2A. AI & Tech Overlap
    has_harvey_or_llm = any(k in combined_text for k in ["harvey", "generative ai", "genai", "prompt", "llm", "large language", "legal tech", "legal technology", "ai-native", "automation", "emerging technology"])
    if has_harvey_or_llm:
        skill_pts += 6
        reasons.append("✨ Superpower: Role utilizes AI workflows, GenAI, or LegalTech")

    # 2B. Entertainment & IP Overlap
    has_ent_skills = any(k in combined_text for k in ["licensing", "distribution", "merchandising", "chain of title", "copyright", "talent agreements", "sponsorship", "clearance"])
    if has_ent_skills:
        skill_pts += 5
        reasons.append("🎭 Key Skills: Involves licensing, copyright, distribution, or talent agreements")

    # 2C. Litigation & Commercial Contracts Overlap
    has_lit_skills = any(k in combined_text for k in ["litigation", "depositions", "discovery", "motions", "motion practice", "settlement", "mediation", "commercial contracts", "drafting"])
    if has_lit_skills:
        skill_pts += 4
        reasons.append("📑 Core Skills: Commercial drafting, discovery, motion practice, or dispute resolution")

    score += min(15, skill_pts)

    # -------------------------------------------------------------------------
    # Dimension 3: Experience Level & Class Year Match (Max 10 pts)
    # -------------------------------------------------------------------------
    is_prime_1_3 = bool(re.search(r"\b(1st-2nd\s+year|2nd\s+year|2nd-3rd\s+year|class\s+of\s+202[234]|1-2\s*years?|1-3\s*years?|2\+?\s*years?)\b", combined_text))
    is_reach_4 = bool(re.search(r"\b(3-4\s*years?|3-5\s*years?|2-4\s*years?|4\+?\s*years?|4\s*years?|mid[- ]level)\b", combined_text))

    if is_prime_1_3 and not (job.exp_min and job.exp_min >= 4):
        score += 10
        reasons.append("🎯 Prime Timing: Targets 1–3 years experience / Class of 2023 (~2 yrs post-bar)")
    elif is_reach_4 or (job.exp_min and job.exp_min in [3, 4]):
        score += 5
        reasons.append("⏳ Reach Match: Targets 3–4 years experience (feasible reach for 2-year associate)")
    else:
        score += 6
        reasons.append("⏳ Associate level within 1–4 years experience window")

    # -------------------------------------------------------------------------
    # Dimension 4: Employer / Studio Affinity Bonus (Max 5 pts)
    # -------------------------------------------------------------------------
    if any(k in comp_lower for k in ["mgm", "amazon mgm", "metro-goldwyn-mayer"]):
        score += 5
        reasons.append("🏆 Direct Alumni Affinity: Former employer (MGM Studios / Amazon MGM)")
    elif any(k in comp_lower for k in ["sony", "prime video", "aeg", "nbcuniversal", "nbcu", "telemundo", "nbc", "fox", "riot", "krafton", "live nation", "paramount", "disney", "espn"]):
        score += 5
        reasons.append(f"⭐ Studio / Entertainment Peer Affinity: {job.company}")
    elif any(k in comp_lower for k in ["dla piper", "greenberg traurig", "cooley", "goodwin", "thompson coburn", "simpson thacher"]):
        score += 5
        reasons.append(f"🏛️ BigLaw Peer Match: {job.company}")
    else:
        score += 3
        reasons.append(f"📍 Prime LA Location: {job.location}")

    final_score = max(0, min(100, score))
    job.match_score = final_score
    job.match_reasons = reasons

    is_qualified = final_score >= 75

    return final_score, reasons, is_qualified
