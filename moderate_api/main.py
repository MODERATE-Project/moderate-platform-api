import logging
import os
import re
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version

import marimo
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlmodel import SQLModel

import moderate_api.entities.asset.router
import moderate_api.entities.user.router
import moderate_api.entities.visualization.router
import moderate_api.long_running
import moderate_api.ping.router
from moderate_api.authz.user import get_user
from moderate_api.config import get_settings
from moderate_api.db import DBEngine
from moderate_api.enums import Prefixes
from moderate_api.notebooks import ALL_NOTEBOOKS

_logger = logging.getLogger(__name__)


def raise_if_trailing_slashes(the_app: FastAPI):
    """Checks the app's routes for trailing slashes and exits if any are found.
    https://github.com/tiangolo/fastapi/discussions/7298#discussioncomment-5135720"""

    for route in the_app.routes:
        if route.path.endswith("/"):
            if route.path == "/":
                continue

            err_msg = (
                "Aborting: paths may not end with a slash. Check route: {}".format(
                    route
                )
            )

            _logger.error(err_msg)
            raise Exception(err_msg)


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

app.include_router(
    moderate_api.entities.visualization.router.router,
    prefix=Prefixes.VISUALIZATION.value,
)

raise_if_trailing_slashes(the_app=app)


@app.middleware("http")
async def notebook_middleware(request: Request, call_next):
    """Middleware to check if the request is for a notebook and if the user is authorized to access it."""

    is_notebook_request = re.match(
        f"^{Prefixes.NOTEBOOK.value}(/.*)?$", request.url.path
    )

    if not is_notebook_request:
        return await call_next(request)

    try:
        user = await get_user(request=request, settings=get_settings())

        if not user or not user.is_enabled:
            raise
    except Exception as ex:
        _logger.debug("Unauthorized access to notebook", exc_info=ex)

        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"message": "Unauthorized access to notebook"},
        )

    return await call_next(request)


def build_marimo_server(include_code: bool = True):
    """Builds the ASGI app for Marimo, which serves the notebooks as web applications."""

    marimo_server = marimo.create_asgi_app(include_code=include_code)

    for nb_enum_item, nb_module in ALL_NOTEBOOKS.items():
        nb_path = f"{Prefixes.NOTEBOOK.value}/{nb_enum_item.value}"
        nb_root = os.path.abspath(nb_module.__file__)
        marimo_server = marimo_server.with_app(path=nb_path, root=nb_root)
        _logger.info("Mounted notebook %s at %s", nb_root, nb_path)

    return marimo_server


app.mount("/", build_marimo_server().build())
