"""Personalized Resume Matcher with continuous progressive experience and practice area calibration."""

import re
from typing import List, Tuple
from src.engine.candidate_profile import CandidateProfile, HARRISON_WHEELER
from src.scrapers.base import JobPosting


def match_candidate_to_job(
    job: JobPosting,
    candidate: CandidateProfile = HARRISON_WHEELER,
) -> Tuple[int, List[str], bool]:
    """
    Score a job posting tailored to Harrison Wheeler's resume:
    - Base: 40 pts for passing Hard Gates (LA County, JD/CA Bar, <30d Recency).
    - Dimension 1: Experience Years Calibration:
        * 1–3 yrs: +25 pts (Target sweet spot)
        * 4 yrs: +10 pts (Feasible reach)
        * 5 yrs: -15 pts (Loses points)
        * 6–7 yrs: -25 pts (Loses points heavily)
        * 8–10 yrs: -35 pts
        * 11–14 yrs: -45 pts
        * 15+ yrs: -60 pts
    - Dimension 2: Seniority Title Calibration (+10 for Associate/Counsel, -20 to -35 for VP/GC/Director).
    - Dimension 3: Practice Area & Domain Fit (+20 for AI/LegalTech, +18 for Entertainment BA, -20 for Real Estate/Tax).
    - Dimension 4: Candidate Superpowers & Studio Affinity (+4 to +10 pts).

    Returns:
        (total_score: int, personalized_reasons: List[str], is_qualified: bool)
    """
    reasons: List[str] = []
    combined_text = f"{job.title}\n{job.description}".lower()
    title_lower = job.title.lower()
    comp_lower = job.company.lower()

    # 1. Base Score for passing all eligibility gates
    score = 40
    reasons.append("✅ Hard Gates: Los Angeles County • CA Bar / JD Required • Active (<30d)")

    # -------------------------------------------------------------------------
    # Dimension 1: Experience Level Calibration & Progressive Penalty (Max +25, Min -60)
    # -------------------------------------------------------------------------
    exp_min = job.exp_min

    if exp_min is not None:
        if 1 <= exp_min <= 3:
            score += 25
            reasons.append("🎯 Prime Timing: Requires 1–3 years experience (Class of 2023 target)")
        elif exp_min == 4:
            score += 10
            reasons.append("⏳ Reach Match: Requires 4 years experience (feasible reach for 2-yr associate)")
        elif exp_min == 5:
            score -= 15
            reasons.append(f"⚠️ Experience Gap (-15 pts): Requires 5 years experience (exceeds 1–4 yr target)")
        elif 6 <= exp_min <= 7:
            score -= 25
            reasons.append(f"⚠️ Experience Gap (-25 pts): Requires {exp_min} years experience (exceeds 1–4 yr target)")
        elif 8 <= exp_min <= 10:
            score -= 35
            reasons.append(f"🚫 Senior Level (-35 pts): Requires {exp_min}+ years experience (exceeds 1–4 yr target)")
        elif 11 <= exp_min <= 14:
            score -= 45
            reasons.append(f"🚫 Executive Level (-45 pts): Requires {exp_min}+ years experience (exceeds 1–4 yr target)")
        elif exp_min >= 15:
            score -= 60
            reasons.append(f"🚫 Over-Senior Executive (-60 pts): Requires {exp_min}+ years experience")
    else:
        # Infer from description or title keywords
        is_explicit_prime = bool(re.search(r"\b(1st-2nd\s+year|2nd\s+year|2nd-3rd\s+year|1-2\s*years?|1-3\s*years?|2\+?\s*years?|class\s+of\s+202[234])\b", combined_text))
        is_reach_4 = bool(re.search(r"\b(3-4\s*years?|2-4\s*years?|4\+?\s*years?|junior\s+to\s+mid)\b", combined_text))
        is_5_7_text = bool(re.search(r"\b(5-7\s*years?|5\+?\s*years?|6-8\s*years?)\b", combined_text))
        has_senior_word = bool(re.search(r"\b(senior|lead|principal|director|vp|vice president|general counsel)\b", title_lower))

        if is_explicit_prime:
            score += 25
            reasons.append("🎯 Prime Timing: Targets 1st–3rd year associate / Class of 2023")
        elif is_reach_4:
            score += 10
            reasons.append("⏳ Reach Match: Targets 3–4 years experience (feasible reach for 2-yr associate)")
        elif is_5_7_text:
            score -= 20
            reasons.append("⚠️ Experience Gap (-20 pts): Targets 5–7 years experience (exceeds 1–4 yr target)")
        elif has_senior_word:
            score -= 20
            reasons.append("⚠️ Senior role indicated by title (-20 pts)")
        else:
            score += 10
            reasons.append("📋 Associate / Counsel level (no rigid years requirement stated)")

    # -------------------------------------------------------------------------
    # Dimension 2: Seniority Title Calibration (+10 to -25 pts)
    # -------------------------------------------------------------------------
    is_senior_exec_title = bool(re.search(r"\b(director|senior director|vp|vice president|general counsel|chief legal officer|partner|managing director|head of legal)\b", title_lower))
    is_target_title = bool(re.search(r"\b(associate|junior counsel|counsel|legal engineer|contract attorney|legal specialist|associate attorney|corporate associate)\b", title_lower))

    if is_senior_exec_title:
        if exp_min and exp_min >= 8:
            score -= 25
            reasons.append("⚠️ Executive Seniority (-25 pts): Title is Director / VP / General Counsel")
        else:
            score -= 15
            reasons.append("⚠️ Senior Title (-15 pts): Director / Head level")
    elif is_target_title:
        score += 10
        reasons.append("💼 Ideal Rank (+10 pts): Associate / Counsel / Legal Engineer title")

    # -------------------------------------------------------------------------
    # Dimension 3: Practice Domain & Specialty Alignment (+20 to -25 pts)
    # -------------------------------------------------------------------------
    # 3A. Negative Domain Penalties (Mismatches for Harrison)
    is_real_estate = bool(re.search(r"\b(real\s+estate|land\s+use|zoning|property\s+acquisition|leasing\s+counsel|construction\s+law|tenant\s+disputes|property\s+management)\b", f"{title_lower} {combined_text}"))
    is_tax_erisa = bool(re.search(r"\b(tax\s+counsel|tax\s+attorney|erisa|executive\s+compensation|partnership\s+tax)\b", f"{title_lower} {combined_text}"))
    is_patent_bar = bool(re.search(r"\b(patent\s+prosecution|patent\s+bar|uspto\s+registration|patent\s+attorney)\b", f"{title_lower} {combined_text}"))
    is_labor_union = bool(re.search(r"\b(nlrb|collective\s+bargaining|labor\s+relations|union\s+negotiations)\b", f"{title_lower} {combined_text}"))

    if is_real_estate:
        score -= 25
        reasons.append("⚠️ Practice Mismatch (-25 pts): Commercial Real Estate & Land Use focus (Target: Media/Tech/Corporate)")
    elif is_tax_erisa:
        score -= 25
        reasons.append("⚠️ Practice Mismatch (-25 pts): Tax / ERISA / Executive Comp focus")
    elif is_patent_bar:
        score -= 30
        reasons.append("⚠️ Practice Mismatch (-30 pts): Requires USPTO Patent Bar registration")
    elif is_labor_union:
        score -= 20
        reasons.append("⚠️ Practice Mismatch (-20 pts): Labor Relations / Union Bargaining focus")

    # 3B. Positive Practice Alignment
    has_ai_focus = bool(re.search(r"\b(legal\s+engineer|associate\s*[-–—]\s*ai|ai\s+associate|ai\s+counsel|ai\s+attorney|prompt|legaltech|legal\s+tech|legal\s+innovation)\b", f"{title_lower} {combined_text}"))
    is_entertainment_role = any(k in f"{comp_lower} {title_lower} {combined_text}" for k in ["entertainment", "studio", "studios", "mgm", "music", "prime video", "gaming", "media", "fox", "riot games", "sony", "live nation", "disney", "netflix", "warner", "paramount", "telemundo", "nbcu", "nbcuniversal", "legendary"])
    is_corp_commercial = any(k in title_lower for k in ["in-house", "corporate counsel", "commercial counsel", "product counsel", "privacy counsel", "legal counsel", "business affairs", "contracts counsel", "corporate associate", "commercial", "technology transactions"])

    if has_ai_focus:
        score += 20
        reasons.append("🤖 Prime Match (+20 pts): Legal AI & Engineering (matches Harvey certification & prompt engineering)")
    elif is_entertainment_role and not is_real_estate:
        score += 18
        reasons.append("🎬 Prime Match (+18 pts): Entertainment & Media Legal (matches MGM/NBCU/AEG background)")
    elif is_corp_commercial:
        score += 15
        reasons.append("🏢 Strong Match (+15 pts): Corporate Transactions, Commercial Contracts & Licensing")
    else:
        score += 10
        reasons.append("⚖️ Corporate / Legal Practice match (+10 pts)")

    # -------------------------------------------------------------------------
    # Dimension 4: Candidate Superpowers & Employer Affinity (+4 to +10 pts)
    # -------------------------------------------------------------------------
    # 4A. LegalTech / GenAI Mention
    has_harvey_or_llm = any(k in combined_text for k in ["harvey", "generative ai", "genai", "prompt", "llm", "large language", "legal tech", "legal technology", "ai-native", "automation", "emerging technology"])
    if has_harvey_or_llm:
        score += 5
        reasons.append("✨ Superpower (+5 pts): Role utilizes AI workflows, GenAI, or LegalTech")

    # 4B. Entertainment Skills
    has_ent_skills = any(k in combined_text for k in ["licensing", "distribution", "merchandising", "chain of title", "copyright", "talent agreements", "sponsorship", "clearance"])
    if has_ent_skills and not is_real_estate:
        score += 4
        reasons.append("🎭 Key Skills (+4 pts): Licensing, copyright, distribution, or talent agreements")

    # 4C. Employer Affinity
    if any(k in comp_lower for k in ["mgm", "amazon mgm", "metro-goldwyn-mayer"]):
        score += 5
        reasons.append("🏆 Direct Alumni Affinity (+5 pts): Former employer (MGM Studios / Amazon MGM)")
    elif any(k in comp_lower for k in ["sony", "prime video", "aeg", "nbcuniversal", "nbcu", "telemundo", "nbc", "fox", "riot", "krafton", "live nation", "paramount", "disney", "espn", "netflix", "warner", "legendary"]):
        score += 4
        reasons.append(f"⭐ Studio Peer Affinity (+4 pts): {job.company}")
    elif any(k in comp_lower for k in ["dla piper", "greenberg traurig", "cooley", "goodwin", "thompson coburn", "simpson thacher"]):
        score += 4
        reasons.append(f"🏛️ BigLaw Peer Match (+4 pts): {job.company}")

    # Clamping
    final_score = max(0, min(100, score))
    job.match_score = final_score
    job.match_reasons = reasons

    is_qualified = final_score >= 70

    return final_score, reasons, is_qualified
