"""Tailor resumes for high-scoring jobs using Claude API and generate PDFs."""

import os
import re
import json
import time
import logging

from anthropic import Anthropic

from src.resume_parser import get_resume
from src.resume_builder.build_resume import ResumePDF

from src.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, TAILORED_RESUMES_DIR

logger = logging.getLogger(__name__)

client = None

TAILOR_SYSTEM_PROMPT = """You are an expert resume writer specializing in ATS optimization.
You will receive a candidate's resume (as JSON) and a target job description.
Your task is to tailor the resume for this specific job.

Rules:
1. Rewrite the summary to emphasize skills/experience most relevant to this job.
2. Reorder skills categories so the most relevant category appears first. Within each category, reorder items so the most relevant appear first.
3. Rewrite experience bullet points to emphasize achievements relevant to this job. Use strong action verbs and quantified results.
4. Rewrite project bullet points similarly.
5. DO NOT fabricate any skills, experiences, companies, or metrics the candidate does not have.
6. DO NOT change: name, contact info, education, company names, role titles, dates, project names, project links.
7. Keep the exact same JSON structure.
8. Keep the same number of bullets per experience/project entry.
9. Extract the top 15 keywords/phrases from the job description.
10. Inject these keywords naturally into existing bullets by reformulating the candidate's real experience using the exact vocabulary from the JD. For example: if the JD says "RESTful APIs" and the resume says "backend endpoints", change to "RESTful API endpoints". NEVER add skills the candidate does not have.
11. Add a "core_competencies" field: a JSON array of 6-8 keyword phrases from the JD that match the candidate's actual skills. These will appear as badges on the resume PDF.

Respond ONLY with the complete tailored resume as valid JSON. No markdown fences, no explanation."""

TAILOR_USER_TEMPLATE = """## Current Resume (JSON)
{resume_json}

## Target Job
Title: {title}
Company: {company}
Description: {description}

## Task
Return the tailored resume as JSON with the exact same structure plus an added "core_competencies" array of 6-8 JD keyword phrases matching the candidate's skills."""


def _get_client() -> Anthropic:
    global client
    if client is None:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return client


def _sanitize_filename(name: str) -> str:
    """Replace spaces with underscores, remove non-alphanumeric chars."""
    return re.sub(r"[^\w\-]", "", name.replace(" ", "_"))[:50]


def _validate_structure(tailored: dict):
    """Verify tailored resume has all required keys matching resume structure."""
    original = get_resume()

    required_top = {"name", "contact", "summary", "education", "skills", "experience", "projects"}
    missing = required_top - set(tailored.keys())
    if missing:
        raise ValueError(f"Missing top-level keys: {missing}")

    if tailored["name"] != original["name"]:
        raise ValueError("Name was modified")
    if tailored["contact"] != original["contact"]:
        raise ValueError("Contact info was modified")

    if len(tailored["education"]) != len(original["education"]):
        raise ValueError("Education entries count changed")
    for i, edu in enumerate(original["education"]):
        for key in ("institution", "location", "degree", "dates"):
            if tailored["education"][i].get(key) != edu[key]:
                raise ValueError(f"Education[{i}].{key} was modified")

    if len(tailored["experience"]) != len(original["experience"]):
        raise ValueError("Experience entries count changed")
    for i, exp in enumerate(original["experience"]):
        t_exp = tailored["experience"][i]
        for key in ("company", "role", "dates"):
            if t_exp.get(key) != exp[key]:
                raise ValueError(f"Experience[{i}].{key} was modified")
        if len(t_exp.get("bullets", [])) != len(exp["bullets"]):
            raise ValueError(f"Experience[{i}] bullet count changed")

    if len(tailored["projects"]) != len(original["projects"]):
        raise ValueError("Projects entries count changed")
    for i, proj in enumerate(original["projects"]):
        t_proj = tailored["projects"][i]
        if t_proj.get("name") != proj["name"]:
            raise ValueError(f"Projects[{i}].name was modified")
        if t_proj.get("link") != proj["link"]:
            raise ValueError(f"Projects[{i}].link was modified")
        if len(t_proj.get("bullets", [])) != len(proj["bullets"]):
            raise ValueError(f"Projects[{i}] bullet count changed")


def tailor_resume(job: dict) -> dict | None:
    """Call Claude to tailor resume for a specific job.

    Returns modified resume dict matching resume structure, or None on failure.
    """
    user_msg = TAILOR_USER_TEMPLATE.format(
        resume_json=json.dumps(get_resume(), indent=2),
        title=job.get("title", ""),
        company=job.get("company", ""),
        description=job.get("description", "")[:4000],
    )

    try:
        response = _get_client().messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            system=TAILOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        tailored = json.loads(text)
        _validate_structure(tailored)
        return tailored
    except Exception as e:
        logger.error(
            f"Tailoring failed for {job.get('title')} at {job.get('company')}: {e}"
        )
        return None


