"""CLI command for scraping tournaments."""

import asyncio

import click

from sofascraper.cli.options import global_options, sport_filter
from sofascraper.cli.validators import validate_season, validate_tournament
from sofascraper.core.scraper_app import ScraperApp


@click.command("tournaments")
@global_options
@sport_filter
@click.option(
    "--tournaments",
    "-t",
    required=True,
    multiple=True,
    callback=validate_tournament,
    help="Tournament name, slug or id.",
)
@click.option("--seasons", required=False, multiple=True, callback=validate_season, help="Season years.")
def tournaments(tournaments, sport, seasons=None, **kwargs):
    """Scrape matches for specific tournaments."""
    sport_value = sport.value if hasattr(sport, "value") else sport
    app = ScraperApp()
    asyncio.run(
        app.run_scraper(
            command="tournaments",
            sport=sport_value,
            tournaments=tournaments,
            seasons=seasons,
            **kwargs,
        )
    )
