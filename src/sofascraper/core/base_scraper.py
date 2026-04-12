import asyncio
import base64
import dataclasses
from datetime import UTC, datetime
from enum import Enum
import json
import logging
import random
import re
import threading
import time
from typing import Any
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from playwright.async_api import Page, TimeoutError

from sofascraper.core.url_builder import URLBuilder
from sofascraper.storage.local_data_storage import LocalDataStorage
from sofascraper.utils.constants import SOFASCORE_BASE_URL
from sofascraper.core.playwright_manager import PlaywrightManager

WANTED_SUFFIXES = {"football": ["/lineups", "/statistics", "/incidents", ""]}


class BaseScraper:
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

    def _wait_and_try_again(self, wait, func, retries=3):
        for attempt in range(retries):
            try:
                return func()
            except Exception as e:
                if attempt == retries - 1:
                    raise
                time.sleep(wait)

    def _find_links(self, soup, extraction_type):
        if extraction_type == "tournament":
            container = soup.find("div", id="tabpanel-round")
            if not container:
                self.logger.warning("tabpanel-round not found")
                return None

            matches_container = container.find(
                "div", attrs={"class": lambda c: c and "pb_sm" in c}
            )

            rows = (
                matches_container.find_all("a", href=True) if matches_container else []
            )

        # Extraction type "team"
        else:
            matches = soup.find_all("div", attrs={"class": "card-component never"})
            rows = []
            for m in matches:
                rows.extend(m.find_all("a", href=True))

        return rows

    async def extract_match_links(self, page: Page, extraction_type) -> list[str]:
        try:
            all_match_links = set()

            while True:
                html_content = await page.content()
                self.soup = BeautifulSoup(html_content, "html.parser")

                def _fetch_rows():
                    self.logger.info("Row fetching failed -- retrying")
                    return self._find_links(self.soup, extraction_type)

                rows = self._wait_and_try_again(wait=3, func=_fetch_rows, retries=3)

                if not rows:
                    self.logger.warning("No tabpanel found")

                self.logger.info(f"Found {len(rows)} links on current page.")

                for link in rows:
                    href = link.get("href", "")
                    parts = href.split("/")
                    self.logger.debug(href)
                    if len(parts) > 2 and (parts[2] == "match" or parts[3] == "match"):
                        all_match_links.add(f"{SOFASCORE_BASE_URL}{href}")

                self.logger.info(f"Total collected so far: {len(all_match_links)}")

                # handle pagination
                try:
                    left_arrow = await page.query_selector(
                        "button.p_xs.bd_1\\.5px_solid_transparent"
                    )

                    if not left_arrow:
                        self.logger.info("Left arrow not found, stopping.")
                        break

                    is_disabled = await left_arrow.get_attribute("disabled")

                    if is_disabled is not None:
                        self.logger.info(
                            "Arrow disabled, waiting 3 seconds to confirm..."
                        )
                        await asyncio.sleep(3)

                        # re-check after wait
                        left_arrow = await page.query_selector(
                            "button.p_xs.bd_1\\.5px_solid_transparent"
                        )
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

            self.logger.info(
                f"Final extracted {len(all_match_links)} unique match links."
            )
            return list(all_match_links)

        except Exception as e:
            self.logger.error(f"Error extracting match links: {e}", exc_info=True)
            return []

    def _resolve_dates(self, dates: str | list[str]) -> list[str]:
        """
        Parse the flexible dates argument into a sorted, deduplicated list
        of ISO date strings.

        "2022-11-12"                          → ["2022-11-12"]
        ["2022-11-12", "2022-11-15"]          → ["2022-11-12", "2022-11-15"]
        "2022-11-12 - 2022-12-01"             → ["2022-11-12", … , "2022-12-01"]
        """
        from datetime import date, timedelta

        if isinstance(dates, list):
            resolved = [date.fromisoformat(d).isoformat() for d in dates]

        elif " - " in dates:
            start_str, end_str = [part.strip() for part in dates.split(" - ", 1)]
            start = date.fromisoformat(start_str)
            end = date.fromisoformat(end_str)
            if end < start:
                raise ValueError(f"Range end '{end_str}' is before start '{start_str}'")
            resolved = []
            current = start
            while current <= end:
                resolved.append(current.isoformat())
                current += timedelta(days=1)

        else:
            resolved = [date.fromisoformat(dates.strip()).isoformat()]

        return sorted(set(resolved))

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
                self.logger.debug(
                    f"Failed fetching events -- could not read body for {url}: {e}"
                )

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
            self.logger.error(
                f"Failed fetching events -- page load failed for {target_date}: {e}"
            )
        finally:
            try:
                await cdp.detach()
            except Exception:
                pass

        self.logger.info(f"Success {len(all_events)} events captured for {target_date}")
        return all_events

    async def _scrape_event(
        self, sport: str, match_id: int, match_link: str
    ) -> dict[str, dict]:
        """
        Load the match page and capture the SofaScore API responses for
        /statistics, /incidents, /lineups, and the base event endpoint --
        all within the existing persistent Playwright session.

        Args:
            match_id:  Numeric SofaScore event ID (used to filter URLs).
            match_link: Full page URL for the match, statistics tab, e.g.
                       https://www.sofascore.com/football/match/slug/id#id:NNN,tab:statistics

        Returns:
            Dict with a subset of keys: "lineups", "statistics", "incidents", ""
            (base event).  Keys for endpoints that were not captured are absent.
        """
        page = self.playwright_manager.page
        if not page:
            raise RuntimeError(
                "Playwright is not initialised -- call start_playwright() first."
            )

        captured: dict[str, dict] = {}
        pending: dict[str, str] = {}
        lock = asyncio.Lock()

        cdp = await page.context.new_cdp_session(page)

        async def on_request(params: dict) -> None:
            url = params.get("request", {}).get("url", "")
            rid = params.get("requestId", "")
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
                self.logger.debug(
                    f"match {match_id}: could not read body for /{key}: {e}"
                )

        cdp.on("Network.requestWillBeSent", on_request)
        cdp.on("Network.loadingFinished", on_loading_finished)
        await cdp.send("Network.enable", {})

        try:
            # statistics tab
            self.logger.debug(
                f"Match {match_id}: loading statistics tab — {match_link}"
            )
            await page.goto(match_link, wait_until="domcontentloaded", timeout=30_000)
            try:
                await page.wait_for_load_state("networkidle", timeout=8_000)
            except Exception:
                pass
            await page.wait_for_timeout(1_000)

            # navigate tolineups tab via hash-change
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
                self.logger.debug(
                    f"match {match_id}: hash navigation didn't fire /lineups — trying click"
                )
                try:
                    tab_link = page.locator("a[href*='tab:lineups']").first
                    await tab_link.click(timeout=5_000)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=6_000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(1_500)
                except Exception as e:
                    self.logger.debug(
                        f"match {match_id}: lineups tab click failed — {e}"
                    )

        except Exception as e:
            self.logger.warning(f"match {match_id}: page load error — {e}")
        finally:
            try:
                await cdp.detach()
            except Exception:
                pass

        missing = [
            s.lstrip("/") or "(base)"
            for s in WANTED_SUFFIXES.get(sport.lower())
            if s.lstrip("/") not in captured
        ]
        if missing:
            self.logger.debug(
                f"match {match_id}: missing endpoints after fetch: {missing}"
            )
            self.logger.warning(f"{len(missing)} endpoint not found.")

        return captured
