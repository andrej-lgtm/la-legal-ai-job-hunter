"""JobSpy scraper integrating LinkedIn, Indeed, and Google Jobs."""

import logging
from typing import List, Optional
import pandas as pd
from jobspy import scrape_jobs

from src.scrapers.base import BaseScraper, JobPosting

logger = logging.getLogger(__name__)


class JobSpyScraper(BaseScraper):
    """Scrapes multiple job boards using python-jobspy."""

    @property
    def name(self) -> str:
        return "JobSpy (LinkedIn/Indeed/Google)"

    def search(
        self,
        queries: List[str],
        locations: List[str],
        distance_miles: int = 35,
        results_per_query: int = 15,
        hours_old: int = 72,
    ) -> List[JobPosting]:
        all_postings: List[JobPosting] = []
        # Target LinkedIn, Indeed, and Google Jobs
        sites = ["linkedin", "indeed", "google"]

        for loc in locations:
            for query in queries:
                logger.info(f"Scraping JobSpy for query: '{query}' in '{loc}'...")
                try:
                    jobs_df: pd.DataFrame = scrape_jobs(
                        site_name=sites,
                        search_term=query,
                        location=loc,
                        distance=distance_miles,
                        results_wanted=results_per_query,
                        hours_old=hours_old,
                        country_indeed="USA",
                        is_remote=False,
                    )

                    if jobs_df is not None and not jobs_df.empty:
                        for _, row in jobs_df.iterrows():
                            posting = self._df_row_to_posting(row)
                            if posting:
                                all_postings.append(posting)
                except Exception as e:
                    logger.warning(f"JobSpy scrape error for '{query}': {e}")
                    continue

        return all_postings

    def _df_row_to_posting(self, row: pd.Series) -> Optional[JobPosting]:
        try:
            title = str(row.get("title", "") or "").strip()
            company = str(row.get("company", "") or "").strip()
            job_url = str(row.get("job_url", "") or row.get("job_url_direct", "") or "").strip()

            if not title or not company or not job_url or job_url == "nan":
                return None

            location = str(row.get("location", "") or "Los Angeles, CA").strip()
            if location == "nan":
                location = "Los Angeles, CA"

            description = str(row.get("description", "") or "").strip()
            if description == "nan":
                description = ""

            source = str(row.get("site", "") or "JobSpy").strip()
            is_remote = bool(row.get("is_remote", False))

            min_amount = row.get("min_amount")
            max_amount = row.get("max_amount")
            salary_min = float(min_amount) if pd.notna(min_amount) else None
            salary_max = float(max_amount) if pd.notna(max_amount) else None

            date_posted = str(row.get("date_posted", "") or "")
            if date_posted == "nan":
                date_posted = None

            return JobPosting(
                title=title,
                company=company,
                location=location,
                is_remote=is_remote,
                job_url=job_url,
                source=source,
                date_posted=date_posted,
                salary_min=salary_min,
                salary_max=salary_max,
                description=description,
            )
        except Exception as e:
            logger.debug(f"Error parsing job row: {e}")
            return None
