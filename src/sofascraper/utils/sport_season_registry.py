import json
from pathlib import Path


class SportSeasonRegistry:
    """Dynamic lookup among seasons"""

    _data = None

    @classmethod
    def _load(cls):
        if cls._data is None:
            path = Path(__file__).parent / "json" / "seasons.json"
            with open(path) as f:
                cls._data = json.load(f)

    @classmethod
    def all(cls):
        cls._load()
        return cls._data

    @classmethod
    def all_flat(cls):
        """Return a flat list of all season dicts across every tournament entry."""
        cls._load()
        return [season for entry in cls._data for season in entry.get("seasons", [])]

    @classmethod
    def get_by_sport(cls, sport):
        cls._load()
        return [l for l in cls._data if l["sport"] == sport]

    @classmethod
    def get_by_tournament(cls, tournament_id):
        cls._load()
        return next((l for l in cls._data if l["tournament_id"] == tournament_id), None)

    @classmethod
    def get_by_id(cls, season_id):
        cls._load()
        for league in cls._data:
            for season in league.get("seasons", []):
                if season["id"] == season_id:
                    return season
        return None

    @classmethod
    def get_by_name(cls, name):
        cls._load()
        results = []
        for league in cls._data:
            for season in league.get("seasons", []):
                if season["year"] == name:
                    results.append(season)
        return results
