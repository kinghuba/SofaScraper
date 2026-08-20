import logging
from datetime import UTC, datetime
from typing import Any

from sofascraper.utils.position_handler import get_player_position
from sofascraper.utils.country_registry import CountryRegistry
from sofascraper.utils.dataclasses.football_data_classes import (
    BaseEvent,
    Block,
    Commentary,
    Coordinate,
    Coordinates,
    Country,
    CupTree,
    CupTreeRound,
    Event,
    Incident,
    LineupPlayer,
    Lineups,
    Manager,
    Managers,
    MarketValue,
    MatchData,
    MissingPlayer,
    Momentum,
    MomentumElement,
    Odds,
    OddsChoices,
    Participant,
    Player,
    Promotion,
    Referee,
    Round,
    Row,
    Score,
    Season,
    Shotmap,
    Standings,
    StatisticGroup,
    StatisticItem,
    StatisticsPeriod,
    Status,
    Team,
    TieBreakingRule,
    TimeInfo,
    Tournament,
    Venue,
)
from sofascraper.utils.utils import fractional_to_all_odds, to_snake_case

#! Football Constants

FOOTBALL_INCIDENT_TYPES = {
    "goal": "goal",
    "card": "card",
    "substitution": "substitution",
    "injuryTime": "injury_time",
    "varDecision": "var",
}

# Map for possibly accidents and their player names
SOFASCORE_INCIDENT_TYPE_MAP = {
    "goal": ["player", "assist1"],
    "substitution": ["playerIn", "playerOut"],
}

# Local version of player
PLAYER_INCIDENT_TYPE_MAP = {
    "player": "goal_scorer",
    "assist1": "assist",
    "playerIn": "player_in",
    "playerOut": "player_out",
}


