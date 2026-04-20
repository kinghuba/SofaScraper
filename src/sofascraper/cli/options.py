"""Shared Click options for Sofascraper CLI."""

import functools

import click

from sofascraper.cli.types import STORAGE_FORMAT
from sofascraper.cli.validators import (
    validate_file_path,
    validate_proxy_url,
)
from sofascraper.utils.enums import Sport


def global_options(func):
    """Options related to the environment, proxy, and storage."""

    @click.option(
        "--format",
        "-f",
        "storage_format",
        type=STORAGE_FORMAT,
        default="json",
        envvar="SS_FORMAT",
        help="Output format.",
    )
    @click.option(
        "--output",
        "-o",
        "file_path",
        type=click.Path(),
        default="data",
        callback=validate_file_path,
        envvar="SS_FILE_PATH",
        help="Output file path.",
    )
    @click.option(
        "--headless/--no-headless",
        default=True,
        envvar="SS_HEADLESS",
        help="Run browser in headless mode.",
    )
    @click.option(
        "--proxy-url",
        callback=validate_proxy_url,
        envvar="SS_PROXY_URL",
        help="Proxy URL.",
    )
    @click.option("--proxy-user", envvar="SS_PROXY_USER", help="Proxy username.")
    @click.option("--proxy-pass", envvar="SS_PROXY_PASS", help="Proxy password.")
    @click.option(
        "--user-agent",
        "browser_user_agent",
        envvar="SS_USER_AGENT",
        help="Browser User Agent.",
    )
    @click.option(
        "--locale",
        "browser_locale_timezone",
        envvar="SS_LOCALE",
        help="Browser locale.",
    )
    @click.option(
        "--timezone",
        "browser_timezone_id",
        envvar="SS_TIMEZONE",
        help="Browser timezone ID.",
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def sport_filter(func):
    """Standard sport selection option."""

    @click.option(
        "--sport",
        "-s",
        type=click.Choice([s.value for s in Sport], case_sensitive=False),
        required=True,
        envvar="SS_SPORT",
        help="Sport to scrape.",
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper
