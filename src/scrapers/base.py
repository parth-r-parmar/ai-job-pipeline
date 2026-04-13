"""Abstract base class for all job scrapers."""

import abc
import time
import random
import logging

import requests
from bs4 import BeautifulSoup

from src.config import (
    REQUEST_DELAY_MIN, REQUEST_DELAY_MAX,
    REQUEST_TIMEOUT, FALLBACK_USER_AGENTS,
)

logger = logging.getLogger(__name__)

try:
    from fake_useragent import UserAgent
    _ua_instance = UserAgent()
except Exception:
    _ua_instance = None


class BaseScraper(abc.ABC):
    """Common scraping infrastructure with rotating user-agents and rate limiting."""

    SOURCE: str = ""

    def __init__(self):
        self.session = requests.Session()

    def _get_user_agent(self) -> str:
        if _ua_instance:
            try:
                return _ua_instance.random
            except Exception:
                pass
        return random.choice(FALLBACK_USER_AGENTS)

    def _delay(self):
        time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

    def _get(self, url: str, params: dict = None) -> BeautifulSoup | None:
        headers = {
            "User-Agent": self._get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            resp = self.session.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            logger.warning(f"[{self.SOURCE}] Request failed for {url}: {e}")
            return None

    def _get_json(self, url: str, params: dict = None) -> dict | None:
        headers = {"User-Agent": self._get_user_agent(), "Accept": "application/json"}
        try:
            resp = self.session.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            logger.warning(f"[{self.SOURCE}] JSON request failed for {url}: {e}")
            return None

    def _normalize_job(self, raw: dict) -> dict:
        return {
            "title": raw.get("title", "N/A"),
            "company": raw.get("company", "N/A"),
            "location": raw.get("location", "N/A"),
            "experience": raw.get("experience", "N/A"),
            "salary": raw.get("salary", "Not disclosed"),
            "job_type": raw.get("job_type", "N/A"),
            "posted_date": raw.get("posted_date", "N/A"),
            "description": raw.get("description", ""),
            "url": raw.get("url", ""),
            "source": self.SOURCE,
        }

    def _fetch_description(self, url: str) -> str:
        """Fetch full job description from a detail page URL."""
        if not url:
            return ""
        self._delay()
        soup = self._get(url)
        if not soup:
            return ""
        for selector in [
            "div.show-more-less-html__markup",  # LinkedIn
            "div.description__text",            # LinkedIn alt
            "div.about_job div.text",           # Internshala
            "div.about_job",                    # Internshala alt
            "div.job-description",              # Generic
            "div[class*='description']",        # Fallback
        ]:
            el = soup.select_one(selector)
            if el and len(el.get_text(strip=True)) > 50:
                return el.get_text(strip=True)[:3000]
        return ""

    def enrich_descriptions(self, jobs: list[dict], max_fetches: int = 20):
        """Fetch full descriptions for jobs that have URLs but empty/short descriptions."""
        fetched = 0
        for job in jobs:
            if fetched >= max_fetches:
                break
            if len(job.get("description", "")) < 50 and job.get("url"):
                desc = self._fetch_description(job["url"])
                if desc:
                    job["description"] = desc
                    fetched += 1
                    logger.info(f"[{self.SOURCE}] Fetched description for: {job.get('title')}")
        if fetched:
            logger.info(f"[{self.SOURCE}] Enriched {fetched} job descriptions")

    @abc.abstractmethod
    def scrape(self, keywords: list[str], location: str, pages: int) -> list[dict]:
        ...
