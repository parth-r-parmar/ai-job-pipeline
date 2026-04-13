# AI Job Pipeline

An AI-powered job search automation tool that scrapes jobs from multiple Indian job portals, scores them against your resume using Claude AI, tailors your resume for top matches, and exports everything to a formatted Excel workbook.

## Features

- **Multi-site scraping** — LinkedIn, Internshala, Naukri, Indeed (with rotating user-agents and rate limiting)
- **Full job description fetching** — Automatically fetches detailed JDs from job detail pages for better scoring
- **Smart filtering** — Minimum salary threshold, internship exclusion, product-company detection
- **AI-powered scoring** — Claude API evaluates job-resume match (0-100) with keyword analysis
- **JD keyword injection** — Tailoring rewrites your resume using exact JD vocabulary for ATS optimization
- **Two PDF styles** — Classic (fpdf2, lightweight) or Modern (HTML+Playwright with custom fonts, gradient headers, competency badges)
- **Resume tailoring** — Automatically rewrites your resume for each top-matching job (no fabrication)
- **Excel export** — 4-sheet workbook with color coding, clickable links, and analytics
- **Cold outreach sheet** — Recommends product companies worth cold-emailing
- **One-click apply** — `--open-top 10` opens top job URLs in your browser
- **Scheduled scans** — `--schedule daily` runs every morning to catch fresh postings
- **Remote job search** — Automatically searches for remote opportunities worldwide
- **No API key required** — Core scraping and filtering works without any API key

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/parth-r-parmar/ai-job-pipeline.git
cd ai-job-pipeline

# 2. Install dependencies
pip install -r requirements.txt

# 3. Edit your resume
#    Open resume.json and replace the mock data with your own

# 4. Run the pipeline
python -m src.main --keywords "React Developer" --location "India" --pages 2 --dry-run
```

Your results will be in `output/jobs.xlsx`.

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | _(empty)_ | Claude API key for scoring/tailoring. Get from [console.anthropic.com](https://console.anthropic.com) |
| `MIN_SALARY_LPA` | `8` | Filter out jobs below this salary (in Lakhs Per Annum) |
| `MATCH_THRESHOLD` | `70` | Jobs scoring above this get tailored resumes |
| `PAGES_PER_SITE` | `3` | Pages to scrape per job site |

## Usage

### Basic (scrape + filter + export)
```bash
python -m src.main --keywords "React Developer" --location "Gujarat"
```

### Dry run (scrape + score, skip tailoring)
```bash
python -m src.main --dry-run --keywords "Full Stack Developer" --location "India"
```

### Auto keywords from resume
```bash
python -m src.main --location "Bangalore"
# Keywords are automatically extracted from your resume.json
```

### Specific scrapers only
```bash
python -m src.main --scrapers linkedin internshala --pages 3
```

### Skip remote job search
```bash
python -m src.main --no-remote --keywords "Node.js Developer"
```

### One-click apply
```bash
python -m src.main --open-top 10    # opens top 10 job URLs in your browser
```

### Modern PDF style
```bash
pip install playwright && playwright install chromium
python -m src.main --pdf-style modern    # gradient headers, custom fonts, competency badges
```

### Schedule daily scans
```bash
python -m src.main --schedule daily --keywords "React Developer" --location "India"
python -m src.main --schedule off       # remove scheduled task
```

### All flags
```
python -m src.main [-h]
  --keywords / -k       Search keywords (default: auto from resume)
  --location / -l       Job location (default: India)
  --pages / -p          Pages per site (default: 3)
  --dry-run             Scrape + score only, skip tailoring
  --output / -o         Output Excel path (default: output/jobs.xlsx)
  --scrapers / -s       Specific scrapers: naukri indeed linkedin internshala
  --no-remote           Skip remote jobs search pass
  --pdf-style           PDF style: classic (default) or modern (HTML+Playwright)
  --open-top N          Open top N job URLs in browser after export
  --schedule            Set up recurring scan: daily, weekly, or off
