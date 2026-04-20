import logging
import re
import time
from functools import cache

from sofascraper.utils.enums import Sport
from sofascraper.utils.sport_tournament_registry import SportTournamentRegistry

logger = logging.getLogger(__name__)


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


# def resolve_dates(dates: str | list[str]) -> list[str]:
#     """
#     Parse the flexible dates argument into a sorted, deduplicated list
#     of ISO date strings.

#     2022-11-12                            -->    ["2022-11-12"]
#     [2022-11-12, 2022-11-15]              -->    ["2022-11-12", "2022-11-15"]
#     2022-11-12-2022-12-01                 -->    ["2022-11-12", … , "2022-12-01"]
#     """

#     # Handle multiple dates
#     if isinstance(dates, list):
#         resolved = [date.fromisoformat(d).isoformat() for d in dates]

#     # Handles date intervals
#     elif len(dates) == 21:
#         left, right = dates[:10], dates[11:]
#         start = date.fromisoformat(left)
#         end = date.fromisoformat(right)
#         if end < start:
#             raise ValueError(f"Range end '{start}' is before start '{end}'")
#         resolved = []
#         current = start
#         while current <= end:
#             resolved.append(current.isoformat())
#             current += timedelta(days=1)

#     # Handle single date
#     else:
#         resolved = [date.fromisoformat(dates.strip()).isoformat()]

#     # Return all of them as a set
#     return sorted(set(resolved))


# def resolve_tournaments(tournaments: list[list]) -> list[str]:
#     if not tournaments:
#         return None

#     results = []

#     # Handle it as list of items
#     for tournament in tournaments:
#         if bool(re.fullmatch(r"\d+", tournament)):
#             results.append(_get_tournament_data(tournament_id=int(tournament)).get("slug"))
#         elif bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", tournament)):
#             results.append(_get_tournament_data(slug=tournament).get("slug"))
#         else:
#             results.append(_get_tournament_data(name=tournament).get("slug"))

#     return results


def _get_tournament_data(
    tournament_id: int | None = None,
    slug: str | None = None,
    name: str | None = None,
) -> dict:

    result = None
    tournament = SportTournamentRegistry()
    slug = slug.strip() if slug else slug
    name = name.strip() if name else name

    if tournament_id is not None:
        result = tournament.get_by_id(tournament_id)

    if result is None and slug is not None:
        result = tournament.get_by_slug(slug)

    if result is None and name is not None:
        result = tournament.get_by_name(name)

    return result


def wait_and_try_again(wait, func, retries=3):
    for attempt in range(retries):
        try:
            return func()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(wait)
