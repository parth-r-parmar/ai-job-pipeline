"""Schedule recurring job scans using OS-native schedulers."""

import os
import sys
import platform
import subprocess
import logging

from src.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

TASK_NAME = "ai-job-pipeline-scan"


def setup_schedule(interval: str, args):
    """Set up or remove a recurring job scan.

    Args:
        interval: "daily", "weekly", or "off"
        args: The parsed argparse namespace (used to reconstruct the command)
    """
    if interval == "off":
        _remove_schedule()
        return

    # Build the command that will run on schedule
    python = sys.executable
    project_dir = str(PROJECT_ROOT)
    cmd_parts = [python, "-m", "src.main", "--dry-run"]

    if args.keywords:
        cmd_parts.extend(["--keywords"] + args.keywords)
    if args.location != "India":
        cmd_parts.extend(["--location", args.location])
    if args.pages != 3:
        cmd_parts.extend(["--pages", str(args.pages)])
    if args.scrapers:
        cmd_parts.extend(["--scrapers"] + args.scrapers)
    if args.no_remote:
        cmd_parts.append("--no-remote")

    cmd = " ".join(cmd_parts)

    if platform.system() == "Windows":
        _schedule_windows(interval, cmd, project_dir)
    else:
        _schedule_unix(interval, cmd, project_dir)


def _schedule_windows(interval: str, cmd: str, working_dir: str):
    """Create a Windows Task Scheduler entry."""
    freq = "DAILY" if interval == "daily" else "WEEKLY"
    extra = ["/d", "MON"] if interval == "weekly" else []

    try:
        subprocess.run(
            ["schtasks", "/create", "/tn", TASK_NAME,
             "/tr", f'cmd /c "cd /d {working_dir} && {cmd}"',
             "/sc", freq, "/st", "09:00", *extra, "/f"],
            check=True,
            capture_output=True,
        )
        logger.info(f"Scheduled {interval} scan at 9:00 AM (Windows Task Scheduler: {TASK_NAME})")
        logger.info(f"  Command: {cmd}")
        logger.info(f"  Verify: schtasks /query /tn {TASK_NAME}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create scheduled task: {e.stderr.decode()}")


def _schedule_unix(interval: str, cmd: str, working_dir: str):
    """Add a crontab entry for Linux/macOS."""
    cron_time = "0 9 * * *" if interval == "daily" else "0 9 * * 1"
    cron_line = f'{cron_time} cd {working_dir} && {cmd} >> {working_dir}/output/scan.log 2>&1'
    marker = f"# {TASK_NAME}"

    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = result.stdout if result.returncode == 0 else ""

        # Remove old entry if exists
        lines = [l for l in existing.splitlines() if TASK_NAME not in l]
        lines.append(f"{cron_line}  {marker}")

        subprocess.run(
            ["crontab", "-"],
            input="\n".join(lines) + "\n",
            text=True,
            check=True,
        )
        logger.info(f"Scheduled {interval} scan at 9:00 AM (crontab)")
        logger.info(f"  Verify: crontab -l | grep {TASK_NAME}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Failed to set up cron job: {e}")


def _remove_schedule():
    """Remove the scheduled scan."""
    if platform.system() == "Windows":
        try:
            subprocess.run(
                ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                check=True, capture_output=True,
            )
            logger.info(f"Removed scheduled task: {TASK_NAME}")
        except subprocess.CalledProcessError:
            logger.info("No scheduled task found to remove.")
    else:
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            if result.returncode == 0:
                lines = [l for l in result.stdout.splitlines() if TASK_NAME not in l]
                subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)
                logger.info("Removed cron job.")
            else:
                logger.info("No cron job found to remove.")
        except FileNotFoundError:
            logger.info("crontab not available.")
