import logging
import sys
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlmodel import SQLModel

import moderate_api.entities.asset.router
import moderate_api.entities.user.router
import moderate_api.long_running
import moderate_api.ping.router
from moderate_api.config import get_settings
from moderate_api.db import DBEngine
from moderate_api.enums import Prefixes

_logger = logging.getLogger(__name__)


def abort_if_trailing_slashes(the_app: FastAPI):
    """Checks the app's routes for trailing slashes and exits if any are found.
    https://github.com/tiangolo/fastapi/discussions/7298#discussioncomment-5135720"""

    for route in the_app.routes:
        if route.path.endswith("/"):
            if route.path == "/":
                continue

            _logger.warning(
                "Aborting: paths may not end with a slash. Check route: %s", route
            )

            sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _logger.debug("Entering lifespan context manager for app: %s", app)

    async with DBEngine.instance().begin() as conn:
        _logger.debug("Creating database tables...")
        await conn.run_sync(SQLModel.metadata.create_all)
        _logger.debug("Created database tables")

    yield

    _logger.debug("Exiting lifespan context manager for app: %s", app)


try:
    _pkg_version = version("moderate_api")
except PackageNotFoundError:
    _pkg_version = "development"


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


@app.exception_handler(DBAPIError)
async def db_exception_handler(request: Request, exc: DBAPIError):
    settings = get_settings()
    status_code = 409 if isinstance(exc, IntegrityError) else 500
    msg = str(exc) if settings.verbose_errors else "Database operation error"
    _logger.warning("Database error: %s", exc, exc_info=exc)
    return JSONResponse(status_code=status_code, content={"message": msg})


app.include_router(
    moderate_api.ping.router.router,
    prefix=Prefixes.PING.value,
)

app.include_router(
    moderate_api.entities.asset.router.router,
    prefix=Prefixes.ASSET.value,
)

app.include_router(
    moderate_api.entities.user.router.router,
    prefix=Prefixes.USER.value,
)

abort_if_trailing_slashes(the_app=app)
