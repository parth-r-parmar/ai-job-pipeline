"""Ghost job detection using Python heuristics (no AI needed).

Flags jobs as low/medium/high risk based on posting age,
description quality, salary disclosure, and title specificity.
"""

import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Vague title patterns that suggest ghost/bulk postings
VAGUE_TITLES = {
    "multiple openings", "various positions",
    "urgent requirement", "walk-in", "immediate joiner",
}

# Pre-compiled regex for posting age parsing
_RE_DAYS = re.compile(r"(\d+)\s*days?\s*ago")
_RE_WEEKS = re.compile(r"(\d+)\s*weeks?\s*ago")
_RE_MONTHS = re.compile(r"(\d+)\s*months?\s*ago")


def _parse_posting_age_days(posted_str: str) -> int | None:
    """Try to extract posting age in days from various formats."""
    if not posted_str or posted_str == "N/A":
        return None
    s = posted_str.lower().strip()

    m = _RE_DAYS.search(s)
    if m:
        return int(m.group(1))

    m = _RE_WEEKS.search(s)
    if m:
        return int(m.group(1)) * 7

    m = _RE_MONTHS.search(s)
    if m:
        return int(m.group(1)) * 30

    # ISO date "2026-04-01"
    try:
        posted_date = datetime.strptime(s[:10], "%Y-%m-%d")
        return (datetime.now() - posted_date).days
    except ValueError:
        pass

    return None


def detect_ghost_risk(job: dict) -> str:
    """Classify a job as low/medium/high ghost risk.

    Returns 'low', 'medium', or 'high'.
    """
    risk_score = 0  # 0-10 scale, mapped to low/medium/high

    # 1. Posting age
    age_days = _parse_posting_age_days(job.get("posted_date", ""))
    if age_days is not None:
        if age_days > 60:
            risk_score += 4
        elif age_days > 30:
            risk_score += 2
        elif age_days > 14:
            risk_score += 1

    # 2. Description quality
    desc = job.get("description", "")
    desc_len = len(desc.strip())
    if desc_len < 30:
        risk_score += 3  # Almost empty description
    elif desc_len < 100:
        risk_score += 2  # Very short
    elif desc_len < 200:
        risk_score += 1  # Short

    # 3. Salary transparency
    salary = job.get("salary", "")
    if salary in ("Not disclosed", "N/A", "", "Competitive salary"):
        # No salary alone is weak signal (many legit jobs don't disclose)
        # But combined with short description, it's stronger
        if desc_len < 200:
            risk_score += 2
        else:
            risk_score += 1

    # 4. Title specificity
    title_lower = job.get("title", "").lower()
    if any(vague in title_lower for vague in VAGUE_TITLES):
        risk_score += 3

    # Map to categories
    if risk_score >= 6:
        return "high"
    elif risk_score >= 3:
        return "medium"
    return "low"


def flag_ghost_jobs(jobs: list[dict]):
    """Add ghost_risk field to each job dict in-place."""
    high = medium = 0
    for job in jobs:
        risk = detect_ghost_risk(job)
        job["ghost_risk"] = risk
        if risk == "high":
            high += 1
        elif risk == "medium":
            medium += 1
    if high or medium:
        logger.info(f"Ghost risk flagged: {high} high, {medium} medium, {len(jobs) - high - medium} low")
