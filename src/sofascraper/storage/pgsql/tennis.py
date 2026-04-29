import json
from typing import Any

from sofascraper.utils.dataclasses.tennis_data_classes import MatchData, Score, StatisticItem


class TennisRepository:

    # Public entry point

    async def save_data(self, conn, match_data: MatchData, run_id: int) -> None:
        """Persist a full (or partial) MatchData object to the database."""
        base = match_data.base

        await self._upsert_venue(conn, base.venue)
        await self._upsert_players(conn, base.home_team, base.away_team, run_id)
        await self._upsert_tournament(conn, base.tournament, run_id)
        await self._upsert_season(conn, base.season, run_id)
        await self._upsert_match(conn, match_data, run_id)

        if match_data.statistics:
            await self._insert_stats(conn, match_data.match_id, match_data.statistics, run_id)

        if match_data.incidents:
            await self._insert_game_log(conn, match_data.match_id, match_data.incidents)
            await self._insert_set_scores(conn, match_data.match_id, match_data.base)

        if match_data.momentum and match_data.momentum.momentum:
            await self._insert_momentum(conn, match_data.match_id, match_data.momentum)

        if match_data.odds:
            await self._insert_odds(conn, match_data.match_id, match_data.odds)

        if match_data.rankings:
            await self._insert_rankings(conn, match_data.match_id, match_data.rankings)

        is_partial = not match_data.fully_captured
        await self._upsert_scrape(conn, run_id, match_data.match_id, is_partial)

    # Scrape tracking

    async def _upsert_scrape(self, conn, run_id: int, match_id: int, is_partial: bool) -> None:
        await conn.fetchrow(
            """
            UPDATE core.scrapes
            SET
                is_partial   = $1,
                collected    = $2,
                scrape_run_id = $3
            WHERE item = $4
            """,
            is_partial,
            True,
            run_id,
            match_id,
        )

    # Reference / dimension tables

    async def _upsert_venue(self, conn, venue) -> None:
        if venue is None or venue.id is None:
            return
        await conn.execute(
            """
            INSERT INTO tennis.venues (id, country_id, slug, name, city, stadium)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE SET
                slug    = EXCLUDED.slug,
                name    = EXCLUDED.name,
                city    = EXCLUDED.city,
                stadium = EXCLUDED.stadium
            """,
            venue.id,
            venue.country_id,
            venue.slug,
            venue.name,
            venue.city,
            venue.stadium,
        )

    async def _upsert_players(self, conn, home_team, away_team, run_id: int) -> None:
        for team in (home_team, away_team):
            info = team.player_info
            prize_total = info.prize_total_raw.value if info and info.prize_total_raw else None
            prize_currency = info.prize_total_raw.currency if info and info.prize_total_raw else None
            await conn.execute(
                """
                INSERT INTO tennis.players (
                    id, country_id, name, short_name, slug, name_code, gender,
                    ranking, height, weight, plays, date_of_birth,
                    place_of_birth, residence, prize_total_value, prize_total_currency
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                ON CONFLICT (id) DO UPDATE SET
                    name               = EXCLUDED.name,
                    short_name         = EXCLUDED.short_name,
                    slug               = EXCLUDED.slug,
                    name_code          = EXCLUDED.name_code,
                    gender             = EXCLUDED.gender,
                    ranking            = EXCLUDED.ranking,
                    height             = EXCLUDED.height,
                    weight             = EXCLUDED.weight,
                    plays              = EXCLUDED.plays,
                    date_of_birth      = EXCLUDED.date_of_birth,
                    place_of_birth     = EXCLUDED.place_of_birth,
                    residence          = EXCLUDED.residence,
                    prize_total_value  = EXCLUDED.prize_total_value,
                    prize_total_currency = EXCLUDED.prize_total_currency,
                    updated_at         = now()
                """,
                team.id,
                team.country_id,
                team.name,
                team.short_name,
                team.slug,
                team.name_code,
                team.gender,
                int(team.ranking) if team.ranking and team.ranking.isdigit() else None,
                info.height if info else None,
                info.weight if info else None,
                info.plays if info else None,
                info.date_of_birth if info else None,
                info.place_of_birth if info else None,
                info.residence if info else None,
                prize_total,
                prize_currency,
            )

    async def _upsert_tournament(self, conn, tournament, run_id: int) -> None:
        await conn.execute(
            """
            INSERT INTO tennis.tournaments (id, name, slug, ground_type, tennis_points, flag, priority, scrape_run_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            ON CONFLICT (id) DO UPDATE SET
                name          = EXCLUDED.name,
                slug          = EXCLUDED.slug,
                ground_type   = EXCLUDED.ground_type,
                tennis_points = EXCLUDED.tennis_points,
                flag          = EXCLUDED.flag,
                priority      = EXCLUDED.priority,
                scrape_run_id = EXCLUDED.scrape_run_id,
                updated_at    = now()
            """,
            tournament.id,
            tournament.name,
            tournament.slug,
            tournament.ground_type,
            tournament.tennis_points,
            tournament.flag,
            tournament.priority,
            run_id,
        )

    async def _upsert_season(self, conn, season, run_id: int) -> None:
        await conn.execute(
            """
            INSERT INTO tennis.seasons (id, tournament_id, name, year, scrape_run_id)
            VALUES ($1,$2,$3,$4,$5)
            ON CONFLICT (id) DO UPDATE SET
                name          = EXCLUDED.name,
                year          = EXCLUDED.year,
                scrape_run_id = EXCLUDED.scrape_run_id,
                updated_at    = now()
            """,
            season.id,
            season.tournament_id,
            season.name,
            int(season.year) if season.year else None,
            run_id,
        )

    # Core match row

    async def _upsert_match(self, conn, match_data: MatchData, run_id: int) -> None:
        base = match_data.base
        home_score = base.home_score
        away_score = base.away_score

        await conn.execute(
            """
            INSERT INTO tennis.matches (
                id, season_id, home_player_id, away_player_id, venue_id,
                started_at, status_code, status_label,
                round_number, round_name,
                home_seed, away_seed, first_to_serve,
                home_sets, away_sets, winner_code,
                scrape_run_id
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
            ON CONFLICT (id) DO UPDATE SET
                status_code    = EXCLUDED.status_code,
                status_label   = EXCLUDED.status_label,
                home_sets      = EXCLUDED.home_sets,
                away_sets      = EXCLUDED.away_sets,
                winner_code    = EXCLUDED.winner_code,
                scrape_run_id  = EXCLUDED.scrape_run_id
            """,
            base.id,
            base.season.id,
            base.home_team.id,
            base.away_team.id,
            base.venue.id if base.venue else None,
            base.date,
            base.status.code,
            base.status.description,
            base.round.round if base.round else None,
            base.round.round_name if base.round else None,
            base.home_team_seed,
            base.away_team_seed,
            base.first_to_serve,
            home_score.current if home_score else None,
            away_score.current if away_score else None,
            base.winner_code,
            run_id,
        )

    # Set scores (derived from Score fields on the event)

    async def _insert_set_scores(self, conn, match_id: int, event) -> None:
        """Unpack period scores from home/away Score objects into set_scores rows."""
        home: Score = event.home_score
        away: Score = event.away_score
        if home is None or away is None:
            return

        period_fields = [
            (1, "period1"),
            (2, "period2"),
            (3, "period3"),
            (4, "period4"),
            (5, "period5"),
        ]
        time_info = event.time

        for set_num, games_attr in period_fields:
            home_games = getattr(home, games_attr, None)
            if home_games is None:
                break

            duration = getattr(time_info, games_attr, None) if time_info else None

            await conn.execute(
                """
                INSERT INTO tennis.set_scores
                    (match_id, set_number, home_games, away_games, duration_secs)
                VALUES ($1,$2,$3,$4,$5)
                ON CONFLICT (match_id, set_number) DO UPDATE SET
                    home_games    = EXCLUDED.home_games,
                    away_games    = EXCLUDED.away_games,
                    duration_secs = EXCLUDED.duration_secs
                """,
                match_id,
                set_num,
                home_games,
                getattr(away, games_attr, None),
                duration,
            )

    # Statistics

    async def _insert_stats(self, conn, match_id: int, statistics, run_id: int) -> None:
        for period_block in statistics:
            period = period_block.period
            for group in period_block.groups:
                for item in group.statistics:
                    stat_id = await self._ensure_stat_definition(conn, item, group.group_name)
                    for is_home, value in ((True, item.home_value), (False, item.away_value)):
                        if value is None:
                            continue
                        value_numeric, value_text = self._classify_stat_value(value)
                        await conn.execute(
                            """
                            INSERT INTO tennis.match_stats
                                (match_id, is_home, stat_id, period, value_numeric, value_text, scrape_run_id)
                            VALUES ($1,$2,$3,$4,$5,$6,$7)
                            ON CONFLICT (match_id, is_home, stat_id, period) DO UPDATE SET
                                value_numeric = EXCLUDED.value_numeric,
                                value_text    = EXCLUDED.value_text,
                                scrape_run_id = EXCLUDED.scrape_run_id
                            """,
                            match_id,
                            is_home,
                            stat_id,
                            period,
                            value_numeric,
                            value_text,
                            run_id,
                        )

    async def _ensure_stat_definition(self, conn, item: StatisticItem, group_name: str) -> int:
        row = await conn.fetchrow(
            "SELECT id FROM tennis.stat_definitions WHERE slug = $1", item.key
        )
        if row:
            return row["id"]
        row = await conn.fetchrow(
            """
            INSERT INTO tennis.stat_definitions (slug, name, group_name, stat_type)
            VALUES ($1,$2,$3,$4)
            ON CONFLICT (slug) DO UPDATE SET slug = EXCLUDED.slug
            RETURNING id
            """,
            item.key,
            item.name,
            group_name,
            item.statistics_type,
        )
        return row["id"]

    @staticmethod
    def _classify_stat_value(value: Any) -> tuple[float | None, str | None]:
        """Return (value_numeric, value_text) — exactly one will be non-None."""
        try:
            return float(value), None
        except (TypeError, ValueError):
            return None, str(value)

    # Game log (incidents)

    async def _insert_game_log(self, conn, match_id: int, incidents) -> None:
        for incident in incidents:
            points_payload = json.dumps(
                [
                    {
                        "home_point": p.home_point,
                        "away_point": p.away_point,
                        "point_description": p.point_description,
                        "home_point_type": p.home_point_type,
                        "away_point_type": p.away_point_type,
                    }
                    for p in incident.points
                ]
            )
            await conn.execute(
                """
                INSERT INTO tennis.game_log
                    (match_id, set_number, game_number, home_score, away_score, serving, scoring, points)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                ON CONFLICT (match_id, set_number, game_number) DO UPDATE SET
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    serving    = EXCLUDED.serving,
                    scoring    = EXCLUDED.scoring,
                    points     = EXCLUDED.points
                """,
                match_id,
                incident.set,
                incident.game,
                incident.score.home_score,
                incident.score.away_score,
                incident.score.serving,
                incident.score.scoring,
                points_payload,
            )

    # Momentum

    async def _insert_momentum(self, conn, match_id: int, momentum) -> None:
        for element in momentum.momentum:
            await conn.execute(
                """
                INSERT INTO tennis.match_momentum
                    (match_id, set_number, game_number, value, break_occurred)
                VALUES ($1,$2,$3,$4,$5)
                ON CONFLICT (match_id, set_number, game_number) DO UPDATE SET
                    value          = EXCLUDED.value,
                    break_occurred = EXCLUDED.break_occurred
                """,
                match_id,
                element.set,
                element.game,
                element.value,
                element.break_occurred,
            )

    # Odds

    async def _insert_odds(self, conn, match_id: int, odds) -> None:
        for market in odds:
            for choice in market.choices:
                await conn.execute(
                    """
                    INSERT INTO tennis.match_odds (
                        match_id, market_name, market_group, period,
                        choice_name, decimal_odds, fractional_odds, american_odds,
                        implied_prob, true_prob, true_decimal, is_winning
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                    """,
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

    # Rankings

    async def _insert_rankings(self, conn, match_id: int, rankings) -> None:
        for ranking in rankings:
            await conn.execute(
                """
                INSERT INTO tennis.rankings (
                    player_id, match_id, tournaments_played,
                    ranking, points, previous_ranking, previous_points,
                    best_ranking, ranking_class
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                """,
                ranking.player_id,
                match_id,
                ranking.tournaments_played,
                ranking.ranking,
                ranking.points,
                ranking.previous_ranking,
                ranking.previous_points,
                ranking.best_ranking,
                ranking.ranking_class,
            )
