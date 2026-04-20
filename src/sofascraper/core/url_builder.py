import logging
import re

from sofascraper.utils.constants import SOFASCORE_BASE_URL
from sofascraper.utils.country_registry import CountryRegistry
from sofascraper.utils.sport_tournament_registry import SportTournamentRegistry

logger = logging.getLogger("URLBuilder")


class URLBuilder:
    """
    A utility class for constructing URLs used in scraping data from OddsPortal.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_tournament_url(self, sport: str, tournament: str, season: str | None = None) -> str:
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
        country_dict = CountryRegistry.get_by_id(tournament_dict.get("country_id"))

        # Year could be saved as 25/26
        def extract_year(year_str):
            # Normalize input to string
            year_str = str(year_str)

            # Case 1: format like "24/25"
            if re.fullmatch(r"\d{2}/\d{2}", year_str):
                return max(int(f"20{y}") for y in year_str.split("/"))

            # Case 2: format like "2024"
            if re.fullmatch(r"\d{4}", year_str):
                year = int(year_str)
                short = year % 100
                next_short = (short + 1) % 100
                return f"{short:02d}/{next_short:02d}"

            raise ValueError(f"Invalid year format: {year_str}")

        # Sorting by season value
        sorted_seasons = sorted(tournament_dict["seasons"], key=lambda x: extract_year(x["year"]), reverse=True)

        if tournament_dict:
            base_url = f"{SOFASCORE_BASE_URL}/{sport}/tournament/{country_dict.get('flag').lower()}/{tournament_dict.get('slug').lower()}/{tournament_dict.get('id')}"
            self.logger.debug(base_url)

        # Treat missing season as current
        if not season:
            self.logger.debug(f"{base_url}#id:{sorted_seasons[0]['id']}")
            return f"{base_url}#id:{sorted_seasons[0]['id']}"

        if isinstance(season, str) and season.lower() == "current":
            raise ValueError(f"Invalid season format: {season}. Expected format: 'YY/YY' or 'YYYY'")

        if re.match(r"^\d{5,}$", season):
            return f"{base_url}#id:{season}"

        if re.match(r"^\d{4}$", season) or re.match(r"^\d{2}/\d{2}$", season):
            season_id = next(
                # Check against both
                (s["id"] for s in sorted_seasons if s["year"] == season or s["year"] == extract_year(season)),
                None,
            )
            self.logger.debug(f"{base_url}#id:{season_id}")
            return f"{base_url}#id:{season_id}"

        raise ValueError(f"Invalid season format: {season}. Expected format: 'YYYY' or 'YY/YY'")

    def get_url(self, match_url: str, match_id: int) -> str:
        """
        Return the match URL.
        """
        base = match_url.split("#")[0]
        return f"{base}#id:{match_id}"

    def get_match_id(self, url: str) -> int | None:
        """
        Extract the numeric SofaScore match ID from a page URL.
        """
        # Hash-style  #id:12345
        m = re.search(r"#id:(\d+)", url)
        if m:
            return int(m.group(1))
        return None
