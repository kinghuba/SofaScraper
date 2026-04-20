import logging

from asyncpg import Connection

from sofascraper.storage.pgsql.connection import Database
from sofascraper.storage.pgsql.football import FootballRepository
from sofascraper.utils.dataclasses.football_data_classes import MatchData


class PgsqlDataStorage:
    """
    Mirrors LocalDataStorage's public interface but persists data to PostgreSQL
    via the repository module instead of writing JSON files to disk.

    The Database pool must be initialised before any method is called:

        await Database.connect()
        storage = PgsqlDataStorage(sport_slug="football", scraper_version="1.0.0")
        await storage.open_run()
        ...
        await storage.close_run(row_count=n)
        await Database.disconnect()
    """

    def __init__(
        self,
        sport_slug: str = "football",
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
                "SELECT item FROM core.scrapes WHERE sport_id = $1 and is_date IS false",
                self.sport_id,
            )

        existing: set[int] = {int(row["item"]) for row in rows}
        self.logger.info(f"Found {len(existing)} existing match(es) in the database (sport_id={self.sport_id})")
        return existing

    async def get_existing_dates(self, file_path: str | None = None) -> set[str]:
        """
        Return the set of ISO date strings (YYYY-MM-DD) which were already scraped in the core.scrapes.
        """
        async with Database.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT item::date::text AS match_date
                FROM core.scrapes
                WHERE sport_id = $1
                  AND is_date IS true
                """,
                self.sport_id,
            )

        existing: set[str] = {row["match_date"] for row in rows}

        self.logger.debug(f"Found {len(existing)} existing date(s) in the database (sport_id={self.sport_id})")
        return existing

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

            football = FootballRepository()

            self.saved = 0
            for match in data:
                try:
                    await football.save_match(
                        conn,
                        match_data=match,
                        match_id=self.sport_id,
                        run_id=self.run_id,
                    )
                    self.saved += 1
                except Exception as exc:
                    self.logger.error(
                        f"Failed to save match sofascore_id={match.match_id}: {exc!s}",
                        exc_info=True,
                    )
                    raise

        self.logger.info(f"Saved {self.saved} match(es) to the database.")
