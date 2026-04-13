"""
AI Job Pipeline CLI — Scrape jobs, score matches, tailor resumes, export results.

Usage:
    python -m src.main --keywords "react developer" --location "India" --pages 2
    python -m src.main --dry-run
    python -m src.main --scrapers naukri indeed --pages 1
"""

import argparse
import logging
import time

import webbrowser

from src.config import (
    MATCH_THRESHOLD, PAGES_PER_SITE, OUTPUT_EXCEL,
    ANTHROPIC_API_KEY, INCLUDE_REMOTE, OUTPUT_DIR,
    MAX_DETAIL_FETCHES, PDF_STYLE,
)
from src.resume_parser import get_search_keywords
from src.scrapers import ALL_SCRAPERS
from src.filters import filter_jobs
from src.scorer import score_all_jobs
from src.tailor import tailor_and_generate
from src.exporter import export

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_SCRAPER_MAP = {s.SOURCE: s for s in ALL_SCRAPERS}


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI-powered job search pipeline — scrape, score, tailor, export."
    )
    parser.add_argument(
        "--keywords", "-k", nargs="+",
        help="Search keywords (default: auto-extracted from resume)",
    )
    parser.add_argument(
        "--location", "-l", default="India",
        help="Job location filter (default: India)",
    )
    parser.add_argument(
        "--pages", "-p", type=int, default=PAGES_PER_SITE,
        help=f"Pages to scrape per site (default: {PAGES_PER_SITE})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Scrape + score only, skip resume tailoring (saves API cost)",
    )
    parser.add_argument(
        "--output", "-o", default=OUTPUT_EXCEL,
        help=f"Output Excel path (default: {OUTPUT_EXCEL})",
    )
    parser.add_argument(
        "--scrapers", "-s", nargs="+", choices=list(_SCRAPER_MAP.keys()),
        help="Run only specific scrapers (default: all)",
    )
    parser.add_argument(
        "--no-remote", action="store_true",
        help="Skip the remote jobs search pass",
    )
    parser.add_argument(
        "--pdf-style", choices=["classic", "modern", "both"], default=PDF_STYLE,
        help="Resume PDF style: classic (fpdf2), modern (HTML+Playwright), or both",
    )
    parser.add_argument(
        "--scorer", choices=["api", "cli"], default="api",
        help="AI backend: api (Anthropic SDK, needs ANTHROPIC_API_KEY) or cli (Claude Code CLI, uses existing login)",
    )
    parser.add_argument(
        "--open-top", type=int, default=0,
        help="Open top N job URLs in browser after export (e.g., --open-top 10)",
    )
    parser.add_argument(
        "--schedule", choices=["daily", "weekly", "off"],
        help="Set up recurring scan: daily (9AM), weekly (Monday 9AM), or off",
    )
    return parser.parse_args()


def _scrape_pass(scraper_classes, keywords, location, pages, label=""):
    jobs = []
    tag = f" ({label})" if label else ""
    for ScraperClass in scraper_classes:
        scraper = ScraperClass()
        logger.info(f"Scraping {scraper.SOURCE}{tag}...")
        try:
            result = scraper.scrape(keywords, location, pages)
            logger.info(f"  Found {len(result)} jobs from {scraper.SOURCE}{tag}")
            jobs.extend(result)
        except Exception as e:
            logger.error(f"  Scraper {scraper.SOURCE} failed: {e}")
    return jobs


