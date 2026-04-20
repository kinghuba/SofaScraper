from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

# Core shared models


@dataclass
class Country:
    id: int
    alpha2: str | None
    alpha3: str | None
    flag: str
    name: str | None
    slug: str | None


@dataclass
class Status:
    code: int
    description: str
    type: str


@dataclass
class Season:
    id: int
    name: str
    year: str
    tournament_id: int


@dataclass
class Tournament:
    id: int
    name: str
    slug: str
    priority: int
    country: Country


@dataclass
class Round:
    round: int | None
    round_name: str | None
    slug: str | None
    cup_round_type: int | None


@dataclass
class Team:
    id: int
    name: str
    short_name: str | None
    name_code: str
    slug: str
    country_id: int | None
    is_national: bool


@dataclass
class Score:
    current: int | None
    display: int | None
    period1: int | None
    period2: int | None
    normaltime: int | None
    extra1: int | None
    extra2: int | None
    overtime: int | None
    penalties: int | None
    aggregated: int | None


@dataclass
class TimeInfo:
    injuryTime1: int | None
    injuryTime2: int | None
    injuryTime3: int | None
    injuryTime4: int | None


# Extended event details


@dataclass
class Referee:
    id: int | None
    slug: str | None
    name: str | None
    country_id: int | None


@dataclass
class Coordinates:
    lat: float | None
    long: float | None


@dataclass
class Venue:
    id: int | None
    slug: str | None
    name: str | None
    country_id: int | None
    capacity: int | None
    coordinates: Coordinates


# Base Event


@dataclass
class BaseEvent:
    id: int
    slug: str
    custom_id: str | None
    status: Status
    winner_code: int | None
    date: datetime
    season: Season
    tournament: Tournament
    aggregated_winner_code: int | None
    previous_leg_event: int | None
    round: Round
    home_team: Team
    away_team: Team
    home_score: Score | None
    away_score: Score | None
    time: TimeInfo | None


# Extended Event (base + extras)


@dataclass
class Event(BaseEvent):
    referee: Referee | None
    venue: Venue | None


# Player & Incidents


@dataclass
class MarketValue:
    value: int | None
    currency: str | None


@dataclass
class Player:
    id: int
    slug: str
    name: str
    short_name: str
    country_id: int | None
    position: str | None
    height: int | None
    date_of_birth: date | None
    shirt_number: str | None
    proposed_market_value: MarketValue


@dataclass
class Incident:
    id: int
    time: int | None
    added_time: int | None
    is_home: bool | None
    incident_class: str | None
    incident_type: Any  # str | list[str]
    player: Player | None = None
    player_in: Player | None = None
    player_out: Player | None = None
    goal_scorer: Player | None = None
    assist: Player | None = None
    rescinded: bool | None = None
    injury: bool | None = None


# Statistics


@dataclass
class StatisticItem:
    name: str
    home_value: float | None
    away_value: float | None
    statistics_type: str
    key: str


@dataclass
class StatisticGroup:
    group_name: str
    statistics: list[StatisticItem]


@dataclass
class StatisticsPeriod:
    period: str
    groups: list[StatisticGroup]


# Lineups


@dataclass
class PlayerStatistics:
    stats: dict[str, Any]


@dataclass
class LineupPlayer:
    player: Player
    team_id: int
    shirt_number: str | None
    position: str | None
    substitute: bool
    statistics: dict[str, Any]


@dataclass
class MissingPlayer:
    player: Player
    type: str | None
    reason: str | None
    description: str | None
    external_type: str | None
    expected_end_date: str | None


@dataclass
class Lineups:
    confirmed: bool
    home_formation: str
    home_players: list[LineupPlayer]
    away_formation: str
    away_players: list[LineupPlayer]
    missing_players: list[MissingPlayer]


# Shotmap


@dataclass
class Coordinate:
    x: int
    y: int
    z: int


@dataclass
class Shotmap:
    player: Player
    is_home: bool
    shot_type: str | None
    situation: str | None
    player_coordinates: Coordinate | None
    body_part: str | None
    goal_mouth_location: str | None
    goal_mouth_coordinates: Coordinate | None
    block_coordinates: Coordinate | None
    xg: float | None
    xgot: float | None
    goalkeeper: Player
    time: int | None
    added_time: int | None


# Momentum


@dataclass
class MomentumElement:
    minute: int
    value: int


@dataclass
class Momentum:
    momentum: list[MomentumElement]


# Odds


@dataclass
class OddsChoices:
    name: str
    winning: bool
    fractional: str
    decimal: float
    american: int
    implied_probability: float
    true_probability: float
    true_decimal: float


@dataclass
class Odds:
    name: str
    period: str | None
    group: str | None
    choices: list[OddsChoices]


# Manager


@dataclass
class Manager:
    id: int
    name: str
    slug: str | None
    short_name: str | None


@dataclass
class Managers:
    home_manager: Manager
    away_manager: Manager


# Commentary


@dataclass
class Commentary:
    id: int
    type: str
    text: str
    period_name: str | None
    time: int | None


# Root response


@dataclass
class MatchData:
    match_id: int | None
    match_url: str | None
    base: Event
    statistics: list[StatisticsPeriod]
    incidents: list[Incident]
    lineups: Lineups
    shotmap: list[Shotmap] | None
    odds: list[Odds] | None
    momentum: Momentum | None
    managers: Managers | None
    commentary: list[Commentary] | None

    @property
    def fully_captured(self) -> bool:
        """True when all four endpoints were successfully captured."""
        return all(
            [
                self.base,
                self.statistics,
                self.incidents,
                self.lineups,
                self.momentum,
                self.shotmap,
                self.odds,
                self.managers,
                self.commentary,
            ]
        )
