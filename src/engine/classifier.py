"""Job role classifier and Legal AI detector with comprehensive practice group support."""

import re
from typing import Tuple

AI_SPECIFIC_KEYWORDS = [
    r"\b(artificial\s+intelligence|generative\s+ai|genai|gen\s*ai|large\s+language\s+models?|\bllms?\b)\b",
    r"\b(ai\s+governance|ai\s+ethics|ai\s+policy|ai\s+compliance|ai\s+regulation|ai\s+safety|ai\s+risk)\b",
    r"\b(prompt\s+engineering|prompt\s+engineer|machine\s+learning\s+legal)\b",
    r"\b(legal\s+ai|legal\s+technology|legaltech|legal\s+tech|legal\s+innovation)\b",
    r"\b(harvey\s+ai|robin\s+ai|ironclad|casetext|evenup|evisort)\b",
    r"\b(ai\s+practice|ai\s+strategy|ai\s+counsel|ai\s+associate)\b",
]

LEGAL_TITLE_KEYWORDS = [
    r"\b(counsel|attorney|lawyer|legal\s+engineer|legal\s+technologist|legal\s+ops|legal\s+operations|legal\s+innovation)\b",
    r"\b(corporate\s+counsel|commercial\s+counsel|associate\s+counsel|associate\s+attorney)\b",
    r"\b(corporate\s+associate|m&a\s+associate|mergers\s+and\s+acquisitions\s+associate|technology\s+associate|ip\s+associate|privacy\s+associate)\b",
    r"\b(associate\s*[-–—]\s*ai|ai\s+associate|emerging\s+tech\s+associate|associate|litigation\s+associate|litigation\s+attorney)\b",
    r"\b(business\s+&\s+legal\s+affairs|legal\s+affairs|business\s+affairs)\b",
    r"\b(contract\s+manager|contracts\s+manager)\b",
]

NON_LEGAL_TITLES = [
    r"\b(facilities|data\s+center|property\s+manager|practice\s+manager|office\s+manager)\b",
    r"\b(tax\s+manager|accounting|sales|marketing|human\s+resources|recruiter|coordinator)\b",
    r"\b(paralegal|assistant|secretary|clerk|billing|administrator)\b",
    r"\b(software\s+engineer|devops|data\s+scientist|security\s+engineer|systems\s+engineer)\b",
]


def classify_role(title: str, text: str = "") -> Tuple[str, bool]:
    """
    Classify job into category and detect if it is Legal AI related.

    Returns:
        (category, is_legal_ai)
    """
    title_lower = title.lower()
    combined = f"{title}\n{text}".lower()

    # 1. Non-legal title filter -> Instantly reject
    if any(re.search(pat, title_lower, re.IGNORECASE) for pat in NON_LEGAL_TITLES):
        return "Non-Legal / Admin", False

    # 2. Must have legal keyword in title
    if not any(re.search(pat, title_lower, re.IGNORECASE) for pat in LEGAL_TITLE_KEYWORDS):
        return "Non-Legal / Admin", False

    # 3. Check for genuine AI keywords
    is_legal_ai = any(re.search(pat, combined, re.IGNORECASE) for pat in AI_SPECIFIC_KEYWORDS)

    # 4. Legal Engineer / Legal Innovation / Legal Ops check
    if any(w in title_lower for w in ["legal engineer", "legal technologist", "legal ops", "legal operations", "legal innovation"]):
        return "Legal Engineer", is_legal_ai

    # 5. Legal AI specific title (e.g. Associate - AI, AI Counsel, Prompt Lawyer)
    has_ai_title = bool(re.search(r"\b(associate\s*[-–—]\s*ai|ai\s+associate|ai\s+counsel|ai\s+attorney|prompt\s+engineer)\b", title_lower))
    if has_ai_title:
        return "Legal AI", True

    # 6. Litigation Associate check
    if any(w in title_lower for w in [
        "litigation associate", "litigation attorney", "litigation counsel", "trial attorney",
        "defense attorney", "civil litigation", "commercial litigation", "entertainment litigation",
        "wage and hour", "class action", "employment litigation", "labor and employment", "labor & employment", "paga"
    ]):
        return "Litigation Associate", is_legal_ai

    # 7. In-House Counsel / Business Affairs check
    if any(w in title_lower for w in ["in-house", "corporate counsel", "commercial counsel", "product counsel", "privacy counsel", "counsel, corporate", "contracts counsel", "business affairs", "legal affairs"]):
        return "In-House Counsel", is_legal_ai

    # 8. Associate Counsel & Firm Associate check
    if any(w in title_lower for w in ["associate counsel", "associate attorney", "junior counsel", "associate corporate", "associate commercial", "corporate associate", "m&a associate", "mergers and acquisitions associate", "associate"]):
        return "Associate Counsel", is_legal_ai

    # 9. General Counsel/Attorney role
    if "counsel" in title_lower or "attorney" in title_lower or "lawyer" in title_lower:
        return "In-House Counsel", is_legal_ai

    return "Associate Counsel", is_legal_ai
