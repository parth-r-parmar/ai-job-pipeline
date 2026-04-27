# AI Job Pipeline

**Stop retyping your resume for every job application.** This tool scrapes job portals, scores each posting against your resume with Claude AI, and generates a tailored resume PDF for every strong match — all in one click (or one command). Runs locally on your laptop, MIT licensed, no account needed.

Built for job seekers who apply to 10+ roles a week and are tired of the copy-paste grind. Especially handy in the Indian market — parses LPA salaries, flags product vs service companies (Razorpay, CRED, Swiggy etc.), and has a curated cold-outreach list built in.

---

## Table of contents

- [What you get](#what-you-get)
- [Quick start — Web GUI](#quick-start--web-gui) *(recommended for most people)*
- [Quick start — CLI](#quick-start--cli) *(for power users)*
- [Screenshots](#screenshots)
- [Configuration](#configuration)
- [How it works](#how-it-works)
- [How this compares to alternatives](#how-this-compares-to-alternatives)
- [GUI vs CLI feature matrix](#gui-vs-cli-feature-matrix)
- [CLI usage examples](#cli-usage-examples)
- [Full CLI flag reference](#full-cli-flag-reference)
- [Development](#development)
- [Known limitations](#known-limitations)
- [License](#license)

---

## What you get

- **Finds** matching jobs across LinkedIn, Internshala, Naukri, and Indeed
- **Scores** every job 0–100 against your resume and lists the keywords you're missing
- **Tailors** your resume PDF per strong-match job — with a validator that blocks the AI from inventing skills you don't have
- **Exports** everything to an Excel workbook (sorted, colour-coded, Cold Outreach sheet included)
- **Detects ghost postings** using Python heuristics (no AI for this one, just pattern matching)

> **What this is NOT:** a recruiter service, a paid SaaS, or an account-based tool. Everything runs on your machine. The only external call is to Claude AI, using your key (or your Claude Code CLI login).

---

## Quick start — Web GUI

```bash
git clone https://github.com/parth-r-parmar/ai-job-pipeline.git
cd ai-job-pipeline
pip install -r requirements.txt
python app.py
```

Your browser opens at `http://localhost:5000`. Click **Demo** to see sample output in under 1 second. When you're ready to run for real, edit `resume.json` with your details, put your Anthropic API key in `.env` (or install [Claude Code](https://claude.com/claude-code) to run with no key), then click **Run**.

**GUI highlights**

- Live progress log (phases, counters, ETA)
- Dark / light mode with a cycling toggle; follows your OS by default
- Mobile-friendly — check results from your phone during standups
- "Open top N in tabs" button after a run — one click, ten applications open in new browser tabs
- **Discreet mode** (`Esc Esc`) swaps the tab title to "Quarterly Report — Google Sheets" for moments when you're at the office
- CLI equivalent preview below the form — tweak the UI, copy the exact terminal command, run it anywhere

---

## Quick start — CLI

```bash
# See it work instantly (no API key, no scraping)
python -m src.main --demo

# First real run — scrape + score, skip the tailoring pass
python -m src.main --keywords "React Developer" --location "India" --dry-run

# Full run — scrape → score → tailor top matches → open top 10 URLs
python -m src.main --keywords "React Developer" --location "India" --open-top 10
```

Results land in `output/jobs.xlsx` plus `output/tailored_resumes/*.pdf` for every job scoring ≥ your threshold.

---

## Screenshots

| Dark (desktop) | Light (desktop) | Mobile |
|----------------|-----------------|--------|
| [1440-dark](screenshots/polish-v2/1440-dark.png) | [1440-light](screenshots/polish-v2/1440-light.png) | [375-dark](screenshots/polish-v2/375-dark.png) |

(See `screenshots/polish-v2/` for full-page captures at every breakpoint.)

---

## Configuration

### `.env` — copy and edit

```bash
cp .env.example .env
```

| Variable | Default | What it does |
|----------|---------|--------------|
| `ANTHROPIC_API_KEY` | *(empty)* | Your Claude API key. Leave empty if you use `--scorer cli` and have Claude Code installed — no key needed. |
| `MIN_SALARY_LPA` | `8` | Drops jobs below this salary (in Lakhs Per Annum) |
| `MATCH_THRESHOLD` | `70` | Jobs scoring ≥ this get a tailored resume PDF |
| `PAGES_PER_SITE` | `3` | How many pages to scrape per job site |
| `PDF_STYLE` | `classic` | `classic` (default, no extra deps), `modern` (needs Playwright), or `both` |
| `MAX_DETAIL_FETCHES` | `20` | Max detail pages to fetch per scraper |
| `RESUME_PATH` | `resume.json` | Path to your resume JSON (supports absolute paths for shared/private setups) |

### `resume.json` — your profile as data

The tool scores jobs against this file. See `examples/resume.example.json` for a full template. The minimal shape:

```json
{
  "name": "Your Name",
  "contact": {
    "phone": "+1 555-123-4567",
    "email": "you@example.com",
    "linkedin": "linkedin.com/in/you",
    "location": "City, Country"
  },
  "summary": "Full Stack Developer with 4+ years of experience...",
  "core_competencies": ["React", "Node.js", "TypeScript", "..."],
  "education": [...],
  "skills": { "Languages": "JavaScript, Python, ...", "...": "..." },
  "experience": [...],
  "projects": [...]
}
```

---

## How it works

```
┌──────────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐    ┌────────┐
│  Scrape  │ →  │ Filter  │ →  │  Ghost   │ →  │  Score   │ →  │ Tailor  │ →  │ Export │
│ LinkedIn │    │ salary  │    │ detection│    │  Claude  │    │ resume  │    │  Excel │
│ Intern…  │    │ intern. │    │heuristic │    │  0-100   │    │  + PDF  │    │ + PDF  │
└──────────┘    └─────────┘    └──────────┘    └──────────┘    └─────────┘    └────────┘
```

Each stage is a module under `src/`. The Flask web GUI (`app.py`) wraps the same pipeline and streams progress over Server-Sent Events. Re-running is cheap: already-scored jobs and already-tailored resumes are cached and skipped (saves 15-20 minutes on the second run).

The tailoring pass has a **validator** that compares the AI-rewritten resume to your original JSON. If it detects a fabricated skill, altered company name, or changed date, the rewrite is rejected. The AI can reorder, emphasise, and rephrase — but never invent.

---

## How this compares to alternatives

| | ai-job-pipeline | Paid tools (Rezi / Teal / JobScan) | ChatGPT copy-paste | Other OSS scrapers |
|---|---|---|---|---|
| **Cost** | Free | $10–30/mo | Free-ish (rate limits) | Free |
| **Data stays local** | ✅ | ❌ (cloud) | ❌ (OpenAI) | ✅ |
| **End-to-end (scrape → score → tailor → PDF)** | ✅ | ❌ (tailor only) | ❌ (manual paste per JD) | ❌ (scrape only) |
| **Ghost-job detection** | ✅ Python heuristics | ❌ | ❌ | ❌ |
| **Indian market (LPA, product companies)** | ✅ first-class | ⚠️ generic | ❌ manual | ⚠️ |
| **Hallucination guard (no invented skills)** | ✅ validator | ⚠️ varies | ❌ (your responsibility) | N/A |
| **Cold outreach list** | ✅ 20 curated + LinkedIn | ❌ | ❌ | ❌ |
| **Batch PDF generation** | ✅ | ❌ (one at a time) | ❌ | ❌ |

---

## GUI vs CLI feature matrix

Everything you can do in the GUI, you can do in the CLI. A few power-user flags are CLI-only because they wouldn't make sense in a web form.

| Feature | Web GUI | CLI flag | Notes |
|---|---|---|---|
| Keywords | text input | `--keywords` | |
| Location | text + autocomplete | `--location` | Freeform — "Ahmedabad", "Singapore", anything |
| Pages to scrape | number input | `--pages` | |
| Scraper selection | checkboxes | `--scrapers` | |
| Include remote jobs | checkbox | *(default on; `--no-remote` opts out)* | |
| AI scorer (api / cli) | radio | `--scorer` | CLI mode needs Claude Code installed |
| PDF style | radio | `--pdf-style` | Default `classic` — no Playwright required |
| Min salary (LPA) | number input | *(env-var `MIN_SALARY_LPA`)* | GUI writes to env at runtime |
| Match threshold | number input | *(env-var `MATCH_THRESHOLD`)* | Same |
| Dry run (no tailoring) | checkbox | `--dry-run` | |
| Force re-process | checkbox | `--force` | |
| Demo (sample data) | Demo button | `--demo` | |
| Open top N in tabs | button in stats bar | `--open-top` | GUI uses one `window.open()` per URL |
| **Schedule recurring scan** | — | `--schedule daily\|weekly\|off` | CLI-only: drops a crontab / Task Scheduler entry |
| **Custom output path** | — | `--output path.xlsx` | CLI-only |

---

## CLI usage examples

```bash
# Dry run — scrape + score only, no tailored PDFs
python -m src.main --dry-run --keywords "Full Stack Developer"

# Use Claude Code CLI instead of Anthropic API (no API key needed)
python -m src.main --scorer cli --keywords "React Developer"

# Modern PDFs (needs one-time setup)
pip install playwright && playwright install chromium
python -m src.main --pdf-style modern

# Open top 10 job URLs in browser after export
python -m src.main --open-top 10

# Install a daily recurring scan (uses OS scheduler)
python -m src.main --schedule daily --keywords "React Developer"
python -m src.main --schedule off  # remove it

# Force re-score + re-tailor everything (ignores cached scores)
python -m src.main --force

# Separately: generate a general (no-JD) resume PDF from resume.json
python gen_general_resume.py
```

---

## Full CLI flag reference

<details>
<summary>Click to expand</summary>

```
python -m src.main [-h]
  --keywords / -k       Search keywords (default: auto-generated from your resume)
  --location / -l       Job location (default: India; accepts any string)
  --pages / -p          Pages per site (default: 3)
  --dry-run             Scrape + score only, skip tailoring
  --output / -o         Output Excel path (default: output/jobs.xlsx)
  --scrapers / -s       Pick specific scrapers: naukri indeed linkedin internshala
  --no-remote           Skip the remote-jobs scrape pass
  --pdf-style           classic (default), modern (HTML + Playwright), or both
  --scorer              api (uses ANTHROPIC_API_KEY) or cli (uses Claude Code login)
  --open-top N          Open top N job URLs in browser after export
  --schedule            daily / weekly / off — install or remove a recurring scan
  --demo                Run against sample data; no scraping, no AI, ~1 second
  --force               Ignore cached scores, re-process everything from scratch
```

</details>

---

## Development

```bash
# Install dev tools
pip install -r requirements-dev.txt

# Run the test suite (covers routes, HTML landmarks, theme toggle, CLI preview,
# icon sprite, default PDF style, sort behaviour, resume-exists endpoint, …)
python -m pytest tests/ -v
```

21+ pytest tests, runs in under a second. No Playwright dependency for the test suite; Playwright is used separately for interactive verification.

### Project layout

```
ai-job-pipeline/
├── app.py                  # Flask web GUI
├── src/
│   ├── main.py             # CLI entrypoint + orchestration
│   ├── scrapers/           # LinkedIn, Internshala, Naukri, Indeed
│   ├── scorer.py           # Anthropic SDK scorer
│   ├── scorer_cli.py       # Claude Code CLI scorer (no API key)
│   ├── tailor.py           # Resume tailoring (with hallucination validator)
│   ├── ghost_detector.py   # Heuristics, no AI
│   ├── filters.py          # Salary, internship, product/service classifier
│   └── exporter.py         # 4-sheet Excel writer
├── static/                 # GUI CSS + JS
├── templates/index.html    # Single-page GUI template
├── tests/                  # pytest suite
└── screenshots/            # Reference captures (dark/light/mobile)
```

---

## Known limitations

- **Naukri** API returns 400 intermittently → HTML fallback with rotating user-agents
- **Indeed** has Cloudflare anti-bot → 403 on most attempts. Shipped as a known limit rather than fake success.
- **LinkedIn** scraper uses the public guest API; only listing-level data is reliably fetched (detail pages are harder)
- Resume tailor is **conservative by design** — it reorders bullets and swaps vocabulary, but never adds new experience, changes dates, or alters company names. This is a feature.

---

## License

MIT. Use it, fork it, ship derivatives. PRs welcome.
