from dataclasses import dataclass
from datetime import date, datetime

# Core shared models


@dataclass
class MarketValue:
    value: int | None
    currency: str | None


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
    ground_type: str
    tennis_points: int
    flag: str


@dataclass
class Round:
    round: int | None
    round_name: str | None
    slug: str | None


@dataclass
class PlayerTeamInfo:
    residence: str
    place_of_birth: str
    height: float
    weight: int
    plays: str
    date_of_birth: date | None
    prize_current_raw: MarketValue
    prize_total_raw: MarketValue


@dataclass
class Team:
    id: int
    name: str
    short_name: str | None
    gender: str
    name_code: str
    slug: str
    ranking: str
    country_id: int | None
    player_info: PlayerTeamInfo | None


@dataclass
class Score:
    current: int | None
    display: int | None
    period1: int | None
    period2: int | None
    period3: int | None
    period4: int | None
    period5: int | None
    period1_tie_break: int | None
    period2_tie_break: int | None
    period3_tie_break: int | None
    period4_tie_break: int | None
    period5_tie_break: int | None
    normaltime: int | None


@dataclass
class TimeInfo:
    period1: int | None
    period2: int | None
    period3: int | None
    period4: int | None
    period5: int | None


@dataclass
class Venue:
    id: int | None
    slug: str | None
    name: str | None
    country_id: int | None
    city: str | None
    stadium: str | None


# Base Event


@dataclass
class Event:
    id: int
    slug: str
    custom_id: str | None
    status: Status
    winner_code: int | None
    date: datetime
    season: Season
    tournament: Tournament
    round: Round
    home_team: Team
    away_team: Team
    home_team_seed: str
    away_team_seed: str
    first_to_serve: int
    home_score: Score | None
    away_score: Score | None
    time: TimeInfo | None
    venue: Venue | None


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


# Momentum


@dataclass
class MomentumElement:
    set: int
    game: int
    value: int
    break_occurred: bool


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


# Incidents


@dataclass
class IncidentScore:
    home_score: int
    away_score: int
    serving: int
    scoring: int


@dataclass
class IncidentPoints:
    home_point: str
    away_point: str
    point_description: int
    home_point_type: int
    away_point_type: int


@dataclass
class Incident:
    set: int
    game: int
    points: list[IncidentPoints]
    score: IncidentScore


# Rankings


@dataclass
class Ranking:
    player_id: int
    tournaments_played: int | None
    ranking: int | None
    points: int | None
    previous_ranking: int | None
    previous_points: int | None
    best_ranking: int | None
    ranking_class: str
    id: int


# Root response


@dataclass
class MatchData:
    match_id: int | None
    match_url: str | None
    base: Event
    statistics: list[StatisticsPeriod] | None
    incidents: list[Incident] | None
    odds: list[Odds] | None
    momentum: Momentum | None
    rankings: list[Ranking] | None

    @property
    def fully_captured(self) -> bool:
        """True when all endpoints were successfully captured."""
        return all([self.base, self.statistics, self.momentum, self.odds, self.incidents, self.rankings])
