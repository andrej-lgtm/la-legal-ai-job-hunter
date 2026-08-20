"""Salary extraction and formatting engine for job postings supporting all employer formats."""

import re
from typing import Optional, Tuple


def extract_salary(text: str) -> Tuple[Optional[float], Optional[float], str, str]:
    """
    Extract salary range from text and return (salary_min, salary_max, salary_interval, salary_display).
    """
    if not text:
        return None, None, "yearly", ""

    # Replace &nbsp; and normalize spaces
    clean = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean)

    # 1. Explicit Hourly Pattern (must have dollar sign and explicit hourly keyword)
    hourly_match = re.search(
        r"(?:\$|USD\s*)\s*([0-9]{2,3}(?:\.[0-9]{2})?)\s*(?:-|–|—|to)\s*(?:\$|USD\s*)?\s*([0-9]{2,3}(?:\.[0-9]{2})?)\s*(?:\/|\s*per|\s*an)?\s*(?:hr|hour|hourly)",
        clean,
        re.IGNORECASE,
    )
    if hourly_match:
        min_val = float(hourly_match.group(1))
        max_val = float(hourly_match.group(2))
        if 20 <= min_val <= 400 and 20 <= max_val <= 400:
            return min_val, max_val, "hourly", f"💵 ${int(min_val)} – ${int(max_val)}/hr"

    # 2. Annual Range with $ / USD / salary context (handles comma and non-comma 5-6 digit numbers or k)
    # Examples: $165300 - $281010, $165,300.00 - $281,010.00, $150k - $200k, 130,000 - 180,000 USD
    annual_match = re.search(
        r"(?:\$|USD\s*)?\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{2})?|[0-9]{5,7}(?:\.[0-9]{2})?|[0-9]{2,3}\s*k)\s*(?:-|–|—|to)\s*(?:\$|USD\s*)?\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{2})?|[0-9]{5,7}(?:\.[0-9]{2})?|[0-9]{2,3}\s*k)\s*(?:USD|annually|per year|\/yr|\/year)?",
        clean,
        re.IGNORECASE,
    )
    if annual_match:
        s1 = annual_match.group(1).replace(",", "").strip().lower()
        s2 = annual_match.group(2).replace(",", "").strip().lower()
        
        try:
            v1 = float(s1.replace("k", "")) * (1000 if "k" in s1 else 1)
            v2 = float(s2.replace("k", "")) * (1000 if "k" in s2 else 1)
            
            if 30000 <= v1 <= 2000000 and 30000 <= v2 <= 2000000:
                k1 = int(round(min(v1, v2) / 1000))
                k2 = int(round(max(v1, v2) / 1000))
                return min(v1, v2), max(v1, v2), "yearly", f"💵 ${k1}k – ${k2}k/yr"
        except ValueError:
            pass

    # 3. Fallback Single Value Pattern (e.g. Base Salary: $165,000 or $180k)
    single_match = re.search(
        r"(?:base\s+salary|base\s+pay|compensation|salary)(?:[^\$\n\d]{1,30})(?:\$|USD\s*)?\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{2})?|[0-9]{5,7}(?:\.[0-9]{2})?|[0-9]{2,3}\s*k)",
        clean,
        re.IGNORECASE,
    )
    if single_match:
        s = single_match.group(1).replace(",", "").strip().lower()
        try:
            v = float(s.replace("k", "")) * (1000 if "k" in s else 1)
            if 30000 <= v <= 2000000:
                k = int(round(v / 1000))
                return v, v, "yearly", f"💵 ${k}k+/yr"
        except ValueError:
            pass

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
