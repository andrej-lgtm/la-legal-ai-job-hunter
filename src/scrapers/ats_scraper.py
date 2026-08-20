"""Direct ATS scraper for LegalTech, AI companies, and top startups (Greenhouse, Lever, Ashby)."""

import concurrent.futures
import html
import logging
import re
from typing import Any, Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from src.scrapers.base import BaseScraper, JobPosting

logger = logging.getLogger(__name__)

# List of prominent LegalTech, AI, and Tech companies with public ATS endpoints
TARGET_ATS_BOARDS = [
    # Ashby Boards
    {"type": "ashby", "name": "Harvey AI", "token": "harvey"},
    {"type": "ashby", "name": "Perplexity AI", "token": "perplexity"},
    {"type": "ashby", "name": "Ramp", "token": "ramp"},
    {"type": "ashby", "name": "Notion", "token": "notion"},
    # Greenhouse Boards
    {"type": "greenhouse", "name": "Everlaw", "token": "everlaw"},
    {"type": "greenhouse", "name": "Relativity", "token": "relativity"},
    {"type": "greenhouse", "name": "Scale AI", "token": "scaleai"},
    {"type": "greenhouse", "name": "Anthropic", "token": "anthropic"},
    {"type": "greenhouse", "name": "Databricks", "token": "databricks"},
    {"type": "greenhouse", "name": "Riot Games", "token": "riotgames"},
    {"type": "greenhouse", "name": "Scopely", "token": "scopely"},
    {"type": "greenhouse", "name": "SpaceX", "token": "spacex"},
    {"type": "greenhouse", "name": "Anduril Industries", "token": "andurilindustries"},
    {"type": "greenhouse", "name": "Stripe", "token": "stripe"},
    {"type": "greenhouse", "name": "Figma", "token": "figma"},
    {"type": "greenhouse", "name": "Robinhood", "token": "robinhood"},
    {"type": "greenhouse", "name": "Coinbase", "token": "coinbase"},
    {"type": "greenhouse", "name": "Affirm", "token": "affirm"},
    {"type": "greenhouse", "name": "Brex", "token": "brex"},
    {"type": "greenhouse", "name": "Discord", "token": "discord"},
    # Lever Boards
    {"type": "lever", "name": "OpenAI", "token": "openai"},
    {"type": "lever", "name": "Evisort", "token": "evisort"},
]

LEGAL_TITLE_KEYWORDS = [
    r"\b(counsel|attorney|lawyer|legal|compliance|policy|regulatory|contracts|in-house)\b",
    r"\b(legal\s+engineer|legal\s+ops|legal\s+operations|legaltech|ai\s+governance)\b",
]

# Non-legal disqualifiers in title
TITLE_EXCLUSIONS = [
    r"\b(paralegal|legal\s+assistant|legal\s+secretary|administrative|intern|internship)\b",
    r"\b(security\s+engineer|software\s+engineer|devops|data\s+scientist)\b",
]


