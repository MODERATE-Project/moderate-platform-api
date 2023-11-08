import enum
import logging
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI
from sqlmodel import SQLModel

import moderate_api.ping.router
from moderate_api.db import engine

_logger = logging.getLogger(__name__)


class Prefixes(enum.Enum):
    """The prefixes for the different API endpoints."""

    PING = "/ping"


try:
    _pkg_version = version("moderate_api")
except PackageNotFoundError:
    _pkg_version = "development"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        _logger.debug("Creating database tables...")
        await conn.run_sync(SQLModel.metadata.create_all)
        _logger.debug("Created database tables")

    yield


app = FastAPI(
    title="MODERATE HTTP API",
    description="The HTTP API for the MODERATE platform.",
    version=_pkg_version,
    contact={
        "name": "The MODERATE Platform development team",
        "url": "https://github.com/MODERATE-Project",
    },
    lifespan=lifespan,
)


app.include_router(moderate_api.ping.router.router, prefix=Prefixes.PING.value)
