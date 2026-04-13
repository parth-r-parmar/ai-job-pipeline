"""Score job-resume match quality using Claude API."""

import json
import time
import logging

from anthropic import Anthropic

from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from src.resume_parser import get_profile_context

logger = logging.getLogger(__name__)

client = None

SCORER_SYSTEM_PROMPT = """You are an expert technical recruiter and job-matching analyst.
You will receive a candidate profile and a job listing. Score how well the candidate matches the job.

Rules:
- Score from 0 to 100 based on skills match, experience level, role alignment, and location fit.
- matched_keywords: skills/technologies from the job that the candidate HAS.
- missing_keywords: skills/technologies from the job that the candidate LACKS.
- recommendation: one of "Strong Match", "Good Match", "Moderate Match", "Weak Match", "Poor Match".
- reason: 1-2 sentence explanation of the score.
- Be objective. Do not inflate scores. A 70+ means the candidate could realistically get an interview.

Respond ONLY with valid JSON, no markdown fences."""

SCORER_USER_TEMPLATE = """## Candidate Profile
{profile_json}

## Job Listing
Title: {title}
Company: {company}
Location: {location}
Experience Required: {experience}
Job Type: {job_type}

### Job Description
{description}

## Task
Score this candidate-job match. Return JSON:
{{
  "match_score": <int 0-100>,
  "matched_keywords": [<str>, ...],
  "missing_keywords": [<str>, ...],
  "recommendation": "<str>",
  "reason": "<str>"
}}"""


def _get_client() -> Anthropic:
    global client
    if client is None:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return client


def score_job(job: dict) -> dict:
    """Score a single job against the resume.

    Returns dict with match_score, matched_keywords, missing_keywords,
    recommendation, reason. On error returns defaults with score=0.
    """
    profile = get_profile_context()
    user_msg = SCORER_USER_TEMPLATE.format(
        profile_json=json.dumps(profile, indent=2),
        title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        experience=job.get("experience", ""),
        job_type=job.get("job_type", ""),
        description=job.get("description", "")[:3000],
    )

    try:
        response = _get_client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            system=SCORER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = response.content[0].text.strip()
        # Handle possible markdown fences despite prompt instruction
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Scoring failed for {job.get('title')} at {job.get('company')}: {e}")
        return {
            "match_score": 0,
            "matched_keywords": [],
            "missing_keywords": [],
            "recommendation": "Error",
            "reason": f"API call failed: {str(e)[:100]}",
        }


def score_all_jobs(jobs: list[dict]) -> list[dict]:
    """Score all jobs. Adds score fields to each job dict in-place."""
    total = len(jobs)
    for i, job in enumerate(jobs):
        logger.info(
            f"Scoring job {i + 1}/{total}: {job.get('title')} at {job.get('company')}"
        )
        result = score_job(job)
        job.update(result)
        if i < total - 1:
            time.sleep(0.5)
    return jobs
