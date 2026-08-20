"""Scraper for SmartRecruiters ATS targeting Los Angeles and California legal, compliance, and legal tech roles."""

import concurrent.futures
import logging
import re
from typing import List, Optional
import requests
from src.engine.salary_parser import extract_salary
from src.scrapers.base import BaseScraper, JobPosting, clean_html_text

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

TARGET_COMPANIES = [
    ("NBCUniversal3", "NBCUniversal"),
    ("LiveNationEntertainment", "Live Nation Entertainment"),
    ("Ubisoft2", "Ubisoft"),
    ("Ubisoft", "Ubisoft"),
    ("SquareEnix", "Square Enix"),
    ("Sega", "SEGA"),
    ("PublicisGroupe", "Publicis Groupe"),
    ("AveryDennison", "Avery Dennison"),
    ("Mirantis", "Mirantis"),
    ("Axiado", "Axiado"),
    ("Visa", "Visa"),
    ("BoschGroup", "Bosch"),
    ("Cerebras", "Cerebras Systems"),
    ("EpicGames", "Epic Games"),
    ("Capcom", "Capcom"),
]

LEGAL_KEYWORDS = [
    r"\b(counsel|attorney|lawyer|legal|business\s+affairs|legal\s+affairs|legal\s+ops|legal\s+innovation|legal\s+engineer)\b",
    r"\b(contracts\s+manager|contract\s+manager|licensing\s+manager|compliance|intellectual\s+property|ip\s+counsel)\b",
]


class SmartRecruitersScraper(BaseScraper):
    """Scrapes legal, business affairs, and legal tech postings from SmartRecruiters ATS."""

    @property
    def name(self) -> str:
        return "SmartRecruiters"

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
        seen_ids = set()

        for comp_id, comp_name in TARGET_COMPANIES:
            url = f"https://api.smartrecruiters.com/v1/companies/{comp_id}/postings?limit=100"
            try:
                resp = requests.get(url, headers=HEADERS, timeout=8)
                if resp.status_code != 200:
                    continue

                data = resp.json()
                items = data.get("content", [])

                for item in items:
                    job_id = item.get("id")
                    title = item.get("name", "").strip()
                    loc_obj = item.get("location", {})
                    city = loc_obj.get("city", "")
                    region = loc_obj.get("region", "")
                    country = loc_obj.get("country", "")

                    if not job_id or job_id in seen_ids or not title:
                        continue

                    # Filter for legal-related titles
                    is_legal_title = any(re.search(pat, title, re.IGNORECASE) for pat in LEGAL_KEYWORDS)
                    if not is_legal_title:
                        continue

                    # Check location within California / LA
                    loc_str = f"{city} {region} {country}".lower()
                    if country.lower() not in ["us", "usa", "united states", ""] and "ca" not in loc_str:
                        continue

                    seen_ids.add(job_id)
                    raw_items.append((comp_id, comp_name, job_id, title, city, region, item.get("releasedDate")))

            except Exception as e:
                logger.warning(f"Error querying SmartRecruiters for {comp_id}: {e}")
                continue

        logger.info(f"Fetching {len(raw_items)} SmartRecruiters legal job details in parallel...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_job = {executor.submit(self._fetch_job_detail, *item): item for item in raw_items}
            for future in concurrent.futures.as_completed(future_to_job):
                try:
                    posting = future.result()
                    if posting:
                        all_postings.append(posting)
                except Exception as e:
                    logger.debug(f"Error fetching SmartRecruiters job detail: {e}")

        logger.info(f"SmartRecruiters scraper successfully fetched {len(all_postings)} postings.")
        return all_postings

    def _fetch_job_detail(
        self, comp_id: str, comp_name: str, job_id: str, title: str, city: str, region: str, released_date: Optional[str]
    ) -> Optional[JobPosting]:
        """Fetch full job detail including sections and compensation from SmartRecruiters API."""
        try:
            url = f"https://api.smartrecruiters.com/v1/companies/{comp_id}/postings/{job_id}"
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code != 200:
                return None

            data = resp.json()
            official_url = f"https://jobs.smartrecruiters.com/{comp_id}/{job_id}"

            # Location formatting
            location = "Los Angeles, CA"
            loc_obj = data.get("location", {})
            c = loc_obj.get("city", city)
            r = loc_obj.get("region", region)
            if c:
                location = f"{c}, CA" if ("ca" in str(r).lower() or not r) else f"{c}, {r}"

            # Assemble description sections
            sections = data.get("jobAd", {}).get("sections", {})
            desc_parts = []
            for sec_name in ["companyDescription", "jobDescription", "qualifications", "additionalInformation"]:
                sec = sections.get(sec_name, {})
                t = sec.get("title", "")
                txt = sec.get("text", "")
                if txt:
                    if t:
                        desc_parts.append(f"\n📌 {t}:\n{txt}")
                    else:
                        desc_parts.append(txt)

            full_desc = clean_html_text("\n\n".join(desc_parts))

            # Extract salary
            sal_min, sal_max, sal_int, sal_disp = extract_salary(f"{title}\n{full_desc}")

            return JobPosting(
                title=title,
                company=comp_name,
                location=location,
                job_url=official_url,
                source="SmartRecruiters",
                date_posted=released_date or "Today",
                description=full_desc,
                salary_min=sal_min,
                salary_max=sal_max,
                salary_interval=sal_int,
                salary_display=sal_disp,
            )
        except Exception as e:
            logger.debug(f"Error parsing SmartRecruiters posting {job_id}: {e}")
            return None
