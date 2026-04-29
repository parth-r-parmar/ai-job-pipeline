"""LinkedIn guest job search scraper."""

import time
import logging
from urllib.parse import urljoin

from .base import BaseScraper

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    SOURCE = "linkedin"
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    PAGE_SIZE = 10

    def scrape(self, keywords: list[str], location: str, pages: int) -> list[dict]:
        # LinkedIn's guest search returns ~3 cards/page when keywords are joined
        # (over-specific match) but ~30 cards/page per single keyword. Iterate
        # per keyword and dedupe by URL across iterations.
        jobs = []
        seen_urls = set()

        for kw in keywords:
            for page in range(pages):
                self._delay()
                start = page * self.PAGE_SIZE
                logger.info(
                    f"[linkedin] Scraping page {page + 1} for '{kw}' in {location}"
                )

                soup = self._fetch_with_retry(
                    self.BASE_URL,
                    params={"keywords": kw, "location": location, "start": start},
                )
                if not soup:
                    continue

                cards = soup.select("div.base-card, li div.base-search-card")
                for card in cards:
                    title_el = card.select_one("h3.base-search-card__title")
                    company_el = card.select_one(
                        "h4.base-search-card__subtitle, a.hidden-nested-link"
                    )
                    location_el = card.select_one("span.job-search-card__location")
                    date_el = card.select_one("time.job-search-card__listdate")
                    link_el = card.select_one(
                        "a.base-card__full-link, a.base-search-card--link"
                    )

                    if not title_el:
                        continue

                    job_url = ""
                    if link_el and link_el.has_attr("href"):
                        job_url = link_el["href"].split("?")[0]
                    if not job_url or job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    posted_date = ""
                    if date_el:
                        posted_date = date_el.get("datetime", date_el.get_text(strip=True))

                    jobs.append(
                        self._normalize_job(
                            {
                                "title": title_el.get_text(strip=True),
                                "company": company_el.get_text(strip=True)
                                if company_el
                                else "",
                                "location": location_el.get_text(strip=True)
                                if location_el
                                else "",
                                "posted_date": posted_date,
                                "url": job_url,
                            }
                        )
                    )

        logger.info(f"[linkedin] Found {len(jobs)} jobs total")
        return jobs

    def _fetch_with_retry(self, url: str, params: dict, max_retries: int = 3):
        """Fetch with exponential backoff on 429 responses."""
        for attempt in range(max_retries):
            soup = self._get(url, params)
            if soup is not None:
                return soup
            # Exponential backoff: 2s, 4s, 8s
            wait = 2 ** (attempt + 1)
            logger.info(f"[linkedin] Retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
        return None
