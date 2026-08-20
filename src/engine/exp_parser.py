"""Experience level extraction and 1-4 years filtering module with tiered scoring."""

import re
from typing import Optional, Tuple

WORD_TO_NUM = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
}

# Senior titles and phrases
SENIOR_DISQUALIFIERS = [
    r"\b(general\s+counsel|chief\s+legal\s+officer|clo\b|vp\s+of\s+legal|vice\s+president\s+legal)\b",
    r"\b(senior\s+director|managing\s+director|director[,\s]+production|director[,\s]+tax|director[,\s]+finance)\b",
    r"\b(head\s+of\s+legal|head\s+of\s+compliance|partner|equity\s+partner)\b",
    r"\b(sr\.?\s*attorney|sr\.?\s*counsel|senior\s+attorney|senior\s+counsel|senior\s+corporate\s+counsel|senior\s+commercial\s+counsel|senior\s+legal\s+counsel)\b",
    r"\b(lead\s+counsel|principal\s+counsel|managing\s+counsel|senior\s+tax\s+manager|senior\s+manager)\b",
]

# Patterns to extract experience numbers (digits or words)
EXP_RANGE_PATTERNS = [
    # 1-3 years, 1 to 3 years, 2-4 years, 3-5 years, 8-10 years, 10-15 years
    r"(\d+|one|two|three|four|five|six|seven|eight|ten|twelve|fifteen)\s*(?:-|–|to)\s*(\d+|one|two|three|four|five|six|seven|eight|ten|twelve|fifteen|twenty)\s*\+?\s*years?(?:\s+of)?(?:\s+legal|\s+relevant|\s+in-house|\s+experience|\s+practice|\s+law|\s+pqe|\s+post-bar)?",
    # 10+ years, 7+ years, 5+ years, 2+ years, 1+ year
    r"(\d+|one|two|three|four|five|six|seven|eight|ten|twelve|fifteen)\s*\+\s*years?(?:\s+of)?(?:\s+legal|\s+relevant|\s+in-house|\s+experience|\s+practice|\s+law|\s+pqe|\s+post-bar)?",
    # minimum 10 years, at least four (4) years
    r"(?:minimum\s+(?:of\s+)?|at\s+least\s+)(\d+|one|two|three|four|five|six|seven|eight|ten|twelve|fifteen)(?:\s*\(\s*\d+\s*\))?\s*years?(?:\s+of)?(?:\s+legal|\s+relevant|\s+in-house|\s+experience|\s+practice|\s+law)?",
    # 10 years of experience, 3 years of legal practice
    r"(\d+|one|two|three|four|five|six|seven|eight|ten|twelve|fifteen)\s*years?(?:\s+of)?(?:\s+legal|\s+in-house|\s+relevant|\s+experience|\s+practice|\s+law|\s+pqe)",
]

# Junior indicators
JUNIOR_INDICATORS = [
    r"\b(entry[- ]level|junior|early[- ]career|new\s+grad|first[- ]year|1st\s+year|2nd\s+year|3rd\s+year|junior\s+associate)\b",
    r"\b(associate\s+counsel|junior\s+counsel|assistant\s+counsel|associate\s+corporate\s+counsel|associate\s+commercial\s+counsel|associate\s+attorney)\b",
]


def _parse_num(val: str) -> Optional[int]:
    val_clean = val.strip().lower()
    if val_clean.isdigit():
        return int(val_clean)
    return WORD_TO_NUM.get(val_clean)


def extract_experience(
    text: str, title: str = "", min_target: int = 1, max_target: int = 4
) -> Tuple[Optional[int], Optional[int], str, bool, bool, str]:
    """
    Extract experience years from text and determine if it matches expanded target 1-4 years.

    Returns:
        (min_years, max_years, raw_match_str, is_target_match, is_ideal_1_to_3, reason)
    """
    title_lower = title.lower()
    combined = f"{title}\n{text}".lower()

    has_junior_title = bool(
        re.search(r"\b(associate\s+counsel|associate\s+corporate|associate\s+commercial|associate\s+attorney|junior|assistant\s+counsel|associate\s+director)\b", title_lower)
    )

    # 1. Search for experience numbers first in text/description
    found_ranges = []
    for pattern in EXP_RANGE_PATTERNS:
        for match in re.finditer(pattern, combined, re.IGNORECASE):
            groups = match.groups()
            if len(groups) >= 2 and groups[1] is not None:
                exp_min = _parse_num(groups[0])
                exp_max = _parse_num(groups[1])
                if exp_min is not None:
                    found_ranges.append((exp_min, exp_max, match.group(0)))
            elif len(groups) >= 1 and groups[0] is not None:
                exp_min = _parse_num(groups[0])
                if exp_min is not None:
                    found_ranges.append((exp_min, None, match.group(0)))

    if found_ranges:
        valid_ranges = [r for r in found_ranges if r[0] <= 30]
        if valid_ranges:
            primary = valid_ranges[0]
            exp_min, exp_max, raw_str = primary

            # Disqualification / High requirement check for 5+ years
            if exp_min >= 5:
                return (
                    exp_min,
                    exp_max,
                    raw_str,
                    False,
                    False,
                    f"Requires {exp_min}+ years experience (exceeds 1-4 years target)",
                )

            # Ideal Match: 1-3 years (Harrison's exact sweet spot)
            if exp_min <= 2 or (exp_min == 3 and (exp_max is None or exp_max <= 4)):
                return (
                    exp_min,
                    exp_max,
                    raw_str,
                    True,
                    True,
                    f"Prime 1–3 years experience match ({raw_str.strip()})",
                )
            # Acceptable Reach Match: 3-4 or 4+ years
            elif exp_min <= max_target and (exp_max is None or exp_max <= max_target + 1):
                return (
                    exp_min,
                    exp_max,
                    raw_str,
                    True,
                    False,
                    f"Acceptable 3–4 years reach experience ({raw_str.strip()})",
                )
            else:
                return (
                    exp_min,
                    exp_max,
                    raw_str,
                    False,
                    False,
                    f"Experience requirement {raw_str.strip()} is outside 1-4 years",
                )

    # 2. Check for senior disqualifiers in title if no numbers found
    if any(re.search(pat, title_lower, re.IGNORECASE) for pat in SENIOR_DISQUALIFIERS) and not has_junior_title:
        return None, None, "Senior Title", False, False, f"Senior role detected in title: '{title}'"

    # 3. Check for junior phrasing if no numbers found
    has_junior_phrase = any(re.search(pat, combined, re.IGNORECASE) for pat in JUNIOR_INDICATORS)
    if has_junior_phrase or has_junior_title:
        return 1, 3, "Junior / Associate indicator", True, True, "Title/description indicates early-career legal role (1-3 yrs)"

    # Default fallback: experience unstated (neutral match, not explicit)
    return None, None, "Not explicitly stated", True, False, "Experience level not explicitly stated (associate level)"
