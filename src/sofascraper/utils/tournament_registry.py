from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List

from sofascraper.utils.dataclasses.registry_data_classes import RegistrySeason, RegistryTournament


class SportTournamentRegistry:
    """Dynamic lookup among tournaments and seasons"""

    _data: list[RegistryTournament] | None = None
    _id_map: dict[int, RegistryTournament] = {}
    _slug_map: dict[str, RegistryTournament] = {}
    _name_map: dict[str, RegistryTournament] = {}
    _sport_map: dict[str, list[RegistryTournament]] = {}
    _country_id_map: dict[int, list[RegistryTournament]] = {}
    _season_id_map: dict[int, RegistrySeason] = {}
    _season_tournament_map: dict[int, RegistryTournament] = {}

    @classmethod
    def _load(cls) -> None:
        if cls._data is not None:
            return

        path = Path(__file__).parent / "json" / "tournaments.json"

        with open(path, encoding="utf-8") as f:
            raw_data = json.load(f)

        cls._data = []

        for raw_tournament in raw_data:
            seasons = [
                RegistrySeason(
                    id=season["id"],
                    year=season["year"],
                )
                for season in raw_tournament.get("seasons", [])
            ]

            tournament = RegistryTournament(
                id=raw_tournament["id"],
                name=raw_tournament["name"],
                slug=raw_tournament.get("slug"),
                priority=raw_tournament.get("priority", 0),
                sport=raw_tournament["sport"],
                country_id=raw_tournament.get("countryId"),
                seasons=seasons,
            )

            cls._data.append(tournament)

            cls._id_map[tournament.id] = tournament

            if tournament.slug:
                cls._slug_map[tournament.slug] = tournament

            cls._name_map[tournament.name] = tournament

            cls._sport_map.setdefault(
                tournament.sport,
                [],
            ).append(tournament)

            if tournament.country_id is not None:
                cls._country_id_map.setdefault(
                    tournament.country_id,
                    [],
                ).append(tournament)

            for season in seasons:
                cls._season_id_map[season.id] = season
                cls._season_tournament_map[season.id] = tournament

    # ^ Tournament methods

    @classmethod
    def all(cls) -> list[RegistryTournament]:
        cls._load()
        return cls._data or []

    @classmethod
    def get_by_id(cls, tournament_id) -> RegistryTournament | None:
        cls._load()
        return cls._id_map.get(tournament_id)

    @classmethod
    def get_by_slug(cls, slug) -> RegistryTournament | None:
        cls._load()
        return cls._slug_map.get(slug)

    @classmethod
    def get_by_name(cls, name) -> RegistryTournament | None:
        cls._load()
        return cls._name_map.get(name)

    @classmethod
    def get_by_sport(cls, sport) -> list[RegistryTournament]:
        cls._load()
        return cls._sport_map.get(sport, [])

    @classmethod
    def get_by_country_id(cls, country_id) -> list[RegistryTournament]:
        cls._load()
        return cls._country_id_map.get(country_id, [])

    # ^ Season methods

    @classmethod
    def get_seasons_by_tournament(cls, tournament_id) -> list[RegistrySeason]:
        cls._load()
        tournament = cls._id_map.get(int(tournament_id))
        return tournament.seasons if tournament else []

    @classmethod
    def get_by_season_id(cls, season_id)  -> RegistrySeason | None:
        cls._load()
        return cls._season_id_map.get(season_id) or None

    @classmethod
    def get_tournament_by_season_id(
        cls,
        season_id: int,
    ) -> RegistryTournament | None:
        cls._load()
        return cls._season_tournament_map.get(season_id)
