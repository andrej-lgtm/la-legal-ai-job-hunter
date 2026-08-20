"""Personalized Resume Matcher with continuous progressive experience, practice area calibration, pay alignment, and clean pills."""

import re
from typing import List, Optional, Tuple
from src.engine.candidate_profile import CandidateProfile, HARRISON_WHEELER
from src.scrapers.base import JobPosting


def match_candidate_to_job(
    job: JobPosting,
    candidate: CandidateProfile = HARRISON_WHEELER,
) -> Tuple[int, List[str], bool]:
    """
    Score a job posting tailored to Harrison Wheeler's resume:
    - Base: 40 pts for passing Hard Gates (LA County, JD/CA Bar, <30d Recency).
    - Dimension 1: Experience Years Calibration (1-3 yrs: +25, 4 yrs: +10, 5 yrs: -15, 6-7 yrs: -25, 8-10 yrs: -35, 11-14 yrs: -45, 15+ yrs: -60).
    - Dimension 2: Seniority Title Calibration (+10 for Associate/Counsel, -15 to -25 for VP/GC/Director).
    - Dimension 3: Practice Area & Domain Fit (+20 for AI/LegalTech, +18 for Entertainment BA, -25 for Litigation, -25 for Real Estate/Tax).
    - Dimension 4: Candidate Superpowers & Studio Affinity (+4 to +10 pts).
    - Dimension 5: Compensation Alignment (Ideal: $170k+ / $80+/hr: +10, $140k-$169k: -5, $110k-$139k: -15, <$110k: -25, Unstated: 0 neutral).

    Returns:
        (total_score: int, personalized_reasons: List[str], is_qualified: bool)
    """
    reasons: List[str] = []
    combined_text = f"{job.title}\n{job.description}".lower()
    title_lower = job.title.lower()
    comp_lower = job.company.lower()

    # 1. Base Score for passing all eligibility gates (hard gates pill removed per user request)
    score = 40

    # -------------------------------------------------------------------------
    # Dimension 1: Experience Level Calibration & Progressive Penalty
    # -------------------------------------------------------------------------
    exp_min = getattr(job, "exp_min", None)
    exp_max = getattr(job, "exp_max", None)

    is_explicit_prime = bool(re.search(r"\b(1st[- ]2nd\s+year|1st\s+year|2nd\s+year|2nd[- ]3rd\s+year|1[- ]2\s*years?|1[- ]3\s*years?|1\s*to\s*2\s*years?|1\s*to\s*3\s*years?|class\s+of\s+202[234])\b", combined_text))
    is_reach_3_4 = bool(re.search(r"\b(3[- ]4\s*years?|3[- ]5\s*years?|2[- ]4\s*years?|3\+?\s*years?|4\+?\s*years?|3\s*to\s*4\s*years?|3\s*to\s*5\s*years?|junior\s+to\s+mid)\b", combined_text))

    if exp_min is not None:
        # True Prime Experience (1-3 years): requires 1-2 yrs, 1-3 yrs, 2 yrs, 2-3 yrs, or 3 yrs max
        if (exp_min in [1, 2] and (exp_max is None or exp_max <= 3)) or (exp_min == 3 and exp_max == 3):
            score += 25
            reasons.append("🎯 Prime Experience: Requires 1–3 years experience")
        # Reach Experience (3-4 years): requires 3-4 yrs, 2-4 yrs, 4 yrs, 4+ yrs
        elif (exp_min == 3 and (exp_max is None or exp_max >= 4)) or exp_min == 4 or (exp_min == 2 and exp_max and exp_max >= 4):
            score -= 5
            reasons.append("⚠️ Reach Experience: Requires 3–4 years experience")
        elif exp_min == 5:
            score -= 15
            reasons.append("⚠️ Experience Gap: Requires 5 years experience")
        elif 6 <= exp_min <= 7:
            score -= 25
            reasons.append(f"⚠️ Experience Gap: Requires {exp_min} years experience")
        elif 8 <= exp_min <= 10:
            score -= 35
            reasons.append(f"🚫 Senior Level: Requires {exp_min}+ years experience")
        elif 11 <= exp_min <= 14:
            score -= 45
            reasons.append(f"🚫 Executive Level: Requires {exp_min}+ years experience")
        elif exp_min >= 15:
            score -= 60
            reasons.append(f"🚫 Over-Senior Executive: Requires {exp_min}+ years experience")
    else:
        # Infer from description or title keywords
        is_5_7_text = bool(re.search(r"\b(5[- ]7\s*years?|5\+?\s*years?|6[- ]8\s*years?)\b", combined_text))
        is_8_plus_text = bool(re.search(r"\b(8\+?\s*years?|10\+?\s*years?|12\+?\s*years?)\b", combined_text))
        has_senior_word = bool(re.search(r"\b(senior|lead|principal|director|vp|vice president|general counsel)\b", title_lower))

        if is_explicit_prime:
            score += 25
            reasons.append("🎯 Prime Experience: Requires 1–3 years experience")
        elif is_reach_3_4:
            score -= 5
            reasons.append("⚠️ Reach Experience: Requires 3–4 years experience")
        elif is_5_7_text:
            score -= 20
            reasons.append("⚠️ Experience Gap: Requires 5–7 years experience")
        elif is_8_plus_text:
            score -= 35
            reasons.append("🚫 Senior Level: Requires 8+ years experience")
        elif has_senior_word:
            score -= 20
            reasons.append("⚠️ Senior role indicated by title")

    # -------------------------------------------------------------------------
    # Dimension 2: Seniority Title Calibration
    # -------------------------------------------------------------------------
    is_senior_exec_title = bool(re.search(r"\b(director|senior director|vp|vice president|general counsel|chief legal officer|partner|managing director|head of legal)\b", title_lower))
    is_target_title = bool(re.search(r"\b(associate|junior counsel|counsel|legal engineer|contract attorney|legal specialist|associate attorney|corporate associate|litigation associate)\b", title_lower))

    if is_senior_exec_title:
        if exp_min and exp_min >= 8:
            score -= 25
            reasons.append("⚠️ Executive Seniority")
        else:
            score -= 15
            reasons.append("⚠️ Senior Title")
    elif is_target_title:
        score += 10
        reasons.append("💼 Ideal Position")

    # -------------------------------------------------------------------------
    # Dimension 3: Practice Domain & Specialty Alignment
    # -------------------------------------------------------------------------
    # 3A. Negative Domain Penalties (Mismatches for Harrison)
    is_real_estate = bool(re.search(r"\b(real\s+estate|land\s+use|zoning|property\s+acquisition|leasing\s+counsel|construction\s+law|tenant\s+disputes|property\s+management)\b", f"{title_lower} {combined_text}"))
    is_tax_erisa = bool(re.search(r"\b(tax\s+counsel|tax\s+attorney|erisa|executive\s+compensation|partnership\s+tax)\b", f"{title_lower} {combined_text}"))
    is_patent_bar = bool(re.search(r"\b(patent\s+prosecution|patent\s+bar|uspto\s+registration|patent\s+attorney)\b", f"{title_lower} {combined_text}"))
    is_labor_union = bool(re.search(r"\b(nlrb|collective\s+bargaining|labor\s+relations|union\s+negotiations)\b", f"{title_lower} {combined_text}"))
    is_litigation = bool(re.search(r"\b(litigation|trial\s+attorney|defense\s+attorney|civil\s+litigation|commercial\s+litigation|entertainment\s+litigation|personal\s+injury|lemon\s+law|insurance\s+defense|complex\s+litigation|trial\s+lawyer|wage\s+and\s+hour|class\s+action|employment\s+litigation|paga|labor\s+and\s+employment|labor\s+&\s+employment)\b", f"{title_lower} {combined_text}"))

    if is_real_estate:
        score -= 25
        reasons.append("⚠️ Practice Mismatch: Commercial Real Estate & Land Use")
    elif is_tax_erisa:
        score -= 25
        reasons.append("⚠️ Practice Mismatch: Tax & ERISA")
    elif is_patent_bar:
        score -= 30
        reasons.append("⚠️ Practice Mismatch: Requires Patent Bar")
    elif is_labor_union:
        score -= 20
        reasons.append("⚠️ Practice Mismatch: Labor Relations")
    elif is_litigation:
        score -= 25
        reasons.append("⚖️ Litigation Practice: Secondary focus")

    # 3B. Positive Practice Alignment
    has_ai_focus = bool(re.search(r"\b(legal\s+engineer|associate\s*[-–—]\s*ai|ai\s+associate|ai\s+counsel|ai\s+attorney|prompt|legaltech|legal\s+tech|legal\s+innovation)\b", f"{title_lower} {combined_text}"))
    is_entertainment_role = any(k in f"{comp_lower} {title_lower} {combined_text}" for k in ["entertainment", "studio", "studios", "mgm", "music", "prime video", "gaming", "media", "fox", "riot games", "sony", "live nation", "disney", "netflix", "warner", "paramount", "telemundo", "nbcu", "nbcuniversal", "legendary"])
    is_corp_commercial = any(k in title_lower for k in ["in-house", "corporate counsel", "commercial counsel", "product counsel", "privacy counsel", "legal counsel", "business affairs", "contracts counsel", "corporate associate", "commercial", "technology transactions"])

    if has_ai_focus:
        score += 20
        reasons.append("🤖 Prime Match: Legal AI & Engineering")
    elif is_entertainment_role and not is_real_estate:
        score += 18
        reasons.append("🎬 Prime Match: Entertainment & Media Legal")
    elif is_corp_commercial:
        score += 15
        reasons.append("🏢 Strong Match: Corporate Transactions & Licensing")
    elif not is_litigation:
        score += 10
        reasons.append("⚖️ Corporate / Legal Practice match")

    # -------------------------------------------------------------------------
    # Dimension 4: Candidate Superpowers & Employer Affinity
    # -------------------------------------------------------------------------
    # 4A. LegalTech / GenAI Mention
    has_harvey_or_llm = any(k in combined_text for k in ["harvey", "generative ai", "genai", "prompt", "llm", "large language", "legal tech", "legal technology", "ai-native", "automation", "emerging technology"])
    if has_harvey_or_llm:
        score += 5
        reasons.append("✨ Superpower: Role utilizes AI & LegalTech")

    # 4B. Entertainment Skills
    has_ent_skills = any(k in combined_text for k in ["licensing", "distribution", "merchandising", "chain of title", "copyright", "talent agreements", "sponsorship", "clearance"])
    if has_ent_skills and not is_real_estate:
        score += 4
        reasons.append("🎭 Key Skills: Licensing, copyright & distribution")

    # 4C. Litigation Skills (When applicable)
    if is_litigation:
        has_lit_skills = any(k in combined_text for k in ["discovery", "motions", "motion practice", "depositions", "briefs", "courtroom", "trial prep"])
        if has_lit_skills:
            score += 5
            reasons.append("📑 Case Skills: Discovery, motions & depositions")

    # 4D. Employer Affinity
    if any(k in comp_lower for k in ["mgm", "amazon mgm", "metro-goldwyn-mayer"]):
        score += 5
        reasons.append("🏆 Alumni Affinity")
    elif any(k in comp_lower for k in ["sony", "prime video", "aeg", "nbcuniversal", "nbcu", "telemundo", "nbc", "fox", "riot", "krafton", "live nation", "paramount", "disney", "espn", "netflix", "warner", "legendary"]):
        score += 4
        reasons.append("⭐ Studio Peer")
    elif any(k in comp_lower for k in ["dla piper", "greenberg traurig", "cooley", "goodwin", "thompson coburn", "simpson thacher"]):
        score += 4
        reasons.append("🏛️ BigLaw Peer")

    # -------------------------------------------------------------------------
    # Dimension 5: Compensation Alignment (Calculated in score, pill suppressed per user request)
    # -------------------------------------------------------------------------
    effective_pay: Optional[float] = None
    if job.salary_max or job.salary_min:
        val = job.salary_max or job.salary_min
        if job.salary_interval == "hourly":
            effective_pay = val * 2080.0
        else:
            effective_pay = val

    if effective_pay is not None:
        if effective_pay >= 170000.0:
            pass  # No bonus, standard neutral baseline
        elif 150000.0 <= effective_pay < 170000.0:
            score -= 5
        elif 125000.0 <= effective_pay < 150000.0:
            score -= 20
        elif 100000.0 <= effective_pay < 125000.0:
            score -= 35
        elif effective_pay < 100000.0:
            score -= 50

    # Clamping
    final_score = max(0, min(100, score))
    job.match_score = final_score
    job.match_reasons = reasons

    is_qualified = final_score >= 70

    return final_score, reasons, is_qualified
