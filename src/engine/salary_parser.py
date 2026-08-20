"""Salary extraction and formatting engine for job postings supporting all employer formats."""

import re
from typing import Optional, Tuple


def extract_salary(text: str) -> Tuple[Optional[float], Optional[float], str, str]:
    """
    Extract salary range from text and return (salary_min, salary_max, salary_interval, salary_display).

    Examples of handled formats:
    - "USA, CA, Culver City - 70,400.00 - 101,800.00 USD annually" -> (70400.0, 101800.0, "yearly", "💵 $70k – $102k/yr")
    - "USA, CA, Culver City - 131,500.00 - 178,000.00 USD annually" -> (131500.0, 178000.0, "yearly", "💵 $132k – $178k/yr")
    - "$185,200.00 - $258,000.00 USD" -> (185200.0, 258000.0, "yearly", "💵 $185k – $258k/yr")
    - "$135,000 to $180,000" -> (135000.0, 180000.0, "yearly", "💵 $135k – $180k/yr")
    - "$225,000 - $235,000" -> (225000.0, 235000.0, "yearly", "💵 $225k – $235k/yr")
    - "$103,100.00-$147,200.00" -> (103100.0, 147200.0, "yearly", "💵 $103k – $147k/yr")
    - "$150k - $200k" -> (150000.0, 200000.0, "yearly", "💵 $150k – $200k/yr")
    - "$50 - $100 / hr" -> (50.0, 100.0, "hourly", "💵 $50 – $100/hr")
    """
    if not text:
        return None, None, "yearly", ""

    # Replace &nbsp; and normalize spaces
    clean = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean)

    # 1. Hourly Pattern ($50 - $100 / hr)
    hourly_match = re.search(
        r"[\$]?\s*([0-9]{2,3}(?:\.[0-9]{2})?)\s*(?:-|–|—|to)\s*[\$]?\s*([0-9]{2,3}(?:\.[0-9]{2})?)\s*(?:\/|\s*per)?\s*(?:hr|hour)",
        clean,
        re.IGNORECASE,
    )
    if hourly_match:
        min_val = float(hourly_match.group(1))
        max_val = float(hourly_match.group(2))
        return min_val, max_val, "hourly", f"💵 ${int(min_val)} – ${int(max_val)}/hr"

    # 2. Universal Range Pattern (with or without $, with or without .00, with or without k)
    m = re.search(
        r"[\$]?\s*([0-9]{2,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)\s*(k)?\s*(?:-|–|—|to)\s*[\$]?\s*([0-9]{2,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)\s*(k)?",
        clean,
        re.IGNORECASE,
    )
    if m:
        raw_min = m.group(1).replace(",", "")
        is_min_k = bool(m.group(2))
        raw_max = m.group(3).replace(",", "")
        is_max_k = bool(m.group(4))

        try:
            min_val = float(raw_min) * (1000 if is_min_k else 1)
            max_val = float(raw_max) * (1000 if is_max_k else 1)

            if min_val >= 25000 and max_val <= 2000000:
                k1 = int(round(min_val / 1000))
                k2 = int(round(max_val / 1000))
                return min_val, max_val, "yearly", f"💵 ${k1}k – ${k2}k/yr"
            elif min_val < 500 and max_val < 500:
                return min_val, max_val, "hourly", f"💵 ${int(min_val)} – ${int(max_val)}/hr"
        except ValueError:
            pass

    # 3. Fallback single value pattern: "base salary: $160,000" or "base pay $180,000"
    single_match = re.search(
        r"(?:base\s+salary|base\s+pay|compensation|salary)(?:[^\$\n]{1,30})[\$]?\s*([0-9]{2,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
        clean,
        re.IGNORECASE,
    )
    if single_match:
        raw_val = single_match.group(1).replace(",", "")
        try:
            val = float(raw_val)
            if val >= 25000:
                k_val = round(val / 1000)
                return val, val, "yearly", f"💵 ${k_val}k+/yr"
        except ValueError:
            pass

    return None, None, "yearly", ""
