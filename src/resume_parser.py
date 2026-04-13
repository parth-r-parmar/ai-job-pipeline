"""Extract structured information from resume JSON for search and scoring."""

import re
import json
from datetime import datetime

from src.config import RESUME_PATH

_resume_cache = None


def _load_resume() -> dict:
    global _resume_cache
    if _resume_cache is None:
        with open(RESUME_PATH, "r", encoding="utf-8") as f:
            _resume_cache = json.load(f)
    return _resume_cache


def get_resume() -> dict:
    """Return the full resume dict."""
    return _load_resume()


def get_all_skills() -> list[str]:
    """Flatten skills dict into a deduplicated list of individual skill strings."""
    resume = _load_resume()
    skills = []
    seen = set()
    for items_str in resume["skills"].values():
        for item in items_str.split(","):
            clean = re.sub(r"\s*\(.*?\)", "", item).strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                skills.append(clean)
    return skills


def get_job_titles() -> list[str]:
    """Extract unique role titles from experience entries."""
    resume = _load_resume()
    return list(dict.fromkeys(exp["role"] for exp in resume["experience"]))


def get_years_of_experience() -> float:
    """Calculate total years of professional experience from date ranges."""
    resume = _load_resume()
    total_days = 0
    for exp in resume["experience"]:
        dates = exp["dates"]
        parts = [d.strip() for d in dates.split("-")]
        if len(parts) != 2:
            continue
        try:
            start = datetime.strptime(parts[0], "%b %Y")
        except ValueError:
            continue
        if parts[1].lower() == "present":
            end = datetime.now()
        else:
            try:
                end = datetime.strptime(parts[1], "%b %Y")
            except ValueError:
                continue
        total_days += (end - start).days
    return round(total_days / 365.25, 1)


def get_search_keywords() -> list[str]:
    """Generate job search keywords from resume content."""
    resume = _load_resume()
    keywords = []
    seen = set()

    for title in get_job_titles():
        if title.lower() not in seen:
            seen.add(title.lower())
            keywords.append(title)

    priority_categories = ["Languages", "Frameworks & Libraries"]
    for cat in priority_categories:
        if cat in resume["skills"]:
            for item in resume["skills"][cat].split(","):
                clean = re.sub(r"\s*\(.*?\)", "", item).strip()
                if clean and clean.lower() not in seen:
                    seen.add(clean.lower())
                    keywords.append(clean)

    return keywords


def get_profile_context() -> dict:
    """Build a structured profile dict for Claude API prompts."""
    resume = _load_resume()
    return {
        "name": resume["name"],
        "summary": resume["summary"],
        "skills": get_all_skills(),
        "years_of_experience": get_years_of_experience(),
        "job_titles": get_job_titles(),
        "education": resume["education"][0]["degree"] if resume["education"] else "",
        "location": resume["contact"]["location"],
    }
