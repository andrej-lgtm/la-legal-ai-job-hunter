"""Base classes and data models for job postings and scrapers with robust deduplication, text cleaning, and date parsing."""

import hashlib
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field


def normalize_company(company: str) -> str:
    """Normalize company name to merge common aliases."""
    c = str(company or "").lower().strip()
    c = re.sub(r"\b(inc\.?|llc|corp\.?|corporation|ltd\.?|co\.?|llp|p\.?c\.?)\b", "", c)
    c = re.sub(r"[^\w\s]", "", c).strip()
    c = re.sub(r"\s+", " ", c)
    if any(k in c for k in ["amazon", "aws", "amazon web services"]):
        return "amazon"
    if "pelican" in c:
        return "pelican products"
    if any(k in c for k in ["disney", "hulu", "abc"]):
        return "disney"
    if "riot" in c:
        return "riot games"
    if any(k in c for k in ["nbc", "nbcu", "nbcuniversal", "telemundo", "peacock"]):
        return "nbcuniversal"
    if any(k in c for k in ["paramount", "cbs", "viacom"]):
        return "paramount"
    return c


def normalize_title(title: str) -> str:
    """Normalize title to catch duplicates posted with slight title variations."""
    t = str(title or "").lower().strip()
    t = re.sub(r"\b(remote|hybrid|full[- ]time|onsite|\(remote\)|\(hybrid\)|\(onsite\))\b", "", t)
    t = re.sub(r"[^\w\s]", "", t).strip()
    t = re.sub(r"\s+", " ", t)
    return t


def normalize_location(location: str) -> str:
    """Normalize city name within LA County."""
    loc = str(location or "").lower().strip()
    loc = re.sub(r"\b(ca|california|usa|us|united states)\b", "", loc)
    loc = re.sub(r"[^\w\s]", "", loc).strip()
    loc = re.sub(r"\s+", " ", loc)
    return loc


def generate_job_id(company: str, title: str, location: str = "") -> str:
    """Generate a stable unique SHA256 ID based on normalized company, title, and location."""
    c = normalize_company(company)
    t = normalize_title(title)
    l = normalize_location(location)
    raw = f"{c}|{t}|{l}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def clean_html_text(text: str) -> str:
    """Strip HTML tags, fix mojibake, remove boilerplate navigation, and format cleanly."""
    if not text:
        return ""

    # 1. Fix common mojibake sequences
    mojibake_map = {
        "â€¢": "• ",
        "â€¢": "• ",
        "â€™": "'",
        "â€™": "'",
        "â€˜": "'",
        "â€˜": "'",
        "â€œ": '"',
        "â€œ": '"',
        "â€ ": '"',
        "â€ ": '"',
        "â€“": "–",
        "â€“": "–",
        "â€”": "—",
        "â€”": "—",
        "â€¦": "...",
        "Â": "",
        "\xa0": " ",
        "&nbsp;": " ",
        "&amp;": "&",
        "&quot;": '"',
        "&#39;": "'",
    }
    for bad, good in mojibake_map.items():
        text = text.replace(bad, good)

    # 2. Extract clean text from HTML if tags present
    if "<" in text and ">" in text:
        try:
            soup = BeautifulSoup(text, "html.parser")
            for elem in soup.find_all(["script", "style", "nav", "header", "footer"]):
                elem.decompose()
            for br in soup.find_all("br"):
                br.replace_with("\n")
            for p in soup.find_all(["p", "div", "li", "h1", "h2", "h3", "h4"]):
                p.append("\n")
            text = soup.get_text()
        except Exception:
            text = re.sub(r"<[^>]+>", "\n", text)

    # 3. Clean up EntertainmentCareers navigation and header fluff
    text = re.sub(r"(?is)^.*?play_circle[^\n]*\n", "", text)
    text = re.sub(r"(?is)^.*?Tip of the Week[^\n]*\n", "", text)
    text = re.sub(r"(?is)^.*?Not to worry[^\n]*\n", "", text)
    text = re.sub(r"(?is)^.*?Browse the Legal and Business Affairs[^\n]*\n", "", text)
    text = re.sub(r"^\s*This is a Full Time Job\s*", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*Member Sign In\s*", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s*Job Description\s*", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"(?i)Search for [^\n]+ jobs in [^\n]+\n", "", text)
    text = re.sub(r"(?i)Search all [^\n]+ postings\n", "", text)
    text = re.sub(r"Pursuant to the Los Angeles County Fair Chance Ordinance[^\n]+", "", text)

    # 4. Format lines and sections
    raw_lines = [l.strip() for l in text.split("\n")]
    formatted: List[str] = []

    for line in raw_lines:
        if not line:
            continue
        # Skip job board navigation lines
        if any(nav in line.lower() for nav in ["browse all jobs", "search for corporate", "search all corporate", "job seekers", "premium membership", "local_fire_department", "tip of the week"]):
            continue

        # Strip any existing pin emojis or bullet markers before re-formatting
        clean_line = re.sub(r"^[\s📌•\-\*\|\t]+\s*", "", line).strip()
        if not clean_line:
            continue

        # Format bullet points
        if line.startswith("•") or line.startswith("-") or line.startswith("*") or line.startswith("â€¢"):
            formatted.append(f"  • {clean_line}")
        # Format Section Headers
        elif (line.endswith(":") or clean_line.lower() in [
            "responsibilities", "qualifications", "basic qualifications", "role purpose",
            "summary", "overview", "key responsibilities", "about the role", "here you'll need",
            "what we'll look for", "about us", "desired characteristics"
        ]):
            header_name = clean_line.rstrip(":")
            formatted.append(f"\n📌 {header_name}:")
        else:
            formatted.append(clean_line)

    result = "\n".join(formatted).strip()
    return re.sub(r"\n{3,}", "\n\n", result)


