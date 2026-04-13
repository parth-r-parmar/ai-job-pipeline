"""Naukri.com job scraper."""

import logging
from urllib.parse import quote_plus

from .base import BaseScraper

logger = logging.getLogger(__name__)


class NaukriScraper(BaseScraper):
    SOURCE = "naukri"
    BASE_URL = "https://www.naukri.com/jobapi/v3/search"

    def scrape(self, keywords: list[str], location: str, pages: int) -> list[dict]:
        jobs = []
        query = " ".join(keywords)

        for page in range(1, pages + 1):
            self._delay()
            logger.info(f"[naukri] Scraping page {page} for '{query}' in {location}")

            # Try JSON API first
            data = self._get_json(
                self.BASE_URL,
                params={
                    "noOfResults": 20,
                    "urlType": "search_by_keyword",
                    "searchType": "adv",
                    "keyword": query,
                    "location": location,
                    "pageNo": page,
                },
            )

            if data and "jobDetails" in data:
                for item in data["jobDetails"]:
                    jobs.append(
                        self._normalize_job(
                            {
                                "title": item.get("title", ""),
                                "company": item.get("companyName", ""),
                                "location": ", ".join(
                                    item.get("placeholders", [{}])[0]
                                    .get("value", "")
                                    .split(", ")
                                )
                                if item.get("placeholders")
                                else "N/A",
                                "experience": (
                                    item.get("placeholders", [{}])[1].get("value", "")
                                    if len(item.get("placeholders", [])) > 1
                                    else "N/A"
                                ),
                                "salary": (
                                    item.get("placeholders", [{}])[2].get("value", "")
                                    if len(item.get("placeholders", [])) > 2
                                    else "Not disclosed"
                                ),
                                "job_type": item.get("jobType", "N/A"),
                                "posted_date": item.get(
                                    "footerPlaceholderLabel", "N/A"
                                ),
                                "description": item.get("jobDescription", ""),
                                "url": item.get("jdURL", ""),
                            }
                        )
                    )
                continue

            # Fallback: HTML scraping
            logger.info("[naukri] JSON API unavailable, trying HTML fallback")
            slug = query.lower().replace(" ", "-")
            loc_slug = location.lower().replace(" ", "-")
            html_url = f"https://www.naukri.com/{slug}-jobs-in-{loc_slug}-{page}"
            soup = self._get(html_url)
            if not soup:
                continue

            for card in soup.select("article.jobTuple, div.srp-jobtuple-wrapper"):
                title_el = card.select_one("a.title, a.jobTitle")
                company_el = card.select_one("a.subTitle, a.companyName")
                loc_el = card.select_one("li.location span, span.locWdth")
                exp_el = card.select_one("li.experience span, span.expwdth")
                sal_el = card.select_one("li.salary span, span.salwdth")
                desc_el = card.select_one("div.job-description, div.jobDescription")

                jobs.append(
                    self._normalize_job(
                        {
                            "title": title_el.get_text(strip=True) if title_el else "",
                            "company": company_el.get_text(strip=True)
                            if company_el
                            else "",
                            "location": loc_el.get_text(strip=True) if loc_el else "",
                            "experience": exp_el.get_text(strip=True) if exp_el else "",
                            "salary": sal_el.get_text(strip=True) if sal_el else "",
                            "description": desc_el.get_text(strip=True)
                            if desc_el
                            else "",
                            "url": title_el["href"]
                            if title_el and title_el.has_attr("href")
                            else "",
                        }
                    )
                )

        logger.info(f"[naukri] Found {len(jobs)} jobs total")
        return jobs
