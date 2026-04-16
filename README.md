# AI Job Pipeline

An AI-powered job search automation tool that scrapes jobs from multiple portals, scores them against your resume, tailors your resume per job with JD keyword injection, detects ghost postings, and exports everything to a formatted Excel workbook.

## Features

- **Multi-site scraping** — LinkedIn, Internshala, Naukri, Indeed (rotating user-agents, rate limiting)
- **Full JD fetching** — Fetches detailed descriptions from job detail pages for better scoring
- **Ghost job detection** — Flags suspicious postings (high/medium/low risk) using Python heuristics — no AI needed
- **Smart filtering** — Salary threshold, internship exclusion, product vs service company detection
- **AI-powered scoring** — Claude evaluates job-resume match (0-100) with matched/missing keywords
- **JD keyword injection** — Tailoring rewrites bullets using exact JD vocabulary for ATS optimization
- **Tailoring diff view** — Shows exactly what changed in each bullet vs your original resume
- **Two PDF styles** — Classic (fpdf2) or Modern (HTML+Playwright with custom fonts, gradient headers, competency badges)
- **Cross-run dedup** — Re-running reuses previous scores and skips already-tailored PDFs (saves 15-20 min)
- **Excel export** — 4-sheet workbook with Ghost Risk, Injected Keywords, color coding, clickable links
- **Cold outreach sheet** — 20 curated product companies with LinkedIn links and suggested actions
- **One-click apply** — `--open-top 10` opens top job URLs in your browser
- **Scheduled scans** — `--schedule daily` catches fresh postings before others apply
- **Demo mode** — `--demo` shows full output in under 1 second with sample data (no scraping/AI)
- **Remote job search** — Automatically searches for remote opportunities worldwide
- **No API key required** — Scraping, filtering, ghost detection, and export work without any key

## Quick Start

```bash
# 1. Clone
git clone https://github.com/parth-r-parmar/ai-job-pipeline.git
cd ai-job-pipeline

# 2. Install
pip install -r requirements.txt

# 3. Try the demo (no setup needed)
python -m src.main --demo

# 4. Edit resume.json with your data, then run for real
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
| `MIN_SALARY_LPA` | `8` | Filter out jobs below this salary (Lakhs Per Annum) |
| `MATCH_THRESHOLD` | `70` | Jobs scoring above this get tailored resumes |
| `PAGES_PER_SITE` | `3` | Pages to scrape per job site |
| `PDF_STYLE` | `classic` | Default PDF style: `classic`, `modern`, or `both` |
| `MAX_DETAIL_FETCHES` | `20` | Max job detail pages to fetch per scraper |

## Usage

### Demo (try it in 1 second, no setup)
```bash
python -m src.main --demo
```

### Basic (scrape + filter + export)
```bash
python -m src.main --keywords "React Developer" --location "India"
```

### With AI scoring (needs API key or Claude Code CLI)
```bash
# Using Anthropic API key (set in .env)
python -m src.main --keywords "React Developer" --location "India"

# Using Claude Code CLI (no API key needed, uses your login)
python -m src.main --scorer cli --keywords "React Developer" --location "India"
```

### Dry run (scrape + score, skip tailoring)
```bash
python -m src.main --dry-run --keywords "Full Stack Developer"
```

### Modern PDFs
```bash
pip install playwright && playwright install chromium
python -m src.main --pdf-style modern
```

### One-click apply
```bash
python -m src.main --open-top 10    # opens top 10 job URLs in browser
```

### Schedule daily scans
```bash
python -m src.main --schedule daily --keywords "React Developer" --location "India"
python -m src.main --schedule off       # remove scheduled task
```

### Force re-process (ignore cached scores)
```bash
python -m src.main --force    # re-scores and re-tailors everything from scratch
```

### Generate a general resume (no JD needed)
```bash
python gen_general_resume.py    # uses resume.json, outputs to output/
```

### All CLI flags
```
python -m src.main [-h]
  --keywords / -k       Search keywords (default: auto from resume)
  --location / -l       Job location (default: India)
  --pages / -p          Pages per site (default: 3)
  --dry-run             Scrape + score only, skip tailoring
  --output / -o         Output Excel path (default: output/jobs.xlsx)
  --scrapers / -s       Specific scrapers: naukri indeed linkedin internshala
  --no-remote           Skip remote jobs search pass
  --pdf-style           classic (default), modern (HTML+Playwright), or both
  --scorer              api (needs ANTHROPIC_API_KEY) or cli (Claude Code CLI)
  --open-top N          Open top N job URLs in browser after export
  --schedule            Set up recurring scan: daily, weekly, or off
  --demo                Run with sample data, no scraping or AI needed
  --force               Ignore cached scores, re-process everything
```

## Resume Format

Edit `resume.json` with your data:

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
  "core_competencies": [
    "React.js Architecture",
    "Node.js Backend",
    "TypeScript"
  ],
  "education": [{ "institution": "...", "location": "...", "degree": "...", "dates": "..." }],
  "skills": { "Category": "Skill1, Skill2, Skill3" },
  "experience": [{ "company": "...", "role": "...", "dates": "...", "bullets": ["..."] }],
  "projects": [{ "name": "...", "link": "...", "bullets": ["..."] }]
}
```

