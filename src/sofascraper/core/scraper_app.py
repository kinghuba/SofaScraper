import logging

from dotenv import load_dotenv
from playwright.async_api import ProxySettings

from sofascraper.core.base_scraper import Scraper
from sofascraper.core.playwright_manager import PlaywrightManager
from sofascraper.storage.local_data_storage import LocalDataStorage
from sofascraper.storage.pgsql.connection import Database
from sofascraper.storage.pgsql_data_storage import PgsqlDataStorage
from sofascraper.utils.constants import VERSION
from sofascraper.utils.enums import CommandEnum
from sofascraper.utils.proxy_manager import ProxyManager


class ScraperApp:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.playwright_manager = PlaywrightManager()
        self.scraper = Scraper(playwright_manager=self.playwright_manager)

    async def run_scraper(
        self,
        command: CommandEnum,
        match_links: list | None = None,
        sport: str = "football",
        dates: str | None = None,
        tournaments: list[str] | None = None,
        seasons: list[str] = ["current"],
        storage_format: str = "json",
        file_path: str | None = None,
        proxy_url: str | None = None,
        proxy_user: str | None = None,
        proxy_pass: str | None = None,
        browser_user_agent: str | None = None,
        browser_locale_timezone: str | None = None,
        browser_timezone_id: str | None = None,
        headless: bool = False,
        concurrency: int = 1
    ):
        """
        Runs the scraping process and handles execution.
        """

        self.logger.info(
            f"Starting scraper with parameters: command={command}, match_links={match_links}, "
            f"sport={sport}, date={dates}, leagues={tournaments}, season={seasons}, file_path={file_path} "
            f"proxy_url={proxy_url}, browser_user_agent={browser_user_agent}, "
            f"browser_locale_timezone={browser_locale_timezone}, browser_timezone_id={browser_timezone_id}, "
            f"headless={headless} storage={storage_format} concurrency={concurrency}"
        )

        self.proxy_manager = ProxyManager(proxy_url=proxy_url, proxy_user=proxy_user, proxy_pass=proxy_pass)

        try:
            proxy_config = self.proxy_manager.get_proxy()
            proxy = None
            if proxy_config is not None:
                proxy = ProxySettings(
                    server=proxy_config["proxy_url"],
                    username=proxy_config["proxy_user"],
                    password=proxy_config["proxy_pass"],
                )

            await self.scraper.start_playwright(
                headless=headless,
                browser_user_agent=browser_user_agent,
                browser_locale_timezone=browser_locale_timezone,
                browser_timezone_id=browser_timezone_id,
                proxy=proxy,
            )

            if storage_format == "database":
                load_dotenv()
                await Database.connect()
                self.scraper.storage = PgsqlDataStorage(sport_slug=sport, scraper_version=VERSION)
                async with Database.transaction() as conn:
                    await self.scraper.storage.open_scrape_run(conn)
            else:
                match command:
                    case CommandEnum.TOURNAMENTS:
                        self.scraper.storage = LocalDataStorage(
                            default_file_path=f"{file_path}/{sport}",
                        )
                    case CommandEnum.MATCHES:
                        self.scraper.storage = LocalDataStorage(
                            default_file_path=f"{file_path}/{sport}/matches",
                        )
                    case CommandEnum.DATES:
                        self.scraper.storage = LocalDataStorage(
                            default_file_path=f"{file_path}/{sport}/dates",
                        )

            if command == CommandEnum.TOURNAMENTS:
                if not sport or not tournaments:
                    raise ValueError("Both 'sport' and 'tournaments' must be provided for scraping.")

                self.logger.info(
                    f"\n Scraping matches and their details for sport={sport}, tournaments={tournaments}, season={seasons}\n")
                return await self.scraper.scrape_tournaments(sport=sport, tournaments=tournaments, seasons=seasons, concurrency=concurrency)

            if command == CommandEnum.MATCHES:
                if not match_links or not sport:
                    raise ValueError("At least one match link and the sport must be provided for scraping.")

                self.logger.info(f"\n Scraping details for matches={match_links} sport={sport}")
                return await self.scraper.scrape_links(sport=sport, match_links=list(match_links), concurrency=concurrency)

            if command == CommandEnum.DATES:
                if not dates:
                    raise ValueError("At least one 'match_link' must be provided for scraping.")

                self.logger.info(f"\n Scraping details for dates={dates}, sport={sport}\n")
                return await self.scraper.scrape_dates(sport=sport, dates=dates, concurrency=concurrency)
            else:
                raise ValueError(f"Unknown command: {command}.")
        except Exception as e:
            self.logger.error(f"An error occured: {e}")
            return None
        finally:
            # Close db connection if needed
            if isinstance(self.scraper.storage, PgsqlDataStorage):
                async with Database.transaction() as conn:
                    await self.scraper.storage.close_scrape_run(conn)
                await Database.disconnect()
            # End playwright
            await self.scraper.stop_playwright()
            self.logger.info("Process stopped successfully")
