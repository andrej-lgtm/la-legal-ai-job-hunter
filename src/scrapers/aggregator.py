"""Scraper aggregator to execute all scrapers, deduplicate results, and hydrate full descriptions."""

import logging
from typing import Dict, List
from src.config import AppConfig
from src.scrapers.ats_scraper import ATSScraper
from src.scrapers.base import BaseScraper, JobPosting
from src.scrapers.entertainmentcareers_scraper import EntertainmentCareersScraper
from src.scrapers.hydrator import hydrate_jobs
from src.scrapers.jobspy_scraper import JobSpyScraper
from src.scrapers.smartrecruiters_scraper import SmartRecruitersScraper

logger = logging.getLogger(__name__)


class ScraperAggregator:
    """Orchestrates job scraping across multiple sources."""

    def __init__(self, scrapers: List[BaseScraper] = None):
        if scrapers is None:
            self.scrapers = [
                ATSScraper(),
                JobSpyScraper(),
                EntertainmentCareersScraper(),
                SmartRecruitersScraper(),
            ]
        else:
            self.scrapers = scrapers

    def fetch_all(self, config: AppConfig) -> List[JobPosting]:
        """Fetch jobs from all scrapers, deduplicate, and hydrate complete descriptions."""
        all_jobs: Dict[str, JobPosting] = {}

        for scraper in self.scrapers:
            logger.info(f"Running scraper: {scraper.name}...")
            try:
                postings = scraper.search(
                    queries=config.search.queries,
                    locations=config.search.locations,
                    distance_miles=config.search.distance_miles,
                    results_per_query=config.search.results_per_query,
                    hours_old=config.search.hours_old,
                )
                logger.info(f"Scraper {scraper.name} returned {len(postings)} raw postings.")

                for posting in postings:
                    if posting.id not in all_jobs:
                        all_jobs[posting.id] = posting
            except Exception as e:
                logger.error(f"Error executing scraper {scraper.name}: {e}")

        jobs_list = list(all_jobs.values())
        logger.info(f"Total unique postings fetched across all sources: {len(jobs_list)}")

        hydrate_jobs(jobs_list)

        return jobs_list
