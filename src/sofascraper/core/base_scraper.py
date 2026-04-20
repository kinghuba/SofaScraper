import asyncio
import base64
import json
import logging
import random
from collections.abc import Iterable
from dataclasses import dataclass, field

from bs4 import BeautifulSoup
from playwright.async_api import Page

from sofascraper.core.parsers.football_parser import FootballParser
from sofascraper.core.parsers.tennis_parser import TennisParser
from sofascraper.core.playwright_manager import PlaywrightManager
from sofascraper.core.url_builder import URLBuilder
from sofascraper.utils.browser_helpers import BrowserHelpers
from sofascraper.utils.constants import GOTO_TIMEOUT_MS, SOFASCORE_BASE_URL, WANTED_SUFFIXES
from sofascraper.utils.dataclasses.football_data_classes import MatchData
from sofascraper.utils.progress_tracker import ProgressTracker
from sofascraper.utils.sport_tournament_registry import SportTournamentRegistry
from sofascraper.utils.utils import wait_and_try_again

PARSERS = {
    "tennis": TennisParser,
    "football": FootballParser,
}


@dataclass
class ScrapeResult:
    """Aggregate results."""

    matches: list[MatchData] = field(default_factory=list)
    failed_urls: list[str] = field(default_factory=list)
    skipped: int = 0

    @property
    def total(self) -> int:
        return len(self.matches) + len(self.failed_urls)

    @property
    def success_rate(self) -> float:
        return len(self.matches) / self.total if self.total else 0.0


