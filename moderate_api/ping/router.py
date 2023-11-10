import datetime
import platform
from typing import Union

from fastapi import APIRouter, Request

from moderate_api.authz import OptionalUserDep, User, UserDep
from moderate_api.ping.models import PingResponse

_TAG_PING = "Ping"

router = APIRouter()


async def build_ping_response(request: Request, user: Union[User, None]):
    return {
        "python_version": platform.python_version(),
        "datetime": datetime.datetime.utcnow(),
        "request_headers": dict(request.headers),
        "user": user.to_dict() if user else None,
    }


@router.get("/", response_model=PingResponse, tags=[_TAG_PING])
async def respond_to_ping(request: Request, user: OptionalUserDep):
    """Respond to a ping request with the current Python version and UTC time."""

    return await build_ping_response(request=request, user=user)


@router.get("/auth", response_model=PingResponse, tags=[_TAG_PING])
async def respond_to_ping(request: Request, user: UserDep):
    """Respond to a ping request with the current Python version and UTC time
    while ensuring the user is authenticated."""

    return await build_ping_response(request=request, user=user)
