"""CLI command for scraping matches by date."""

import asyncio
import click
from sofascraper.cli.options import global_options, sport_filter
from sofascraper.core.scraper_app import ScraperApp
from sofascraper.cli.validators import validate_date


@click.command("dates")
@global_options
@sport_filter
@click.option(
    "-dates",
    "-d",
    required=True,
    callback=validate_date,
    help="Date to scrape (YYYY-MM-DD) or (YYYY-MM-DD, ...) or (YYYY-MM-DD-YYYY-MM-DD).",
)
def dates(dates, sport, **kwargs):
    """Scrape matches for a given date."""
    sport_value = sport.value if hasattr(sport, "value") else sport
    app = ScraperApp()

    asyncio.run(
        app.run_scraper(command="dates", sport=sport_value, dates=dates, **kwargs)
    )