The `core_competencies` field is optional — if present, renders as keyword badges in the modern PDF.

## Output

### Excel Workbook (4 sheets)

| Sheet | Contents |
|-------|----------|
| **All Jobs** | Every job sorted by score. Columns: Title, Company, Match Score, Recommendation, Reason, **Ghost Risk**, Salary, Matched Keywords, Missing Keywords, **Injected Keywords**, URL |
| **Top Matches** | Jobs above threshold, product companies first |
| **Cold Outreach** | Product companies to cold-email + 20 recommended companies with LinkedIn links |
| **Summary** | Stats: jobs per source, salary range, company type breakdown, score distribution, skill gaps |

### Tailored Resumes

For each top-matching job, the pipeline generates:
- `{Company}_{Role}.json` — tailored resume data with `core_competencies`
- `{Company}_{Role}.pdf` — ATS-friendly PDF (classic or modern)
- `{Company}_{Role}_diff.txt` — shows exactly what changed vs your original resume

### Ghost Job Detection

Every job gets a Ghost Risk flag (low/medium/high) based on:
- Posting age (>30 days = medium, >60 = high)
- Description quality (short/vague = higher risk)
- Salary transparency (undisclosed + vague description = higher risk)
- Title specificity ("Multiple Openings" = high risk)

No AI needed — pure Python heuristics. Ghost risk is color-coded in the Excel (red = high, yellow = medium).

### Cross-Run Deduplication

Re-running the pipeline reuses results from previous runs:
- Jobs already scored in `output/jobs.xlsx` → score is reused (saves ~13s per job)
- Jobs already tailored in `output/tailored_resumes/` → PDF is reused (saves ~60s per job)
- New jobs are scored and tailored normally
- Use `--force` to ignore the cache and re-process everything

## Scrapers

| Site | Method | Status |
|------|--------|--------|
| **LinkedIn** | Guest job API (no login required) | Working |
| **Internshala** | HTML scraping (full-time jobs only) | Working |
| **Naukri** | JSON API + HTML fallback | Partial (API often returns 400) |
| **Indeed** | HTML scraping | Blocked (403 — Cloudflare) |

Contributions welcome for better scraping strategies — especially Playwright-based scrapers for Naukri/Indeed.

## Scoring Modes

### 1. Claude API (recommended for speed)
Set `ANTHROPIC_API_KEY` in `.env`. ~2-3 seconds per job.

### 2. Claude Code CLI (no API key needed)
```bash
python -m src.main --scorer cli
```
Uses your existing Claude Code login via subprocess. ~12-15 seconds per job.

### 3. No scoring
Without an API key or `--scorer cli`, the pipeline scrapes, filters, detects ghost jobs, and exports — just without AI scoring or tailoring.

## How It Compares

| Feature | ai-job-pipeline | Jobright | Sonara | BulkApply |
|---------|----------------|----------|--------|-----------|
| Open source | Yes (MIT) | No | No | No |
| Indian market (LPA, Naukri, Internshala) | Yes | No (US only) | No (US only) | No |
| Ghost job detection | Yes | No | No | No |
| Resume tailoring with diff view | Yes | Partial | No | No |
| Works without API key | Yes | No | No | No |
| Cross-run dedup | Yes | N/A | N/A | N/A |
| Product vs service company detection | Yes | No | No | No |
| Cold outreach recommendations | Yes | No | No | No |
| Bulk auto-apply | No (intentional — quality > quantity) | Yes | Yes | Yes |
| Price | Free | $30+/mo | $20+/mo | $10+/mo |

## Project Structure

```
ai-job-pipeline/
├── README.md
├── LICENSE
├── requirements.txt
├── setup.py
├── .env.example
├── .gitignore
├── resume.json                 # YOUR resume (edit this)
├── gen_general_resume.py       # Generate a general-purpose PDF
├── examples/
│   └── sample_jobs.json        # Sample data for --demo mode
├── src/
│   ├── __init__.py
│   ├── config.py               # .env loader + defaults
│   ├── resume_parser.py        # Extracts keywords from resume
│   ├── filters.py              # Salary, internship, company filters
│   ├── ghost_detector.py       # Ghost job risk detection
│   ├── scorer.py               # Claude API scoring
│   ├── scorer_cli.py           # Claude Code CLI scoring
│   ├── tailor.py               # Resume tailoring + diff + PDF
│   ├── tailor_cli.py           # CLI-based tailoring
│   ├── exporter.py             # Excel export (4 sheets)
│   ├── scheduler.py            # Cron / Task Scheduler setup
│   ├── main.py                 # CLI entry point
│   ├── resume_builder/
│   │   ├── build_resume.py     # Classic PDF (fpdf2)
│   │   ├── html_resume.py      # Modern PDF (HTML+Playwright)
│   │   ├── fonts/              # Space Grotesk + DM Sans
│   │   └── templates/          # HTML template
│   └── scrapers/
│       ├── base.py             # Abstract scraper with UA rotation
│       ├── naukri.py
│       ├── indeed.py
│       ├── linkedin.py
│       └── internshala.py
└── output/                     # Generated at runtime
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
