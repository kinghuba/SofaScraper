import logging
import os

import asyncpg

from sofascraper.utils.dataclasses.football_data_classes import (
    MatchData,
    Season,
    Team,
    Tournament,
    Venue,
)


class Supabase:
    """Persists scraped football match data to PostgreSQL (Supabase)."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._pool: asyncpg.Pool | None = None

    # Connection lifecycle

    async def connect(self) -> None:
        """
        Create the asyncpg connection pool.

        Call once at application startup before using any other method.
        Reads DATABASE_URL (required), DB_MIN_CONNECTIONS, and
        DB_MAX_CONNECTIONS from the environment.
        """
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise EnvironmentError(
                "DATABASE_URL environment variable is not set. "
                "Set it to your Supabase Postgres connection string, e.g. "
                "postgresql://postgres:<password>@db.<project>.supabase.co:5432/postgres"
            )

        min_conn = int(os.environ.get("DB_MIN_CONNECTIONS", 2))
        max_conn = int(os.environ.get("DB_MAX_CONNECTIONS", 10))

        self._pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=min_conn,
            max_size=max_conn,
        )
        self.logger.info("asyncpg pool created (min=%d, max=%d)", min_conn, max_conn)

    async def close(self) -> None:
        """
        Gracefully close the connection pool.

        Call once at application shutdown.
        """
        if self._pool:
            await self._pool.close()
            self._pool = None
            self.logger.info("asyncpg pool closed")

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError(
                "Database pool is not initialised. Call await repo.connect() first."
            )
        return self._pool

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def save_match(
        self,
        match_data: MatchData,
    ) -> None:
        """
        Persist all available data for one football match.

        Acquires a connection from the pool and runs all upserts inside a
        single transaction.  Re-running is safe — every write is an upsert.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await self._save_match_in_transaction(
                    conn=conn,
                    match_data=match_data,
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _save_match_in_transaction(
        self,
        conn: asyncpg.Connection,
        match_data: MatchData,
    ) -> None:
        event = match_data.base

        await self._upsert_tournament(conn=conn, tournament=event.tournament)
        await self._upsert_season(conn=conn, season=event.season)

        home_team_id = await self._upsert_team(conn, event.home_team)
        away_team_id = await self._upsert_team(conn, event.away_team)

        venue_id: int | None = None
        if event.venue:
            venue_id = await self._upsert_venue(conn, event.venue)

        await self._upsert_match(
            conn,
            event=event,
            match_id=event.id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            venue_id=venue_id,
        )

        self.logger.debug("Saved match id=%s", event.id)

    async def _upsert_match(
        self,
        conn: asyncpg.Connection,
        *,
        event,
        match_id: int,
        home_team_id: int,
        away_team_id: int,
        venue_id: int | None,
    ) -> None:
        home_score = event.home_score.current if event.home_score else None
        away_score = event.away_score.current if event.away_score else None
        agg_home = event.home_score.aggregated if event.home_score else None
        agg_away = event.away_score.aggregated if event.away_score else None
        round_num = event.round.round if event.round else None

        await conn.execute(
            """
            INSERT INTO matches
                (id, season_id, home_team_id, away_team_id, venue_id, started_at, status_code,
                 status_label, round, home_score, away_score, winner_code,
                 agg_home_score, agg_away_score, previous_leg_id,
                 created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,now())
            ON CONFLICT (id) DO UPDATE SET
                season_id       = EXCLUDED.season_id,
                home_team_id    = EXCLUDED.home_team_id,
                away_team_id    = EXCLUDED.away_team_id,
                venue_id        = EXCLUDED.venue_id,
                started_at      = EXCLUDED.started_at,
                status_code     = EXCLUDED.status_code,
                status_label    = EXCLUDED.status_label,
                round           = EXCLUDED.round,
                home_score      = EXCLUDED.home_score,
                away_score      = EXCLUDED.away_score,
                winner_code     = EXCLUDED.winner_code,
                agg_home_score  = EXCLUDED.agg_home_score,
                agg_away_score  = EXCLUDED.agg_away_score,
                previous_leg_id = EXCLUDED.previous_leg_id
            """,
            match_id,
            event.season.id,
            home_team_id,
            away_team_id,
            venue_id,
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
        )

    async def _upsert_tournament(
        self,
        conn: asyncpg.Connection,
        tournament: Tournament,
    ) -> int:
        await conn.execute(
            """
            INSERT INTO tournaments (
                id,
                country_id,
                name,
                slug,
                priority,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, now(), now())
            ON CONFLICT (id) DO NOTHING
            """,
            tournament.id,
            tournament.country.id,
            tournament.name,
            tournament.slug,
            tournament.priority,
        )
        return tournament.id

    async def _upsert_season(
        self,
        conn: asyncpg.Connection,
        season: Season,
    ) -> int:
        await conn.execute(
            """
            INSERT INTO seasons (
                id,
                tournament_id,
                name,
                year,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, now(), now())
            ON CONFLICT (id) DO NOTHING
            """,
            season.id,
            season.tournament_id,
            season.name,
            season.year,
        )
        return season.id

    async def _upsert_team(self, conn: asyncpg.Connection, team: Team) -> int:
        """Upsert a team and return its PK (= sofascore id)."""
        await conn.execute(
            """
            INSERT INTO teams
                (id, name, short_name, name_code, slug, is_national_team, country_id,
                 created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, now(), now())
            ON CONFLICT (id) DO UPDATE SET
                name             = EXCLUDED.name,
                short_name       = EXCLUDED.short_name,
                name_code        = EXCLUDED.name_code,
                slug             = EXCLUDED.slug,
                is_national_team = EXCLUDED.is_national_team,
                country_id       = EXCLUDED.country_id,
                updated_at       = now()
            """,
            team.id,
            team.name,
            team.short_name,
            team.name_code,
            team.slug,
            str(team.is_national),
            team.country_id,
        )
        self.logger.debug("Upserted team: %s (%s)", team.name, team.id)
        return team.id

    async def _upsert_venue(self, conn: asyncpg.Connection, venue: Venue) -> int:
        lat = venue.coordinates.lat if venue.coordinates else None
        lon = venue.coordinates.long if venue.coordinates else None

        await conn.execute(
            """
            INSERT INTO venues
                (id, name, slug, country_id, latitude, longitude, created_at)
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