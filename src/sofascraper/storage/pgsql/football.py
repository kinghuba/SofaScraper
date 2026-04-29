"""
sofascraper/db/football_repository.py

Maps parsed football dataclasses to the football.* schema tables.

Entry point:
    await repo.save_match(conn, match_data, match_id, run_id)

Insert order (respects FK dependencies):
    football.teams
    football.players
    football.referees
    football.venues
    football.managers
    football.matches
    football.match_scores
    football.incidents
    football.lineups
    football.shot_events
    football.stat_definitions + football.team_match_stats
    football.match_odds
    football.match_momentum
    football.match_commentary
"""

from __future__ import annotations

import json
import logging

import asyncpg

from sofascraper.utils.dataclasses.football_data_classes import (
    Commentary,
    Incident,
    LineupPlayer,
    Manager,
    MatchData,
    MomentumElement,
    Odds,
    Player,
    Referee,
    Season,
    Shotmap,
    StatisticsPeriod,
    Team,
    TimeInfo,
    Tournament,
    Venue,
)


class FootballRepository:
    """Persists scraped football match data to PostgreSQL."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    # Public entry point

    async def save_match(
        self,
        conn: asyncpg.Connection,
        match_data: MatchData,
        run_id: int,
    ) -> None:
        """
        Persist all available data for one football match.

        All operations run inside the caller's transaction; nothing is
        committed here.  Re-running is safe — every write is an upsert.
        """
        event = match_data.base
        is_partial = not match_data.incidents or not match_data.lineups or not match_data.statistics
        await self._upsert_scrape(conn=conn, run_id=run_id, match_id=event.id, is_partial=is_partial)

        await self._upsert_tournament(conn=conn, run_id=run_id, tournament=event.tournament)
        await self._upsert_season(conn=conn, run_id=run_id, season=event.season)

        home_team_id = await self._upsert_team(conn, event.home_team)
        away_team_id = await self._upsert_team(conn, event.away_team)

        referee_id: int | None = None
        if event.referee:
            referee_id = await self._upsert_referee(conn, event.referee)

        venue_id: int | None = None
        if event.venue:
            venue_id = await self._upsert_venue(conn, event.venue)

        home_manager_id: int | None = None
        away_manager_id: int | None = None
        if match_data.managers:
            home_manager_id = await self._upsert_manager(conn, match_data.managers.home_manager)
            away_manager_id = await self._upsert_manager(conn, match_data.managers.away_manager)

        await self._upsert_match(
            conn,
            event=event,
            match_id=event.id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            venue_id=venue_id,
            referee_id=referee_id,
            home_manager_id=home_manager_id,
            away_manager_id=away_manager_id,
            run_id=run_id,
        )

        if event.home_score and event.away_score:
            await self._upsert_match_scores(conn, event.id, event, run_id)

        if match_data.incidents:
            for incident in match_data.incidents:
                await self._upsert_incident_players(conn, incident)
            await self._insert_incidents(conn, event.id, match_data.incidents)

        if match_data.lineups:
            await self._insert_lineups(conn, event.id, match_data.lineups)

        if match_data.shotmap:
            await self._insert_shot_events(conn, event.id, match_data.shotmap)

        if match_data.statistics:
            await self._insert_team_stats(conn, event.id, home_team_id, away_team_id, match_data.statistics)

        if match_data.odds:
            await self._insert_odds(conn, event.id, match_data.odds)

        if match_data.momentum:
            await self._insert_momentum(conn, event.id, match_data.momentum)

        if match_data.commentary:
            await self._insert_commentary(conn, event.id, match_data.commentary)

        self.logger.debug(f"Saved match id={event.id}")

    # Reference entities

    async def _upsert_scrape(self, conn, run_id, match_id, is_partial):
        row = await conn.fetchrow(
            """
            UPDATE core.scrapes 
            SET
                is_partial = $1,
                collected = $2,
                scrape_run_id = $3
            WHERE item = $4
            """,
            is_partial,
            True,
            run_id,
            match_id
        )

    async def _upsert_tournament(self, conn: asyncpg.Connection, run_id: int, tournament: Tournament) -> int:
        row = await conn.fetchrow(
            """
            INSERT INTO football.tournaments (
                id,
                country_id,
                name,
                slug,
                priority,
                scrape_run_id,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, now(), now())
            ON CONFLICT (id) DO NOTHING
            """,
            tournament.id,
            tournament.country.id,
            tournament.name,
            tournament.slug,
            tournament.priority,
            run_id,
        )
        return tournament.id

    async def _upsert_season(self, conn: asyncpg.Connection, run_id: int, season: Season) -> int:
        row = await conn.fetchrow(
            """
            INSERT INTO football.seasons (
                id,
                tournament_id,
                name,
                year,
                scrape_run_id,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, now(), now())
            ON CONFLICT (id) DO NOTHING
            """,
            season.id,
            season.tournament_id,
            season.name,
            season.year,
            run_id,
        )
        return season.id

    async def _upsert_team(self, conn: asyncpg.Connection, team: Team) -> int:
        """Upsert a team and return its PK (= sofascore id)."""
        row = await conn.fetchrow(
            """
            INSERT INTO football.teams
                (id, name, short_name, name_code, slug, is_national_team, country_id,
                 created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, now(), now())
            ON CONFLICT (id) DO UPDATE SET
                name            = EXCLUDED.name,
                short_name      = EXCLUDED.short_name,
                name_code       = EXCLUDED.name_code,
                slug            = EXCLUDED.slug,
                is_national_team = EXCLUDED.is_national_team,
                country_id      = EXCLUDED.country_id,
                updated_at      = now()
            """,
            team.id,
            team.name,
            team.short_name,
            team.name_code,
            team.slug,
            team.is_national,
            team.country_id,
        )
        self.logger.debug("Upserted team: " + team.name + " " + str(team.id))
        return team.id

    async def _upsert_player(self, conn: asyncpg.Connection, player: Player) -> int:
        """Upsert a player and return its PK."""
        mv_value = player.proposed_market_value.value if player.proposed_market_value else None
        mv_currency = player.proposed_market_value.currency if player.proposed_market_value else None

        row = await conn.fetchrow(
            """
            INSERT INTO football.players
                (id, name, short_name, slug, country_id, position, height,
                 date_of_birth, proposed_market_value, proposed_market_currency,
                 created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now(), now())
            ON CONFLICT (id) DO UPDATE SET
                name                     = EXCLUDED.name,
                short_name               = EXCLUDED.short_name,
                slug                     = EXCLUDED.slug,
                country_id               = EXCLUDED.country_id,
                position                 = EXCLUDED.position,
                height                   = EXCLUDED.height,
                date_of_birth            = EXCLUDED.date_of_birth,
                proposed_market_value    = EXCLUDED.proposed_market_value,
                proposed_market_currency = EXCLUDED.proposed_market_currency,
                updated_at               = now()
            """,
            player.id,
            player.name,
            player.short_name,
            player.slug,
            player.country_id,
            player.position,
            player.height,
            player.date_of_birth,
            mv_value,
            mv_currency,
        )
        return player.id

    async def _upsert_referee(self, conn: asyncpg.Connection, referee: Referee) -> int:
        row = await conn.fetchrow(
            """
            INSERT INTO football.referees (id, name, slug, country_id, created_at)
            VALUES ($1, $2, $3, $4, now())
            ON CONFLICT (id) DO UPDATE SET
                name       = EXCLUDED.name,
                slug       = EXCLUDED.slug,
                country_id = EXCLUDED.country_id
            """,
            referee.id,
            referee.name,
            referee.slug,
            referee.country_id,
        )
        return referee.id

    async def _upsert_venue(self, conn: asyncpg.Connection, venue: Venue) -> int:
        lat = venue.coordinates.lat if venue.coordinates else None
        lon = venue.coordinates.long if venue.coordinates else None

        row = await conn.fetchrow(
            """
            INSERT INTO football.venues (id, name, slug, country_id, latitude, longitude, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, now())
            ON CONFLICT (id) DO UPDATE SET
                name       = EXCLUDED.name,
                slug       = EXCLUDED.slug,
                country_id = EXCLUDED.country_id,
                latitude   = EXCLUDED.latitude,
                longitude  = EXCLUDED.longitude
            """,
            venue.id,
            venue.name,
            venue.slug,
            venue.country_id,
            lat,
            lon,
        )
        return venue.id

    async def _upsert_manager(self, conn: asyncpg.Connection, manager: Manager) -> int:
        row = await conn.fetchrow(
            """
            INSERT INTO football.managers (id, name, slug, short_name, created_at)
            VALUES ($1, $2, $3, $4, now())
            ON CONFLICT (id) DO UPDATE SET
                name       = EXCLUDED.name,
                slug       = EXCLUDED.slug,
                short_name = EXCLUDED.short_name
            """,
            manager.id,
            manager.name,
            manager.slug,
            manager.short_name,
        )
        return manager.id

    # Match

    async def _upsert_match(
        self,
        conn: asyncpg.Connection,
        *,
        event,
        match_id: int,
        home_team_id: int,
        away_team_id: int,
        venue_id: int | None,
        referee_id: int | None,
        home_manager_id: int | None,
        away_manager_id: int | None,
        run_id: int,
    ) -> None:
        home_score = event.home_score.current if event.home_score else None
        away_score = event.away_score.current if event.away_score else None
        agg_home = event.home_score.aggregated if event.home_score else None
        agg_away = event.away_score.aggregated if event.away_score else None
        round_num = event.round.round if event.round else None

        await conn.execute(
            """
            INSERT INTO football.matches
                (id, season_id, home_team_id, away_team_id, venue_id, referee_id,
                 home_manager_id, away_manager_id, started_at, status_code,
                 status_label, round, home_score, away_score, winner_code,
                 agg_home_score, agg_away_score, previous_leg_id, scrape_run_id,
                 created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,now())
            ON CONFLICT (id) DO UPDATE SET
                season_id       = EXCLUDED.season_id,
                home_team_id    = EXCLUDED.home_team_id,
                away_team_id    = EXCLUDED.away_team_id,
                venue_id        = EXCLUDED.venue_id,
                referee_id      = EXCLUDED.referee_id,
                home_manager_id = EXCLUDED.home_manager_id,
                away_manager_id = EXCLUDED.away_manager_id,
                started_at      = EXCLUDED.started_at,
                status_code     = EXCLUDED.status_code,
                status_label    = EXCLUDED.status_label,
                round           = EXCLUDED.round,
                home_score      = EXCLUDED.home_score,
                away_score      = EXCLUDED.away_score,
                winner_code     = EXCLUDED.winner_code,
                agg_home_score  = EXCLUDED.agg_home_score,
                agg_away_score  = EXCLUDED.agg_away_score,
                previous_leg_id = EXCLUDED.previous_leg_id,
                scrape_run_id   = EXCLUDED.scrape_run_id
            """,
            match_id,
            event.season.id,
            home_team_id,
            away_team_id,
            venue_id,
            referee_id,
            home_manager_id,
            away_manager_id,
            event.date,
            event.status.code,
            event.status.description,
            round_num,
            home_score,
            away_score,
            event.winner_code,
            agg_home,
            agg_away,
            event.previous_leg_event,
            run_id,
        )

    # Match scores

    async def _upsert_match_scores(self, conn: asyncpg.Connection, match_id: int, event, run_id: int) -> None:
        hs = event.home_score
        aws = event.away_score
        ti: TimeInfo = event.time

        await conn.execute(
            """
            INSERT INTO football.match_scores
                (match_id,
                 home_period1, away_period1, home_period2, away_period2,
                 home_extra1,  away_extra1,  home_extra2,  away_extra2,
                 home_penalties, away_penalties,
                 home_aggregated, away_aggregated,
                 injury_time1, injury_time2, injury_time3, injury_time4,
                 scrape_run_id, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,now())
            ON CONFLICT (match_id) DO UPDATE SET
                home_period1    = EXCLUDED.home_period1,
                away_period1    = EXCLUDED.away_period1,
                home_period2    = EXCLUDED.home_period2,
                away_period2    = EXCLUDED.away_period2,
                home_extra1     = EXCLUDED.home_extra1,
                away_extra1     = EXCLUDED.away_extra1,
                home_extra2     = EXCLUDED.home_extra2,
                away_extra2     = EXCLUDED.away_extra2,
                home_penalties  = EXCLUDED.home_penalties,
                away_penalties  = EXCLUDED.away_penalties,
                home_aggregated = EXCLUDED.home_aggregated,
                away_aggregated = EXCLUDED.away_aggregated,
                injury_time1    = EXCLUDED.injury_time1,
                injury_time2    = EXCLUDED.injury_time2,
                injury_time3    = EXCLUDED.injury_time3,
                injury_time4    = EXCLUDED.injury_time4,
                scrape_run_id   = EXCLUDED.scrape_run_id
            """,
            match_id,
            hs.period1,
            aws.period1,
            hs.period2,
            aws.period2,
            hs.extra1,
            aws.extra1,
            hs.extra2,
            aws.extra2,
            hs.penalties,
            aws.penalties,
            hs.aggregated,
            aws.aggregated,
            int(ti.injuryTime1) if ti and ti.injuryTime1 else None,
            int(ti.injuryTime2) if ti and ti.injuryTime2 else None,
            int(ti.injuryTime3) if ti and ti.injuryTime3 else None,
            int(ti.injuryTime4) if ti and ti.injuryTime4 else None,
            run_id,
        )

    # Incidents

    async def _upsert_incident_players(self, conn: asyncpg.Connection, incident: Incident) -> None:
        """Ensure all players referenced in an incident exist in football.players."""
        for player in filter(
            None,
            [
                incident.player,
                incident.player_in,
                incident.player_out,
                incident.goal_scorer,
                incident.assist,
            ],
        ):
            await self._upsert_player(conn, player)

    async def _insert_incidents(self, conn: asyncpg.Connection, match_id: int, incidents: list[Incident]) -> None:
        await conn.execute("DELETE FROM football.incidents WHERE match_id = $1", match_id)

        rows = []
        for inc in incidents:
            incident_type = (
                inc.incident_type
                if isinstance(inc.incident_type, str)
                else (inc.incident_type[0] if inc.incident_type else "unknown")
            )
            rows.append(
                (
                    match_id,
                    incident_type,
                    inc.incident_class or "",
                    inc.is_home,
                    inc.time,
                    inc.added_time,
                    inc.goal_scorer.id if inc.goal_scorer else None,
                    inc.assist.id if inc.assist else None,
                    (inc.player.id if inc.player else None),  # carded_player_id
                    inc.rescinded,
                    inc.player_in.id if inc.player_in else None,
                    inc.player_out.id if inc.player_out else None,
                    inc.injury,
                )
            )

        await conn.executemany(
            """
            INSERT INTO football.incidents
                (match_id, incident_type, incident_class, is_home,
                 minute, added_time,
                 goal_scorer_id, assist_player_id,
                 carded_player_id, rescinded,
                 player_in_id, player_out_id, is_injury_sub,
                 created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,now())
            """,
            rows,
        )

    # Lineups

    async def _insert_lineups(self, conn: asyncpg.Connection, match_id: int, lineups) -> None:
        all_entries: list[LineupPlayer] = lineups.home_players + lineups.away_players

        # Upsert every player first
        for entry in all_entries:
            await self._upsert_player(conn, entry.player)

        rows = []
        for entry in all_entries:
            rows.append(
                (
                    match_id,
                    entry.team_id,
                    entry.player.id,
                    int(entry.shirt_number) if entry.shirt_number and entry.shirt_number.isdigit() else None,
                    entry.position,
                    not entry.substitute,
                    entry.statistics.get("rating") if entry.statistics else None,
                    entry.statistics.get("ratingVersions", {}).get("alternative") if entry.statistics else None,
                    json.dumps(entry.statistics) if entry.statistics else None,
                )
            )

        await conn.executemany(
            """
            INSERT INTO football.lineups
                (match_id, team_id, player_id, shirt_number, position,
                 is_starter,
                 rating, rating_alt, statistics, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,now())
            ON CONFLICT (match_id, player_id) DO UPDATE SET
                shirt_number   = EXCLUDED.shirt_number,
                position       = EXCLUDED.position,
                is_starter     = EXCLUDED.is_starter,
                rating         = EXCLUDED.rating,
                rating_alt     = EXCLUDED.rating_alt,
                statistics     = EXCLUDED.statistics
            """,
            rows,
        )

    # Shot events

    async def _insert_shot_events(self, conn: asyncpg.Connection, match_id: int, shotmap: list[Shotmap]) -> None:
        # Ensure players are persisted
        for shot in shotmap:
            await self._upsert_player(conn, shot.player)
            if shot.goalkeeper:
                await self._upsert_player(conn, shot.goalkeeper)

        await conn.execute("DELETE FROM football.shot_events WHERE match_id = $1", match_id)

        rows = []
        for shot in shotmap:
            pc = shot.player_coordinates
            gm = shot.goal_mouth_coordinates
            bc = shot.block_coordinates

            rows.append(
                (
                    match_id,
                    shot.player.id if shot.player else None,
                    shot.goalkeeper.id if shot.goalkeeper else None,
                    shot.time,
                    shot.added_time,
                    shot.shot_type,
                    shot.situation,
                    shot.body_part,
                    pc.x if pc else None,
                    pc.y if pc else None,
                    pc.z if pc else None,
                    shot.goal_mouth_location,
                    gm.x if gm else None,
                    gm.y if gm else None,
                    gm.z if gm else None,
                    bc.x if bc else None,
                    bc.y if bc else None,
                    bc.z if bc else None,
                    shot.xg,
                    shot.xgot,
                )
            )

        await conn.executemany(
            """
            INSERT INTO football.shot_events
                (match_id, player_id, goalkeeper_id,
                 minute, added_time,
                 shot_type, situation, body_part,
                 player_x, player_y, player_z,
                 goal_mouth_location, goal_mouth_x, goal_mouth_y, goal_mouth_z,
                 block_x, block_y, block_z,
                 xg, xgot, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,now())
            """,
            rows,
        )

    # Statistics

    async def _upsert_stat_definition(
        self, conn: asyncpg.Connection, key: str, name: str, group_name: str, stat_type: str
    ) -> int:
        row = await conn.fetchrow(
            """
            INSERT INTO football.stat_definitions (slug, name, group_name, stat_type, created_at)
            VALUES ($1, $2, $3, $4, now())
            ON CONFLICT (slug) DO UPDATE SET
                name       = EXCLUDED.name,
                group_name = EXCLUDED.group_name
            RETURNING id
            """,
            key,
            name,
            group_name,
            stat_type,
        )
        return row["id"]

    async def _insert_team_stats(
        self,
        conn: asyncpg.Connection,
        match_id: int,
        home_team_id: int,
        away_team_id: int,
        statistics: list[StatisticsPeriod],
    ) -> None:
        rows = []
        for period_block in statistics:
            period = period_block.period
            for group in period_block.groups:
                for item in group.statistics:
                    stat_id = await self._upsert_stat_definition(
                        conn,
                        item.key,
                        item.name,
                        group.group_name,
                        item.statistics_type,
                    )
                    if item.home_value is not None:
                        rows.append((match_id, home_team_id, stat_id, period, item.home_value, None))
                    if item.away_value is not None:
                        rows.append((match_id, away_team_id, stat_id, period, item.away_value, None))

        await conn.executemany(
            """
            INSERT INTO football.team_match_stats
                (match_id, team_id, stat_id, period, value_numeric, value_text, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,now())
            ON CONFLICT (match_id, team_id, stat_id, period) DO UPDATE SET
                value_numeric = EXCLUDED.value_numeric,
                value_text    = EXCLUDED.value_text
            """,
            rows,
        )

    # Odds

    async def _insert_odds(self, conn: asyncpg.Connection, match_id: int, odds_list: list[Odds]) -> None:
        await conn.execute("DELETE FROM football.match_odds WHERE match_id = $1", match_id)

        rows = []
        for market in odds_list:
            for choice in market.choices:
                rows.append(
                    (
                        match_id,
                        market.name,
                        market.group,
                        market.period,
                        choice.name,
                        choice.decimal,
                        choice.fractional,
                        choice.american,
                        choice.implied_probability,
                        choice.true_probability,
                        choice.true_decimal,
                        choice.winning,
                    )
                )

        await conn.executemany(
            """
            INSERT INTO football.match_odds
                (match_id, market_name, market_group, period, choice_name,
                 decimal_odds, fractional_odds, american_odds,
                 implied_prob, true_prob, true_decimal, is_winning, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,now())
            """,
            rows,
        )

    # Momentum

    async def _insert_momentum(self, conn: asyncpg.Connection, match_id: int, momentum: list[MomentumElement]) -> None:
        await conn.execute("DELETE FROM football.match_momentum WHERE match_id = $1", match_id)

        rows = [(match_id, elem.minute, elem.value) for elem in momentum]

        await conn.executemany(
            """
            INSERT INTO football.match_momentum (match_id, minute, value, created_at)
            VALUES ($1, $2, $3, now())
            ON CONFLICT (match_id, minute) DO UPDATE SET value = EXCLUDED.value
            """,
            rows,
        )

    # Commentary

    async def _insert_commentary(self, conn: asyncpg.Connection, match_id: int, commentary: list[Commentary]) -> None:
        await conn.execute("DELETE FROM football.match_commentary WHERE match_id = $1", match_id)

        rows = [(match_id, c.type, c.text, c.time, c.period_name) for c in commentary]

        await conn.executemany(
            """
            INSERT INTO football.match_commentary
                (match_id, type, text, time, period_name)
            VALUES ($1, $2, $3, $4, $5)
            """,
            rows,
        )
