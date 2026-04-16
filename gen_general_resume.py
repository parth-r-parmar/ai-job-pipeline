"""Generate a general-purpose modern resume PDF from resume.json.

Use this when you don't have a specific JD yet (cold outreach, referrals,
general applications).

Optional: add a "core_competencies" field to resume.json (list of 6-8
keyword phrases) to render keyword badges under the summary. If omitted,
the Core Competencies section is hidden cleanly.

Run:
    python gen_general_resume.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from src.resume_builder.html_resume import HtmlResumePDF
from src.config import OUTPUT_DIR, RESUME_PATH


def main():
    with open(RESUME_PATH, "r", encoding="utf-8") as f:
        resume = json.load(f)

    safe_name = resume["name"].replace(" ", "_")
    output_path = os.path.join(str(OUTPUT_DIR), f"{safe_name}_Resume.pdf")

    path = HtmlResumePDF(resume).build(output_path)
    print(f"Generated: {path}")
    print(f"Size: {os.path.getsize(path) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
