import re
import time
from functools import cache

from sofascraper.utils.constants import SOFASCORE_BASE_URL
from sofascraper.utils.country_registry import CountryRegistry
from sofascraper.utils.enums import Sport
from sofascraper.utils.sport_tournament_registry import SportTournamentRegistry


def get_supported_seasons(sport: Sport | str) -> list[str]:
    """
    Return all season years (as strings) for a given sport.
    """
    if isinstance(sport, str):
        try:
            sport = Sport(sport.lower())
        except ValueError:
            valid_sports = [s.value for s in Sport]
            raise ValueError(f"Invalid sport name: {sport}. Expected one of {valid_sports}.") from None

    tournaments = SportTournamentRegistry.get_by_sport(sport=sport.value)

    seasons = {season["year"] for t in tournaments for season in t.get("seasons", [])}

    return sorted(seasons)


def get_supported_tournaments(sport: Sport | str) -> list[dict]:
    """
    Return all tournaments for a given sport.
    """
    if isinstance(sport, str):
        try:
            sport = Sport(sport.lower())
        except ValueError:
            valid_sports = [s.value for s in Sport]
            raise ValueError(f"Invalid sport name: {sport}. Expected one of {valid_sports}.") from None

    return SportTournamentRegistry.get_by_sport(sport.value)


@cache
def to_snake_case(text: str) -> str:

    text = re.sub(r"[^\w\s-]", "", text)  # remove special chars
    text = re.sub(r"[ -]+", "_", text)
    text = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    return text.lower()


def fractional_to_all_odds(fractional_input: str | list[str]) -> list[dict]:
    """
    Convert fractional odds to decimal, American, implied probability,
    and (if multiple) true/fair odds.

    Args:
        fractional_input: str or list of str (e.g. "5/2" or ["5/2", "2/1"])

    Returns:
        list of dicts
    """

    def parse_fraction(frac_str):
        try:
            num, denom = map(float, frac_str.split("/"))
            if denom == 0:
                raise ValueError
            if num == 0 and denom == 1:
                return 0
            return num / denom
        except:
            raise ValueError(f"Invalid fractional odds: {frac_str}")

    # Normalize input to list
    if isinstance(fractional_input, str):
        fractional_list = [fractional_input]
    else:
        fractional_list = fractional_input

    results = []

    # Base odds
    for frac_str in fractional_list:
        frac = parse_fraction(frac_str)

        decimal_odds = frac + 1

        if frac >= 1:
            american_odds = int(frac * 100)
        elif frac == 0:
            american_odds = 0
        else:
            american_odds = int(-100 / frac)

        implied_prob = 1 / decimal_odds

        results.append(
            {
                "fractional": frac_str,
                "decimal": decimal_odds,
                "american": american_odds,
                "implied_probability": implied_prob,
            }
        )

    # Remove wig
    if len(results) > 1:
        total_prob = sum(r["implied_probability"] for r in results)

        for r in results:
            true_prob = r["implied_probability"] / total_prob
            true_decimal = 1 / true_prob

            r["true_probability"] = round(true_prob, 4)
            r["true_decimal_odds"] = round(true_decimal, 4)

    # Rounding
    for r in results:
        r["decimal"] = round(r["decimal"], 4)
        r["implied_probability"] = round(r["implied_probability"], 4)

    return results

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

def get_tournament_information(sport: str, tournament: str, season: str | None = None):
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
        tournament_dict = SportTournamentRegistry.get_by_id(tournament)
        country_dict = CountryRegistry.get_by_id(tournament_dict.get("country_id"))



        # Sorting by season value
        sorted_seasons = sorted(tournament_dict["seasons"], key=lambda x: extract_year(x["year"]), reverse=True)

        if tournament_dict:
            base_url = f"{SOFASCORE_BASE_URL}/{sport}/tournament/{country_dict.get('flag').lower()}/{tournament_dict.get('slug').lower()}/{tournament_dict.get('id')}"
        season_id = None
        # country_id = tournament_dict.get("country_id")

        # Treat missing season as current
        if season == "current":
            season_id = sorted_seasons[0]['id']

        if re.match(r"^\d{5,}$", season):
            season_id = season

        if re.match(r"^\d{4}$", season) or re.match(r"^\d{2}/\d{2}$", season):
            season_id = next(
                # Check against both
                (s["id"] for s in sorted_seasons if s["year"] == season or s["year"] == extract_year(season)),
                None,
            )

        url = f"{base_url}#id:{season_id}"

        return url, season_id

def get_match_id(url: str) -> int | None:
    """
    Extract the numeric SofaScore match ID from a page URL.
    """
    # Hash-style  #id:12345
    m = re.search(r"#id:(\d+)", url)
    if m:
        return int(m.group(1))
    return None

def wait_and_try_again(wait, func, retries=3):
    for attempt in range(retries):
        try:
            return func()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(wait)
