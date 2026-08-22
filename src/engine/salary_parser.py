"""Salary extraction and formatting engine for job postings supporting all employer formats."""

import re
from typing import Optional, Tuple


def _parse_num(s: str) -> Optional[float]:
    """Parse numeric string with support for standard commas, European dot-thousands, and k suffixes."""
    if not s:
        return None
    s = s.strip().lower()

    # Check European dot-thousands e.g. 120.000,00 or 120.000
    if re.match(r"^\d{1,3}(?:\.\d{3})+(?:,\d{2})?$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        # Standard US comma-thousands e.g. 120,000.00 or 120000
        s = s.replace(",", "")

    mult = 1
    if "k" in s:
        mult = 1000
        s = s.replace("k", "")
    try:
        val = float(s) * mult
        return val
    except ValueError:
        return None


def extract_salary(text: str) -> Tuple[Optional[float], Optional[float], str, str]:
    """
    Extract salary range from text and return (salary_min, salary_max, salary_interval, salary_display).
    Supports all platforms (LinkedIn, Indeed, SmartRecruiters, Greenhouse, etc.).
    """
    if not text:
        return None, None, "yearly", ""

    # Normalize HTML entities, non-breaking spaces, and whitespace
    clean = re.sub(r"&nbsp;|&#160;", " ", text, flags=re.IGNORECASE)
    clean = re.sub(r"[ \t\r\f\v]+", " ", clean)

    # Prefix pattern matching $, USD, USD $, US $, US$, etc.
    CURR = r"(?:USD\s*\$|US\s*\$|USD|\$)"
    NUM = r"(?:\d{1,3}(?:[,\.]\d{3})+(?:\.\d{2}|,\d{2})?|\d{5,7}(?:\.\d{2})?|\d{2,3}\s*[kK])"
    SEP = r"(?:\s*(?:-|–|—|to|and|through|\/)\s*)"
    POSTFIX = r"(?:\s*(?:USD|annually|per year|\/yr|\/year|\/annum|per annum))?"

    # 1. Hourly Range: e.g. "$50.00 - $85.00 / hour", "USD $45 - USD $75 / hr"
    hourly_match = re.search(
        rf"{CURR}?\s*(\d{{2,3}}(?:\.\d{{2}})?)\s*{SEP}\s*{CURR}?\s*(\d{{2,3}}(?:\.\d{{2}})?)\s*(?:\/|\s*per|\s*an)?\s*(?:hr|hour|hourly)",
        clean,
        re.IGNORECASE,
    )
    if hourly_match:
        v1 = _parse_num(hourly_match.group(1))
        v2 = _parse_num(hourly_match.group(2))
        if v1 and v2 and 15 <= v1 <= 450 and 15 <= v2 <= 450:
            low = min(v1, v2)
            high = max(v1, v2)
            return low, high, "hourly", f"💵 ${int(low)} – ${int(high)}/hr"

    # 2. Annual Range with Currency: e.g. "USD $150,000.00 - USD $210,000.00 /Yr.", "$120.000,00 - $250.000,00", "$150k - $200k"
    annual_match = re.search(
        rf"(?:{CURR}\s*)?({NUM})\s*{SEP}\s*(?:{CURR}\s*)?({NUM}){POSTFIX}",
        clean,
        re.IGNORECASE,
    )
    if annual_match:
        start_idx = max(0, annual_match.start() - 40)
        end_idx = min(len(clean), annual_match.end() + 40)
        context = clean[start_idx:end_idx].lower()
        if any(k in context for k in ["$", "usd", "salary", "pay", "compensation", "rate", "yr", "year", "k"]):
            v1 = _parse_num(annual_match.group(1))
            v2 = _parse_num(annual_match.group(2))
            if v1 and v2 and 30000 <= v1 <= 2000000 and 30000 <= v2 <= 2000000:
                low = min(v1, v2)
                high = max(v1, v2)
                k1 = int(round(low / 1000))
                k2 = int(round(high / 1000))
                if k1 == k2:
                    return low, high, "yearly", f"💵 ${k1}k/yr"
                return low, high, "yearly", f"💵 ${k1}k – ${k2}k/yr"

    # 3. Contextual Single Match: e.g. "Salary: $185,000", "Base Pay: USD $175,000 / year", "Up to $225,000"
    single_match = re.search(
        rf"(?:base\s+salary|base\s+pay|compensation|pay\s+range|salary|up\s+to|starting\s+at)(?:[^\$\n\d]{{1,30}}){CURR}?\s*({NUM}){POSTFIX}",
        clean,
        re.IGNORECASE,
    )
    if single_match:
        v = _parse_num(single_match.group(1))
        if v and 30000 <= v <= 2000000:
            k = int(round(v / 1000))
            if "up to" in clean[max(0, single_match.start() - 10):single_match.end()].lower():
                return None, v, "yearly", f"💵 Up to ${k}k/yr"
            return v, v, "yearly", f"💵 ${k}k+/yr"

    return None, None, "yearly", ""


def format_salary_display(min_val: Optional[float], max_val: Optional[float], interval: str = "yearly") -> str:
    """Format numeric salary values into a clean display string."""
    if not min_val and not max_val:
        return ""
    val1 = min_val or max_val
    val2 = max_val or min_val
    if not val1 or not val2:
        return ""
    if interval == "hourly" or (val1 < 500 and val2 < 500):
        if val1 == val2:
            return f"💵 ${int(val1)}/hr"
        return f"💵 ${int(min(val1, val2))} – ${int(max(val1, val2))}/hr"
    else:
        k1 = int(round(min(val1, val2) / 1000))
        k2 = int(round(max(val1, val2) / 1000))
        if k1 == k2:
            return f"💵 ${k1}k/yr"
        return f"💵 ${k1}k – ${k2}k/yr"

