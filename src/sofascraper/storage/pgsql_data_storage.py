import logging

from asyncpg import Connection

from sofascraper.storage.pgsql.connection import Database
from sofascraper.storage.pgsql.football import FootballRepository
from sofascraper.storage.pgsql.tennis import TennisRepository
from sofascraper.utils.constants import SOFASCORE_BASE_URL
from sofascraper.utils.dataclasses.football_data_classes import MatchData

REPOSITORIES = {
    "tennis": TennisRepository,
    "football": FootballRepository,
}

class PgsqlDataStorage:

    def __init__(
        self,
        sport_slug: str = None,
        scraper_version: str = "1.0.0",
    ):
        """
        Args:
            sport_slug:            Slug used to look up the sport PK in core.sports
                                   (e.g. "football").
            scraper_version:       Version string recorded in core.scrape_runs.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.default_file_path = "data"
        self.sport_slug = sport_slug
        self.scraper_version = scraper_version
        self.run_id: int | None = None
        self.sport_id: int | None = None
        self.saved: int | None = 0

    def _get_repository(self, sport):
        repository = REPOSITORIES.get(sport)
        if not repository:
            raise ValueError(f"Unsupported sport: {sport}")
        return repository()

    async def open_scrape_run(
        self,
        conn: Connection,
    ) -> None:
        """
        Insert a new scrape_run row and return its id.
        """
        self.sport_id = await self._get_sport_id(conn, self.sport_slug)

        if self.sport_id is None:
            raise RuntimeError("sport_id is not set. Call open_run() first or pass sport_id explicitly.")

        row = await conn.fetchrow(
            """
            INSERT INTO core.scrape_runs (sport_id, scraper_version, started_at)
            VALUES ($1, $2, now())
            RETURNING id
            """,
            self.sport_id,
            self.scraper_version,
        )
        self.run_id: int = row["id"]
        self.logger.debug(
            f"Opened scrape run id={self.run_id} (sport_id={self.sport_id}, scraper_version={self.scraper_version})"
        )
        return

    async def close_scrape_run(
        self,
        conn: Connection,
    ) -> None:
        """Mark a scrape_run as finished with a final row count."""
        await conn.execute(
            """
            UPDATE core.scrape_runs
            SET finished_at = now(), row_count = $2
            WHERE id = $1
            """,
            self.run_id,
            self.saved,
        )
        self.logger.debug(f"Closed scrape_run id={self.run_id}, rows={self.saved}")

    async def _get_sport_id(self, conn: Connection, slug: str) -> int:
        """
        Return the PK of a sport by its slug (e.g. 'football').
        """
        row = await conn.fetchrow("SELECT id FROM core.sports WHERE slug = $1", slug)
        if row is None:
            raise ValueError(f"Sport '{slug}' not found in core.sports. Seed the table before scraping.")
        return row["id"]

    async def get_existing_match_ids(self, file_path: str | None = None) -> set[int]:
        """
        Return the set of SofaScore match IDs already stored.
        """
        async with Database.acquire() as conn:
            rows = await conn.fetch(
                "SELECT item FROM core.scrapes WHERE sport_id = $1 AND collected = true",
                self.sport_id,
            )

        existing: set[int] = {int(row["item"]) for row in rows}
        self.logger.debug(f"Found {len(existing)} existing match(es) in the database (sport_id={self.sport_id})")
        return existing

    async def get_existing_dates(self, file_path: str | None = None) -> set[str]:
        return

    async def save_link(
        self,
        match_slug,
        match_id,
        match_custom_id,
        season_id,
        collected
    ) -> None:
        async with Database.transaction() as conn:
            await conn.fetchrow(
                """
                INSERT INTO core.scrapes (
                    sport_id,
                    item,
                    item_slug,
                    item_custom_id,
                    item_url,
                    item_season_id,
                    scrape_run_id,
                    collected
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (sport_id, item) DO NOTHING
                """,
                1,
                match_id,
                match_slug,
                match_custom_id,
                f"{SOFASCORE_BASE_URL}/football/match/{match_slug}/{match_custom_id}#id:{match_id}",
                season_id,
                self.run_id,
                collected
            )

        self.logger.debug(f"Inserted {SOFASCORE_BASE_URL}/football/match/{match_slug}/{match_custom_id}#id:{match_id} match to the database.")

    async def save_season(
        self,
        season_id,
        all_rounds_collected,
    ) -> None:
        async with Database.transaction() as conn:
            await conn.fetchrow(
                """
                INSERT INTO core.scrape_tournaments (
                    sport_id,
                    season_id,
                    links_collected,
                    scrape_run_id,
                    last_checked_at
                )
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (sport_id, season_id) DO UPDATE
                SET
                    links_collected = EXCLUDED.links_collected,
                    last_checked_at = NOW(),
                    scrape_run_id = EXCLUDED.scrape_run_id
                """,
                self.sport_id,
                int(season_id),
                all_rounds_collected,
                self.run_id
            )

            self.logger.debug(f"Saved {season_id}, with link collection status {all_rounds_collected}")

    async def check_season(
        self,
        season_id
    ):
        async with Database.transaction() as conn:
            row = await conn.fetchrow(
                """
                SELECT links_collected from core.scrape_tournaments WHERE season_id = $1
                """,
                int(season_id)
            )
            self.logger.debug(f"Links for {season_id} are {"collected" if row and row["links_collected"] else "not collected"}.")

            return bool(row and row["links_collected"])

    async def get_collected_links(self, season_id):
        async with Database.transaction() as conn:
            rows = await conn.fetch(
                """
                SELECT item_url 
                FROM core.scrapes 
                WHERE item_season_id = $1 AND collected = FALSE
                """,
                int(season_id)
            )

        # Extract item_url values into a list
        return [row["item_url"] for row in rows]

    async def save_data(
        self,
        data: MatchData | list[MatchData],
        file_name_key=None,
        file_path=None,
    ) -> None:
        """
        Persist one or more MatchData objects to the database.
        """
        async with Database.transaction() as conn:
            if isinstance(data, MatchData):
                data = [data]

            repository = self._get_repository(self.sport_slug)

            self.saved = 0
            for match in data:
                try:
                    await repository.save_match(
                        conn,
                        match_data=match,
                        run_id=self.run_id,
                    )
                    self.saved += 1
                except Exception as exc:
                    self.logger.error(
                        f"Failed to save match sofascore_id={match.match_id}: {exc!s}",
                        exc_info=True,
                    )
                    raise

        self.logger.debug(f"Saved {self.saved} match(es) to the database.")
