"""CLI-based resume tailoring using Claude Code CLI (no API key needed).

Mirrors src/scorer_cli.py pattern — calls the `claude` CLI via subprocess
instead of the Anthropic SDK. Reuses prompts and validation from src/tailor.py.
"""

import os
import json
import subprocess
import logging
import time
import shutil
import tempfile


def _find_claude_cli() -> str | None:
    for name in ("claude", "claude.cmd", "claude.exe"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _get_neutral_cwd() -> str:
    home = os.path.expanduser("~")
    scratch = os.path.join(home, ".ai-job-pipeline-scratch")
    os.makedirs(scratch, exist_ok=True)
    return scratch


_CLAUDE_CMD = _find_claude_cli()
_NEUTRAL_CWD = _get_neutral_cwd()

from src.resume_parser import get_resume
from src.resume_builder.build_resume import ResumePDF
from src.config import TAILORED_RESUMES_DIR
from src.tailor import (
    TAILOR_SYSTEM_PROMPT,
    TAILOR_USER_TEMPLATE,
    _validate_structure,
    _sanitize_filename,
    save_tailored_json,
)

logger = logging.getLogger(__name__)


def _call_claude_cli(prompt: str, timeout: int = 300) -> str | None:
    """Call the claude CLI and return the response text."""
    if not _CLAUDE_CMD:
        logger.error("Claude CLI not found on PATH. Install: npm install -g @anthropic-ai/claude-code")
        return None
    try:
        full_prompt = f"{TAILOR_SYSTEM_PROMPT}\n\n{prompt}"
        result = subprocess.run(
            [_CLAUDE_CMD, "-p", "--no-session-persistence",
             "--output-format", "text", "--model", "sonnet"],
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            shell=False,
            cwd=_NEUTRAL_CWD,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        logger.error(f"Claude CLI error: {result.stderr[:200]}")
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"Claude CLI timed out (>{timeout}s)")
        return None


def tailor_resume(job: dict) -> dict | None:
    """Call Claude CLI to tailor resume for a specific job."""
    prompt = TAILOR_USER_TEMPLATE.format(
        resume_json=json.dumps(get_resume(), indent=2),
        title=job.get("title", ""),
        company=job.get("company", ""),
        description=job.get("description", "")[:4000],
    )

    response = _call_claude_cli(prompt)
    if not response:
        return None

    try:
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        tailored = json.loads(text)
        _validate_structure(tailored)
        return tailored
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse tailored resume for {job.get('title')}: {e}")
        return None


def generate_tailored_pdf(tailored: dict, job: dict, pdf_style: str = "classic") -> str | list[str]:
    """Generate tailored PDF(s). Returns single path or list of paths if style='both'."""
    os.makedirs(TAILORED_RESUMES_DIR, exist_ok=True)
    safe_company = _sanitize_filename(job.get("company", "unknown"))
    safe_title = _sanitize_filename(job.get("title", "unknown"))
    base_name = f"{safe_company}_{safe_title}"

    paths = []

    def build_classic():
        path = os.path.join(TAILORED_RESUMES_DIR, f"{base_name}{'_classic' if pdf_style == 'both' else ''}.pdf")
        return ResumePDF(tailored).build(output_path=path)

    def build_modern():
        try:
            from src.resume_builder.html_resume import HtmlResumePDF
            path = os.path.join(TAILORED_RESUMES_DIR, f"{base_name}{'_modern' if pdf_style == 'both' else ''}.pdf")
            return HtmlResumePDF(tailored).build(output_path=path)
        except ImportError:
            logger.warning("Playwright not installed. Falling back to classic.")
            return build_classic()

    if pdf_style == "modern":
        return build_modern()
    if pdf_style == "both":
        paths.append(build_classic())
        paths.append(build_modern())
        return paths
    return build_classic()


def tailor_and_generate(job: dict, pdf_style: str = "classic") -> str | list[str] | None:
    """Full CLI pipeline: tailor resume + save JSON + generate PDF(s) for one job."""
    tailored = tailor_resume(job)
    if tailored is None:
        return None

    json_path = save_tailored_json(tailored, job)
    logger.info(f"  Saved tailored JSON: {json_path}")

    result = generate_tailored_pdf(tailored, job, pdf_style=pdf_style)
    if isinstance(result, list):
        for p in result:
            logger.info(f"  Generated tailored PDF: {p}")
    else:
        logger.info(f"  Generated tailored PDF: {result}")

    return result


def score_all_jobs_alias(jobs):
    """Re-export so main.py can import uniformly if needed."""
    from src.scorer_cli import score_all_jobs
    return score_all_jobs(jobs)
