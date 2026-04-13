"""Centralized configuration — loads from .env with sensible defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = parent of src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
MATCH_THRESHOLD = int(os.environ.get("MATCH_THRESHOLD", "70"))

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
MIN_SALARY_LPA = float(os.environ.get("MIN_SALARY_LPA", "8"))
EXCLUDE_INTERNSHIPS = True
INCLUDE_REMOTE = True
PREFER_PRODUCT_COMPANIES = True

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RESUME_PATH = PROJECT_ROOT / os.environ.get("RESUME_PATH", "resume.json")
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_EXCEL = str(OUTPUT_DIR / "jobs.xlsx")
TAILORED_RESUMES_DIR = str(OUTPUT_DIR / "tailored_resumes")

# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------
PAGES_PER_SITE = int(os.environ.get("PAGES_PER_SITE", "3"))
MAX_DETAIL_FETCHES = int(os.environ.get("MAX_DETAIL_FETCHES", "20"))
PDF_STYLE = os.environ.get("PDF_STYLE", "classic")  # classic | modern
REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 3.5
REQUEST_TIMEOUT = 15

FALLBACK_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]
