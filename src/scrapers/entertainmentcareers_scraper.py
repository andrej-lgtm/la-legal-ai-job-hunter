"""Scraper for EntertainmentCareers.net targeting Hollywood & Los Angeles entertainment legal roles in parallel."""

import concurrent.futures
import json
import logging
import re
from datetime import datetime
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from src.scrapers.base import BaseScraper, JobPosting, clean_html_text
from src.engine.salary_parser import extract_salary

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class EntertainmentCareersScraper(BaseScraper):
    """Scrapes entertainment legal and business affairs jobs from EntertainmentCareers.net."""

    @property
    def name(self) -> str:
        return "EntertainmentCareers.net"

    def search(
        self,
        queries: List[str] = None,
        locations: List[str] = None,
        distance_miles: int = 35,
        results_per_query: int = 30,
        hours_old: int = 720,
    ) -> List[JobPosting]:
        all_postings: List[JobPosting] = []
        raw_items = []
        seen_urls = set()

        search_terms = [
            "legal",
            "counsel",
            "attorney",
            "business-affairs",
            "legal-affairs",
            "contracts",
            "associate-counsel",
            "business-and-legal-affairs",
            "corporate-counsel",
            "legal-innovation",
        ]

        for term in search_terms:
            url = f"https://www.entertainmentcareers.net/search/{term}/los-angeles-ca/"
            logger.info(f"Scraping EntertainmentCareers.net index for '{term}'...")
            try:
                resp = requests.get(url, headers=HEADERS, timeout=8)
                resp.encoding = "utf-8"
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                job_links = soup.find_all("a", href=re.compile(r"/job/\d+/"))

                for link in job_links:
                    href = link.get("href", "")
                    full_url = "https://www.entertainmentcareers.net" + href if href.startswith("/") else href
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    title = link.get_text().strip()
                    if not title or len(title) < 3 or "member sign in" in title.lower():
                        continue

                    raw_items.append((full_url, title))

            except Exception as e:
                logger.warning(f"Error scraping EntertainmentCareers term '{term}': {e}")
                continue

        logger.info(f"Fetching {len(raw_items)} job details from EntertainmentCareers in parallel...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            future_to_job = {executor.submit(self._fetch_job_detail, item[0], item[1]): item for item in raw_items}
            for future in concurrent.futures.as_completed(future_to_job):
                try:
                    posting = future.result()
                    if posting:
                        all_postings.append(posting)
                except Exception as e:
                    logger.debug(f"Error fetching detail: {e}")

        logger.info(f"EntertainmentCareers scraper successfully fetched {len(all_postings)} postings.")
        return all_postings

    def _fetch_job_detail(self, url: str, title: str) -> Optional[JobPosting]:
        """Fetch individual job detail page to extract company, description, date, and salary with clean UTF-8."""
        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            resp.encoding = "utf-8"
            if resp.status_code != 200:
                return None

            # Skip if posting has been removed or filled
            if re.search(r"This position has been filled|removed by the employer", resp.text, re.IGNORECASE):
                logger.info(f"Skipping expired/removed EntertainmentCareers job: {url}")
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            h1 = soup.find("h1")
            if h1:
                t = h1.get_text().strip()
                t = re.sub(r"\s*-\s*EntertainmentCareers\.net.*$", "", t).strip()
                if len(t) > 3:
                    title = t

            company = "Entertainment Company"
            comp_el = (
                soup.find("div", {"class": re.compile(r"job-company|company-name")})
                or soup.find("h2")
                or soup.find("span", {"class": "company"})
            )
            if comp_el:
                company = comp_el.get_text().strip()
                company = re.sub(r"^About\s+", "", company).strip()

            location = "Los Angeles, CA"
            loc_el = soup.find("span", {"class": re.compile(r"location|city")})
            if loc_el:
                loc_text = loc_el.get_text().strip()
                if any(k in loc_text.lower() for k in ["los angeles", "burbank", "culver", "hollywood", "santa monica", "beverly", "universal city"]):
                    location = loc_text

            # Extract exact posted date from JSON-LD schema or HTML text
            posted_date = "Today"
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.get_text())
                    if isinstance(data, dict) and data.get("datePosted"):
                        posted_date = data["datePosted"]
                        break
                except Exception:
                    pass

            if posted_date == "Today":
                m = re.search(r"Posted:\s*([A-Za-z]+\s+\d{1,2},\s*\d{4})", resp.text, re.IGNORECASE)
                if m:
                    raw_date = m.group(1).strip()
                    try:
                        d = datetime.strptime(raw_date, "%B %d, %Y")
                        posted_date = d.strftime("%Y-%m-%d")
                    except Exception:
                        posted_date = raw_date

            desc_el = (
                soup.find("div", {"class": re.compile(r"column\s+middle|job-description|description|job_description")})
                or soup.find("article")
                or soup.find("body")
            )
            desc = clean_html_text(desc_el.get_text(separator="\n")) if desc_el else ""

            sal_min, sal_max, sal_int, sal_disp = extract_salary(f"{title}\n{desc}")

            return JobPosting(
                title=title,
                company=company,
                location=location,
                job_url=url,
                source="EntertainmentCareers.net",
                date_posted=posted_date,
                description=desc,
                salary_min=sal_min,
                salary_max=sal_max,
                salary_interval=sal_int,
                salary_display=sal_disp,
            )
        except Exception as e:
            logger.debug(f"Error parsing EntertainmentCareers job detail {url}: {e}")
            return None
