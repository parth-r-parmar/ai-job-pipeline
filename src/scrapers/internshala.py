"""Internshala job scraper."""

import logging
from urllib.parse import urljoin

from .base import BaseScraper

logger = logging.getLogger(__name__)


class IntershalaScraper(BaseScraper):
    SOURCE = "internshala"
    BASE_URL = "https://internshala.com"

    def scrape(self, keywords: list[str], location: str, pages: int) -> list[dict]:
        jobs = []
        query = "-".join(kw.lower().replace(" ", "-") for kw in keywords[:3])
        loc_slug = location.lower().replace(" ", "-")

        for page in range(1, pages + 1):
            self._delay()
            logger.info(
                f"[internshala] Scraping page {page} for '{query}' in {location}"
            )

            # Full-time jobs only (internships filtered out by config)
            for section in ["jobs"]:
                url = f"{self.BASE_URL}/{section}/{query}-{section}-in-{loc_slug}/page-{page}"
                soup = self._get(url)
                if not soup:
                    continue

                # Each job card is div.individual_internship
                cards = soup.select("div.individual_internship")

                for card in cards:
                    # Title: h2.job-internship-name or a.job-title-href
                    title_el = card.select_one(
                        "h2.job-internship-name, a.job-title-href"
                    )
                    # Company: p.company-name
                    company_el = card.select_one("p.company-name")
                    # Location: p.locations or p.row-1-item.locations
                    location_el = card.select_one("p.locations, div.locations")
                    # Salary: span.desktop (inside the salary row-1-item)
                    salary_el = card.select_one("span.desktop")
                    # Experience: div.row-1-item with briefcase icon (3rd row-1-item)
                    exp_items = card.select("div.row-1-item")
                    experience = ""
                    if len(exp_items) >= 3:
                        experience = exp_items[2].get_text(strip=True)
                    # Description: div.about_job div.text
                    desc_el = card.select_one("div.about_job div.text, div.about_job")
                    # Detail link
                    detail_link = card.select_one("a.job-title-href, h2 a")

                    if not title_el:
                        continue

                    job_url = ""
                    if detail_link and detail_link.has_attr("href"):
                        job_url = urljoin(self.BASE_URL, detail_link["href"])
                    elif title_el.name == "a" and title_el.has_attr("href"):
                        job_url = urljoin(self.BASE_URL, title_el["href"])

                    job_type = "Internship" if section == "internships" else "Full-time"

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
                                "salary": salary_el.get_text(strip=True)
                                if salary_el
                                else "",
                                "experience": experience,
                                "description": desc_el.get_text(strip=True)[:500]
                                if desc_el
                                else "",
                                "job_type": job_type,
                                "url": job_url,
                            }
                        )
                    )

        logger.info(f"[internshala] Found {len(jobs)} jobs total")
        return jobs
