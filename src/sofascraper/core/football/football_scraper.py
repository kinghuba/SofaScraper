import asyncio
import base64
from dataclasses import dataclass, field
import dataclasses
import json
import time
from typing import Any
import logging
import re

from sofascraper.utils.football_data_classes import MatchData
from sofascraper.utils.enums import StorageFormat
from sofascraper.core.base_scraper import BaseScraper
from sofascraper.core.football.football_parser import FootballParser
from sofascraper.utils.browser_helpers import BrowserHelpers
from sofascraper.core.url_builder import URLBuilder
from sofascraper.storage.local_data_storage import LocalDataStorage
from sofascraper.utils.constants import (
    GOTO_TIMEOUT_MS,
    SOFASCORE_BASE_URL,
)


@dataclass
class ScrapeResult:
    """Aggregate result returned by scrape_league."""

    matches: list[MatchData] = field(default_factory=list)
    failed_urls: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.matches) + len(self.failed_urls)

    @property
    def success_rate(self) -> float:
        return len(self.matches) / self.total if self.total else 0.0


class FootballScraper(BaseScraper):
    """
    Orchestrates the full SofaScore scraping workflow.
    """

    def __init__(self, playwright_manager):
        super().__init__(playwright_manager)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.url = URLBuilder()
        self.parser = FootballParser()

    # ^ Common Functions

    async def _scrape_matches(
        self,
        sport: str,
        match_links: list[str],
        result: ScrapeResult,
        storage: LocalDataStorage | None = None,
    ) -> ScrapeResult:
        """
        Scrapes a batch of matches

        Args:
            match_links: List of the sofascore urls pointing to the matches
            storage: Storage
        """

        # Scrape each match
        for match_link in match_links:
            try:
                match_id = self.url.get_match_id(match_link)
                if match_id is None:
                    self.logger.warning(
                        f"Could not extract match ID from URL: {match_link}"
                    )
                    raise ValueError(f"Invalid match URL: {match_link}")

                stat_url = self.url.get_statistics_tab_url(match_link, match_id)
                self.logger.info(f"Scraping match {match_id} - {stat_url}")

                raw = await self._scrape_event(
                    sport=sport, match_id=match_id, match_link=stat_url
                )

                if raw:
                    data = self.parser.parse_match(
                        match_id=match_id, match_url=match_link, raw=raw
                    )

                if data is None:
                    result.failed_urls.append(match_link)
                    self.logger.warning(f"Failed to scrape: {match_link}")
                    continue

                if not data.fully_captured:
                    self.logger.warning(
                        f"Match {data.match_id}: partial capture --"
                        f"base={bool(data.base)}, stats={bool(data.statistics)}, "
                        f"incidents={bool(data.incidents)}, lineups={bool(data.lineups)}"
                    )

                result.matches.append(data)

                try:
                    storage.save_data(
                        data=dataclasses.asdict(data), file_name_key="match_id"
                    )
                except Exception as save_err:
                    self.logger.error(
                        f"Match {data.match_id}: failed to save -- {save_err}",
                        exc_info=True,
                    )

            except Exception as e:
                self.logger.error(f"Failed to scrape {match_link}: {e}", exc_info=True)
                result.failed_urls.append(match_link)

        self.logger.info(
            f"League scrape complete --> "
            f"{len(result.matches)} succeeded, {len(result.failed_urls)} failed."
        )
        return result

    # ^ Scrape links

    async def scrape_links(
        self,
        sport: str,
        match_links: list[str],
        storage: LocalDataStorage | None = None,
    ) -> ScrapeResult | None:
        result = ScrapeResult()
        current_page = self.playwright_manager.page
        if not current_page:
            raise RuntimeError(
                "Playwright is not initialised — call start_playwright() first."
            )

        # Navigate to base page and wait to load.
        await current_page.goto(
            SOFASCORE_BASE_URL, timeout=GOTO_TIMEOUT_MS, wait_until="domcontentloaded"
        )
        await asyncio.sleep(5)

        # Close pop-up window
        browser_helpers = BrowserHelpers(current_page)
        consent = await browser_helpers.handle_all_popups() or {}

        if consent and consent.consent_accepted:
            await self._scrape_matches(sport, match_links, result, storage)

        return result

    # ^ Scrape tournaments

    async def scrape_tournaments(
        self,
        sport: str,
        tournament: str | None = None,
        season: str | None = None,
        storage: LocalDataStorage | None = None,
    ) -> ScrapeResult | None:
        """
        Collects every match link for the given league/season,
        then scrape each match.

        Args:
            sport:      Sport slug, e.g. "football".
            tournament: Tournament slug, e.g. "premier-league".
            season:     Season string ("YY/YY" or "YYYY"), or None for current.
        """
        result = ScrapeResult()
        current_page = self.playwright_manager.page
        if not current_page:
            raise RuntimeError(
                "Playwright is not initialised — call start_playwright() first."
            )

        if storage is None:
            storage = LocalDataStorage(
                default_file_path=tournament or "scraped_data",
                default_storage_format=StorageFormat.JSON,
            )

        url = self.url.get_tournament_url(
            sport=sport, tournament=tournament, season=season
        )
        self.logger.debug(f"Loading league page: {url}")

        # Go to league url and wait for load.
        await current_page.goto(
            url, timeout=GOTO_TIMEOUT_MS, wait_until="domcontentloaded"
        )
        await asyncio.sleep(5)

        browser_helpers = BrowserHelpers(current_page)
        await browser_helpers.handle_all_popups()
        await browser_helpers.scroll_until_loaded()

        match_links = await self.extract_match_links(
            page=current_page,
            extraction_type="tournament",
        )

        if not match_links:
            self.logger.warning("No match links found — aborting league scrape.")
            return None

        self.logger.info(f"Collected {len(match_links)} match links.")

        # Scrape only after links are available
        if match_links:
            await self._scrape_matches(sport, match_links, result, storage)

        return result

    # ^ Scrape dates

    async def scrape_dates(
        self,
        sport: str,
        dates: str | list[str],
        storage,
    ) -> ScrapeResult:
        """
        Fetch and parse all scheduled events for one or more dates.

        Args:
            sport:  Sport slug, e.g. "football".
            dates:  One of:
                    - single date string:       "2022-11-12"
                    - list of date strings:     ["2022-11-12", "2022-11-15"]
                    - range string (inclusive): "2022-11-12 - 2022-12-01"
        """
        result = ScrapeResult()
        page = self.playwright_manager.page
        if not page:
            raise RuntimeError(
                "Playwright is not initialised — call start_playwright() first."
            )

        date_list = self._resolve_dates(dates)
        self.logger.info(
            f"Fetching dates: {len(date_list)} date(s) — {date_list[0]} … {date_list[-1]}"
        )

        for target_date in date_list:
            try:
                raw_events = await self._scrape_date_events(page, sport, target_date)

                day_events = []

                for event in raw_events:
                    try:
                        parsed = self.parser.parse_event(event=event)
                        if parsed:
                            result.matches.append(parsed)
                            day_events.append(parsed)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse event: {event}")

                try:
                    data_to_save = [
                        dataclasses.asdict(e) if dataclasses.is_dataclass(e) else e
                        for e in day_events
                    ]

                    storage.save_data(
                        data=data_to_save,
                        file_path=f"data/dates/{target_date}",
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to save events for {target_date}: {e}", exc_info=True
                    )
            except Exception as e:
                self.logger.error(
                    f"Failed to save events for {target_date}: {e}", exc_info=True
                )

        return result
