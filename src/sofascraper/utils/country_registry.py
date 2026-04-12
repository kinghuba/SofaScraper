import json
from pathlib import Path


class CountryRegistry:
    """Dynamic lookup among countries"""

    _data = None
    _id_map = None
    _alpha2_map = None
    _alpha3_map = None
    _name_map = None
    _slug_map = None

    @classmethod
    def _load(cls):
        if cls._data is None:
            path = Path(__file__).parent / "json" / "countries.json"
            with open(path) as f:
                cls._data = json.load(f)

            # Build lookup maps
            cls._id_map = {c["id"]: c for c in cls._data}
            cls._alpha2_map = {c["alpha2"]: c for c in cls._data if c.get("alpha2")}
            cls._alpha3_map = {c["alpha3"]: c for c in cls._data if c.get("alpha3")}
            cls._name_map = {c["name"]: c for c in cls._data}
            cls._slug_map = {c["slug"]: c for c in cls._data if c.get("slug")}

    @classmethod
    def all(cls):
        cls._load()
        return cls._data

    @classmethod
    def get_by_id(cls, country_id):
        cls._load()
        return cls._id_map.get(country_id)

    @classmethod
    def get_by_alpha2(cls, alpha2):
        cls._load()
        return cls._alpha2_map.get(alpha2)

    @classmethod
    def get_by_alpha3(cls, alpha3):
        cls._load()
        return cls._alpha3_map.get(alpha3)

    @classmethod
    def get_by_name(cls, name):
        cls._load()
        return cls._name_map.get(name)

    @classmethod
    def get_by_slug(cls, slug):
        cls._load()
        return cls._slug_map.get(slug)
