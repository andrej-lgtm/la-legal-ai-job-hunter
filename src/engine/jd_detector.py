"""JD (Juris Doctor) and Bar admission detector with enhanced distinction for JD Required vs Preferred vs Non-Lawyer roles."""

import re
from typing import Tuple

# Regex patterns for JD and Bar admission
JD_PATTERNS = [
    r"\b(juris\s+doctor|juris\s+doctorate|juris\s+doctoral)\b",
    r"\b(j\.?\s*d\.?(?!\s*edwards))\b",  # Avoid "JD Edwards" ERP
    r"\b(law\s+degree|graduat(?:e|ed)\s+from\s+an\s+aba[- ]accredited\s+law\s+school)\b",
    r"\b(aba[- ]accredited\s+law\s+school)\b",
]

BAR_PATTERNS = [
    r"\b(member\s+of\s+(?:the\s+)?california\s+bar|ca\s+bar\s+admission|california\s+state\s+bar)\b",
    r"\b(admitted\s+to\s+(?:the\s+)?(?:state\s+bar\s+of\s+)?california|admitted\s+to\s+practice\s+in\s+ca|admitted\s+in\s+california)\b",
    r"\b(active\s+member\s+in\s+good\s+standing\s+of\s+(?:the\s+)?(?:california\s+)?bar)\b",
    r"\b(licensed\s+to\s+practice\s+law\s+in\s+(?:the\s+state\s+of\s+)?california)\b",
    r"\b(active\s+bar\s+license|admitted\s+to\s+(?:the\s+)?bar|bar\s+admission)\b",
    r"\b(licensed\s+attorney|licensed\s+to\s+practice\s+law)\b",
]

# Patterns where JD is expressly marked as preferred or optional
JD_PREFERRED_PATTERNS = [
    r"\b(j\.?\s*d\.?|juris\s+doctor|law\s+degree)\s+(?:is\s+)?(?:preferred|a\s+plus|optional|desired)\b",
    r"\b(?:preferred|plus|desired|optional)[:\s]+[^\n\.\;]*(?:a\s+)?(j\.?\s*d\.?|juris\s+doctor|law\s+degree)\b",
    r"\b(bachelor(?:'s)?\s+degree\s+required[^\n\.\;]*(?:j\.?\s*d\.?|juris\s+doctor)\s+(?:is\s+)?(?:a\s+plus|preferred))\b",
    r"\b(cpa\s+or\s+j\.?\s*d\.?|j\.?\s*d\.?\s+or\s+cpa)\b",
]

# Non-attorney management / admin / assistant roles where JD is not required
NON_LAWYER_TITLES = [
    r"\b(practice\s+manager|office\s+manager|billing|tax\s+manager|finance\s+manager|accounting\s+manager)\b",
    r"\b(paralegal|legal\s+assistant|legal\s+secretary|contract\s+administrator|coordinator|clerk)\b",
    r"\b(executive\s+assistant|administrative\s+assistant|assistant\s+to|administrative\s+coordinator)\b",
    r"\b(director[,\s]+production\s+finance|finance\s+director)\b",
]


def detect_jd_requirement(text: str, title: str = "") -> Tuple[bool, bool, str]:
    """
    Detect if a job posting requires or prefers a JD or Bar admission.

    Returns:
        (has_jd_mention, is_strictly_required, notes)
    """
    title_lower = title.lower()
    combined_text = f"{title}\n{text}".lower()

    # Filter out JD Edwards false positive
    clean_text = re.sub(r"\bjd\s+edwards\b", "", combined_text, flags=re.IGNORECASE)

    # Check if title is a non-lawyer administrative/finance/assistant role
    if any(re.search(pat, title_lower, re.IGNORECASE) for pat in NON_LAWYER_TITLES):
        return False, False, "Non-lawyer operational/admin/assistant role (JD not required)"

    has_bar_mention = any(re.search(pat, clean_text, re.IGNORECASE) for pat in BAR_PATTERNS)
    has_jd_mention = any(re.search(pat, clean_text, re.IGNORECASE) for pat in JD_PATTERNS)
    is_preferred = any(re.search(pat, clean_text, re.IGNORECASE) for pat in JD_PREFERRED_PATTERNS)

    if has_bar_mention:
        return True, True, "Bar admission / CA Bar required"

    if has_jd_mention:
        if is_preferred:
            return True, False, "JD preferred / plus (optional)"
        return True, True, "JD required"

    # Check for explicit Attorney / Counsel / Law Firm Associate title
    attorney_title_match = re.search(
        r"\b(counsel|attorney|lawyer|corporate\s+associate|m&a\s+associate|mergers\s+and\s+acquisitions\s+associate|associate\s*[-–—]\s*ai|ai\s+associate|technology\s+associate)\b",
        title_lower,
    )
    if attorney_title_match and not any(re.search(pat, title_lower, re.IGNORECASE) for pat in NON_LAWYER_TITLES):
        return True, True, "Attorney/Counsel role (JD required by title)"

    return False, False, "No JD / Bar requirement found"
