import asyncio
import base64
import json
import logging
import random
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from playwright.async_api import Page

from sofascraper.core.parsers.football_parser import FootballParser
from sofascraper.core.parsers.tennis_parser import TennisParser
from sofascraper.core.playwright_manager import PlaywrightManager
from sofascraper.storage.pgsql_data_storage import PgsqlDataStorage
from sofascraper.utils.browser_helpers import BrowserHelpers
from sofascraper.utils.constants import GOTO_TIMEOUT_MS, SOFASCORE_BASE_URL, WANTED_SUFFIXES
from sofascraper.utils.dataclasses.football_data_classes import MatchData
from sofascraper.utils.progress_tracker import ProgressTracker
from sofascraper.utils.sport_tournament_registry import SportTournamentRegistry
from sofascraper.utils.utils import extract_year, get_match_id, get_tournament_information, wait_and_try_again

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
        storage = None
    ):
        """
        Args:
            playwright_manager (PlaywrightManager): Handles Playwright lifecycle.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.playwright_manager = playwright_manager
        self.storage = storage
        self.whole_site_failures = 0

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
        self, match_links: list[str], file_path: str | None = None, sport: str | None = None
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
        existing_ids = await self.storage.get_existing_match_ids(file_path=file_path)

        if not existing_ids:
            return match_links, 0

        filtered = []
        for link in match_links:
            match_id = get_match_id(link)
            if match_id is not None and match_id in existing_ids:
                self.logger.debug(f"Skipping already-scraped match {match_id}")
            else:
                filtered.append(link)

        skipped = len(match_links) - len(filtered)

        if skipped:
            self.logger.debug(f"Deduplication: {skipped} match(es) already present - {len(filtered)} remaining.")

        return filtered, skipped

    async def _filter_existing_dates(
        self, date_list: Iterable[str], file_path: str | None = None, sport: str | None = None
    ) -> tuple[list[str], int]:

        directory = file_path or None
        # Only works for local files, not database
        existing_dates = await self.storage.get_existing_dates(file_path=directory)

        if not existing_dates:
            return list(date_list), 0

        existing_set = set(existing_dates)
        filtered = [d for d in date_list if d not in existing_set]
        skipped = len(list(date_list)) - len(filtered)

        if skipped:
            self.logger.debug(f"Deduplication: {skipped} date(s) already present - {len(filtered)} remaining.")

        return filtered, skipped

    # ^ Match helpers

    def extract_match_info(self, url: str):
        parsed = urlparse(url)

        # Split path and remove empty parts
        parts = [p for p in parsed.path.split("/") if p]

        if "match" in parts:
            match_index = parts.index("match")

            sport = parts[match_index - 1] if len(parts) > match_index - 1 else None
            slug = parts[match_index + 1] if len(parts) > match_index + 1 else None
            code = parts[match_index + 2] if len(parts) > match_index + 2 else None
        else:
            slug = code = sport = None

        # id from fragment (#id:xxxxxx)
        match_id = None
        if parsed.fragment.startswith("id:"):
            match_id = parsed.fragment.split("id:")[1]

        return sport, slug, code, match_id

    async def _extract_match_links(self, page: Page, season) -> list[str]:
        try:
            all_match_links = set()
            go_right = True
            rounds = 0
            right_clicks = 0

            while True:
                html_content = await page.content()
                self.soup = BeautifulSoup(html_content, "html.parser")

                def _fetch_rows():
                    container = self.soup.find("div", id="tabpanel-round")
                    if not container:
                        self.logger.warning("tabpanel-round not found")
                        return None

                    matches_container = container.find("div", attrs={"class": lambda c: c and "pb_sm" in c})

                    rows = matches_container.find_all("a", href=True) if matches_container else []

                    return rows

                rows = wait_and_try_again(wait=3, func=_fetch_rows, retries=3)

                if not rows:
                    self.logger.warning("No tabpanel found")

                self.logger.debug(f"Found {len(rows)} links on current page.")

                for link in rows:
                    sport, slug, code, match_id = self.extract_match_info(f"{SOFASCORE_BASE_URL}{link.get("href", "")}")

                    if not sport or not slug or not code or not match_id:
                        continue

                    if isinstance(self.storage, PgsqlDataStorage):
                        await self.storage.save_link(slug, int(match_id), code, int(season), False)

                    if f"{SOFASCORE_BASE_URL}/{sport}/{slug}/{code}#id:{match_id}" in all_match_links:
                        continue
                    else:
                        all_match_links.add(f"{SOFASCORE_BASE_URL}/{sport}/{slug}/{code}#id:{match_id}")

                self.logger.debug(f"Total collected so far: {len(all_match_links)}")

                # handle pagination
                try:
                    arrows = await page.query_selector_all("button.p_xs.bd_1\\.5px_solid_transparent")

                    if len(arrows) < 2:
                        self.logger.debug("Arrows not found, stopping.")
                        break

                    left_arrow = arrows[0]
                    right_arrow = arrows[1]

                    is_left_disabled = await left_arrow.get_attribute("disabled")
                    is_right_disabled = await right_arrow.get_attribute("disabled")

                    # decide which direction to use
                    if go_right is True:
                        if is_right_disabled is not None:
                            self.logger.debug("Right arrow exhausted. Switching to left.")
                            go_right = False
                            continue
                        arrow_to_click = right_arrow
                        right_clicks+=1
                    else:
                        if is_left_disabled is not None:
                            self.logger.debug("Left arrow exhausted. Done collecting.")
                            break
                        arrow_to_click = left_arrow

                    # confirm disabled state with delay
                    if (go_right and is_right_disabled is not None) or (not go_right and is_left_disabled is not None):
                        self.logger.debug("Arrow disabled, waiting 3 seconds to confirm...")
                        await asyncio.sleep(3)

                        arrows = await page.query_selector_all("button.p_xs.bd_1\\.5px_solid_transparent")
                        left_arrow = arrows[0]
                        right_arrow = arrows[1]

                        is_left_disabled = await left_arrow.get_attribute("disabled")
                        is_right_disabled = await right_arrow.get_attribute("disabled")

                        if (go_right and is_right_disabled is not None) or (not go_right and is_left_disabled is not None):
                            if go_right:
                                self.logger.debug("Right arrow confirmed disabled. Switching to left.")
                                go_right = False
                                continue
                            else:
                                self.logger.debug("Left arrow confirmed disabled. Done collecting.")
                                break

                    # Click and wait
                    delay = random.uniform(2, 3)
                    direction = "right" if go_right else "left"
                    self.logger.debug(f"Clicking {direction} arrow, waiting {delay:.2f}s...")
                    await arrow_to_click.click()
                    rounds+=1
                    await asyncio.sleep(delay)

                except Exception as click_err:
                    self.logger.warning(f"Error handling arrow: {click_err}")
                    break

            self.logger.info(f"Final extracted {len(all_match_links)} unique match links.")
            return list(all_match_links), rounds-right_clicks+1

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

        self.logger.debug(f"Success {len(all_events)} events captured for {target_date}")
        return all_events



    async def _scrape_event_on_page(
        self, page: Page, sport: str, match_id: int, match_link: str
    ) -> dict[str, dict]:

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
                    self.logger.debug(f"/rankings -> {url} found.")

                    # Extract team_id
                    try:
                        team_id = url.split("/team/")[1].split("/")[0]
                    except (IndexError, AttributeError):
                        team_id = None

                    async with lock:
                        pending[rid] = f"rankings-{team_id}"

            for suffix in WANTED_SUFFIXES.get(sport.lower()):
                if url.endswith(f"/v1/event/{match_id}{suffix}"):
                    self.logger.debug(f"/event/{match_id}{suffix} -> {url} found.")
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
            self.logger.debug(f"Match {match_id}: loading - {match_link}")
            await page.goto(match_link, wait_until="domcontentloaded", timeout=30_000)
            try:
                await page.wait_for_load_state("networkidle", timeout=8_000)
            except Exception:
                pass
            await page.wait_for_timeout(4_000)

            # navigate to statistics tab via hash-change
            
            statistics_hash = f"#id:{match_id},tab:statistics"
            self.logger.debug(f"match {match_id}: switching to statistics tab")
            await page.evaluate(f"window.location.hash = '{statistics_hash}'")
            try:
                await page.wait_for_load_state("networkidle", timeout=8_000)
            except Exception:
                pass
            await page.wait_for_timeout(1_500)

            if "statistics" not in captured:
                self.logger.debug(f"match {match_id}: hash navigation didn't fire /statistics - trying click")
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

            # lineups are only relevant for football
            if sport == "football":
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
                    self.logger.debug(f"match {match_id}: hash navigation didn't fire /lineups - trying click")
                    try:
                        tab_link = page.locator("a[href*='tab:lineups']").first
                        await tab_link.click(timeout=5_000)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=6_000)
                        except Exception:
                            pass
                        await page.wait_for_timeout(1_500)
                    except Exception as e:
                        self.logger.debug(f"match {match_id}: lineups tab click failed - {e}")

        except Exception as e:
            self.logger.warning(f"match {match_id}: page load error - {e}")
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

            if len(missing) == len(WANTED_SUFFIXES.get(sport.lower())):
                self.whole_site_failures+=1

            if self.whole_site_failures >= 2:
                raise RuntimeError("Likely blocked by anti-bot protection")


        return captured

    async def _scrape_matches(
        self,
        sport: str,
        match_links: list[str],
        result: ScrapeResult,
        concurrency: int = 1,
    ) -> ScrapeResult:
        """
        Scrapes a batch of matches, skipping any already saved to disk,
        and shows a Rich progress bar.

        Args:
            sport: Slug of scraped sport.
            match_links: List of SofaScore URLs to scrape.
            storage:     Storage instance used for deduplication and saving.
            result
            concurrency: Number of concurrent pages to open
        """
        if self.storage is not None:
            match_links, skipped = await self._filter_existing_matches(
                match_links=match_links,
                file_path=self.storage.default_file_path, sport=sport
            )
            result.skipped += skipped

        if not match_links:
            return result

        page_pool = await self.playwright_manager.create_page_pool(size=concurrency)
        sem = asyncio.Semaphore(concurrency)
        result_lock = asyncio.Lock()  # protect shared result object

        async def scrape_one(match_link: str, pt: ProgressTracker):
            async with sem:
                page = await page_pool.get()
                failed = False
                try:
                    match_id = get_match_id(match_link)
                    if match_id is None:
                        raise ValueError(f"Invalid match URL: {match_link}")

                    raw = await self._scrape_event_on_page(page, sport, match_id, match_link)

                    data = None
                    if raw:
                        parser = self._get_parser(sport)
                        data = parser.parse_match(match_id=match_id, match_url=match_link, raw=raw)

                    if data is None:
                        async with result_lock:
                            result.failed_urls.append(match_link)
                        failed = True
                        return

                    async with result_lock:
                        result.matches.append(data)

                    await self.storage.save_data(data=data, file_name_key="match_id")

                except Exception as e:
                    self.logger.error(f"Failed to scrape {match_link}: {e}", exc_info=True)
                    async with result_lock:
                        result.failed_urls.append(match_link)
                    failed = True
                finally:
                    await page_pool.put(page)  # always return page to pool
                    pt.advance(status=match_link, failed=failed)

        async with ProgressTracker(total=len(match_links), label="Matches") as pt:
            await asyncio.gather(*[scrape_one(link, pt) for link in match_links])

        return result

    # ^ Links

    async def scrape_links(
        self,
        sport: str,
        match_links: list[str],
        concurrency: int = 1
    ) -> ScrapeResult | None:
        result = ScrapeResult()
        current_page = self.playwright_manager.page
        if not current_page:
            raise RuntimeError("Playwright is not initialised - call start_playwright() first.")

        await current_page.goto(SOFASCORE_BASE_URL, timeout=GOTO_TIMEOUT_MS, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        browser_helpers = BrowserHelpers(current_page)
        consent = await browser_helpers.handle_all_popups() or {}

        if consent and consent.consent_accepted:
            await self._scrape_matches(sport, match_links, result, concurrency)

        return result

    # ^ Tournaments

    async def scrape_tournaments(
        self,
        sport: str,
        tournaments: list[str],
        seasons: list[str],
        concurrency: int = 1
    ) -> ScrapeResult | None:
        result = ScrapeResult()
        current_page = self.playwright_manager.page
        if not current_page:
            raise RuntimeError("Playwright is not initialised - call start_playwright() first.")

        all_match_links: list[str] = []

        for tournament in tournaments:
            if len(seasons) == 1 and seasons[0] == "all":
                season_ids = [
                    str(season["id"]) for season in SportTournamentRegistry.get_by_id(tournament).get("seasons", [])
                ]
            elif len(seasons) == 1 and seasons[0] == "current":
                season_ids = [
                    str(sorted(SportTournamentRegistry.get_by_id(tournament).get("seasons", []), key=lambda x: extract_year(x["year"]), reverse=True)[0]["id"]) # Get the latest
                ]
            else:
                season_ids = seasons

            tournament_slug = SportTournamentRegistry.get_by_id(tournament).get("slug", "")
            self.storage.default_file_path = self.storage.default_file_path + f"/{tournament_slug}-{tournament}"

            for season in season_ids:
                url, season_id = get_tournament_information(sport=sport, tournament=tournament, season=season)
                self.logger.debug(f"Loading league page: {url}")

                if not season_id:
                    continue

                if isinstance(self.storage, PgsqlDataStorage):
                    # Check storage first if the season was scraped already
                    collected = await self.storage.check_season(season_id)

                    if collected:
                        all_match_links.extend(await self.storage.get_collected_links(season_id)) # Add the links where it was not already scraped
                        continue

                rounds_data: dict = {}
                pending: dict[str, str] = {}
                lock = asyncio.Lock()

                cdp = await current_page.context.new_cdp_session(current_page)

                async def on_request(params: dict) -> None:
                    req_url = params.get("request", {}).get("url", "")
                    rid = params.get("requestId", "")
                    if "unique-tournament" in req_url and "/rounds" in req_url:
                        async with lock:
                            pending[rid] = req_url

                async def on_loading_finished(params: dict, _rounds=rounds_data, _pending=pending, _lock=lock) -> None:
                    rid = params.get("requestId", "")
                    async with _lock:
                        req_url = _pending.pop(rid, None)
                    if req_url is None:
                        return
                    try:
                        resp = await cdp.send("Network.getResponseBody", {"requestId": rid})
                        raw = resp.get("body", "")
                        if resp.get("base64Encoded"):
                            raw = base64.b64decode(raw).decode("utf-8", errors="replace")
                        _rounds.update(json.loads(raw))
                        self.logger.debug(f"Rounds data captured from {req_url}")
                    except Exception as e:
                        self.logger.debug(f"Failed to read rounds response body: {e}")

                cdp.on("Network.requestWillBeSent", on_request)
                cdp.on("Network.loadingFinished", on_loading_finished)
                await cdp.send("Network.enable", {})

                try:
                    await current_page.goto(url, timeout=GOTO_TIMEOUT_MS, wait_until="domcontentloaded")
                    await asyncio.sleep(5)

                    browser_helpers = BrowserHelpers(current_page)
                    await browser_helpers.handle_all_popups()
                    await browser_helpers.scroll_until_loaded()
                finally:
                    try:
                        await cdp.detach()
                    except Exception:
                        pass

                match_links, rounds = await self._extract_match_links(
                    page=current_page, season=season_id
                )

                if not match_links:
                    self.logger.warning(f"No match links found for {tournament} - skipping.")
                    continue

                if rounds_data:
                    all_rounds_collected = len(rounds_data["rounds"]) == rounds

                    if isinstance(self.storage, PgsqlDataStorage):
                        await self.storage.save_season(season_id, all_rounds_collected)
                else:
                    self.logger.warning(f"No rounds data captured for tournament {tournament}, season {season_id}")

                self.logger.debug(f"Collected {len(match_links)} match links from {tournament}.")
                all_match_links.extend(match_links)

        if not all_match_links:
            self.logger.warning("No match links found across any tournament - aborting.")
            return None

        await self._scrape_matches(sport, all_match_links, result, concurrency)

        return result

    # ^ Dates

    async def scrape_dates(self, sport: str, dates: str | list[str], concurrency: int = 1) -> ScrapeResult:
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
        self.logger.info(f"Requested {len(dates)} date(s): {dates[0]} … {dates[-1]}")

        # Deduplicate dates before opening the browser loop
        dates, skipped = await self._filter_existing_dates(date_list=dates, storage=self.storage, sport=sport)
        result.skipped += skipped

        if not dates:
            self.logger.debug("All dates already scraped - nothing to do.")
            return result

        page_pool = await self.playwright_manager.create_page_pool(size=concurrency)
        result_lock = asyncio.Lock()
        sem = asyncio.Semaphore(concurrency)

        async def scrape_one_date(target_date: str, pt: ProgressTracker):
            async with sem:
                page = await page_pool.get()
                failed = False
                try:
                    raw_events = await self._scrape_date_events(page, sport, target_date)
                    day_events = []
                    for event in raw_events:
                        try:
                            parsed = self._get_parser(sport).parse_event(event)
                            if parsed:
                                day_events.append(parsed)
                        except Exception:
                            self.logger.warning(f"Failed to parse event: {event}")

                    async with result_lock:
                        result.matches.extend(day_events)

                    await self.storage.save_data(
                        data=day_events,
                        file_path=f"{self.storage.default_file_path}/{target_date}"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to scrape {target_date}: {e}", exc_info=True)
                    failed = True
                finally:
                    await page_pool.put(page)
                    pt.advance(status=target_date, failed=failed)

        async with ProgressTracker(total=len(dates), label="Dates") as pt:
            await asyncio.gather(*[scrape_one_date(d, pt) for d in dates])

        return result

