"""Job scrapers for various job portals."""

from .naukri import NaukriScraper
from .indeed import IndeedScraper
from .linkedin import LinkedInScraper
from .internshala import IntershalaScraper

ALL_SCRAPERS = [NaukriScraper, IndeedScraper, LinkedInScraper, IntershalaScraper]
