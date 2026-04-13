"""Indeed.co.in job scraper."""

import logging
from urllib.parse import quote_plus, urljoin

from .base import BaseScraper

logger = logging.getLogger(__name__)


class IndeedScraper(BaseScraper):
    SOURCE = "indeed"
    BASE_URL = "https://www.indeed.co.in/jobs"

    def scrape(self, keywords: list[str], location: str, pages: int) -> list[dict]:
        jobs = []
        query = " ".join(keywords)

        for page in range(pages):
            self._delay()
            start = page * 10
            logger.info(f"[indeed] Scraping page {page + 1} for '{query}' in {location}")

            soup = self._get(
                self.BASE_URL,
                params={"q": query, "l": location, "start": start},
            )
            if not soup:
                continue

            cards = soup.select("div.job_seen_beacon, div.resultContent")
            if not cards:
                # Try alternative selectors
                cards = soup.select("div.tapItem, td.resultContent")

            for card in cards:
                title_el = card.select_one(
                    "h2.jobTitle a, h2.jobTitle span, a.jcs-JobTitle"
                )
                company_el = card.select_one(
                    'span[data-testid="company-name"], span.companyName'
                )
                location_el = card.select_one(
                    'div[data-testid="text-location"], div.companyLocation'
                )
                salary_el = card.select_one(
                    "div.salary-snippet-container, div.metadata.salary-snippet-container"
                )
                date_el = card.select_one("span.date, span.visually-hidden")
                snippet_el = card.select_one("div.job-snippet, td.snip")

                # Extract job URL
                link_el = card.select_one("a[href*='/rc/clk'], a.jcs-JobTitle, h2.jobTitle a")
                job_url = ""
                if link_el and link_el.has_attr("href"):
                    href = link_el["href"]
                    job_url = urljoin("https://www.indeed.co.in", href)

                jobs.append(
                    self._normalize_job(
                        {
                            "title": title_el.get_text(strip=True)
                            if title_el
                            else "",
                            "company": company_el.get_text(strip=True)
                            if company_el
                            else "",
                            "location": location_el.get_text(strip=True)
                            if location_el
                            else "",
                            "salary": salary_el.get_text(strip=True)
                            if salary_el
                            else "",
                            "posted_date": date_el.get_text(strip=True)
                            if date_el
                            else "",
                            "description": snippet_el.get_text(strip=True)
                            if snippet_el
                            else "",
                            "url": job_url,
                        }
                    )
                )

        logger.info(f"[indeed] Found {len(jobs)} jobs total")
        return jobs