class ATSScraper(BaseScraper):
    """Direct ATS scraper querying Greenhouse, Lever, and Ashby in parallel."""

    @property
    def name(self) -> str:
        return "ATS Direct (Greenhouse / Lever / Ashby)"

    def search(
        self,
        queries: List[str],
        locations: List[str],
        distance_miles: int = 35,
        results_per_query: int = 15,
        hours_old: int = 72,
    ) -> List[JobPosting]:
        postings: List[JobPosting] = []

        def _fetch_board(board: Dict[str, str]) -> List[JobPosting]:
            b_type = board["type"]
            company_name = board["name"]
            token = board["token"]
            try:
                if b_type == "greenhouse":
                    return self._scrape_greenhouse(company_name, token)
                elif b_type == "lever":
                    return self._scrape_lever(company_name, token)
                elif b_type == "ashby":
                    return self._scrape_ashby(company_name, token)
            except Exception as e:
                logger.warning(f"Error scraping ATS board for {company_name}: {e}")
            return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_fetch_board, b) for b in TARGET_ATS_BOARDS]
            for f in concurrent.futures.as_completed(futures):
                try:
                    res = f.result()
                    if res:
                        postings.extend(res)
                except Exception as e:
                    logger.debug(f"ATS thread error: {e}")

        return postings

    def _scrape_greenhouse(self, company_name: str, token: str) -> List[JobPosting]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []

        data = resp.json()
        jobs_raw = data.get("jobs", [])
        matched: List[JobPosting] = []

        for job in jobs_raw:
            title = job.get("title", "").strip()
            if not self._is_relevant_title(title):
                continue

            location_obj = job.get("location", {})
            location_name = location_obj.get("name", "United States") if isinstance(location_obj, dict) else str(location_obj)

            content_html = job.get("content", "")
            soup = BeautifulSoup(content_html, "html.parser")
            description = soup.get_text(separator="\n").strip()

            job_url = job.get("absolute_url", f"https://boards.greenhouse.io/{token}/jobs/{job.get('id')}")
            date_posted = job.get("updated_at")
            is_remote = "remote" in location_name.lower() or "remote" in title.lower()

            matched.append(
                JobPosting(
                    title=title,
                    company=company_name,
                    location=location_name,
                    is_remote=is_remote,
                    job_url=job_url,
                    source=f"Greenhouse ({company_name})",
                    date_posted=date_posted,
                    description=description,
                )
            )

        return matched

    def _scrape_lever(self, company_name: str, token: str) -> List[JobPosting]:
        url = f"https://api.lever.co/v0/postings/{token}?mode=json"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []

        jobs_raw = resp.json()
        matched: List[JobPosting] = []

        for job in jobs_raw:
            title = job.get("text", "").strip()
            if not self._is_relevant_title(title):
                continue

            categories = job.get("categories", {})
            location_name = categories.get("location", "United States")
            description_plain = job.get("descriptionPlain", "")
            job_url = job.get("hostedUrl", "")
            created_at = job.get("createdAt")
            is_remote = "remote" in location_name.lower() or "remote" in title.lower()

            matched.append(
                JobPosting(
                    title=title,
                    company=company_name,
                    location=location_name,
                    is_remote=is_remote,
                    job_url=job_url,
                    source=f"Lever ({company_name})",
                    date_posted=str(created_at) if created_at else None,
                    description=description_plain,
                )
            )

        return matched

    def _scrape_ashby(self, company_name: str, token: str) -> List[JobPosting]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []

        data = resp.json()
        jobs_raw = data.get("jobs", [])
        matched: List[JobPosting] = []

        for job in jobs_raw:
            title = job.get("title", "").strip()
            if not self._is_relevant_title(title):
                continue

            # Accurate location resolution for Ashby
            loc_city = job.get("location") or ""
            addr = job.get("address", {}) or {}
            postal = addr.get("postalAddress", {}) or {}
            region = postal.get("addressRegion") or ""
            country = postal.get("addressCountry") or ""

            if loc_city and region and region.lower() != loc_city.lower():
                location_name = f"{loc_city}, {region}"
            elif loc_city:
                location_name = loc_city
            elif region:
                location_name = region
            else:
                location_name = "Remote / United States"

            # Check if strictly remote vs specific city
            is_pure_remote = bool(job.get("isRemote")) and (not loc_city or loc_city.lower() in ["remote", "us", "usa", "united states"])

            content_html = job.get("descriptionHtml", "")
            soup = BeautifulSoup(content_html, "html.parser")
            description = soup.get_text(separator="\n").strip()

            job_url = job.get("jobUrl", "")
            date_posted = job.get("publishedAt")

            matched.append(
                JobPosting(
                    title=title,
                    company=company_name,
                    location=location_name,
                    is_remote=is_pure_remote,
                    job_url=job_url,
                    source=f"Ashby ({company_name})",
                    date_posted=date_posted,
                    description=description,
                )
            )

        return matched

    def _is_relevant_title(self, title: str) -> bool:
        """Check if title matches legal / counsel / legal engineer and is not excluded."""
        t_lower = title.lower()
        if any(re.search(pat, t_lower, re.IGNORECASE) for pat in TITLE_EXCLUSIONS):
            if not any(w in t_lower for w in ["legal engineer", "legal ops"]):
                return False
        return any(re.search(pat, t_lower, re.IGNORECASE) for pat in LEGAL_TITLE_KEYWORDS)
