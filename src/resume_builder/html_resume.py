"""Modern HTML+Playwright PDF resume generator with custom fonts and ATS optimization."""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"
FONTS_DIR = Path(__file__).parent / "fonts"


def _sanitize_ats(text: str) -> str:
    """Replace Unicode characters that break legacy ATS parsers."""
    replacements = {
        "\u2013": "-", "\u2014": "-",       # en-dash, em-dash
        "\u2018": "'", "\u2019": "'",        # smart single quotes
        "\u201c": '"', "\u201d": '"',        # smart double quotes
        "\u2026": "...",                      # ellipsis
        "\u00a0": " ",                        # non-breaking space
        "\u200b": "", "\u200c": "", "\u200d": "", "\ufeff": "",  # zero-width chars
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _build_competencies_html(competencies: list[str]) -> str:
    """Build the Core Competencies section with keyword badges."""
    if not competencies:
        return ""
    tags = "\n      ".join(
        f'<span class="competency-tag">{_sanitize_ats(c)}</span>'
        for c in competencies
    )
    return f"""<div class="section">
    <div class="section-title">Core Competencies</div>
    <div class="competencies-grid">
      {tags}
    </div>
  </div>"""


def _build_experience_html(experience: list[dict]) -> str:
    """Build Work Experience section HTML."""
    parts = []
    for exp in experience:
        bullets = "\n        ".join(
            f"<li>{_sanitize_ats(b)}</li>" for b in exp.get("bullets", [])
        )
        parts.append(f"""<div class="job">
      <div class="job-header">
        <span class="job-company">{_sanitize_ats(exp['company'])}</span>
        <span class="job-period">{_sanitize_ats(exp['dates'])}</span>
      </div>
      <div class="job-role">{_sanitize_ats(exp['role'])}</div>
      <ul>
        {bullets}
      </ul>
    </div>""")
    return "\n    ".join(parts)


def _build_projects_html(projects: list[dict]) -> str:
    """Build Projects section HTML."""
    parts = []
    for proj in projects:
        link_html = ""
        if proj.get("link"):
            link_html = f' &mdash; <a class="project-link" href="https://{proj["link"]}">{proj["link"]}</a>'
        bullets = " ".join(
            _sanitize_ats(b) for b in proj.get("bullets", [])
        )
        parts.append(f"""<div class="project">
      <span class="project-title">{_sanitize_ats(proj['name'])}</span>{link_html}
      <div class="project-desc">{bullets}</div>
    </div>""")
    return "\n    ".join(parts)


def _build_education_html(education: list[dict]) -> str:
    """Build Education section HTML."""
    parts = []
    for edu in education:
        parts.append(f"""<div class="edu-item">
      <div class="edu-header">
        <span class="edu-title">{_sanitize_ats(edu['degree'])} &mdash; <span class="edu-org">{_sanitize_ats(edu['institution'])}</span></span>
        <span class="edu-year">{_sanitize_ats(edu['dates'])}</span>
      </div>
      <div class="edu-desc">{_sanitize_ats(edu.get('location', ''))}</div>
    </div>""")
    return "\n    ".join(parts)


def _build_skills_html(skills: dict) -> str:
    """Build Technical Skills section HTML."""
    parts = []
    for category, items in skills.items():
        parts.append(
            f'<span class="skill-item"><span class="skill-category">{_sanitize_ats(category)}:</span> {_sanitize_ats(items)}</span>'
        )
    return "\n      ".join(parts)


class HtmlResumePDF:
    """Generates a modern, ATS-optimized PDF using HTML template + Playwright."""

    def __init__(self, data: dict):
        self.data = data

    def build(self, output_path: str = "resume.pdf") -> str:
        """Render HTML template with resume data and generate PDF via Playwright."""
        template_path = TEMPLATE_DIR / "modern.html"
        with open(template_path, "r", encoding="utf-8") as f:
            html = f.read()

        contact = self.data["contact"]
        fonts_abs = FONTS_DIR.resolve().as_uri()

        # Fill template placeholders
        replacements = {
            "{{FONTS_DIR}}": str(FONTS_DIR.resolve()).replace("\\", "/"),
            "{{NAME}}": _sanitize_ats(self.data["name"]),
            "{{EMAIL}}": contact["email"],
            "{{PHONE}}": contact["phone"],
            "{{LINKEDIN}}": contact["linkedin"],
            "{{GITHUB}}": contact["github"],
            "{{LOCATION}}": contact["location"],
            "{{SUMMARY}}": _sanitize_ats(self.data.get("summary", "")),
            "{{COMPETENCIES_SECTION}}": _build_competencies_html(
                self.data.get("core_competencies", [])
            ),
            "{{EXPERIENCE}}": _build_experience_html(self.data.get("experience", [])),
            "{{PROJECTS}}": _build_projects_html(self.data.get("projects", [])),
            "{{EDUCATION}}": _build_education_html(self.data.get("education", [])),
            "{{SKILLS}}": _build_skills_html(self.data.get("skills", {})),
        }

        for placeholder, value in replacements.items():
            html = html.replace(placeholder, value)

        # Write temp HTML
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        tmp_html = output_path.replace(".pdf", ".html")
        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(html)

        # Generate PDF via Playwright
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file:///{os.path.abspath(tmp_html).replace(os.sep, '/')}")
            page.pdf(
                path=output_path,
                format="A4",
                margin={"top": "0.6in", "bottom": "0.6in", "left": "0.6in", "right": "0.6in"},
                print_background=True,
            )
            browser.close()

        # Clean up temp HTML
        os.remove(tmp_html)

        logger.info(f"Modern PDF generated: {os.path.abspath(output_path)}")
        return os.path.abspath(output_path)