def _deduplicate(jobs: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for job in jobs:
        key = job.get("url") or f"{job.get('title')}|{job.get('company')}"
        if key and key not in seen:
            seen.add(key)
            unique.append(job)
    if len(unique) < len(jobs):
        logger.info(f"Removed {len(jobs) - len(unique)} duplicates")
    return unique


def _open_top_jobs(jobs: list[dict], count: int):
    """Open top N job URLs in default browser."""
    scored = sorted(jobs, key=lambda j: j.get("match_score", 0), reverse=True)
    opened = 0
    for job in scored:
        if opened >= count:
            break
        url = job.get("url")
        if url:
            webbrowser.open(url)
            opened += 1
            time.sleep(0.5)
    logger.info(f"Opened {opened} job URLs in browser")


def main():
    args = parse_args()
    start_time = time.time()

    # Handle scheduling
    if args.schedule:
        from src.scheduler import setup_schedule
        setup_schedule(args.schedule, args)
        return

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Keywords
    keywords = args.keywords or get_search_keywords()
    logger.info(f"Search keywords: {keywords}")
    logger.info(f"Location: {args.location} | Pages per site: {args.pages}")

    scraper_classes = (
        [_SCRAPER_MAP[name] for name in args.scrapers]
        if args.scrapers else ALL_SCRAPERS
    )

    # Step 2: Scrape (location)
    all_jobs = _scrape_pass(scraper_classes, keywords, args.location, args.pages)

    # Step 2b: Scrape remote
    if INCLUDE_REMOTE and not args.no_remote:
        logger.info("--- Remote jobs pass ---")
        remote_jobs = _scrape_pass(
            scraper_classes, keywords, "Remote", args.pages, label="remote"
        )
        for job in remote_jobs:
            if job.get("location") in ("N/A", "", None):
                job["location"] = "Remote"
            elif "remote" not in job.get("location", "").lower():
                job["location"] = job["location"] + " (Remote)"
        all_jobs.extend(remote_jobs)

    # Step 3: Deduplicate
    all_jobs = _deduplicate(all_jobs)
    logger.info(f"Total unique jobs before filtering: {len(all_jobs)}")

    # Step 3b: Enrich — fetch full descriptions for jobs with empty/short descriptions
    logger.info("Fetching full job descriptions from detail pages...")
    for ScraperClass in scraper_classes:
        scraper = ScraperClass()
        source_jobs = [j for j in all_jobs if j.get("source") == scraper.SOURCE]
        scraper.enrich_descriptions(source_jobs, max_fetches=MAX_DETAIL_FETCHES)

    # Step 4: Filter
    all_jobs = filter_jobs(all_jobs)

    if not all_jobs:
        logger.warning("No jobs remaining after filters. Exiting.")
        return

    # Step 5: Score — pick backend based on --scorer flag
    if args.scorer == "cli":
        from src.scorer_cli import score_all_jobs as _score_fn
        from src.tailor_cli import tailor_and_generate as _tailor_fn
        ai_available = True
        logger.info("Using Claude Code CLI backend (no API key needed)")
    else:
        _score_fn = score_all_jobs
        _tailor_fn = tailor_and_generate
        ai_available = bool(ANTHROPIC_API_KEY)

    if ai_available:
        logger.info("Scoring jobs against resume...")
        all_jobs = _score_fn(all_jobs)

        scored_above = sum(1 for j in all_jobs if j.get("match_score", 0) >= MATCH_THRESHOLD)
        logger.info(f"Jobs scoring >= {MATCH_THRESHOLD}: {scored_above}")

        # Step 6: Tailor (unless dry-run)
        if not args.dry_run:
            top_jobs = [j for j in all_jobs if j.get("match_score", 0) >= MATCH_THRESHOLD]
            if top_jobs:
                logger.info(f"Tailoring resumes for {len(top_jobs)} top matches...")
                for job in top_jobs:
                    pdf_path = _tailor_fn(job, pdf_style=args.pdf_style)
                    if pdf_path:
                        job["tailored_pdf_path"] = str(pdf_path) if not isinstance(pdf_path, list) else " | ".join(pdf_path)
                    time.sleep(0.5)
            else:
                logger.info("No jobs above threshold — skipping tailoring.")
        else:
            logger.info("Dry run — skipping resume tailoring.")
    else:
        logger.warning(
            "No AI backend available. ANTHROPIC_API_KEY not set and --scorer cli not specified. "
            "Use --scorer cli to use Claude Code CLI, or set ANTHROPIC_API_KEY in .env."
        )

    # Step 7: Export
    output = export(all_jobs, args.output)
    elapsed = round(time.time() - start_time, 1)
    logger.info(f"Done! Results exported to: {output} ({elapsed}s)")

    # Step 8: Open top jobs in browser
    if args.open_top > 0:
        _open_top_jobs(all_jobs, args.open_top)


if __name__ == "__main__":
    main()
