import logging

from sofascraper.utils.enums import StorageFormat
from sofascraper.core.football.football_scraper import FootballScraper
from sofascraper.core.playwright_manager import PlaywrightManager
from sofascraper.storage.local_data_storage import LocalDataStorage
from sofascraper.utils.enums import CommandEnum
from sofascraper.utils.proxy_manager import ProxyManager


class ScraperApp:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.playwright_manager = PlaywrightManager()
        self.football_scraper = FootballScraper(
            playwright_manager=self.playwright_manager
        )

    async def run_scraper(
        self,
        command: CommandEnum,
        match_links: list | None = None,
        sport: str | None = None,
        dates: str | None = None,
        tournaments: list[str] | None = None,
        seasons: str | None = None,
        storage_format: str = "json",
        file_path: str = "data",
        proxy_url: str | None = None,
        proxy_user: str | None = None,
        proxy_pass: str | None = None,
        browser_user_agent: str | None = None,
        browser_locale_timezone: str | None = None,
        browser_timezone_id: str | None = None,
        headless: bool = False,
    ):
        """
        Runs the scraping process and handles execution.
        """

        self.logger.info(
            f"Starting scraper with parameters: command={command}, match_links={match_links}, "
            f"sport={sport}, date={dates}, leagues={tournaments}, season={seasons}, file_path={file_path}"
            f"proxy_url={proxy_url}, browser_user_agent={browser_user_agent}, "
            f"browser_locale_timezone={browser_locale_timezone}, browser_timezone_id={browser_timezone_id}, "
            f"headless={headless}"
        )

        self.proxy_manager = ProxyManager(
            proxy_url=proxy_url, proxy_user=proxy_user, proxy_pass=proxy_pass
        )

        try:
            proxy_config = self.proxy_manager.get_current_proxy()
            await self.football_scraper.start_playwright(
                headless=headless,
                browser_user_agent=browser_user_agent,
                browser_locale_timezone=browser_locale_timezone,
                browser_timezone_id=browser_timezone_id,
                proxy=proxy_config,
            )

            if command == CommandEnum.TOURNAMENTS:
                if not sport or not tournaments:
                    raise ValueError(
                        "Both 'sport' and 'tournaments' must be provided for scraping."
                    )

                printable_season = seasons if seasons else "current"
                self.logger.info(
                    "\n Scraping matches and their details for "
                    f"sport={sport}, tournaments={tournaments}, season={printable_season}\n"
                )

                storage = LocalDataStorage(
                    default_file_path=f"{file_path}/{tournaments[0].lower()}",
                    default_storage_format=StorageFormat(
                        storage_format.strip().lower()
                    ),
                )

                return await self.football_scraper.scrape_tournaments(
                    sport=sport,
                    tournament=tournaments[0],
                    season=seasons,
                    storage=storage,
                )

            if command == CommandEnum.MATCHES:
                if not match_links or not sport:
                    raise ValueError(
                        "At least one match link and the sport must be provided for scraping."
                    )

                self.logger.info(
                    f"\n Scraping details for matches={match_links} sport={sport}"
                )

                storage = LocalDataStorage(
                    default_file_path=f"{file_path}/matches",
                    default_storage_format=StorageFormat(
                        storage_format.strip().lower()
                    ),
                )

                return await self.football_scraper.scrape_links(
                    sport=sport, match_links=list(match_links), storage=storage
                )

            if command == CommandEnum.DATES:
                if not dates:
                    raise ValueError(
                        "At least one 'match_link' must be provided for scraping."
                    )

                self.logger.info(
                    f"\n Scraping details for dates={dates}, sport={sport}"
                )

                storage = LocalDataStorage(
                    default_file_path=f"{file_path}/dates",
                    default_storage_format=StorageFormat(
                        storage_format.strip().lower()
                    ),
                )

                return await self.football_scraper.scrape_dates(
                    sport=sport, dates=dates, storage=storage
                )

            else:
                raise ValueError(
                    f"Unknown command: {command}. Supported commands are 'upcoming-matches' and 'historic'."
                )

        except Exception as e:
            self.logger.error(f"An error occured: {e}")
            return None

        finally:
            await self.football_scraper.stop_playwright()
            self.logger.info("Process stopped successfully")
