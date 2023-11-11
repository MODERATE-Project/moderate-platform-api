import asyncio
import logging
import os

from sqlalchemy.ext.asyncio import create_async_engine

_logger = logging.getLogger(__name__)

_ENV_POSTGRES_URL = "MODERATE_API_POSTGRES_URL"
DB_SKIP_REASON = "PostgreSQL database is unavailable"


async def is_db_online_async() -> bool:
    postgres_url = os.environ.get(_ENV_POSTGRES_URL, None)
    _logger.debug("Checking database connection: %s", postgres_url)

    try:
        engine = create_async_engine(postgres_url)

        async with engine.connect() as connection:
            assert connection
            return True
    except Exception:
        _logger.warning("Database is offline", exc_info=True)
        return False


def is_db_online() -> bool:
    return asyncio.run(is_db_online_async())
