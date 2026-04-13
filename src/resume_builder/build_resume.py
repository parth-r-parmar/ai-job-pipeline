"""
Resume PDF Builder — Generates a professional ATS-friendly resume using fpdf2.

Usage:
    from src.resume_builder.build_resume import ResumePDF
    pdf = ResumePDF(data)
    path = pdf.build("output/resume.pdf")
"""

import os
from fpdf import FPDF

# Layout constants
PAGE_W = 210  # A4
MARGIN = 19   # ~0.75 inch
CONTENT_W = PAGE_W - MARGIN * 2

NAME_SIZE = 22
CONTACT_SIZE = 9.5
SECTION_SIZE = 12
HEADING_SIZE = 10.5
BODY_SIZE = 10
SMALL_SIZE = 9.5

LINE_H = 4.5
BULLET_LINE_H = 4.3
BULLET_GAP = 1.2
SECTION_GAP_BEFORE = 6
SECTION_GAP_AFTER = 3.5
ENTRY_GAP = 3
HEADING_AFTER = 1.5
BULLET_INDENT = 5
BULLET_CHAR_W = 3.5

RULE_THICKNESS = 0.35
RULE_GRAY = 60

# Try common system font paths
FONT_DIRS = [
    "C:/Windows/Fonts",
    "/usr/share/fonts/truetype",
    "/System/Library/Fonts",
    os.path.expanduser("~/.fonts"),
]


class ResumePDF(FPDF):
    def __init__(self, data: dict):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.data = data
        self.set_auto_page_break(auto=True, margin=12)
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self._register_fonts()
        self.add_page()

    def _register_fonts(self):
        fonts = [
            ("georgia.ttf", "georgiab.ttf", "georgiai.ttf", "georgiaz.ttf"),
            ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"),
            ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"),
        ]
        for font_dir in FONT_DIRS:
            if not os.path.isdir(font_dir):
                continue
            for regular, bold, italic, bi in fonts:
                path = os.path.join(font_dir, regular)
                if os.path.exists(path):
                    self.add_font("resume", "", path)
                    self.add_font("resume", "B", os.path.join(font_dir, bold))
                    self.add_font("resume", "I", os.path.join(font_dir, italic))
                    self.add_font("resume", "BI", os.path.join(font_dir, bi))
                    self.ff = "resume"
                    return
        self.ff = "Helvetica"

    def _f(self, style="", size=BODY_SIZE):
        self.set_font(self.ff, style, size)

    def _section_title(self, title: str):
        self.set_y(self.get_y() + SECTION_GAP_BEFORE)
        self._f("B", SECTION_SIZE)
        self.cell(0, 6, title.upper(), new_x="LMARGIN", new_y="NEXT")
        y = self.get_y() + 0.5
        self.set_draw_color(RULE_GRAY)
        self.set_line_width(RULE_THICKNESS)
        self.line(MARGIN, y, PAGE_W - MARGIN, y)
        self.set_y(y + SECTION_GAP_AFTER)

    def _heading_row(self, left: str, right: str):
        self._f("B", HEADING_SIZE)
        self.cell(CONTENT_W * 0.68, 5, left)
        self._f("I", SMALL_SIZE)
        self.cell(CONTENT_W * 0.32, 5, right, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_y(self.get_y() + HEADING_AFTER)

    def _subtitle_row(self, left: str, right: str):
        self._f("I", BODY_SIZE)
        self.cell(CONTENT_W * 0.68, 5, left)
        self._f("I", SMALL_SIZE)
        self.cell(CONTENT_W * 0.32, 5, right, align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_y(self.get_y() + 0.5)

    def _bullet(self, text: str):
        self._f("", BODY_SIZE)
        x = MARGIN + BULLET_INDENT
        self.set_x(x)
        self.cell(BULLET_CHAR_W, BULLET_LINE_H, "\u2022")
        self.set_x(x + BULLET_CHAR_W)
        self.multi_cell(
            CONTENT_W - BULLET_INDENT - BULLET_CHAR_W,
            BULLET_LINE_H, text,
            new_x="LMARGIN", new_y="NEXT",
        )
        self.set_y(self.get_y() + BULLET_GAP)

    def _skill_bullet(self, category: str, items: str):
        x = MARGIN + BULLET_INDENT
        self.set_x(x)
        self._f("", BODY_SIZE)
        self.cell(BULLET_CHAR_W, BULLET_LINE_H, "\u2022")
        self._f("B", BODY_SIZE)
        label = category + ": "
        label_w = self.get_string_width(label)
        self.cell(label_w, BULLET_LINE_H, label)
        self._f("", BODY_SIZE)
        remain_w = CONTENT_W - BULLET_INDENT - BULLET_CHAR_W - label_w
        self.multi_cell(remain_w, BULLET_LINE_H, items, new_x="LMARGIN", new_y="NEXT")
        self.set_y(self.get_y() + BULLET_GAP)

    def build_header(self):
        d = self.data
        self._f("B", NAME_SIZE)
        self.cell(0, 10, d["name"], align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_y(self.get_y() + 2)
        contact = d["contact"]
        parts = [contact["phone"], contact["email"], contact["github"], contact["linkedin"]]
        self._f("", CONTACT_SIZE)
        self.cell(0, 4.5, "  |  ".join(parts), align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_y(self.get_y() + 1)
        self.cell(0, 4.5, contact["location"], align="C", new_x="LMARGIN", new_y="NEXT")

    def build_summary(self):
        if not self.data.get("summary"):
            return
        self._section_title("Professional Summary")
        self._f("", BODY_SIZE)
        self.multi_cell(0, LINE_H, self.data["summary"], new_x="LMARGIN", new_y="NEXT")

    def build_skills(self):
        self._section_title("Technical Skills")
        for cat, items in self.data["skills"].items():
            self._skill_bullet(cat, items)

    def build_experience(self):
        self._section_title("Work Experience")
        for i, exp in enumerate(self.data["experience"]):
            self._heading_row(f"{exp['company']} - {exp['role']}", exp["dates"])
            for b in exp["bullets"]:
                self._bullet(b)
            if i < len(self.data["experience"]) - 1:
                self.set_y(self.get_y() + ENTRY_GAP)

    def build_projects(self):
        self._section_title("Projects")
        for i, proj in enumerate(self.data["projects"]):
            self._heading_row(proj["name"], proj.get("link") or "")
            for b in proj["bullets"]:
                self._bullet(b)
            if i < len(self.data["projects"]) - 1:
                self.set_y(self.get_y() + ENTRY_GAP - 1)

    def build_education(self):
        self._section_title("Education")
        for edu in self.data["education"]:
            self._heading_row(edu["institution"], edu["location"])
            self._subtitle_row(edu["degree"], edu["dates"])

    def build(self, output_path: str = "resume.pdf") -> str:
        """Build the PDF and save to output_path. Returns absolute path."""
        self.build_header()
        self.build_summary()
        self.build_skills()
        self.build_experience()
        self.build_projects()
        self.build_education()

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        self.output(output_path)
        return os.path.abspath(output_path)
