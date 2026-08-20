import json
from pathlib import Path
from sofascraper.utils.dataclasses.registry_data_classes import RegistryCountry

class CountryRegistry:
    """Dynamic lookup among countries."""

    _data: list[RegistryCountry] | None = None
    _id_map: dict[int, RegistryCountry] = {}
    _alpha2_map: dict[str, RegistryCountry] = {}
    _alpha3_map: dict[str, RegistryCountry] = {}
    _name_map: dict[str, RegistryCountry] = {}
    _slug_map: dict[str, RegistryCountry] = {}

    @classmethod
    def _load(cls) -> None:
        if cls._data is not None:
            return

        path = Path(__file__).parent / "json" / "countries.json"

        with open(path, encoding="utf-8") as f:
            raw_data = json.load(f)

        cls._data = []

        for raw_country in raw_data:
            country = RegistryCountry(
                id=raw_country["id"],
                alpha2=raw_country["alpha2"],
                alpha3=raw_country["alpha3"],
                flag=raw_country["flag"],
                name=raw_country["name"],
                slug=raw_country["slug"],
            )

            cls._data.append(country)

            cls._id_map[country.id] = country
            cls._name_map[country.name] = country
            cls._slug_map[country.slug] = country

            if country.alpha2:
                cls._alpha2_map[country.alpha2] = country

            if country.alpha3:
                cls._alpha3_map[country.alpha3] = country

    @classmethod
    def all(cls) -> list[RegistryCountry]:
        cls._load()
        return cls._data or []

    @classmethod
    def get_by_id(cls, country_id: int) -> RegistryCountry | None:
        cls._load()
        return cls._id_map.get(country_id)

    @classmethod
    def get_by_alpha2(cls, alpha2: str) -> RegistryCountry | None:
        cls._load()
        return cls._alpha2_map.get(alpha2)

    @classmethod
    def get_by_alpha3(cls, alpha3: str) -> RegistryCountry | None:
        cls._load()
        return cls._alpha3_map.get(alpha3)

    @classmethod
    def get_by_name(cls, name: str) -> RegistryCountry | None:
        cls._load()
        return cls._name_map.get(name)

    @classmethod
    def get_by_slug(cls, slug: str) -> RegistryCountry | None:
        cls._load()
        return cls._slug_map.get(slug)