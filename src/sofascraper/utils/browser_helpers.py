import logging
import time
from dataclasses import dataclass

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, TimeoutError

from sofascraper.utils.constants import POPUP_TIMEOUT_MS

# Consent button: fc-button fc-cta-consent (CMP/GDPR consent wall)
CONSENT_SELECTOR = "button.fc-button.fc-cta-consent.fc-primary-button"

# Language confirm button: filled primary button used for language selection
LANGUAGE_SELECTOR = (
    "button.button--variant_filled.button--size_secondary.button--colorPalette_primary.button--negative_false"
)


@dataclass
class PopupHandlerResults:
    """Result of popup handling."""

    consent_accepted: bool = False
    language_confirmed: bool = False


class BrowserHelpers:
    """
    Handles transient popup dialogs that may appear on SofaScore pages.

    Both methods are safe to call unconditionally -- if the relevant button
    is not present within the timeout window, the method logs a debug message
    and returns False instead of raising.
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.logger = logging.getLogger(self.__class__.__name__)

    async def accept_consent(self) -> bool:
        """
        Click the GDPR / cookie-consent button if it appears.

        Looks for:
            <button class="fc-button fc-cta-consent fc-primary-button" ...>

        Returns:
            True  -- button was found and clicked.
            False -- button did not appear within the timeout window.
        """
        try:
            btn = self.page.locator(CONSENT_SELECTOR).first
            await btn.wait_for(state="visible", timeout=POPUP_TIMEOUT_MS)
            await btn.click()
            self.logger.debug("Consent popup accepted.")
            return True

        except TimeoutError:
            self.logger.debug("No consent popup detected -- skipping.")
            return False

        except Exception as e:
            self.logger.warning(f"Unexpected error while accepting consent: {e}")
            return False

    async def confirm_language(self) -> bool:
        """
        Click the language-confirmation button if it appears.

        The selector targets the CSS classes rather than the button text so that
        it still works if the label is ever localised, but an extra text filter
        is applied as a safety guard to avoid accidentally clicking an unrelated
        button that shares the same classes.

        Returns:
            True  --> button was found and clicked.
            False --> button did not appear within the timeout window.
        """
        try:
            btn = self.page.locator(LANGUAGE_SELECTOR, has_text="Confirm").first
            await btn.wait_for(state="visible", timeout=POPUP_TIMEOUT_MS)
            await btn.click()
            self.logger.debug("Language confirmation accepted.")
            return True

        except TimeoutError:
            self.logger.warning("No language confirmation popup detected -- skipping.")
            return False

        except Exception as e:
            self.logger.warning(f"Unexpected error while confirming language: {e}")
            return False

    async def handle_all_popups(self) -> PopupHandlerResults:
        consent = await self.accept_consent()
        language = await self.confirm_language()

        return PopupHandlerResults(
            consent_accepted=consent,
            language_confirmed=language,
        )

    async def scroll_until_loaded(
        self,
        timeout=15,
        scroll_pause_time=3,
        max_scroll_attempts=3,
        content_check_selector: str | None = None,
    ):
        """
        Scrolls down the page until no new content is loaded or a timeout is reached.

        This method is useful for pages that load content dynamically as the user scrolls.
        It attempts to scroll the page to the bottom multiple times, waiting for a specified
        interval between scrolls. Scrolling stops when no new content is detected, a timeout
        occurs, or the maximum number of scroll attempts is reached.

        Args:
            page (Page): The Playwright page instance to interact with.
            timeout (int): The maximum time (in seconds) to attempt scrolling (default: 30).
            scroll_pause_time (int): The time (in seconds) to pause between scrolls (default: 3).
            max_scroll_attempts (int): The maximum number of attempts to detect new content (default: 5).
            content_check_selector (str): Optional CSS selector to check for new content after scrolling.

        Returns:
            bool: True if scrolling completed successfully, False otherwise.
        """
        self.logger.debug("Will scroll to the bottom of the page to load all content.")
        end_time = time.time() + timeout
        last_height = await self.page.evaluate("document.body.scrollHeight")
        last_element_count = 0
        stable_count_attempts = 0

        # Get initial element count if selector is provided
        if content_check_selector:
            initial_elements = await self.page.query_selector_all(content_check_selector)
            last_element_count = len(initial_elements)
            self.logger.debug(f"Initial element count: {last_element_count}")

        self.logger.debug(f"Initial page height: {last_height}")

        scroll_step = 500
        current_scroll_pos = 0

        while time.time() < end_time:
            try:
                # Scroll incrementally to trigger lazy-loading content
                page_height = await self.page.evaluate("document.body.scrollHeight")
                if current_scroll_pos < page_height:
                    current_scroll_pos = min(current_scroll_pos + scroll_step, page_height)
                    await self.page.evaluate(f"window.scrollTo(0, {current_scroll_pos})")
                else:
                    # Already at bottom, nudge to trigger any remaining loads
                    await self.page.evaluate(f"window.scrollTo(0, {page_height})")
                await self.page.wait_for_timeout(scroll_pause_time * 1000)

                new_height = await self.page.evaluate("document.body.scrollHeight")
                new_element_count = 0

                # Count elements if selector is provided
                if content_check_selector:
                    new_element_count = await self.page.locator(content_check_selector).count()
                    self.logger.debug(f"Current element count: {new_element_count} (height: {new_height})")

                    # Check if element count is stable
                    if new_element_count == last_element_count and new_height == last_height:
                        stable_count_attempts += 1
                        self.logger.debug(f"Content stable. Attempt {stable_count_attempts}/{max_scroll_attempts}.")

                        if stable_count_attempts >= max_scroll_attempts:
                            self.logger.debug(f"Content stabilized at {new_element_count} elements. Scrolling complete.")
                            return True
                    else:
                        stable_count_attempts = 0  # Reset if content changed
                        last_element_count = new_element_count
                else:
                    # Fallback to height-based detection
                    if new_height == last_height:
                        stable_count_attempts += 1
                        self.logger.debug(f"Height stable. Attempt {stable_count_attempts}/{max_scroll_attempts}.")

                        if stable_count_attempts >= max_scroll_attempts:
                            self.logger.debug("Page height stabilized. Scrolling complete.")
                            return True
                    else:
                        stable_count_attempts = 0

                last_height = new_height
            except PlaywrightError as e:
                if "Execution context was destroyed" in str(e):
                    self.logger.warning("Page context destroyed during scroll -- waiting for reload.")
                    await self.page.wait_for_load_state("domcontentloaded")
                    continue
                raise

        self.logger.warning("Reached scrolling timeout. Stopping scroll.")
        return False

    # TODO Implement utr closing for tennis
    # <button class="button button--variant_clear button--size_primary button--colorPalette_primary button--negative_false c_onColor.primary">Maybe later</button>
