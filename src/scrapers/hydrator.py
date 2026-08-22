"""Automated description, metadata, and posting date hydrator for job postings."""

import concurrent.futures
from datetime import datetime, timedelta
import json
import logging
import random
import re
import time
from typing import List, Optional, Tuple
import requests
from bs4 import BeautifulSoup
from src.scrapers.base import JobPosting, clean_html_text
from src.engine.salary_parser import extract_salary

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }


def parse_relative_time_to_age(time_str: str) -> Tuple[str, int]:
    """
    Parse relative time string (e.g. '3 months ago', '1 week ago', '10 hours ago')
    into (age_display, diff_days).
    """
    if not time_str:
        return "🔥 Today", 0

    s = time_str.lower().strip()

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
            d = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            now = datetime.now(d.tzinfo) if d.tzinfo else datetime.now()
        else:
            d = datetime.strptime(time_str[:10], "%Y-%m-%d")
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


def get_effective_hydration_url(url: str) -> str:
    """Convert standard platform URLs into clean, direct guest APIs if applicable."""
    if not url:
        return url

    # LinkedIn: convert /jobs/view/123456 or currentJobId=123456 to guest API endpoint
    if "linkedin.com" in url:
        m = re.search(r"/view/(\d+)", url) or re.search(r"currentJobId=(\d+)", url)
        if m:
            job_id = m.group(1)
            return f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

    return url


def _extract_from_soup(soup: BeautifulSoup) -> Optional[str]:
    """Extract description text from parsed HTML soup."""
    desc_el = (
        soup.find("div", {"class": re.compile(r"show-more-less-html__markup|description__text|details-pane__content")})
        or soup.find("div", {"class": re.compile(r"job-description|job_description|description|posting-requirements|job-details")})
        or soup.find("section", {"class": re.compile(r"description|job-description")})
        or soup.find("div", {"id": re.compile(r"jobDescriptionText|job-description|content")})
        or soup.find("div", {"class": re.compile(r"core-section-container__content")})
    )
    if desc_el:
        txt = clean_html_text(desc_el.get_text(separator="\n"))
        if len(txt) >= 80:
            return txt

    content_el = soup.find("div", {"id": "content"}) or soup.find("div", {"class": "body"}) or soup.find("article") or soup.find("main")
    if content_el:
        txt = clean_html_text(content_el.get_text(separator="\n"))
        if len(txt) >= 80:
            return txt

    return None


def fetch_full_job_details(url: str, retries: int = 2) -> Tuple[Optional[str], Optional[str]]:
    """Fetch description text and exact posted date metadata from public page with multi-strategy fallbacks."""
    if not url or url == "nan":
        return None, None

    candidate_urls = [get_effective_hydration_url(url)]
    # If LinkedIn guest API was generated, also prepare standard public URL as fallback
    if "jobs-guest/jobs/api/jobPosting/" in candidate_urls[0]:
        m = re.search(r"/jobPosting/(\d+)", candidate_urls[0])
        if m:
            candidate_urls.append(f"https://www.linkedin.com/jobs/view/{m.group(1)}/")
    elif candidate_urls[0] != url:
        candidate_urls.append(url)

    session = requests.Session()

    for target_url in candidate_urls:
        for attempt in range(retries + 1):
            try:
                resp = session.get(target_url, headers=_get_headers(), timeout=10)
                if resp.status_code == 429:
                    # Rate limit encountered, backoff briefly
                    time.sleep(1.0 + random.random())
                    continue
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, "html.parser")

                # 1. Extract exact posting date from JSON-LD or HTML elements
                posted_time = None
                for s in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = json.loads(s.get_text())
                        if isinstance(data, dict) and data.get("datePosted"):
                            posted_time = str(data["datePosted"]).strip()
                            break
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and item.get("datePosted"):
                                    posted_time = str(item["datePosted"]).strip()
                                    break
                    except Exception:
                        pass

                if not posted_time:
                    # Check for Last Updated / Posted date text
                    m = re.search(r"(?:Last Updated|Posted|Date Posted):\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})", resp.text, re.IGNORECASE)
                    if m:
                        raw_d = m.group(1).strip()
                        try:
                            d = datetime.strptime(raw_d, "%B %d, %Y")
                            posted_time = d.strftime("%Y-%m-%d")
                        except Exception:
                            posted_time = raw_d

                if not posted_time:
                    time_el = (
                        soup.find("span", {"class": re.compile(r"posted-time-ago|topcard__flavor--metadata")})
                        or soup.find("time")
                    )
                    if time_el:
                        txt = time_el.get_text().strip()
                        if not any(k in txt for k in ["•", "schedule", "locked"]):
                            posted_time = txt

                # 2. Extract description
                desc = _extract_from_soup(soup)
                if desc:
                    return desc, posted_time

            except Exception as e:
                logger.debug(f"Hydration attempt {attempt} for {target_url} failed: {e}")
                time.sleep(0.5)

    return None, None


def hydrate_job(job: JobPosting) -> bool:
    """Hydrate a single job posting with complete description, salary, and exact posting age."""
    if job.description and len(job.description) >= 100:
        return False

    desc, posted_time = fetch_full_job_details(job.job_url)

    updated = False
    if posted_time and not job.date_posted:
        job.date_posted = posted_time
        age_disp, _ = parse_relative_time_to_age(posted_time)
        job.age_display = age_disp
        updated = True

    if desc and len(desc) >= 100:
        job.description = desc
        clean_snippet = re.sub(r"\s+", " ", desc).strip()
        job.description_snippet = clean_snippet[:280] + ("..." if len(clean_snippet) > 280 else "")

        if not job.salary_display:
            sal_min, sal_max, sal_int, sal_disp = extract_salary(desc)
            if sal_disp:
                job.salary_min = sal_min
                job.salary_max = sal_max
                job.salary_interval = sal_int
                job.salary_display = sal_disp

        updated = True

    return updated


def hydrate_jobs(jobs: List[JobPosting], max_workers: int = 5) -> int:
    """Hydrate jobs in parallel with rate pacing."""
    # Only target jobs missing adequate descriptions
    unhydrated = [j for j in jobs if not j.description or len(j.description) < 100]
    if not unhydrated:
        logger.info("All jobs already have full descriptions.")
        return 0

    logger.info(f"Hydrating {len(unhydrated)} unhydrated jobs in parallel...")
    hydrated_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_job = {executor.submit(hydrate_job, j): j for j in unhydrated}
        for future in concurrent.futures.as_completed(future_to_job):
            try:
                success = future.result()
                if success:
                    hydrated_count += 1
            except Exception as e:
                logger.debug(f"Hydration thread error: {e}")

    logger.info(f"Successfully hydrated {hydrated_count} / {len(unhydrated)} jobs.")
    return hydrated_count

