"""Main CLI entry point for sofascraper."""

import logging

import click

from sofascraper import __version__
from sofascraper.cli.commands import dates, matches, tournaments
from sofascraper.utils.setup_logging import setup_logger


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output except errors.")
@click.version_option(version=__version__, prog_name="SofaScraper")
@click.pass_context
def cli(ctx, verbose, quiet):
    """SofaScraper - Scrape sports from SofaScore."""
    log_level = logging.INFO
    if quiet:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG

    setup_logger(log_level=log_level, save_to_file=False)

    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


# Register commands
cli.add_command(dates)
cli.add_command(matches)
cli.add_command(tournaments)


def main():
    cli()


if __name__ == "__main__":
    main()
