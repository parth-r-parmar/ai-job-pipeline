"""Alternative scorer that uses Claude Code CLI instead of API key.

Usage: Instead of ANTHROPIC_API_KEY, this calls the `claude` CLI directly,
leveraging your existing Claude Code login. No separate API key needed.

Use this by importing score_all_jobs from here instead of scorer.py:
    from src.scorer_cli import score_all_jobs
"""

import os
import json
import subprocess
import logging
import time
import shutil
import tempfile

from src.resume_parser import get_profile_context


def _find_claude_cli() -> str | None:
    """Locate the claude CLI binary cross-platform."""
    for name in ("claude", "claude.cmd", "claude.exe"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _get_neutral_cwd() -> str:
    """Return an empty scratch dir for running Claude CLI.

    Avoids picking up project CLAUDE.md and Claude Code's own temp dir
    (which has session files that confuse fresh subprocess calls).
    Uses user home as root instead of system temp.
    """
    home = os.path.expanduser("~")
    scratch = os.path.join(home, ".ai-job-pipeline-scratch")
    os.makedirs(scratch, exist_ok=True)
    return scratch


_CLAUDE_CMD = _find_claude_cli()
_NEUTRAL_CWD = _get_neutral_cwd()

logger = logging.getLogger(__name__)

SCORER_PROMPT_TEMPLATE = """TASK: Score the candidate-job match below. The candidate profile and job listing are both provided — do not ask for more data. Respond with ONE LINE of valid JSON only, nothing else.

=== CANDIDATE PROFILE (JSON) ===
{profile_json}
=== END CANDIDATE PROFILE ===

=== JOB LISTING ===
Title: {title}
Company: {company}
Location: {location}
Experience Required: {experience}
Job Type: {job_type}
Description: {description}
=== END JOB LISTING ===

Score 0-100 based on skills match, experience level, role alignment, location fit.
RESPOND WITH THIS EXACT JSON STRUCTURE (no prose, no markdown fences):
{{"match_score": <int 0-100>, "matched_keywords": ["skill1","skill2"], "missing_keywords": ["gap1","gap2"], "recommendation": "Strong Match", "reason": "1-2 sentence explanation"}}"""


def _call_claude_cli(prompt: str) -> str | None:
    """Call the claude CLI and return the response text.

    Pipes prompt via stdin to avoid Windows .cmd multi-line arg truncation.
    """
    if not _CLAUDE_CMD:
        logger.error("Claude CLI not found on PATH. Install: npm install -g @anthropic-ai/claude-code")
        return None
    try:
        result = subprocess.run(
            [_CLAUDE_CMD, "-p", "--no-session-persistence",
             "--output-format", "text", "--model", "sonnet"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=180,
            encoding="utf-8",
            shell=False,
            cwd=_NEUTRAL_CWD,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        logger.error(f"Claude CLI error: {result.stderr[:200]}")
        return None
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out")
        return None


def score_job(job: dict) -> dict:
    """Score a single job using Claude Code CLI."""
    profile = get_profile_context()
    prompt = SCORER_PROMPT_TEMPLATE.format(
        profile_json=json.dumps(profile, indent=2),
        title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        experience=job.get("experience", ""),
        job_type=job.get("job_type", ""),
        description=job.get("description", "")[:3000],
    )

    response = _call_claude_cli(prompt)
    if not response:
        return {
            "match_score": 0,
            "matched_keywords": [],
            "missing_keywords": [],
            "recommendation": "Error",
            "reason": "Claude CLI call failed",
        }

    # Parse JSON from response
    try:
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except (json.JSONDecodeError, IndexError) as e:
        logger.error(f"Failed to parse Claude response: {e}")
        return {
            "match_score": 0,
            "matched_keywords": [],
            "missing_keywords": [],
            "recommendation": "Error",
            "reason": f"Parse error: {str(e)[:100]}",
        }


def score_all_jobs(jobs: list[dict]) -> list[dict]:
    """Score all jobs using Claude Code CLI. Adds score fields in-place."""
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
