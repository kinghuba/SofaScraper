"""CLI command for scraping specific matches."""

import asyncio

import click

from sofascraper.cli.options import global_options, sport_filter
from sofascraper.core.scraper_app import ScraperApp


@click.command("matches")
@global_options
@sport_filter
@click.option("--links", "-l", required=True, multiple=True, help="Match URLs to scrape.")
def matches(links, sport, **kwargs):
    """Scrape odds for specific match links."""
    sport_value = sport.value if hasattr(sport, "value") else sport
    app = ScraperApp()
    asyncio.run(app.run_scraper(command="matches", sport=sport_value, match_links=links, **kwargs))
