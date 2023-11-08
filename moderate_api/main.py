import enum
from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI

import moderate_api.ping.router


class Prefixes(enum.Enum):
    """The prefixes for the different API endpoints."""

    PING = "/ping"


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
)

app.include_router(moderate_api.ping.router.router, prefix=Prefixes.PING.value)