class FootballParser:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse_event(self, event: dict) -> BaseEvent | None:
        """
        Args:
            event: Dictinary of whole main event.

        Return:
            BaseEvent: Parsed event with base level of details.
        """

        if "id" not in event:
            self.logger.warning("Event missing 'id'")
            return None

        start_time_stamp = event.get("startTimestamp", "")
        match_date = datetime.fromtimestamp(start_time_stamp, tz=UTC) if start_time_stamp else None

        teams = self._parse_teams(event)
        home_team = teams[0] if teams else None
        away_team = teams[1] if teams else None

        if not home_team or not away_team:
            self.logger.warning(f"Event {event.get('id')}: missing teams")

        tournament = event.get("tournament", {})
        unique_tournament = tournament.get("uniqueTournament", {})
        round_info = event.get("roundInfo", {})

        category = tournament.get("category", {})

        season_data = event.get("season", {})
        season = self._parse_season(season_data, unique_tournament)

        home_score = self._parse_score(event.get("homeScore", {}))
        away_score = self._parse_score(event.get("awayScore", {}))

        time_data = event.get("time", {})
        time = self._parse_time(time_data)

        try:
            return BaseEvent(
                id=event["id"],
                slug=event.get("slug", ""),
                custom_id=event.get("customId"),
                status=Status(**event.get("status", {})),
                winner_code=event.get("winnerCode"),
                date=match_date,
                season=season,
                tournament=Tournament(
                    id=unique_tournament.get("id"),
                    name=tournament.get("name"),
                    slug=tournament.get("slug"),
                    priority=tournament.get("priority"),
                    country=self._parse_country(category),
                ),
                aggregated_winner_code=event.get("aggregatedWinnerCode"),
                previous_leg_event=event.get("previousLegEventId"),
                round=Round(
                    round=round_info.get("round"),
                    round_name=round_info.get("name"),
                    slug=round_info.get("slug"),
                    cup_round_type=round_info.get("cupRoundType"),
                ),
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
                time=time,
            )
        except Exception as e:
            self.logger.error(f"Failed to parse event {event.get('id')}: {e}", exc_info=True)
            return None

    def _parse_time(self, time: dict[str, Any]) -> TimeInfo | None:
        """
        Args:
            time: Time section of main event.

        Returns:
            TimeInfo | None:  The parsed time information.
        """
        return TimeInfo(
            injuryTime1=time.get("injuryTime1", ""),
            injuryTime2=time.get("injuryTime2", ""),
            injuryTime3=time.get("injuryTime3", ""),
            injuryTime4=time.get("injuryTime4", ""),
        )

    def _parse_season(self, season: dict[str, Any], unique_tournament: dict[str, Any]) -> Season | None:
        """
        Args:
            season: Season section of main event.
            unique_tournament: Unique_tournament section of main event.

        Returns:
            Season | None: The parsed season information.
        """

        if not season.get("id"):
            return None

        return Season(
            id=season.get("id", ""),
            name=season.get("name", ""),
            year=season.get("year", ""),
            tournament_id=unique_tournament.get("id", ""),
        )

    def _getCountry(self, alpha2: str) -> int | None:
        """
        Args:
            alpha2: ALPHA2 string of the country. (e.g., DK)

        Returns:
            int: The id of the country from the countries ALPHA2 attribute.
        """
        result = CountryRegistry.get_by_alpha2(alpha2)
        return result.id if result else None

    def _parse_tournament(self, tournament: dict[str, Any], unique_tournament: dict[str, Any]) -> Tournament | None:
        """
        Args:
            tournament: Tournament section of main event.
            unique_tournament: Unique tournament section of main event.

        Returns:
            Tournament | None: The parsed tournament information.
        """

        if not tournament or not unique_tournament:
            self.logger.warning("No data tournament data found")
            return

        category = tournament.get("category", {})
        country = self._parse_country(category)

        return Tournament(
            id=unique_tournament.get("id", ""),
            name=unique_tournament.get("name", ""),
            slug=tournament.get("slug", ""),
            priority=tournament.get("priority", ""),
            country=country if country else None,
        )

    def _parse_teams(self, event: dict[str, Any]) -> list[Team]:
        """
        Args:
            event: Dictinary of whole main event.

        Returns:
            list[Team]: The list of parsed team information.
        """
        teams = []

        for side in ("homeTeam", "awayTeam"):
            team = event.get(side, {})
            if not team.get("id"):
                self.logger.warning(f"Skipping team with missing id: {team}")
                continue

            country = team.get("country", {}).get("alpha2", "")
            country_id = self._getCountry(country)

            teams.append(
                Team(
                    id=team["id"],
                    name=team.get("name", ""),
                    short_name=team.get("shortName"),
                    name_code=team.get("nameCode", ""),
                    slug=team.get("slug", ""),
                    country_id=country_id,
                    is_national=bool(team.get("national", False)),
                )
            )

        return teams

    def _parse_player(self, player: dict[str, Any]) -> Player:
        """
        Args:
            player: Dictinary of player.

        Returns:
            Player | None: The parsed player information.
        """

        country = player.get("country", {})
        country_id = self._getCountry(country.get("alpha2", "")) if country else None

        date_of_birth = None
        time_stamp = player.get("dateOfBirthTimestamp", "")
        if time_stamp:
            try:
                date_of_birth = datetime.fromtimestamp(time_stamp, tz=UTC).date()
            except Exception as e:
                self.logger.warning(f"Invalid birth date timestamp for {player.get("id")}: {time_stamp} (error: {e})")

        return Player(
            id=player.get("id", ""),
            slug=player.get("slug", ""),
            name=player.get("name", ""),
            short_name=player.get("shortName") or player.get("name", ""),
            country_id=country_id,
            position=player.get("position", ""),
            height=player.get("height", ""),
            date_of_birth=date_of_birth,
            shirt_number=player.get("jerseyNumber", ""),
            proposed_market_value=MarketValue(
                value=player.get("proposedMarketValueRaw", {}).get("value", ""),
                currency=player.get("proposedMarketValueRaw", {}).get("currency", ""),
            ),
        )

    def _parse_multi_player_incidents(self, incident: dict[str, Any], incident_type: str) -> Incident | None:
        """
        Args:
            incidents: Raw incident instance.
            incident_type: Type of the incident as a string.

        Returns:
            Incident: Parsed incident, where multiple players are embedded within.
        """

        parsed = Incident(
            id=incident.get("id", ""),
            time=incident.get("time"),
            added_time=incident.get("addedTime", None),
            injury=incident.get("injury"),
            is_home=incident.get("isHome"),
            incident_class=incident.get("incidentClass"),
            incident_type=SOFASCORE_INCIDENT_TYPE_MAP[incident_type],
        )

        for key in SOFASCORE_INCIDENT_TYPE_MAP[incident_type]:
            player = incident.get(key, {})

            if not player:
                continue

            # Append parsed with player_name: player
            setattr(parsed, PLAYER_INCIDENT_TYPE_MAP[key], self._parse_player(player))

        return parsed

    def _parse_incidents(self, match_id: int, data: dict[str, Any]) -> list[Incident] | None:
        """
        Parse /incidents response.

        Args:
            match_id: Id of match parsed.
            data: Response from /incidents api endpoint.

        Returns:
            list[Incident]: List of parsed incidents.
        """

        # All incidents
        incidents_raw = data.get("incidents", {})
        incidents = incidents_raw if isinstance(incidents_raw, list) else incidents_raw.get("incidents", [])

        if not incidents:
            self.logger.warning(f"Match {match_id}: empty incidents response, skipping")
            return

        parsed: list[Incident] = []

        for incident in incidents:
            incident_type = incident.get("incidentType", "")

            # Parse and add accidents, where there are more players involved.
            if incident_type in ["substitution", "goal"]:
                parsed_incident = self._parse_multi_player_incidents(incident, incident_type)
                if parsed_incident:
                    parsed.append(parsed_incident)
                continue

            # Skip over time based periods, already have this data at this point.
            if incident_type in ["injuryTime", "period"]:
                continue

            # Add remaining incidents (cards).
            parsed.append(
                Incident(
                    player=self._parse_player(incident.get("player", {})),
                    id=incident.get("id"),
                    time=incident.get("time"),
                    added_time=incident.get("addedTime", None),
                    rescinded=incident.get("rescinded", False),
                    is_home=incident.get("isHome"),
                    incident_class=incident.get("incidentClass"),
                    incident_type=incident.get("incidentType"),
                )
            )

        self.logger.debug(f"Match {match_id}: {len(parsed)} incidents processed")

        return parsed

    def _parse_lineups(self, match_id: int, data: dict[str, Any]) -> Lineups | None:
        """
        Parse /lineups response.

        Args:
            match_id: Id of match parsed.
            data: Response from /lineups api endpoint.

        Returns:
            Lineups: Returns state of lineups, alongside formation, lineups and missing players.
        """

        # Lineups breaks the structure of the other responses, there is no lineup dict within.
        if not data or "home" not in data or "away" not in data:
            self.logger.debug(f"Match {match_id}: empty lineups response - skipping")
            return

        home_formation = data.get("home", {}).get("formation", "")
        away_formation = data.get("away", {}).get("formation", "")

        home_players = []
        away_players = []
        missing_players = []

        for side in ["home", "away"]:
            for index, player in enumerate(data.get(side, {}).get("players", [])):
                formation = home_formation if side == "home" else away_formation
                position = get_player_position(formation, index)
                player_info = self._parse_player(player.get("player", {}))
                if not player_info:
                    continue

                parsed = LineupPlayer(
                    player=player_info,
                    team=side,
                    shirt_number=player.get("jerseyNumber"),
                    position=player.get("position"),
                    position_title=position.get("position", ""),
                    position_side=position.get("side", None),
                    substitute=player.get("substitute", False),
                    statistics={},
                )

                # Loop over statistics for each player
                for key, value in player.get("statistics", {}).items():
                    if key == "statisticsType":
                        continue

                    # Create statistical element, only modify casing
                    parsed.statistics[to_snake_case(key)] = value

                if side == "home":
                    home_players.append(parsed)
                else:
                    away_players.append(parsed)

            # Loop over missing players similarly
            for player in data.get("missingPlayers", {}):
                missing_players.append(
                    MissingPlayer(
                        player=self._parse_player(player.get("player", {})),
                        team=side,
                        type=player.get("type"),
                        reason=player.get("reason"),
                        description=player.get("description"),
                        external_type=player.get("externalType"),
                        expected_end_date=player.get("expectedEndDate"),
                    )
                )

        return Lineups(
            confirmed=data.get("confirmed", False),
            home_formation=home_formation,
            home_players=home_players,
            away_formation=away_formation,
            away_players=away_players,
            missing_players=missing_players,
        )

    def _parse_managers(self, match_id, data) -> Managers | None:
        home_manager = data.get("homeManager", {})
        away_manager = data.get("awayManager", {})

        if not home_manager or not away_manager:
            self.logger.warning(f"Match {match_id}: no manager data found")
            return None

        return Managers(
            home_manager=Manager(
                id=home_manager.get("id"),
                name=home_manager.get("name"),
                slug=home_manager.get("slug"),
                short_name=home_manager.get("shortName"),
            ),
            away_manager=Manager(
                id=away_manager.get("id"),
                name=away_manager.get("name"),
                slug=away_manager.get("slug"),
                short_name=away_manager.get("shortName"),
            ),
        )

    def _parse_statistics(self, match_id: int, data: dict[str, Any]) -> list[StatisticsPeriod] | None:
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

        parsed: list[StatisticsPeriod] = []

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

    def _parse_detailed_event_information(self, match_id: int, data: dict[str, Any]) -> Event | None:
        """
        Parse /{match_id} response. Return a base event, with added details.

        Args:
            match_id: Id of match parsed.
            data: Response from /{match_id} api endpoint.
        """

        event = data.get("event", {})

        base_event = self.parse_event(event)

        if not base_event:
            self.logger.warning(f"Match {match_id}: failed to parse base event")
            return None

        referee = event.get("referee", {}) or {}
        if not referee:
            self.logger.warning(f"Referee data is missing for match_id: {match_id}")
        else:
            referee_country_id = self._getCountry(referee.get("country", {}).get("alpha2", ""))

        venue = event.get("venue", {}) or {}
        if not venue:
            self.logger.warning(f"Venue data is missing for match_id: {match_id}")
        else:
            venue_country_id = self._getCountry(venue.get("country", {}).get("alpha2", ""))

        coords = venue.get("venueCoordinates") or {}

        self.logger.debug(f"Match {match_id} detailed information successfully parsed.")

        return Event(
            **base_event.__dict__,
            referee=Referee(
                id=referee.get("id"),
                slug=referee.get("slug"),
                name=referee.get("name"),
                country_id=referee_country_id,
            )
            if referee
            else None,
            venue=Venue(
                id=venue.get("id"),
                slug=venue.get("slug"),
                name=venue.get("name"),
                country_id=venue_country_id,
                capacity=venue.get("capacity"),
                coordinates=Coordinates(lat=coords.get("latitude"), long=coords.get("longitude")),
            )
            if venue
            else None,
        )

    def _parse_score(self, score: dict[str, Any]) -> Score | None:
        """
        Args:
            score: Raw score instance.

        Returns:
            Score | None: Parsed score
        """

        if not score:
            self.logger.debug("Empty score object encountered")
            return None

        return Score(
            current=score.get("current", ""),
            display=score.get("display", ""),
            period1=score.get("period1", ""),
            period2=score.get("period2", ""),
            normaltime=score.get("normaltime", ""),
            extra1=score.get("extra1", None),
            extra2=score.get("extra2", None),
            overtime=score.get("overtime", None),
            penalties=score.get("penalties", None),
            aggregated=score.get("aggregated", None),
        )

    def _parse_odds(self, odds: dict[str, Any]) -> list[Odds] | None:
        """
        Args:
            odds: Raw odds instance.
        Returns:
            list[Odds] | odds: Parsed list of odds.
        """
        if not odds:
            return None

        results: list[Odds] = []
        featured = odds.get("featured")

        if not featured:
            return None

        for key in featured.keys():
            item = featured.get(key, {})

            choices = self._parse_odd_choices(item.get("choices", []))
            if not choices:
                continue

            results.append(
                Odds(
                    name=item.get("marketName", ""),
                    period=item.get("marketPeriod", ""),
                    group=item.get("marketGroup", ""),
                    choices=choices,
                )
            )

        return results

    def _parse_odd_choices(self, odd_choices: dict[Any, Any]) -> list[OddsChoices] | None:
        """
        Args:
            odd_choices: Raw odd choices instance.
        Returns:
            list[Odds] | odds: Parsed list of odds.
        """
        if not odd_choices:
            return None

        # Some values appear twice
        seen = set()
        unique_choices = []

        for choice in odd_choices:
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

    def _parse_momentum(self, momentum: dict[str, Any]) -> Momentum | None:
        """
        Args:
            momentum: Raw momentum instance.
        Returns:
            Momentum | None: Parsed momentum data.
        """
        if not momentum:
            return None

        results: list[MomentumElement] = []
        points = momentum.get("graphPoints", {})

        for element in points:
            results.append(MomentumElement(element.get("minute", None), element.get("value", None)))

        return Momentum(
            momentum=results
        )

    def _parse_country(self, category: dict[str, Any]) -> Country | None:
        """
        Args:
            category: Raw country instance.
        Returns:
            Country | None: Parsed country data.
        """
        if not category or not category.get("id"):
            return None

        country = category.get("country", {})

        return Country(
            id=category.get("id", ""),
            alpha2=country.get("alpha2", None),
            alpha3=country.get("alpha3", None),
            flag=category.get("flag", ""),
            name=country.get("name", None),
            slug=country.get("slug", None),
        )

    def _parse_shotmap(self, match_id: int, data: dict[str, Any]) -> list[Shotmap] | None:
        if not data:
            return None

        results: list[Shotmap] = []
        incidents = data.get("shotmap", {})

        for incident in incidents:
            player = self._parse_player(incident.get("player", {}))
            goalkeeper = self._parse_player(incident.get("goalkeeper", {}))
            goal_mouth_coordinates = self._parse_coordinate(incident.get("goalMouthCoordinates", None))
            block_coordinates = self._parse_coordinate(incident.get("blockCoordinates", None))
            player_coordinates = self._parse_coordinate(incident.get("playerCoordinates", None))

            results.append(
                Shotmap(
                    player=player,
                    is_home=incident.get("isHome", None),
                    shot_type=incident.get("shotType", None),
                    situation=incident.get("situation", None),
                    player_coordinates=player_coordinates,
                    body_part=incident.get("bodyPart", None),
                    goal_mouth_location=incident.get("goalMouthLocation", None),
                    goal_mouth_coordinates=goal_mouth_coordinates,
                    block_coordinates=block_coordinates,
                    xg=incident.get("xg", None),
                    xgot=incident.get("xgot", None),
                    goalkeeper=goalkeeper,
                    time=incident.get("time", None),
                    added_time=incident.get("addedTime", None),
                )
            )

        self.logger.debug(f"Match {match_id} shotmap information successfully parsed.")
        return results

    def _parse_coordinate(self, coordinates) -> Coordinate | None:
        if not coordinates:
            return None

        return Coordinate(
            x=coordinates.get("x", ""),
            y=coordinates.get("y", ""),
            z=coordinates.get("z", ""),
        )

    def _parse_comments(self, match_id, data) -> list[Commentary] | None:
        if not data:
            return None
        results: list[Commentary] = []

        for commentary in data.get("comments", {}):
            results.append(
                Commentary(
                    id=commentary.get("id"),
                    type=commentary.get("type"),
                    text=commentary.get("text"),
                    period_name=commentary.get("periodName", None),
                    time=commentary.get("time", None),
                )
            )
        self.logger.debug(f"Match {match_id} commentary successfully parsed.")
        return results

    def _parse_participant(self, participant: dict) -> Participant | None:
        """
        Args:
            participant: Dictionary of a single participant entry within a block.

        Returns:
            Participant: The parsed participant information.
        """

        if not participant:
            self.logger.warning("No participant data found")
            return

        team = participant.get("team", {})

        return Participant(
            team_id=team.get("id", ""),
            winner=participant.get("winner", ""),
            order=participant.get("order", ""),
            id=participant.get("id", ""),
            source_block_id=participant.get("sourceBlockId", None)
        )


    def _parse_block(self, block: dict) -> Block | None:
        """
        Args:
            block: Dictionary of a single block within a round.

        Returns:
            Block: The parsed block information.
        """

        if not block:
            self.logger.warning("No block data found")
            return

        participants = [
            self._parse_participant(participant)
            for participant in block.get("participants", [])
        ]

        return Block(
            event_in_progress=block.get("eventInProgress", False),
            finished=block.get("finished", ""),
            matches_in_round=block.get("matchesInRound", ""),
            order=block.get("order", ""),
            result=block.get("result", None),
            home_team_score=block.get("homeTeamScore", None),
            away_team_score=block.get("awayTeamScore", None),
            participants=participants,
            has_next_round_link=block.get("hasNextRoundLink", None),
            id=block.get("id", ""),
            events=block.get("events", []),
            block_id=block.get("blockId", ""),
            series_start_date_timestamp=block.get("seriesStartDateTimestamp", None),
            automatic_progression=block.get("automaticProgression", None),
        )


    def _parse_round(self, round_: dict) -> CupTreeRound | None:
        """
        Args:
            round_: Dictionary of a single round within a cup tree.

        Returns:
            Round: The parsed round information.
        """

        if not round_:
            self.logger.warning("No round data found")
            return

        blocks = [self._parse_block(block) for block in round_.get("blocks", [])]

        return CupTreeRound(
            id=round_.get("id", ""),
            order=round_.get("order", ""),
            type=round_.get("type", ""),
            description=round_.get("description", ""),
            blocks=blocks,
        )


    def _parse_cup_tree(self, data: dict, season_id: int | None) -> list[CupTree] | None:
        """
        Args:
            data: Dictionary of the cup tree section of the main event.
            season_id: The id of the season this cup tree belongs to.

        Returns:
            list[CupTree]: The parsed cup tree information.
        """

        if not data or not season_id:
            return None

        results: list[CupTree] = []
        cupTrees = data.get("cupTrees")

        if not cupTrees:
            return None

        for i in range(len(cupTrees)):
            item = cupTrees[i]

            tournament = item.get("tournament", {})
            unique_tournament = tournament.get("uniqueTournament", {})

            rounds = [self._parse_round(round_) for round_ in item.get("rounds", [])]
            results.append(CupTree(
                id=item.get("id", ""),
                name=item.get("name", ""),
                tournament_id=unique_tournament.get("id", ""),
                season_id=season_id,
                current_round=item.get("currentRound", ""),
                rounds=rounds,
                type=item.get("type", "")
            ))

        return results

    def _parse_tie_breaking_rule(self, tie_breaking_rule: dict) -> TieBreakingRule | None:
        """
        Args:
            tie_breaking_rule: Dictionary of the tie breaking rule section of a standings entry.
    
        Returns:
            TieBreakingRule: The parsed tie breaking rule information.
        """
    
        if not tie_breaking_rule:
            return None
    
        return TieBreakingRule(
            id=tie_breaking_rule.get("id", ""),
            text=tie_breaking_rule.get("text", ""),
        )
    
    
    def _parse_promotion(self, promotion: dict) -> Promotion | None:
        """
        Args:
            promotion: Dictionary of the promotion section of a standings row.
    
        Returns:
            Promotion: The parsed promotion information.
        """
    
        if not promotion:
            return None
    
        return Promotion(
            id=promotion.get("id", ""),
            text=promotion.get("text", ""),
        )
    
    
    def _parse_row(self, row: dict) -> Row | None:
        """
        Args:
            row: Dictionary of a single row within a standings entry.
    
        Returns:
            Row: The parsed row information.
        """
    
        if not row:
            return None
    
        team = row.get("team", {})
    
        return Row(
            id=row.get("id", ""),
            team_id=team.get("id", ""),
            descriptions=row.get("descriptions", []),
            promotion=self._parse_promotion(row.get("promotion", {})),
            position=row.get("position", ""),
            matches=row.get("matches", ""),
            wins=row.get("wins", ""),
            losses=row.get("losses", ""),
            draws=row.get("draws", ""),
            scores_for=row.get("scoresFor", ""),
            scores_against=row.get("scoresAgainst", ""),
            points=row.get("points", ""),
        )
    
    
    def _parse_standings(self, data: dict, season_id: int | None) -> list[Standings] | None:
        """
        Args:
            data: Dictionary of the main event containing the standings section.
    
        Returns:
            list[Standings]: The parsed standings information.
        """
    
        if not data or not season_id:
            return None
    
        results: list[Standings] = []
        standings = data.get("standings")
    
        if not standings:
            return None
    
        for i in range(len(standings)):
            item = standings[i]
    
            tournament = item.get("tournament", {})
            unique_tournament = tournament.get("uniqueTournament", {})
    
            rows = [self._parse_row(row) for row in item.get("rows", [])]
    
            results.append(Standings(
                id=item.get("id", ""),
                type=item.get("type", ""),
                tournament_id=unique_tournament.get("id", ""),
                season_id=season_id,
                name=item.get("name", ""),
                descriptions=item.get("descriptions", []),
                tie_breaking_rule=self._parse_tie_breaking_rule(item.get("tieBreakingRule", {})),
                rows=rows,
            ))
    
        return results

    def parse_match(self, match_id: int, match_url: str, raw: dict) -> MatchData | None:

        base = self._parse_detailed_event_information(match_id, raw.get("", {}))

        if not base:
            self.logger.error(f"Match {match_id}: base is None - aborting")
            return None

        # TODO: Map the different status codes

        # If the match is finished run everything, otherwise just base
        if base.status.code == 100:
            incidents = self._parse_incidents(match_id, raw.get("incidents", {}))
            statistics = self._parse_statistics(match_id, raw.get("statistics", {}))
            lineups = self._parse_lineups(match_id, raw.get("lineups", {}))
            shotmap = self._parse_shotmap(match_id, raw.get("shotmap", {}))
            momentum = self._parse_momentum(raw.get("graph", {}))
            odds = self._parse_odds(raw.get("odds/1/featured", {}))
            managers = self._parse_managers(match_id, raw.get("managers", {}))
            commentary = self._parse_comments(match_id, raw.get("comments", {}))
            cup_trees = self._parse_cup_tree(raw.get("knockout", {}), base.season.id if base.season else None)
            standings_total = self._parse_standings(raw.get("standings/total", {}), base.season.id if base.season else None)
            standings_home = self._parse_standings(raw.get("standings/home", {}), base.season.id if base.season else None)
            standings_away = self._parse_standings(raw.get("standings/away", {}), base.season.id if base.season else None)
        else:
            self.logger.debug(f"Match {match_id} not finished yet, only base information available.")
            incidents = statistics = lineups = shotmap = momentum = odds = managers = commentary = cupTree = None


        self.logger.debug(f"Match {match_id} successfully parsed.")

        return MatchData(
            match_id=match_id,
            match_url=match_url,
            base=base,
            statistics=statistics,
            incidents=incidents,
            lineups=lineups,
            odds=odds,
            shotmap=shotmap,
            momentum=momentum,
            managers=managers,
            commentary=commentary,
            cup_trees=cup_trees,
            standings_total=standings_total,
            standings_home=standings_home,
            standings_away=standings_away
        )