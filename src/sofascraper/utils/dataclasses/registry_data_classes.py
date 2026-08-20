from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RegistrySeason:
    id: int
    year: str


@dataclass(frozen=True)
class RegistryTournament:
    id: int
    name: str
    slug: str
    priority: int
    sport: str
    country_id: Optional[int]
    seasons: list[RegistrySeason]


@dataclass(frozen=True)
class RegistryCountry:
    id: int
    alpha2: str
    alpha3: str
    flag: str
    name: str
    slug: str
