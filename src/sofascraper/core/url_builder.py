from datetime import UTC, datetime
import re
import logging

from sofascraper.utils.constants import SOFASCORE_BASE_URL
from sofascraper.utils.sport_tournament_registry import SportTournamentRegistry
from sofascraper.utils.sport_season_registry import SportSeasonRegistry
from sofascraper.utils.country_registry import CountryRegistry

logger = logging.getLogger("URLBuilder")


class URLBuilder:
    """
    A utility class for constructing URLs used in scraping data from OddsPortal.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_tournament_url(
        self, sport: str, tournament: str, season: str | None = None
    ) -> str:
        """
        Constructs the tournament URL for specific sport and season.

        Args:
            sport (str): The sport for which the URL is required (e.g., "football", "tennis").
            tournament (str): The tournament slug for which the URL is required (e.g., "premier-league", "laliga").
            season (Optional[str]): The season for which the URL is required. Accepts either:
                - a single season (e.g., "2024/2025")
                - None or empty string for the current season

        Returns:
            str: The constructed URL for the league and season.

        Raises:
            ValueError: If the season is provided but does not follow the expected format(s).
        """

        # Resolve league alias for this season
        tournament_dict = SportTournamentRegistry.get_by_slug(tournament)
        self.logger.debug(tournament_dict)
        country_dict = CountryRegistry.get_by_id(tournament_dict.get("country_id"))
        self.logger.debug(country_dict)
        seasons = SportSeasonRegistry.get_by_tournament(tournament_dict.get("id"))

        # Year could be saved as 25/26
        def extract_year(year_str):
            return max(int(f"20{y}") for y in year_str.split("/"))

        # Sorting by season value
        sorted_seasons = sorted(
            seasons["seasons"], key=lambda x: extract_year(x["year"]), reverse=True
        )

        if tournament_dict:
            base_url = f"{SOFASCORE_BASE_URL}/{sport}/tournament/{country_dict.get('slug').lower()}/{tournament_dict.get('slug').lower()}/{tournament_dict.get('id')}"

        # Treat missing season as current
        if not season:
            self.logger.debug(f"{base_url}#id:{sorted_seasons[0]['id']}")
            return f"{base_url}#id:{sorted_seasons[0]['id']}"

        if isinstance(season, str) and season.lower() == "current":
            raise ValueError(
                f"Invalid season format: {season}. Expected format: 'YY/YY' or 'YYYY'"
            )

        if re.match(r"^\d{4}$", season) or re.match(r"^\d{2}/\d{2}$", season):
            season_id = next(
                # Check against both
                (
                    s["id"]
                    for s in seasons["seasons"]
                    if s["year"] == season or s["year"] == extract_year(season)
                ),
                None,
            )
            self.logger.debug(f"{base_url}#id:{season_id}/")
            return f"{base_url}#id:{season_id}/"

        raise ValueError(
            f"Invalid season format: {season}. Expected format: 'YYYY' or 'YY/YY'"
        )

    def get_statistics_tab_url(self, match_url: str, match_id: int) -> str:
        """
        Return the match URL forced onto the statistics tab.
        """
        base = match_url.split("#")[0]
        return f"{base}#id:{match_id},tab:statistics"

    def get_match_id(self, url: str) -> int | None:
        """
        Extract the numeric SofaScore match ID from a page URL.
        """
        # Hash-style  #id:12345
        m = re.search(r"#id:(\d+)", url)
        if m:
            return int(m.group(1))
        return None
