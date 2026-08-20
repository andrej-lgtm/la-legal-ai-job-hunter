"""Main entrypoint for Legal & AI Job Hunter."""

import argparse
import io
import logging
import sys
from datetime import datetime
from pathlib import Path
import uvicorn
from rich.console import Console
from rich.table import Table

from src.config import load_config
from src.db.database import Database
from src.engine.scorer import score_job
from src.notifiers.digest_html import generate_html_digest
from src.notifiers.email_notifier import send_email_digest
from src.notifiers.webhook import send_webhook_alert
from src.scrapers.aggregator import ScraperAggregator

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("legal_job_hunter")
console = Console(force_terminal=True)


def run_pipeline(config_path: str = "config.yaml"):
    """Execute end-to-end scrape, scoring, storage, and notifications."""
    console.print("\n[bold cyan]⚖️  Starting Legal & AI Job Hunt (Los Angeles & LA Metro)...[/bold cyan]")
    config = load_config(config_path)
    db = Database(config.database.path)

    # 1. Scraping
    console.print("[dim]Fetching jobs from JobSpy (LinkedIn/Indeed/Glassdoor/Google) and direct ATS boards...[/dim]")
    aggregator = ScraperAggregator()
    raw_jobs = aggregator.fetch_all(config)
    console.print(f"[green]✓[/green] Fetched [bold]{len(raw_jobs)}[/bold] total raw postings.")

    # 2. Filtering and Scoring
    console.print("[dim]Evaluating JD requirements, 1-3 years experience, and Legal AI relevance...[/dim]")
    qualified_jobs = []
    for job in raw_jobs:
        score, reasons, is_qual = score_job(job, config)
        if is_qual:
            qualified_jobs.append(job)

    # 3. Database Persistence
    new_count, updated_count = db.save_jobs(raw_jobs)
    console.print(
        f"[green]✓[/green] Database updated: [bold green]{new_count} new[/bold green], [bold yellow]{updated_count} updated[/bold yellow]."
    )

    # 4. Generate Daily HTML Digest
    digest_file = generate_html_digest(qualified_jobs, output_dir=config.notifications.digest.output_dir)
    console.print(f"[green]✓[/green] Daily HTML digest created: [bold underline cyan]{digest_file.resolve()}[/bold underline cyan]")

    # 5. Send Alerts if configured
    if config.notifications.webhook.enabled:
        if send_webhook_alert(qualified_jobs, config.notifications.webhook):
            console.print("[green]✓[/green] Webhook notification delivered.")
    if config.notifications.email.enabled:
        if send_email_digest(qualified_jobs, config.notifications.email):
            console.print("[green]✓[/green] Email digest sent.")

    # 6. Render Terminal Table Summary
    table = Table(
        title=f"Top Legal & AI Job Matches (LA Metro) — {datetime.now().strftime('%Y-%m-%d')}",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Score", style="bold cyan", width=8)
    table.add_column("Category", style="green", width=18)
    table.add_column("Title & Company", style="white", min_width=30)
    table.add_column("Location", style="yellow", width=18)
    table.add_column("JD / Exp Detected", style="dim", min_width=25)

    sorted_qualified = sorted(qualified_jobs, key=lambda x: x.match_score, reverse=True)
    for j in sorted_qualified[:15]:
        exp_info = f"JD: {j.jd_notes} | Exp: {j.exp_raw or '1-3 yrs'}"
        table.add_row(
            f"{j.match_score}%",
            j.category,
            f"{j.title}\n[dim]{j.company}[/dim]",
            j.location,
            exp_info,
        )

    console.print("\n", table)
    console.print(
        f"\n[bold green]Complete![/bold green] Found [bold]{len(qualified_jobs)}[/bold] roles matching your criteria."
    )
    console.print(f"Open [cyan]{digest_file.resolve()}[/cyan] in your browser or run [bold]python main.py --dashboard[/bold] to review.\n")


def start_dashboard(port: int = 8000):
    """Start the interactive local web dashboard."""
    console.print(f"\n[bold cyan]🚀 Starting Legal & AI Job Dashboard on [underline]http://localhost:{port}[/underline] ...[/bold cyan]")
    uvicorn.run("src.dashboard.app:app", host="127.0.0.1", port=port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="Legal & AI Job Hunter (Los Angeles Metro)")
    parser.add_argument("--run-now", action="store_true", help="Run the scraper and generate digest immediately")
    parser.add_argument("--dashboard", action="store_true", help="Launch the local interactive web dashboard")
    parser.add_argument("--port", type=int, default=8000, help="Port for dashboard (default: 8000)")
    parser.add_argument("--digest", action="store_true", help="Generate HTML digest from existing DB records")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")

    args = parser.parse_args()

    if args.dashboard:
        start_dashboard(port=args.port)
    elif args.digest:
        config = load_config(args.config)
        db = Database(config.database.path)
        jobs = db.get_jobs(min_score=60)
        digest_file = generate_html_digest(jobs, output_dir=config.notifications.digest.output_dir)
        console.print(f"[green]✓[/green] HTML digest regenerated: {digest_file.resolve()}")
    else:
        # Default or explicit --run-now
        run_pipeline(config_path=args.config)


if __name__ == "__main__":
    main()
