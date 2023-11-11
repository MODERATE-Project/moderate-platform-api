import logging
import sys

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from typing_extensions import Annotated

from moderate_api.config import get_settings

_logger = logging.getLogger(__name__)


def _is_pytest_running():
    if "pytest" in sys.modules:
        _logger.warning("Pytest seems to be running")
        return True
    else:
        _logger.debug("Pytest is not running")
        return False


# Use NullPool when running tests, otherwise use the default poolclass
# https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html#using-multiple-asyncio-event-loops
_poolclass = NullPool if _is_pytest_running() else None
_logger.info("Using poolclass: %s", _poolclass)

engine = create_async_engine(
    get_settings().postgres_url, echo=True, future=True, poolclass=_poolclass
)


async def get_session() -> AsyncSession:
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _logger.debug("Initialized session factory: %s", async_session)

    async with async_session() as session:
        yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]
