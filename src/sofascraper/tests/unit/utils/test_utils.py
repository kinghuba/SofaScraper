"""
Tests for sofascraper.utils.utils

Covers:
- to_snake_case           — camelCase, PascalCase, spaces, hyphens, special chars, caching
- get_supported_seasons   — valid sport string, Sport enum, invalid sport
- get_supported_tournaments — valid sport string, Sport enum, invalid sport
"""

from unittest.mock import patch

import pytest

from sofascraper.utils.enums import Sport
from sofascraper.utils.utils import get_supported_seasons, get_supported_tournaments, to_snake_case


class TestToSnakeCase:
    @pytest.mark.parametrize(
        "input_str, expected",
        [
            ("ballPossession", "ball_possession"),
            ("totalShots", "total_shots"),
            ("onTargetShooting", "on_target_shooting"),
            ("xG", "x_g"),
            ("BigChancesCreated", "big_chances_created"),
            ("already_snake", "already_snake"),
            ("with spaces", "with_spaces"),
            ("with-hyphens", "with_hyphens"),
            ("with--multiple--dashes", "with_multiple_dashes"),
            ("mixedABC123", "mixed_a_b_c123"),
            ("", ""),
        ],
    )
    def test_conversions(self, input_str, expected):
        assert to_snake_case(input_str) == expected

    def test_special_chars_removed(self):
        result = to_snake_case("ball!Possession")
        assert "!" not in result

    def test_result_is_lowercase(self):
        assert to_snake_case("TotalShots").islower()

    def test_cached_result_is_same_object(self):
        """lru_cache means repeated calls return the same string object."""
        r1 = to_snake_case("ballPossession")
        r2 = to_snake_case("ballPossession")
        assert r1 is r2


# ---------------------------------------------------------------------------
# get_supported_seasons
# ---------------------------------------------------------------------------


class TestGetSupportedSeasons:
    @pytest.fixture(autouse=True)
    def mock_registry(self):
        fake_data = [
            {
                "sport": "football",
                "tournament_id": 1,
                "seasons": [
                    {"id": 10, "year": "24/25"},
                    {"id": 11, "year": "23/24"},
                ],
            }
        ]
        with patch(
            "sofascraper.utils.utils.SportSeasonRegistry.get_by_sport",
            return_value=fake_data,
        ):
            yield

    def test_returns_list_of_year_strings(self):
        seasons = get_supported_seasons("football")
        assert "24/25" in seasons
        assert "23/24" in seasons

    def test_accepts_sport_enum(self):
        seasons = get_supported_seasons(Sport.FOOTBALL)
        assert len(seasons) == 2

    def test_invalid_sport_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid sport name"):
            get_supported_seasons("underwater_polo")


# ---------------------------------------------------------------------------
# get_supported_tournaments
# ---------------------------------------------------------------------------


class TestGetSupportedTournaments:
    @pytest.fixture(autouse=True)
    def mock_registry(self):
        fake_tournaments = [
            {"id": 1, "name": "Premier League", "slug": "premier-league", "sport": "football"},
            {"id": 2, "name": "La Liga", "slug": "laliga", "sport": "football"},
        ]
        with patch(
            "sofascraper.utils.utils.SportTournamentRegistry.get_by_sport",
            return_value=fake_tournaments,
        ):
            yield

    def test_returns_list_of_dicts(self):
        tournaments = get_supported_tournaments("football")
        assert isinstance(tournaments, list)
        assert len(tournaments) == 2

    def test_accepts_sport_enum(self):
        tournaments = get_supported_tournaments(Sport.FOOTBALL)
        assert tournaments[0]["name"] == "Premier League"

    def test_invalid_sport_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid sport name"):
            get_supported_tournaments("table_tennis")
