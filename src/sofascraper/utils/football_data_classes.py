from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List, Dict, Any


# Core shared models


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


@dataclass
class Tournament:
    id: int
    name: str
    slug: str
    priority: int


@dataclass
class Round:
    round: Optional[int]
    round_name: Optional[str]
    slug: Optional[str]
    cup_round_type: Optional[int]


@dataclass
class Team:
    id: int
    name: str
    short_name: Optional[str]
    name_code: str
    slug: str
    country_id: Optional[int]
    is_national: bool


@dataclass
class Score:
    current: Optional[int]
    display: Optional[int]
    period1: Optional[int]
    period2: Optional[int]
    normaltime: Optional[int]


@dataclass
class TimeInfo:
    injuryTime1: Optional[int]
    injuryTime2: Optional[int]


# Extended event details


@dataclass
class Referee:
    id: Optional[int]
    slug: Optional[str]
    name: Optional[str]
    country_id: Optional[int]


@dataclass
class Coordinates:
    lat: Optional[float]
    long: Optional[float]


@dataclass
class Venue:
    id: Optional[int]
    slug: Optional[str]
    name: Optional[str]
    country_id: Optional[int]
    capacity: Optional[int]
    coordinates: Coordinates


# Base Event


@dataclass
class BaseEvent:
    id: int
    slug: str
    custom_id: Optional[str]
    status: Status
    winner_code: Optional[int]
    date: datetime
    season: Season
    tournament: Tournament
    aggregated_winner_code: Optional[int]
    previous_leg_event: Optional[int]
    round: Round
    home_team: Team
    away_team: Team
    home_score: Optional[Score]
    away_score: Optional[Score]
    time: Optional[TimeInfo]


# Extended Event (base + extras)


@dataclass
class Event(BaseEvent):
    referee: Optional[Referee]
    venue: Optional[Venue]


# Player & Incidents


@dataclass
class MarketValue:
    value: Optional[int]
    currency: Optional[str]


@dataclass
class Player:
    id: int
    slug: str
    name: str
    short_name: str
    country_id: Optional[int]
    position: Optional[str]
    height: Optional[int]
    date_of_birth: Optional[date]
    shirt_number: Optional[str]
    proposed_market_value: MarketValue


@dataclass
class Incident:
    id: int
    time: Optional[int]
    added_time: Optional[int]
    is_home: Optional[bool]
    incident_class: Optional[str]
    incident_type: Any  # str | list[str]
    player: Optional[Player] = None
    player_in: Optional[Player] = None
    player_out: Optional[Player] = None
    goal_scorer: Optional[Player] = None
    assist: Optional[Player] = None
    rescinded: Optional[bool] = None
    injury: Optional[bool] = None


# Statistics


@dataclass
class StatisticItem:
    name: str
    home_value: Optional[float]
    away_value: Optional[float]
    statistics_type: str
    key: str


@dataclass
class StatisticGroup:
    group_name: str
    statistics: List[StatisticItem]


@dataclass
class StatisticsPeriod:
    period: str
    groups: List[StatisticGroup]


# Lineups


@dataclass
class PlayerStatistics:
    stats: Dict[str, Any]


@dataclass
class LineupPlayer:
    player: Player
    team_id: int
    shirt_number: Optional[str]
    position: Optional[str]
    substitute: bool
    statistics: Dict[str, Any]


@dataclass
class MissingPlayer:
    player: Player
    type: Optional[str]
    reason: Optional[str]
    description: Optional[str]
    external_type: Optional[str]
    expected_end_date: Optional[str]


@dataclass
class Lineups:
    confirmed: bool
    home_formation: str
    home_players: List[LineupPlayer]
    away_formation: str
    away_players: List[LineupPlayer]
    missing_players: List[MissingPlayer]


# Root response


@dataclass
class MatchData:
    match_id: Optional[int]
    match_url: Optional[str]
    base: Event
    statistics: List[StatisticsPeriod]
    incidents: List[Incident]
    lineups: Lineups

    @property
    def fully_captured(self) -> bool:
        """True when all four endpoints were successfully captured."""
        return all([self.base, self.statistics, self.incidents, self.lineups])
