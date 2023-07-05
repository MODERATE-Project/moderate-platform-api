import enum

import pkg_resources
from fastapi import FastAPI

import moderate_api.ping.router


class Prefixes(enum.Enum):
    """The prefixes for the different API endpoints."""

    PING = "/ping"


_pkg_version = pkg_resources.get_distribution("moderate_api").version

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
