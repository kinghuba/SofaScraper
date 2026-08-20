import asyncio
import logging
import random
import re

from playwright.async_api import Page

from sofascraper.utils.browser_helpers import BrowserHelpers
from sofascraper.utils.constants import MAX_TIMEOUT_MS, MIN_TIMEOUT_MS, WANTED_SUFFIXES

class FootballScraper:
    def __init__(self):
            self.logger = logging.getLogger(self.__class__.__name__)
            self.sport = "football"
            self.min_ms=MIN_TIMEOUT_MS
            self.max_ms=MAX_TIMEOUT_MS

    async def scrape_event(
            self,
            page: Page,
            match_id, 
            match_link
        ) -> dict[str, dict]:

            if not page:
                raise RuntimeError("Playwright is not initialised - call start_playwright() first.")

            captured: dict[str, dict] = {}
            lock = asyncio.Lock()

            STANDINGS_RE = re.compile(r"/standings/(total|home|away)(?:$|\?)")

            async def handle_response(response) -> None:
                url = response.url

                wanted = WANTED_SUFFIXES.get(self.sport.lower(), [])

                # Standings use a different schema (unique-tournament/season based,
                # not event-based), so it needs its own match instead of the
                # generic endswith(f"/v1/event/{match_id}{suffix}") check below.
                if "/standings" in wanted:
                    m = STANDINGS_RE.search(url)
                    if m:
                        variant = m.group(1)          # "total" | "home" | "away"
                        key = f"standings/{variant}"
                        try:
                            body = await response.json()
                            self.logger.info(key + " found")
                            async with lock:
                                captured[key] = body
                            self.logger.debug(f"match {match_id}: captured /{key}")
                        except Exception as e:
                            self.logger.debug(f"match {match_id}: failed to read body for /{key}: {e}")
                        return

                if "/knockout" in wanted:
                    if url.endswith(f"/cuptrees"):
                        key = "knockout"
                        try:
                            body = await response.json()
                            self.logger.info(key + " found")
                            async with lock:
                                captured[key] = body
                            self.logger.debug(f"match {match_id}: captured /{key}")
                        except Exception as e:
                            self.logger.debug(f"match {match_id}: failed to read body for /{key}: {e}")
                        return

                # All other wanted suffixes (event-scoped)
                for suffix in wanted:
                    if (suffix == "/standings") | (suffix == "/knockout"):
                        continue  # handled above
                    if url.endswith(f"/v1/event/{match_id}{suffix}"):
                        key = suffix.lstrip("/")
                        try:
                            body = await response.json()
                            async with lock:
                                captured[key] = body
                            self.logger.debug(f"match {match_id}: captured /{key}")
                        except Exception as e:
                            self.logger.debug(f"match {match_id}: failed to read body for /{key}: {e}")
                        break

            page.on("response", handle_response)

            try:
                self.logger.debug(f"Match {match_id}: loading - {match_link}")
                await page.goto(match_link, wait_until="domcontentloaded", timeout=30_000)
                try:
                    await page.wait_for_load_state("networkidle", timeout=8_000)
                except Exception:
                    pass
                await page.wait_for_timeout(random.randint(self.min_ms, self.max_ms))

                # manage popups
                browser_helpers = BrowserHelpers(page)
                await browser_helpers.handle_all_popups()

                # navigate to statistics tab via hash-change

                statistics_hash = f"#id:{match_id},tab:statistics"
                self.logger.debug(f"match {match_id}: switching to statistics tab")
                await page.evaluate(f"window.location.hash = '{statistics_hash}'")
                try:
                    await page.wait_for_load_state("networkidle", timeout=8_000)
                except Exception:
                    pass
                await page.wait_for_timeout(random.randint(self.min_ms, self.max_ms))

                if "statistics" not in captured:
                    self.logger.debug(f"match {match_id}: hash navigation didn't fire /statistics - trying click")
                    try:
                        tab_link = page.locator("a[href*='tab:statistics']").first
                        await tab_link.click(timeout=5_000)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=6_000)
                        except Exception:
                            pass
                        await page.wait_for_timeout(random.randint(self.min_ms, self.max_ms))
                    except Exception as e:
                        self.logger.debug(f"match {match_id}: statistics tab click failed - {e}")

                lineups_hash = f"#id:{match_id},tab:lineups"
                self.logger.debug(f"match {match_id}: switching to lineups tab")
                await page.evaluate(f"window.location.hash = '{lineups_hash}'")
                try:
                    await page.wait_for_load_state("networkidle", timeout=8_000)
                except Exception:
                    pass
                await page.wait_for_timeout(random.randint(self.min_ms, self.max_ms))

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
                        await page.wait_for_timeout(random.randint(self.min_ms, self.max_ms))
                    except Exception as e:
                        self.logger.debug(f"match {match_id}: lineups tab click failed - {e}")

                knockout_hash = f"#id:{match_id},tab:knockout"
                self.logger.debug(f"match {match_id}: switching to knockout tab")
                await page.evaluate(f"window.location.hash = '{knockout_hash}'")
                try:
                    await page.wait_for_load_state("networkidle", timeout=8_000)
                except Exception:
                    pass
                await page.wait_for_timeout(random.randint(self.min_ms, self.max_ms))

                # if not knockout captured, try pressing knockout button
                if "knockout" not in captured:
                    self.logger.debug(f"match {match_id}: hash navigation didn't fire /knockout - trying click")
                    try:
                        tab_link = page.locator("a[href*='tab:knockout']").first
                        await tab_link.click(timeout=5_000)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=6_000)
                        except Exception:
                            pass
                        await page.wait_for_timeout(random.randint(self.min_ms, self.max_ms))
                    except Exception as e:
                        self.logger.debug(f"match {match_id}: knockout tab click failed - {e}")

                standings_hash = f"#id:{match_id},tab:standings"
                self.logger.debug(f"match {match_id}: switching to standings tab")
                await page.evaluate(f"window.location.hash = '{standings_hash}'")
                try:
                    await page.wait_for_load_state("networkidle", timeout=8_000)
                except Exception:
                    pass
                await page.wait_for_timeout(random.randint(self.min_ms, self.max_ms))

                # if not standings captured, try pressing standings button
                if not any(k.startswith("standings") for k in captured):
                    self.logger.debug(f"match {match_id}: hash navigation didn't fire /standings - trying click")
                    try:
                        tab_link = page.locator("a[href*='tab:standings']").first
                        await tab_link.click(timeout=5_000)

                        try:
                            await page.wait_for_load_state("networkidle", timeout=6_000)
                        except Exception:
                            pass
                        await page.wait_for_timeout(random.randint(self.min_ms, self.max_ms))
                    except Exception as e:
                        self.logger.debug(f"match {match_id}: standings tab click failed - {e}")
                for variant in ("Home", "Away"):
                    try:
                        variant_tab = page.get_by_test_id(f"tab-{variant.lower()}")
                        await variant_tab.click(timeout=5_000)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=6_000)
                        except Exception:
                            pass
                        await page.wait_for_timeout(random.randint(self.min_ms, self.max_ms))
                    except Exception as e:
                        self.logger.debug(f"match {match_id}: standings {variant.lower()} tab click failed - {e}")     

            except Exception as e:
                self.logger.warning(f"match {match_id}: page load error - {e}")

            STANDINGS_VARIANTS = ("total", "home", "away")

            missing = []
            for s in WANTED_SUFFIXES.get(self.sport.lower(), []):
                if s == "/standings":
                    missing.extend(f"standings/{v}" for v in STANDINGS_VARIANTS if f"standings/{v}" not in captured)
                    continue
                key = s.lstrip("/")
                if key not in captured:
                    missing.append(key)

            if missing:
                self.logger.debug(f"match {match_id}: missing endpoints after fetch: {missing}")
                self.logger.warning(f"{len(missing)} endpoint not found.")

            return captured