def save_tailored_json(tailored: dict, job: dict) -> str:
    """Save tailored resume dict as JSON file."""
    os.makedirs(TAILORED_RESUMES_DIR, exist_ok=True)
    safe_company = _sanitize_filename(job.get("company", "unknown"))
    safe_title = _sanitize_filename(job.get("title", "unknown"))
    filename = f"{safe_company}_{safe_title}.json"
    path = os.path.join(TAILORED_RESUMES_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tailored, f, indent=2, ensure_ascii=False)
    return os.path.abspath(path)


def generate_tailored_pdf(tailored: dict, job: dict, pdf_style: str = "classic"):
    """Generate PDF(s) from tailored resume dict. Returns single path or list if style='both'."""
    os.makedirs(TAILORED_RESUMES_DIR, exist_ok=True)
    safe_company = _sanitize_filename(job.get("company", "unknown"))
    safe_title = _sanitize_filename(job.get("title", "unknown"))
    base_name = f"{safe_company}_{safe_title}"

    def build_classic():
        path = os.path.join(TAILORED_RESUMES_DIR, f"{base_name}{'_classic' if pdf_style == 'both' else ''}.pdf")
        return ResumePDF(tailored).build(output_path=path)

    def build_modern():
        try:
            from src.resume_builder.html_resume import HtmlResumePDF
            path = os.path.join(TAILORED_RESUMES_DIR, f"{base_name}{'_modern' if pdf_style == 'both' else ''}.pdf")
            return HtmlResumePDF(tailored).build(output_path=path)
        except ImportError:
            logger.warning(
                "Playwright not installed. Using classic PDF.\n"
                "  To enable modern PDFs: pip install playwright && playwright install chromium"
            )
            return build_classic()

    if pdf_style == "modern":
        return build_modern()
    if pdf_style == "both":
        return [build_classic(), build_modern()]
    return build_classic()


def _generate_diff(original: dict, tailored: dict, job: dict) -> str | None:
    """Generate a text diff showing what changed between original and tailored resume."""
    os.makedirs(TAILORED_RESUMES_DIR, exist_ok=True)
    safe_company = _sanitize_filename(job.get("company", "unknown"))
    safe_title = _sanitize_filename(job.get("title", "unknown"))
    diff_path = os.path.join(TAILORED_RESUMES_DIR, f"{safe_company}_{safe_title}_diff.txt")

    lines = [f"Tailoring Diff: {job.get('title')} at {job.get('company')}", "=" * 60, ""]

    # Summary diff
    if original.get("summary") != tailored.get("summary"):
        lines.append("=== SUMMARY ===")
        lines.append(f"- BEFORE: {original.get('summary', '')[:200]}...")
        lines.append(f"+ AFTER:  {tailored.get('summary', '')[:200]}...")
        lines.append("")

    # Experience bullets diff
    for i, (orig_exp, tail_exp) in enumerate(zip(original.get("experience", []), tailored.get("experience", []))):
        for j, (ob, tb) in enumerate(zip(orig_exp.get("bullets", []), tail_exp.get("bullets", []))):
            if ob != tb:
                lines.append(f"=== EXPERIENCE[{i}] ({orig_exp.get('company')}) BULLET {j+1} ===")
                lines.append(f"- BEFORE: {ob}")
                lines.append(f"+ AFTER:  {tb}")
                lines.append("")

    # Project bullets diff
    for i, (orig_proj, tail_proj) in enumerate(zip(original.get("projects", []), tailored.get("projects", []))):
        for j, (ob, tb) in enumerate(zip(orig_proj.get("bullets", []), tail_proj.get("bullets", []))):
            if ob != tb:
                lines.append(f"=== PROJECT[{i}] ({orig_proj.get('name')}) BULLET {j+1} ===")
                lines.append(f"- BEFORE: {ob}")
                lines.append(f"+ AFTER:  {tb}")
                lines.append("")

    # Injected keywords
    competencies = tailored.get("core_competencies", [])
    if competencies:
        lines.append("=== INJECTED KEYWORDS (core_competencies) ===")
        for kw in competencies:
            lines.append(f"  + {kw}")
        lines.append("")

    if len(lines) <= 3:
        lines.append("(no changes detected)")

    with open(diff_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return diff_path


def tailor_and_generate(job: dict, pdf_style: str = "classic") -> str | None:
    """Full pipeline: tailor resume + save JSON + generate diff + generate PDF.

    Returns PDF path or None on failure.
    """
    original = get_resume()
    tailored = tailor_resume(job)
    if tailored is None:
        return None

    # Save core_competencies to job dict for Excel export
    if tailored.get("core_competencies"):
        job["core_competencies"] = tailored["core_competencies"]

    json_path = save_tailored_json(tailored, job)
    logger.info(f"  Saved tailored JSON: {json_path}")

    diff_path = _generate_diff(original, tailored, job)
    if diff_path:
        logger.info(f"  Saved diff: {diff_path}")

    pdf_path = generate_tailored_pdf(tailored, job, pdf_style=pdf_style)
    logger.info(f"  Generated tailored PDF: {pdf_path}")

    return pdf_path
