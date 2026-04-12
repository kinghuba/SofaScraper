import json
from pathlib import Path


class SportTournamentRegistry:
    """Dynamic lookup among tournaments"""

    _data = None
    _id_map = None
    _slug_map = None
    _name_map = None
    _sport_map = None
    _country_id_map = None
    _country_name_map = None

    @classmethod
    def _load(cls):
        if cls._data is None:
            path = Path(__file__).parent / "json" / "tournaments.json"
            with open(path) as f:
                cls._data = json.load(f)

            cls._id_map = {t["id"]: t for t in cls._data}
            cls._slug_map = {t.get("slug"): t for t in cls._data if t.get("slug")}
            cls._name_map = {t["name"]: t for t in cls._data}

            cls._sport_map = {}
            cls._country_id_map = {}
            cls._country_name_map = {}

            for t in cls._data:
                cls._sport_map.setdefault(t["sport"], []).append(t)
                cls._country_id_map.setdefault(t.get("country_id"), []).append(t)
                cls._country_name_map.setdefault(t.get("country_name"), []).append(t)

    @classmethod
    def all(cls):
        cls._load()
        return cls._data

    @classmethod
    def get_by_id(cls, tournament_id):
        cls._load()
        return cls._id_map.get(tournament_id)

    @classmethod
    def get_by_slug(cls, slug):
        cls._load()
        return cls._slug_map.get(slug)

    @classmethod
    def get_by_name(cls, name):
        cls._load()
        return cls._name_map.get(name)

    @classmethod
    def get_by_sport(cls, sport):
        cls._load()
        return cls._sport_map.get(sport, [])

    @classmethod
    def get_by_country_id(cls, country_id):
        cls._load()
        return cls._country_id_map.get(country_id, [])

    @classmethod
    def get_by_country_name(cls, name):
        cls._load()
        return cls._country_name_map.get(name, [])
