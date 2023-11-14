import asyncio
import logging
import os

from sqlalchemy.ext.asyncio import create_async_engine

_logger = logging.getLogger(__name__)

ENV_TESTS_POSTGRES_URL = "TESTS_POSTGRES_URL"
DB_SKIP_REASON = f"PostgreSQL service from ${ENV_TESTS_POSTGRES_URL} is unavailable"


async def is_db_online_async() -> bool:
    postgres_url = os.environ.get(ENV_TESTS_POSTGRES_URL, None)

    if postgres_url is None:
        _logger.warning("Please set environment variable $%s", ENV_TESTS_POSTGRES_URL)
        return False

    _logger.debug("Checking database connection: %s", postgres_url)

    try:
        engine = create_async_engine(postgres_url)

        async with engine.connect() as connection:
            assert connection
            return True
    except Exception:
        _logger.warning("Database is offline", exc_info=True)
        return False
    finally:
        try:
            _logger.debug("Disposing of DB engine")
            await engine.dispose()
        except Exception:
            _logger.warning("Failed to dispose of DB engine", exc_info=True)


def is_db_online() -> bool:
    return asyncio.run(is_db_online_async())