def calculate_age_display(date_posted: Optional[str], date_discovered: Optional[str]) -> Tuple[str, int]:
    """Calculate human-readable age pill and integer diff_days."""
    d_str = (date_posted or date_discovered or "").strip()
    if not d_str:
        return "🔥 Today", 0

    s = d_str.lower()

    # Months / Years
    m_match = re.search(r"(\d+)\s+month", s)
    if m_match:
        months = int(m_match.group(1))
        days = months * 30
        return f"🕒 {months}mo ago", days

    y_match = re.search(r"(\d+)\s+year", s)
    if y_match:
        years = int(y_match.group(1))
        days = years * 365
        return f"🕒 {years}y ago", days

    # Weeks
    w_match = re.search(r"(\d+)\s+week", s)
    if w_match:
        weeks = int(w_match.group(1))
        days = weeks * 7
        return f"🕒 {weeks}w ago", days

    # Days
    d_match = re.search(r"(\d+)\s+day", s)
    if d_match:
        days = int(d_match.group(1))
        if days <= 0:
            return "🔥 Today", 0
        elif days == 1:
            return "🕒 1d ago", 1
        else:
            return f"🕒 {days}d ago", days

    # Hours / Minutes / Just Now / Today
    if any(k in s for k in ["hour", "minute", "moment", "just now", "today", "sec"]):
        return "🔥 Today", 0

    # ISO or YYYY-MM-DD Date
    try:
        if "t" in s:
            d = datetime.fromisoformat(d_str.replace("Z", "+00:00"))
            now = datetime.now(d.tzinfo) if d.tzinfo else datetime.now()
        else:
            d = datetime.strptime(d_str[:10], "%Y-%m-%d")
            now = datetime.now()

        diff_days = (now - d).days
        if diff_days <= 0:
            return "🔥 Today", 0
        elif diff_days == 1:
            return "🕒 1d ago", 1
        elif diff_days < 7:
            return f"🕒 {diff_days}d ago", diff_days
        elif diff_days < 14:
            return "🕒 1w ago", diff_days
        elif diff_days < 21:
            return "🕒 2w ago", diff_days
        elif diff_days <= 30:
            return f"🕒 {diff_days // 7}w ago", diff_days
        else:
            return f"🕒 {diff_days // 30}mo ago", diff_days
    except Exception:
        pass

    return "🔥 Today", 0


class JobPosting(BaseModel):
    """Unified job posting representation."""

    id: str = ""
    title: str
    company: str
    location: str = "Los Angeles, CA"
    is_remote: bool = False
    job_url: str
    source: str = "Unknown"
    date_posted: Optional[str] = None
    date_discovered: str = Field(default_factory=lambda: datetime.now().isoformat())
    age_display: str = ""

    # Compensation
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "USD"
    salary_interval: str = "yearly"
    salary_display: str = ""

    # Description
    description: str = ""
    description_snippet: str = ""

    # Evaluated Intelligence fields
    jd_required: bool = False
    jd_notes: str = ""
    exp_min: Optional[int] = None
    exp_max: Optional[int] = None
    exp_raw: str = ""
    category: str = "General Legal"
    is_legal_ai: bool = False
    match_score: int = 0
    match_reasons: List[str] = Field(default_factory=list)
    status: str = "new"  # new, saved, applied, dismissed

    def model_post_init(self, __context) -> None:
        if not self.id:
            self.id = generate_job_id(self.company, self.title, self.location)
        if not self.age_display:
            age_disp, _ = calculate_age_display(self.date_posted, self.date_discovered)
            self.age_display = age_disp
        if self.description:
            clean_full = clean_html_text(self.description)
            self.description = clean_full
            if not self.description_snippet or "<" in self.description_snippet:
                clean_snippet = re.sub(r"\s+", " ", clean_full).strip()
                self.description_snippet = clean_snippet[:280] + ("..." if len(clean_snippet) > 280 else "")


class BaseScraper(ABC):
    """Abstract base class for all job scrapers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the scraper source."""
        pass

    @abstractmethod
    def search(
        self,
        queries: List[str],
        locations: List[str],
        distance_miles: int = 35,
        results_per_query: int = 15,
        hours_old: int = 720,
    ) -> List[JobPosting]:
        """Fetch job postings matching the search criteria."""
        pass
