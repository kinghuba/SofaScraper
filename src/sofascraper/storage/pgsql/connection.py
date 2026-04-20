"""
sofascraper/db/connection.py

Manages the asyncpg connection pool for the lifetime of the application.

Usage
-----
    # At startup (e.g. in ScraperApp.__init__ or main):
    await Database.connect()

    # Anywhere that needs a connection:
    async with Database.acquire() as conn:
        await conn.execute(...)

    # At shutdown:
    await Database.disconnect()

Configuration is read from environment variables so no credentials ever
appear in source code:

    SS_DB_HOST      (default: localhost)
    SS_DB_PORT      (default: 5432)
    SS_DB_NAME      (required)
    SS_DB_USER      (required)
    SS_DB_PASSWORD  (required)
    SS_DB_MIN_CONNS (default: 2)
    SS_DB_MAX_CONNS (default: 10)

Or supply a full DSN via SS_DB_DSN which overrides the individual vars.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg

logger = logging.getLogger(__name__)


class Database:
    _pool: asyncpg.Pool | None = None

    @classmethod
    async def connect(cls) -> None:
        """
        Create the connection pool.  Call once at application startup.
        Raises RuntimeError if already connected.
        """
        if cls._pool is not None:
            raise RuntimeError("Database.connect() called while already connected.")

        dsn = os.getenv("SS_DB_DSN") or cls._build_dsn()
        min_size = int(os.getenv("SS_DB_MIN_CONNS", "2"))
        max_size = int(os.getenv("SS_DB_MAX_CONNS", "10"))

        logger.info(f"Connecting to database (pool {min_size}–{max_size} connections)…")

        cls._pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60,
        )
        logger.info("Database pool ready.")

    @classmethod
    async def disconnect(cls) -> None:
        """Close the pool gracefully.  Call once at application shutdown."""
        if cls._pool is None:
            return
        await cls._pool.close()
        cls._pool = None
        logger.info("Database pool closed.")

    @classmethod
    @asynccontextmanager
    async def acquire(cls) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Async context manager that yields a connection from the pool.
        """
        if cls._pool is None:
            raise RuntimeError(
                "Database pool is not initialised. Call await Database.connect() before using the database."
            )
        async with cls._pool.acquire() as conn:
            yield conn

    @classmethod
    @asynccontextmanager
    async def transaction(cls) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Async context manager that yields a connection with an open transaction.
        The transaction is committed on clean exit and rolled back on exception.
        """
        async with cls.acquire() as conn:
            async with conn.transaction():
                yield conn

    @classmethod
    def _build_dsn(cls) -> str:
        host = os.getenv("SS_DB_HOST", "localhost")
        port = os.getenv("SS_DB_PORT", "5432")
        name = os.environ["SS_DB_NAME"]  # required — raises KeyError if absent
        user = os.environ["SS_DB_USER"]  # required
        password = os.environ["SS_DB_PASSWORD"]  # required
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    @classmethod
    def is_connected(cls) -> bool:
        return cls._pool is not None
