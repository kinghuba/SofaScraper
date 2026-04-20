from enum import Enum


class CommandEnum(str, Enum):
    MATCHES = "matches"
    DATES = "dates"
    TOURNAMENTS = "tournaments"


class Sport(Enum):
    """Supported sports.

    Currently only football and tennis is supported.
    """

    FOOTBALL = "football"
    TENNIS = "tennis"
