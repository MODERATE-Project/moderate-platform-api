import logging
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Computed
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from moderate_api.config import get_settings

_logger = logging.getLogger(__name__)


class DBEngine:
    _instance = None

    @classmethod
    def is_test_environment(cls) -> bool:
        pytest_pkg = "pytest"
        _logger.debug("Checking if %s is in sys.modules", pytest_pkg)

        if pytest_pkg in sys.modules:
            _logger.warning("This seems to be a test environment")
            return True
        else:
            _logger.debug("This is not a test environment")
            return False

    @classmethod
    def instance(cls) -> AsyncEngine:
        if cls._instance is None:
            # Use NullPool when running tests, otherwise use the default poolclass
            # https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html#using-multiple-asyncio-event-loops
            poolclass = NullPool if cls.is_test_environment() else None

            _logger.log(
                logging.WARNING if poolclass is NullPool else logging.INFO,
                "Using poolclass: %s",
                poolclass,
            )

            cls._instance = create_async_engine(
                get_settings().postgres_url,
                echo=True,
                future=True,
                poolclass=poolclass,
            )

        return cls._instance


@asynccontextmanager
async def with_session() -> AsyncGenerator[AsyncSession, None]:
    engine = DBEngine.instance()
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]
    _logger.debug("Initialized session factory: %s", async_session)

    async with async_session() as session:
        yield session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with with_session() as session:
        yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]


def build_tsvector_computed(columns: list[str], language: str = "english") -> Computed:
    columns_part = " || ' ' || ".join(columns)
    return Computed(f"to_tsvector('{language}', {columns_part})", persisted=True)