class Scraper:
    """
    Base class for scraping match data from Sofascore.
    The collection of methods that can be used by each scraper.
    """

    def __init__(
        self,
        playwright_manager: PlaywrightManager,
    ):
        """
        Args:
            playwright_manager (PlaywrightManager): Handles Playwright lifecycle.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.playwright_manager = playwright_manager
        self.url = URLBuilder()

    def _get_parser(self, sport):
        parser = PARSERS.get(sport)
        if not parser:
            raise ValueError(f"Unsupported sport: {sport}")
        return parser()

    # ^ Playwright

    async def start_playwright(
        self,
        headless: bool = True,
        browser_user_agent: str | None = None,
        browser_locale_timezone: str | None = None,
        browser_timezone_id: str | None = None,
        proxy: dict[str, str] | None = None,
    ):
        """Initialises Playwright via PlaywrightManager."""
        await self.playwright_manager.initialize(
            headless=headless,
            user_agent=browser_user_agent,
            locale=browser_locale_timezone,
            timezone_id=browser_timezone_id,
            proxy=proxy,
        )

    async def stop_playwright(self):
        """Stops Playwright and releases all resources."""
        await self.playwright_manager.cleanup()

    # ^ Deduplication

    async def _filter_existing_matches(
        self, match_links: list[str], storage, file_path: str | None = None, sport: str | None = None
    ) -> tuple[list[str], int]:
        """
        Remove links whose match IDs already exist in storage.

        Args:
            match_links: Full list of URLs to consider.
            storage:     Storage instance
            file_path:   Directory override

        Returns:
            (filtered_links, skipped_count)
        """
        existing_ids = await storage.get_existing_match_ids(file_path=file_path)

        if not existing_ids:
            return match_links, 0

        filtered = []
        for link in match_links:
            match_id = self.url.get_match_id(link)
            if match_id is not None and match_id in existing_ids:
                self.logger.debug(f"Skipping already-scraped match {match_id}")
            else:
                filtered.append(link)

        skipped = len(match_links) - len(filtered)

        if skipped:
            self.logger.info(f"Deduplication: {skipped} match(es) already present - {len(filtered)} remaining.")

        return filtered, skipped

    async def _filter_existing_dates(
        self, date_list: Iterable[str], storage, file_path: str | None = None, sport: str | None = None
    ) -> tuple[list[str], int]:

        directory = file_path or None
        existing_dates = await storage.get_existing_dates(file_path=directory)

        if not existing_dates:
            return list(date_list), 0

        existing_set = set(existing_dates)
        filtered = [d for d in date_list if d not in existing_set]
        skipped = len(list(date_list)) - len(filtered)

        if skipped:
            self.logger.info(f"Deduplication: {skipped} date(s) already present - {len(filtered)} remaining.")

        return filtered, skipped

    # ^ Match helpers

    async def _extract_match_links(self, page: Page, extraction_type) -> list[str]:
        try:
            all_match_links = set()

            while True:
                html_content = await page.content()
                self.soup = BeautifulSoup(html_content, "html.parser")

                def _fetch_rows():

                    if extraction_type == "tournament":
                        container = self.soup.find("div", id="tabpanel-round")
                        if not container:
                            self.logger.warning("tabpanel-round not found")
                            return None

                        matches_container = container.find("div", attrs={"class": lambda c: c and "pb_sm" in c})

                        rows = matches_container.find_all("a", href=True) if matches_container else []

                    # Extraction type "team" # TODO add team as scraping option
                    else:
                        matches = self.soup.find_all("div", attrs={"class": "card-component never"})
                        rows = []
                        for m in matches:
                            rows.extend(m.find_all("a", href=True))

                    return rows

                rows = wait_and_try_again(wait=3, func=_fetch_rows, retries=3)

                if not rows:
                    self.logger.warning("No tabpanel found")

                self.logger.debug(f"Found {len(rows)} links on current page.")

                for link in rows:
                    href = link.get("href", "")
                    parts = href.split("/")

                    if len(parts) > 2 and (parts[2] == "match" or parts[3] == "match"):
                        all_match_links.add(f"{SOFASCORE_BASE_URL}{href}")
                    self.logger.debug(f"{SOFASCORE_BASE_URL}{href}")

                self.logger.debug(f"Total collected so far: {len(all_match_links)}")

                # handle pagination
                try:
                    left_arrow = await page.query_selector("button.p_xs.bd_1\\.5px_solid_transparent")

                    if not left_arrow:
                        self.logger.debug("Left arrow not found, stopping.")
                        break

                    is_disabled = await left_arrow.get_attribute("disabled")

                    if is_disabled is not None:
                        self.logger.info("Arrow disabled, waiting 3 seconds to confirm...")
                        await asyncio.sleep(3)

                        # re-check after wait
                        left_arrow = await page.query_selector("button.p_xs.bd_1\\.5px_solid_transparent")
                        is_disabled = await left_arrow.get_attribute("disabled")

                        if is_disabled is not None:
                            self.logger.info("Arrow still disabled. Done collecting.")
                            break

                    # Click and wait
                    delay = random.uniform(2, 5)
                    self.logger.info(f"Clicking arrow, waiting {delay:.2f}s...")
                    await left_arrow.click()
                    await asyncio.sleep(delay)

                except Exception as click_err:
                    self.logger.warning(f"Error handling arrow: {click_err}")
                    break

            self.logger.info(f"Final extracted {len(all_match_links)} unique match links.")
            return list(all_match_links)

        except Exception as e:
            self.logger.error(f"Error extracting match links: {e}", exc_info=True)
            return []

    async def _scrape_date_events(
        self,
        page,
        sport: str,
        target_date: str,
    ) -> list[dict]:
        """
        Navigate to the Sofascore schedule page for one date and capture
        all scheduled-events API responses via CDP interception.

        Returns a flat list of raw event dicts.
        """
        all_events: list[dict] = []
        pending: dict[str, str] = {}
        lock = asyncio.Lock()

        cdp = await page.context.new_cdp_session(page)

        async def on_request(params: dict) -> None:
            url = params.get("request", {}).get("url", "")
            rid = params.get("requestId", "")
            if f"scheduled-events/{target_date}" in url:
                async with lock:
                    pending[rid] = url

        async def on_loading_finished(params: dict) -> None:
            rid = params.get("requestId", "")
            async with lock:
                url = pending.pop(rid, None)
            if url is None:
                return
            try:
                resp = await cdp.send("Network.getResponseBody", {"requestId": rid})
                raw = resp.get("body", "")
                if resp.get("base64Encoded"):
                    raw = base64.b64decode(raw).decode("utf-8", errors="replace")
                events = json.loads(raw).get("events", [])
                async with lock:
                    all_events.extend(events)
                self.logger.debug(f"{len(events)} events captured from {url}")
            except Exception as e:
                self.logger.debug(f"Failed fetching events - could not read body for {url}: {e}")

        cdp.on("Network.requestWillBeSent", on_request)
        cdp.on("Network.loadingFinished", on_loading_finished)
        await cdp.send("Network.enable", {})

        try:
            schedule_url = f"https://www.sofascore.com/{sport}/{target_date}"
            self.logger.debug(f"Fetching date: loading {schedule_url}")
            await page.goto(schedule_url, wait_until="domcontentloaded", timeout=30_000)
            try:
                await page.wait_for_load_state("networkidle", timeout=12_000)
            except Exception:
                pass
            await page.wait_for_timeout(5_000)
        except Exception as e:
            self.logger.error(f"Failed fetching events - page load failed for {target_date}: {e}")
        finally:
            try:
                await cdp.detach()
            except Exception:
                pass

        self.logger.info(f"Success {len(all_events)} events captured for {target_date}")
        return all_events

    async def _scrape_event(self, sport: str, match_id: int, match_link: str) -> dict[str, dict]:
        """
        Load the match page and capture the SofaScore API responses for
        /statistics, /incidents, /lineups, and the base event endpoint --
        all within the existing persistent Playwright session.

        Args:
            match_id:  Numeric SofaScore event ID (used to filter URLs).
            match_link: Full page URL for the match, statistics tab, e.g.
                       https://www.sofascore.com/football/match/slug/id#id:NNN
        """
        page = self.playwright_manager.page
        if not page:
            raise RuntimeError("Playwright is not initialised - call start_playwright() first.")

        captured: dict[str, dict] = {}
        pending: dict[str, str] = {}
        lock = asyncio.Lock()

        cdp = await page.context.new_cdp_session(page)

        async def on_request(params: dict) -> None:
            url = params.get("request", {}).get("url", "")
            rid = params.get("requestId", "")

            # Get tennis rankings, different base
            if sport == "tennis":
                if url.endswith("/rankings"):
                    self.logger.debug(f"/rankings --> {url} found.")

                    # Extract team_id
                    try:
                        team_id = url.split("/team/")[1].split("/")[0]
                    except (IndexError, AttributeError):
                        team_id = None

                    async with lock:
                        pending[rid] = f"rankings-{team_id}"

            for suffix in WANTED_SUFFIXES.get(sport.lower()):
                if url.endswith(f"/v1/event/{match_id}{suffix}"):
                    self.logger.debug(f"/event/{match_id}{suffix} --> {url} found.")
                    async with lock:
                        # Store the suffix without the leading slash as dict key
                        pending[rid] = suffix.lstrip("/")
                    break

        async def on_loading_finished(params: dict) -> None:
            rid = params.get("requestId", "")
            async with lock:
                key = pending.pop(rid, None)
            if key is None:
                return
            try:
                resp = await cdp.send("Network.getResponseBody", {"requestId": rid})
                raw = resp.get("body", "")
                if resp.get("base64Encoded"):
                    raw = base64.b64decode(raw).decode("utf-8", errors="replace")
                async with lock:
                    captured[key] = json.loads(raw)
                self.logger.debug(f"match {match_id}: captured /{key or '(base)'}")
            except Exception as e:
                self.logger.debug(f"match {match_id}: could not read body for /{key}: {e}")

        cdp.on("Network.requestWillBeSent", on_request)
        cdp.on("Network.loadingFinished", on_loading_finished)
        await cdp.send("Network.enable", {})

        try:
            # statistics tab
            self.logger.debug(f"Match {match_id}: loading - {match_link}")
            await page.goto(match_link, wait_until="domcontentloaded", timeout=30_000)
            try:
                await page.wait_for_load_state("networkidle", timeout=8_000)
            except Exception:
                pass
            await page.wait_for_timeout(4_000)

            # navigate tolineups tab via hash-change
            if sport == "football":
                statistics_hash = f"#id:{match_id},tab:statistics"
                self.logger.debug(f"match {match_id}: switching to lineups tab")
                await page.evaluate(f"window.location.hash = '{statistics_hash}'")
                try:
                    await page.wait_for_load_state("networkidle", timeout=8_000)
                except Exception:
                    pass
                await page.wait_for_timeout(1_500)

                if "statistics" not in captured:
                    self.logger.debug(f"match {match_id}: hash navigation didn't fire /lineups -- trying click")
                    try:
                        tab_link = page.locator("a[href*='tab:statistics']").first
                        await tab_link.click(timeout=5_000)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=6_000)
                        except Exception:
                            pass
                        await page.wait_for_timeout(1_500)
                    except Exception as e:
                        self.logger.debug(f"match {match_id}: statistics tab click failed - {e}")

                lineups_hash = f"#id:{match_id},tab:lineups"
                self.logger.debug(f"match {match_id}: switching to lineups tab")
                await page.evaluate(f"window.location.hash = '{lineups_hash}'")
                try:
                    await page.wait_for_load_state("networkidle", timeout=8_000)
                except Exception:
                    pass
                await page.wait_for_timeout(1_500)

                # if not lineups captured, try pressing lineups button
                if "lineups" not in captured:
                    self.logger.debug(f"match {match_id}: hash navigation didn't fire /lineups -- trying click")
                    try:
                        tab_link = page.locator("a[href*='tab:lineups']").first
                        await tab_link.click(timeout=5_000)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=6_000)
                        except Exception:
                            pass
                        await page.wait_for_timeout(1_500)
                    except Exception as e:
                        self.logger.debug(f"match {match_id}: lineups tab click failed -- {e}")

        except Exception as e:
            self.logger.warning(f"match {match_id}: page load error -- {e}")
        finally:
            try:
                await cdp.detach()
            except Exception:
                pass

        missing = [
            s.lstrip("/") or "(base)" for s in WANTED_SUFFIXES.get(sport.lower()) if s.lstrip("/") not in captured
        ]
        if missing:
            self.logger.debug(f"match {match_id}: missing endpoints after fetch: {missing}")
            self.logger.warning(f"{len(missing)} endpoint not found.")

        return captured

    async def _scrape_matches(
        self,
        sport: str,
        match_links: list[str],
        result: ScrapeResult,
        storage,
    ) -> ScrapeResult:
        """
        Scrapes a batch of matches, skipping any already saved to disk,
        and shows a Rich progress bar.

        Args:
            match_links: List of SofaScore URLs to scrape.
            storage:     Storage instance used for deduplication and saving.
        """
        # Deduplicate before opening the browser loop
        if storage is not None:
            match_links, skipped = await self._filter_existing_matches(
                match_links=match_links, storage=storage, file_path=storage.default_file_path, sport=sport
            )
            result.skipped += skipped

        if not match_links:
            self.logger.info("All matches already scraped - nothing to do.")
            return result

        async with ProgressTracker(total=len(match_links), label="Matches") as pt:
            for match_link in match_links:
                failed = False
                try:
                    match_id = self.url.get_match_id(match_link)
                    if match_id is None:
                        self.logger.warning(f"Could not extract match ID from URL: {match_link}")
                        raise ValueError(f"Invalid match URL: {match_link}")

                    url = self.url.get_url(match_link, match_id)
                    self.logger.info(f"Scraping match {match_id} - {url}")

                    raw = await self._scrape_event(sport=sport, match_id=match_id, match_link=url)

                    data = None
                    if raw:
                        parser = self._get_parser(sport)
                        data = parser.parse_match(match_id=match_id, match_url=match_link, raw=raw)

                    if data is None:
                        result.failed_urls.append(match_link)
                        self.logger.warning(f"Failed to scrape: {match_link}")
                        failed = True
                        continue

                    # This could occur for matches missing the full data or matches that are yet to start
                    if not data.fully_captured:
                        self.logger.warning(f"Match {data.match_id}: partial capture.")

                    result.matches.append(data)

                    try:
                        await storage.save_data(data=data, file_name_key="match_id")
                    except Exception as save_err:
                        self.logger.error(
                            f"Match {data.match_id}: failed to save - {save_err}",
                            exc_info=True,
                        )

                except Exception as e:
                    self.logger.error(f"Failed to scrape {match_link}: {e}", exc_info=True)
                    result.failed_urls.append(match_link)
                    failed = True

                finally:
                    pt.advance(status=match_link, failed=failed)

        self.logger.info(
            f"Scrape complete"
            f"{len(result.matches)} succeeded, "
            f"{len(result.failed_urls)} failed, "
            f"{result.skipped} skipped."
        )
        return result

    # ^ Links

    async def scrape_links(
        self,
        sport: str,
        match_links: list[str],
        storage,
    ) -> ScrapeResult | None:
        result = ScrapeResult()
        current_page = self.playwright_manager.page
        if not current_page:
            raise RuntimeError("Playwright is not initialised -- call start_playwright() first.")

        await current_page.goto(SOFASCORE_BASE_URL, timeout=GOTO_TIMEOUT_MS, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        browser_helpers = BrowserHelpers(current_page)
        consent = await browser_helpers.handle_all_popups() or {}

        if consent and consent.consent_accepted:
            await self._scrape_matches(sport, match_links, result, storage)

        return result

    # ^ Tournaments

    async def scrape_tournaments(
        self,
        sport: str,
        tournaments: list[str],
        seasons: list[str],
        storage,
    ) -> ScrapeResult | None:
        result = ScrapeResult()
        current_page = self.playwright_manager.page
        if not current_page:
            raise RuntimeError("Playwright is not initialised -- call start_playwright() first.")

        # collect all links
        all_match_links: list[str] = []

        for tournament in tournaments:
            if len(seasons) == 1 and seasons[0] == "all":
                seasons = [
                    str(season["id"]) for season in SportTournamentRegistry.get_by_slug(tournament).get("seasons", [])
                ]
            for season in seasons:
                url = self.url.get_tournament_url(sport=sport, tournament=tournament, season=season)
                self.logger.debug(f"Loading league page: {url}")

                await current_page.goto(url, timeout=GOTO_TIMEOUT_MS, wait_until="domcontentloaded")
                await asyncio.sleep(5)

                browser_helpers = BrowserHelpers(current_page)
                await browser_helpers.handle_all_popups()
                await browser_helpers.scroll_until_loaded()

                match_links = await self._extract_match_links(
                    page=current_page,
                    extraction_type="tournament",
                )

                if not match_links:
                    self.logger.warning(f"No match links found for {tournament} -- skipping.")
                    continue

                self.logger.info(f"Collected {len(match_links)} match links from {tournament}.")
                all_match_links.extend(match_links)

        if not all_match_links:
            self.logger.warning("No match links found across any tournament -- aborting.")
            return None

        await self._scrape_matches(sport, all_match_links, result, storage)

        return result

    # ^ Dates

    async def scrape_dates(self, sport: str, dates: str | list[str], storage) -> ScrapeResult:
        """
        Fetch and parse all scheduled events for one or more dates,
        skipping any dates that already have a saved file on disk.

        Args:
            sport:  Sport slug, e.g. "football" or "tennis".
            dates:  One of:
                    - single date string:       2022-11-12
                    - list of date strings:     [2022-11-12, 2022-11-15]
                    - range string (inclusive): 2022-11-12-2022-12-01
        """
        result = ScrapeResult()
        page = self.playwright_manager.page
        if not page:
            raise RuntimeError("Playwright is not initialised -- call start_playwright() first.")

        self.logger.info(f"Requested {len(dates)} date(s): {dates[0]} … {dates[-1]}")

        # Deduplicate dates before opening the browser loop
        dates, skipped = await self._filter_existing_dates(date_list=dates, storage=storage, sport=sport)
        result.skipped += skipped

        if not dates:
            self.logger.info("All dates already scraped -- nothing to do.")
            return result

        async with ProgressTracker(total=len(dates), label="Dates") as pt:
            for target_date in dates:
                failed = False
                try:
                    raw_events = await self._scrape_date_events(page, sport, target_date)

                    day_events = []
                    for event in raw_events:
                        try:
                            parser = self._get_parser(sport)
                            parsed = parser.parse_event(event)
                            if parsed:
                                result.matches.append(parsed)
                                day_events.append(parsed)
                        except Exception:
                            self.logger.warning(f"Failed to parse event: {event}")

                    try:
                        file_path = storage.default_file_path or None
                        await storage.save_data(
                            data=day_events,
                            file_path=f"{file_path}/{target_date}",
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to save events for {target_date}: {e}", exc_info=True)

                except Exception as e:
                    self.logger.error(f"Failed to scrape events for {target_date}: {e}", exc_info=True)
                    failed = True

                finally:
                    pt.advance(status=target_date, failed=failed)

        return result
