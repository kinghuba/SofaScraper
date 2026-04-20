import logging
from datetime import UTC, datetime
from typing import Any

import tzlocal

from sofascraper.utils.country_registry import CountryRegistry
from sofascraper.utils.dataclasses.tennis_data_classes import (
    Event,
    Incident,
    IncidentPoints,
    IncidentScore,
    MarketValue,
    MatchData,
    Momentum,
    MomentumElement,
    Odds,
    OddsChoices,
    PlayerTeamInfo,
    Ranking,
    Round,
    Score,
    Season,
    StatisticGroup,
    StatisticItem,
    StatisticsPeriod,
    Status,
    Team,
    TimeInfo,
    Tournament,
    Venue,
)
from sofascraper.utils.utils import fractional_to_all_odds, to_snake_case


class TennisParser:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse_event(self, event: dict) -> Event | None:
        """
        Args:
            event: Dictinary of whole main event.

        Return:
            BaseEvent: Parsed event with base level of details.
        """

        if "id" not in event:
            self.logger.warning("Event missing 'id'")
            return None

        start_time_stamp = event.get("startTimestamp")
        match_date = datetime.fromtimestamp(start_time_stamp, tz=tzlocal.get_localzone()) if start_time_stamp else None

        teams = self._parse_teams(event)
        home_team = teams[0] if teams else None
        away_team = teams[1] if teams else None

        if not home_team or not away_team:
            self.logger.warning(f"Event {event.get('id')}: missing teams")

        tournament_data = event.get("tournament", {})
        unique_tournament_data = tournament_data.get("uniqueTournament", {})
        tournament = self._parse_tournament(tournament=tournament_data, unique_tournament=unique_tournament_data)
        round_info = event.get("roundInfo", {})

        season_data = event.get("season") or {}
        season = self._parse_season(season_data, unique_tournament_data)

        home_score = self._parse_score(event.get("homeScore", {}))
        away_score = self._parse_score(event.get("awayScore", {}))

        time_data = event.get("time")
        time = self._parse_time(time_data)

        venue = event.get("venue", {})
        if not venue:
            self.logger.warning("Venue data is missing")
        else:
            venue_country_id = self._getCountry(venue.get("country").get("alpha2", ""))

        try:
            return Event(
                id=event["id"],
                slug=event.get("slug", ""),
                custom_id=event.get("customId"),
                status=Status(**event.get("status", {})),
                winner_code=event.get("winnerCode"),
                date=match_date,
                season=season,
                tournament=tournament,
                round=Round(
                    round=round_info.get("round"),
                    round_name=round_info.get("name"),
                    slug=round_info.get("slug"),
                ),
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
                time=time,
                venue=Venue(
                    id=venue.get("id"),
                    slug=venue.get("slug"),
                    name=venue.get("name"),
                    country_id=venue_country_id,
                    city=venue.get("city", {}).get("name", ""),
                    stadium=venue.get("stadium", {}).get("name", ""),
                )
                if venue
                else None,
                first_to_serve=event.get("firstToServe", ""),
                home_team_seed=event.get("homeTeamSeed", ""),
                away_team_seed=event.get("awayTeamSeed", ""),
            )
        except Exception as e:
            self.logger.error(f"Failed to parse event {event.get('id')}: {e}", exc_info=True)
            return None

    def _parse_time(self, time) -> TimeInfo | None:
        """
        Args:
            season: Dictinary of time section of main event.

        Returns:
            TimeInfo:  The parsed time information.
        """
        return TimeInfo(
            period1=time.get("period1", None),
            period2=time.get("period2", None),
            period3=time.get("period3", None),
            period4=time.get("period4", None),
            period5=time.get("period5", None),
        )

    def _parse_season(self, season, unique_tournament) -> Season | None:
        """
        Args:
            season: Dictinary of season section of main event.
            unique_tournament: Dictinary of unique_tournament section of main event.

        Returns:
            Season:  The parsed season information.
        """

        if not season.get("id"):
            return

        return Season(
            id=season.get("id", ""),
            name=season.get("name", ""),
            year=season.get("year", ""),
            tournament_id=unique_tournament.get("id", ""),
        )

    def _getCountry(self, alpha2: str) -> int | None:
        """
        Args:
            alpha2: Alpha2 string of the country. (e.g., DK)

        Returns:
            int: The id of the country from the countries alpha2 attribute.
        """
        result = CountryRegistry.get_by_alpha2(alpha2)
        return result.get("id") if result else None

    def _parse_tournament(self, tournament: dict, unique_tournament: dict) -> Tournament | None:
        """
        Args:
            tournament: Dictinary of tournament section of main event.
            unique_tournament: Dictinary of unique_tournament section of main event.

        Returns:
            Tournament:  The parsed tournament information.
        """

        if not tournament or not unique_tournament:
            self.logger.warning("No data tournament data found")
            return

        return Tournament(
            id=unique_tournament.get("id", ""),
            name=unique_tournament.get("name", ""),
            slug=unique_tournament.get("slug", ""),
            priority=tournament.get("priority", ""),
            flag=tournament.get("category", {}).get("flag", ""),
            ground_type=unique_tournament.get("groundType", ""),
            tennis_points=unique_tournament.get("tennisPoints", ""),
        )

    def _parse_teams(self, event: dict) -> list[Team]:
        """
        Args:
            event: Dictinary of whole main event.

        Returns:
            list[Team]:  The list of parsed team information.
        """

        teams = []

        for side in ("homeTeam", "awayTeam"):
            team = event.get(side, {})
            if not team.get("id"):
                self.logger.warning(f"Skipping team with missing id: {team}")
                continue

            country = team.get("country", {}).get("alpha2", "")
            country_id = self._getCountry(country)

            player_info = team.get("playerTeamInfo", {})

            date_of_birth = None
            time_stamp = player_info.get("birthDateTimestamp")
            if time_stamp:
                try:
                    date_of_birth = datetime.fromtimestamp(time_stamp, tz=UTC).date()
                except Exception as e:
                    self.logger.warning(f"Invalid birthDateTimestamp: {time_stamp} ({e})")

            teams.append(
                Team(
                    id=team["id"],
                    name=team.get("name", ""),
                    short_name=team.get("shortName"),
                    gender=team.get("gender"),
                    name_code=team.get("nameCode", ""),
                    slug=team.get("slug", ""),
                    ranking=team.get("ranking"),
                    country_id=country_id,
                    player_info=PlayerTeamInfo(
                        residence=player_info.get("residence"),
                        place_of_birth=player_info.get("birthplace"),
                        height=player_info.get("height"),
                        weight=player_info.get("weight"),
                        plays=player_info.get("plays"),
                        date_of_birth=date_of_birth,
                        prize_current_raw=MarketValue(
                            value=player_info.get("prizeCurrentRaw", {}).get("value"),
                            currency=player_info.get("prizeCurrentRaw", {}).get("currency"),
                        ),
                        prize_total_raw=MarketValue(
                            value=player_info.get("prizeTotalRaw", {}).get("value"),
                            currency=player_info.get("prizeTotalRaw", {}).get("currency"),
                        ),
                    ),
                )
            )

        return teams

    def _parse_incidents(self, match_id: int, data: dict[str, Any]) -> list[Incident] | None:
        """
        Args:
            match_id: Id of match parsed.
            data:

        Returns:
            list[Incident]: List of parsed incidents.
        """
        if not data["pointByPoint"]:
            self.logger.warning(f"Match {match_id}: empty incidents response, skipping")
            return None

        incidents = []

        for set_data in data["pointByPoint"]:
            set_number = set_data["set"]

            for game_data in set_data["games"]:
                game_number = game_data["game"]

                # Parse points
                points = [
                    IncidentPoints(
                        home_point=p["homePoint"],
                        away_point=p["awayPoint"],
                        point_description=p["pointDescription"],
                        home_point_type=p["homePointType"],
                        away_point_type=p["awayPointType"],
                    )
                    for p in game_data["points"]
                ]

                # Parse score
                score_data = game_data["score"]
                score = IncidentScore(
                    home_score=score_data["homeScore"],
                    away_score=score_data["awayScore"],
                    serving=score_data["serving"],
                    scoring=score_data["scoring"],
                )

                # Build Incident
                incident = Incident(
                    set=set_number,
                    game=game_number,
                    points=points,
                    score=score,
                )

                incidents.append(incident)

        self.logger.debug(f"Match {match_id}: {len(incidents)} incidents processed")

        return incidents

    def _parse_statistics(self, match_id: int, data: dict[str, Any]) -> list[StatisticItem] | None:
        """
        Parse /statistics response.

        Args:
            match_id: Id of match parsed.
            data: Response from /statistics api endpoint.
        """
        statistics = data.get("statistics", [])

        if not statistics:
            self.logger.warning(f"Match {match_id}: empty statistics response -- skipping")
            return

        parsed = []

        for period in statistics:
            groups = []

            for group in period.get("groups", []):
                grouped_statistics = []

                for statistic in group.get("statisticsItems", []):
                    grouped_statistics.append(
                        StatisticItem(
                            name=statistic.get("name"),
                            home_value=statistic.get("homeValue"),
                            away_value=statistic.get("awayValue"),
                            statistics_type=statistic.get("statisticsType"),
                            key=to_snake_case(statistic.get("key")),
                        )
                    )

                groups.append(StatisticGroup(group_name=group.get("groupName"), statistics=grouped_statistics))

            parsed.append(StatisticsPeriod(period=period.get("period"), groups=groups))

        self.logger.debug(f"Match {match_id}: statistics successfully parsed.")

        return parsed

    def _parse_score(self, score: dict) -> Score:

        if not score:
            self.logger.debug("Empty score object encountered")

        return Score(
            current=score.get("current"),
            display=score.get("display"),
            period1=score.get("period1"),
            period2=score.get("period2"),
            period3=score.get("period3"),
            period4=score.get("period4"),
            period5=score.get("period5"),
            period1_tie_break=score.get("period1TieBreak"),
            period2_tie_break=score.get("period2TieBreak"),
            period3_tie_break=score.get("period3TieBreak"),
            period4_tie_break=score.get("period4TieBreak"),
            period5_tie_break=score.get("period5TieBreak"),
            normaltime=score.get("normaltime"),
        )

    def _parse_odds(self, match_id: int, data: dict[str, Any]) -> list[Odds] | None:
        if not data:
            return None

        results: list[Odds] = []
        featured = data.get("featured")

        for key in featured.keys():
            item = featured.get(key, {})

            choices = self._parse_odds_choices(item.get("choices", []))

            results.append(
                Odds(
                    name=item.get("marketName", ""),
                    period=item.get("marketPeriod", ""),
                    group=item.get("marketGroup", ""),
                    choices=choices,
                )
            )

        self.logger.debug(f"Match {match_id} odds information successfully parsed.")
        return results

    def _parse_odds_choices(self, odds_choices) -> list[OddsChoices] | None:
        if not odds_choices:
            return None

        # Some values appear twice
        seen = set()
        unique_choices = []

        for choice in odds_choices:
            key = (
                choice.get("name"),
                choice.get("fractionalValue"),
            )

            if key not in seen:
                seen.add(key)
                unique_choices.append(choice)

        fractional_list = [choice.get("fractionalValue", "") for choice in unique_choices]

        converted = fractional_to_all_odds(fractional_list)

        results: list[OddsChoices] = []

        for choice, conv in zip(unique_choices, converted):
            results.append(
                OddsChoices(
                    name=choice.get("name", ""),
                    winning=choice.get("winning", False),
                    fractional=conv["fractional"],
                    decimal=conv["decimal"],
                    american=conv["american"],
                    implied_probability=conv["implied_probability"],
                    true_probability=conv.get("true_probability", 0.0),
                    true_decimal=conv.get("true_decimal_odds", 0.0),
                )
            )

        return results

    def _parse_momentum(self, match_id: int, data: dict[str, Any]) -> Momentum | None:
        if not data:
            return None

        results: list[MomentumElement] = []
        points = data.get("tennisPowerRankings", {})

        for element in points:
            results.append(
                MomentumElement(
                    element.get("set", None),
                    element.get("game", None),
                    element.get("value", None),
                    element.get("breakOccurred", None),
                )
            )

        self.logger.debug(f"Match {match_id} momentum information successfully parsed.")
        return results

    def _parse_rankings(
        self, match_id, home_team_id, home_team_rankings, away_team_id, away_team_rankings
    ) -> list[Ranking] | None:
        if not home_team_rankings or not away_team_rankings:
            return None
        results: list[Ranking] = []

        for ranking in home_team_rankings.get("rankings", {}):
            results.append(
                Ranking(
                    player_id=home_team_id,
                    tournaments_played=ranking.get("tournamentsPlayed", None),
                    ranking=ranking.get("ranking", None),
                    points=ranking.get("points", None),
                    previous_points=ranking.get("previousPoints", None),
                    previous_ranking=ranking.get("previousRanking", None),
                    best_ranking=ranking.get("bestRanking", None),
                    ranking_class=ranking.get("rankingClass", None),
                    id=ranking.get("id"),
                )
            )

        for ranking in away_team_rankings.get("rankings", {}):
            results.append(
                Ranking(
                    player_id=away_team_id,
                    tournaments_played=ranking.get("tournamentsPlayed", None),
                    ranking=ranking.get("ranking", None),
                    points=ranking.get("points", None),
                    previous_points=ranking.get("previousPoints", None),
                    previous_ranking=ranking.get("previousRanking", None),
                    best_ranking=ranking.get("bestRanking", None),
                    ranking_class=ranking.get("rankingClass", None),
                    id=ranking.get("id"),
                )
            )

        self.logger.debug(f"Match {match_id} ranking information successfully parsed.")
        return results

    def parse_match(self, match_id: str | None, match_url: str | None, raw: dict) -> MatchData:

        data = raw.get("", {}).get("event", {})

        if not data:
            self.logger.debug("Data is not from indivual match")
            data = raw

        base = self.parse_event(data)

        if not base:
            self.logger.error(f"Match {match_id}: base is None -- aborting")
            return None

        # rankings_{team_id}

        # TODO: Map the different status codes
        # If the match is finished run everything, otherwise just base
        if base.status.code != 0 or base.status.description != "inprogress":
            incidents = self._parse_incidents(match_id, raw.get("point-by-point", {}))
            statistics = self._parse_statistics(match_id, raw.get("statistics", {}))
            odds = self._parse_odds(match_id, raw.get("odds/1/featured", {}))
            momentum = self._parse_momentum(match_id=match_id, data=raw.get("tennis-power", {}))
            rankings = self._parse_rankings(
                match_id=match_id,
                home_team_id=base.home_team.id,
                home_team_rankings=raw.get(f"rankings-{base.home_team.id}", {}),
                away_team_id=base.away_team.id,
                away_team_rankings=raw.get(f"rankings-{base.away_team.id}", {}),
            )
        else:
            self.logger.debug(f"Match {match_id} not finished yet, only base information available.")
            incidents = statistics = momentum = odds = rankings = None

        self.logger.debug(f"Match {match_id} successfully parsed.")

        return MatchData(
            match_id=match_id,
            match_url=match_url,
            base=base,
            statistics=statistics,
            incidents=incidents,
            odds=odds,
            momentum=momentum,
            rankings=rankings,
        )
