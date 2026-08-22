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
    r"(\d+|one|two|three|four|five|six|seven|eight|ten|twelve|fifteen)\s*(?:-|–|—|to)\s*(\d+|one|two|three|four|five|six|seven|eight|ten|twelve|fifteen|twenty)\s*\+?\s*years?",
    # 10+ years, 7+ years, 6+ years, 5+ years, 2+ years, 6 plus years
    r"(\d+|one|two|three|four|five|six|seven|eight|ten|twelve|fifteen)\s*(?:\+|plus)\s*years?",
    # minimum 10 years, at least four (4) years
    r"(?:minimum\s+(?:of\s+)?|at\s+least\s+)(\d+|one|two|three|four|five|six|seven|eight|ten|twelve|fifteen)(?:\s*\(\s*\d+\s*\))?\s*years?",
    # 10 years of experience, 6 years of relevant California labor and employment experience
    r"(\d+|one|two|three|four|five|six|seven|eight|ten|twelve|fifteen)\s*years?(?:\s+of)?(?:\s+[\w\s,-]{0,50})?\s*(?:experience|practice|law|pqe|post-bar)",
]

# Junior title indicators
JUNIOR_TITLE_INDICATORS = [
    r"\b(entry[- ]level|junior\s+counsel|junior\s+associate|junior\s+attorney|associate\s+counsel|assistant\s+counsel|associate\s+corporate\s+counsel|associate\s+commercial\s+counsel|associate\s+attorney|1st\s+year\s+associate|2nd\s+year\s+associate)\b"
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
    # Unescape markdown backslashes (e.g. 6\+ years -> 6+ years)
    clean_text = text.replace(r"\+", "+").replace(r"\-", "-").replace(r"\(", "(").replace(r"\)", ")").replace("\\", "")
    combined = f"{title}\n{clean_text}".lower()

    has_junior_title = bool(
        re.search(r"\b(associate\s+counsel|associate\s+corporate|associate\s+commercial|associate\s+attorney|junior|assistant\s+counsel|associate\s+director)\b", title_lower)
    )

    # 1. Search for experience numbers across all patterns with position tracking
    found_matches = []
    for pattern in EXP_RANGE_PATTERNS:
        for match in re.finditer(pattern, combined, re.IGNORECASE):
            groups = match.groups()
            exp_min = None
            exp_max = None
            if len(groups) >= 2 and groups[1] is not None:
                exp_min = _parse_num(groups[0])
                exp_max = _parse_num(groups[1])
            elif len(groups) >= 1 and groups[0] is not None:
                exp_min = _parse_num(groups[0])

            if exp_min is not None and exp_min <= 30:
                found_matches.append((match.start(), exp_min, exp_max, match.group(0)))

    if found_matches:
        # Sort by appearance order in text
        found_matches.sort(key=lambda x: x[0])

        # If any requirement specifies 5+ years (e.g. 6+ years legal experience, 2-3 years fintech),
        # prioritize the overarching baseline experience requirement
        senior_matches = [m for m in found_matches if m[1] >= 5]
        if senior_matches:
            primary = senior_matches[0]
        else:
            primary = found_matches[0]

        start_pos, exp_min, exp_max, raw_str = primary

        # Requirement check for 5+ years
        if exp_min >= 5:
            return (
                exp_min,
                exp_max,
                raw_str,
                False,
                False,
                f"Requires {exp_min}+ years experience",
            )

        # Ideal Match: 1-3 years (Harrison's exact sweet spot: 1-2 yrs, 1-3 yrs, 2 yrs, 2-3 yrs)
        is_strict_prime = (
            (exp_min in [1, 2] and (exp_max is None or exp_max <= 3))
            or (exp_min == 3 and exp_max == 3)
        )

        if is_strict_prime:
            return (
                exp_min,
                exp_max,
                raw_str,
                True,
                True,
                f"Prime 1–3 years experience match ({raw_str.strip()})",
            )
        # Reach Match: 3-4 years, 2-4 years, or 4+ years
        elif (exp_min == 3 and (exp_max is None or exp_max >= 4)) or exp_min == 4 or (exp_min == 2 and exp_max and exp_max >= 4):
            return (
                exp_min,
                exp_max,
                raw_str,
                True,
                False,
                f"Reach 3–4 years experience ({raw_str.strip()})",
            )
        else:
            return (
                exp_min,
                exp_max,
                raw_str,
                False,
                False,
                f"Requires {raw_str.strip()}",
            )

    # 2. Check for senior disqualifiers in title if no numbers found
    if any(re.search(pat, title_lower, re.IGNORECASE) for pat in SENIOR_DISQUALIFIERS) and not has_junior_title:
        return None, None, "Senior Title", False, False, f"Senior role detected in title: '{title}'"

    # 3. Check for explicit junior title if no numbers found
    has_explicit_junior = any(re.search(pat, title_lower, re.IGNORECASE) for pat in JUNIOR_TITLE_INDICATORS)
    if has_explicit_junior or has_junior_title:
        return 1, 3, "Junior / Associate indicator", True, True, "Title indicates early-career legal role (1-3 yrs)"

    # Default fallback: experience unstated (neutral match, not explicit)
    return None, None, "Not explicitly stated", True, False, "Experience level not explicitly stated (associate level)"