```

## Resume Format

Edit `resume.json` with your data. The structure must match this format:

```json
{
  "name": "Your Name",
  "contact": {
    "phone": "+1 555-123-4567",
    "email": "you@email.com",
    "github": "github.com/username",
    "linkedin": "linkedin.com/in/username",
    "location": "City, Country"
  },
  "summary": "Your professional summary...",
  "education": [
    {
      "institution": "University Name",
      "location": "City, Country",
      "degree": "Degree Name; GPA: X.X/X.X",
      "dates": "Aug 2017 - May 2021"
    }
  ],
  "skills": {
    "Category Name": "Skill1, Skill2, Skill3"
  },
  "experience": [
    {
      "company": "Company Name",
      "role": "Job Title",
      "dates": "Jun 2022 - Present",
      "bullets": [
        "Achievement with metrics..."
      ]
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "link": "project-url.com",
      "bullets": [
        "What you built and impact..."
      ]
    }
  ]
}
```

The optional `core_competencies` field (list of keyword phrases) renders as badges in the modern PDF style.

## Output

### Excel Workbook (4 sheets)

| Sheet | Contents |
|-------|----------|
| **All Jobs** | Every job sorted by score, color coded (green/yellow/red), with company type, salary, clickable URLs |
| **Top Matches** | Jobs above match threshold, product companies first |
| **Cold Outreach** | Product companies to cold-email + 20 recommended companies with LinkedIn links |
| **Summary** | Stats: jobs per source, salary range, company type breakdown, score distribution |

### Tailored Resumes

For jobs scoring above the threshold, the pipeline generates:
- `output/tailored_resumes/{Company}_{Role}.json` — tailored resume data
- `output/tailored_resumes/{Company}_{Role}.pdf` — ATS-friendly PDF

## Scrapers

| Site | Method | Status |
|------|--------|--------|
| **LinkedIn** | Guest job API (no login required) | Working |
| **Internshala** | HTML scraping (jobs only, no internships) | Working |
| **Naukri** | JSON API + HTML fallback | Partial (API often returns 400) |
| **Indeed** | HTML scraping | Blocked (403 — Cloudflare protection) |

> LinkedIn and Internshala consistently return results. Naukri and Indeed have aggressive anti-bot measures. Contributions welcome for better scraping strategies.

## Scoring Modes

### 1. Claude API (recommended)
Set `ANTHROPIC_API_KEY` in `.env`. Each job is evaluated by Claude with:
- Match score (0-100)
- Matched/missing keywords
- Recommendation (Strong/Good/Moderate/Weak Match)

### 2. Claude Code CLI (no API key needed)
If you have [Claude Code](https://claude.com/claude-code) installed and logged in:
```python
# In src/main.py, change the import:
from src.scorer_cli import score_all_jobs  # instead of src.scorer
```
This calls the `claude` CLI using your existing session.

### 3. No scoring
Without an API key, the pipeline still scrapes, filters, and exports — just without AI scoring.

## Project Structure

```
ai-job-pipeline/
├── README.md
├── LICENSE
├── requirements.txt
├── setup.py
├── .env.example
├── .gitignore
├── resume.json              # YOUR resume (edit this)
├── gen_general_resume.py   # Generate a single general-purpose PDF from resume.json
├── src/
│   ├── __init__.py
│   ├── config.py            # .env loader + defaults
│   ├── resume_parser.py     # Extracts keywords from resume
│   ├── filters.py           # Salary, internship, company filters
│   ├── scorer.py            # Claude API scoring
│   ├── scorer_cli.py        # Claude Code CLI scoring
│   ├── tailor.py            # Resume tailoring + PDF
│   ├── exporter.py          # Excel export
│   ├── main.py              # CLI entry point
│   ├── resume_builder/
│   │   ├── __init__.py
│   │   └── build_resume.py  # PDF generator
│   └── scrapers/
│       ├── __init__.py
│       ├── base.py           # Abstract scraper with UA rotation
│       ├── naukri.py
│       ├── indeed.py
│       ├── linkedin.py
│       └── internshala.py
└── output/                   # Generated at runtime
    ├── jobs.xlsx
    └── tailored_resumes/
```

## Adding a New Scraper

1. Create `src/scrapers/my_site.py`
2. Extend `BaseScraper` and implement `scrape(keywords, location, pages)`
3. Set `SOURCE = "my_site"`
4. Return list of dicts with keys: `title, company, location, experience, salary, job_type, posted_date, description, url`
5. Register in `src/scrapers/__init__.py`

```python
from .base import BaseScraper

class MySiteScraper(BaseScraper):
    SOURCE = "my_site"

    def scrape(self, keywords, location, pages):
        jobs = []
        for page in range(1, pages + 1):
            self._delay()
            soup = self._get(f"https://mysite.com/jobs?q={'+'.join(keywords)}&page={page}")
            if not soup:
                continue
            # Parse jobs...
            jobs.append(self._normalize_job({...}))
        return jobs
```

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/new-scraper`)
3. Commit your changes
4. Push and open a Pull Request

## License

MIT License. See [LICENSE](LICENSE) for details.

---

Built with Claude AI by [Parth Parmar](https://github.com/parth-r-parmar)
