from enum import Enum


class CommandEnum(str, Enum):
    MATCHES = "matches"
    DATES = "dates"
    TOURNAMENTS = "tournaments"
    SEASONS = "seasons"


class Sport(Enum):
    """Supported sports.

    Currently only football is supported.
    # TODO: add tennis, basketball, etc. when scrapers are implemented.
    """

    FOOTBALL = "football"


class StorageFormat(Enum):
    JSON = "json"
    DB = "db"
