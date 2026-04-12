import logging
from typing import List
import re
from functools import lru_cache

from sofascraper.utils.enums import Sport
from sofascraper.utils.sport_season_registry import SportSeasonRegistry
from sofascraper.utils.sport_tournament_registry import SportTournamentRegistry

logger = logging.getLogger(__name__)


def get_supported_seasons(sport: Sport | str) -> List[str]:
    """
    Return all season years (as strings) for a given sport.
    """
    if isinstance(sport, str):
        try:
            sport = Sport(sport.lower())
        except ValueError:
            valid_sports = [s.value for s in Sport]
            raise ValueError(
                f"Invalid sport name: {sport}. Expected one of {valid_sports}."
            ) from None

    # Get all tournaments for this sport
    tournaments = SportSeasonRegistry.get_by_sport(sport.value)

    # Flatten seasons
    seasons = [season["year"] for t in tournaments for season in t.get("seasons", [])]

    return seasons


def get_supported_tournaments(sport: Sport | str) -> List[dict]:
    """
    Return all tournaments for a given sport.
    """
    if isinstance(sport, str):
        try:
            sport = Sport(sport.lower())
        except ValueError:
            valid_sports = [s.value for s in Sport]
            raise ValueError(
                f"Invalid sport name: {sport}. Expected one of {valid_sports}."
            ) from None

    return SportTournamentRegistry.get_by_sport(sport.value)


@lru_cache(maxsize=None)
def to_snake_case(text: str) -> str:
    import re

    text = re.sub(r"[^\w\s-]", "", text)  # remove special chars
    text = re.sub(r"[ -]+", "_", text)
    text = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    return text.lower()
