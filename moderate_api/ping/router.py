import datetime
import platform

from fastapi import APIRouter, Depends, Request
from typing_extensions import Annotated

from moderate_api.auth import User, get_user
from moderate_api.ping.models import PingResponse

_TAG_PING = "Ping"

router = APIRouter()


@router.get("/", response_model=PingResponse, tags=[_TAG_PING])
async def respond_to_ping(request: Request, user: Annotated[User, Depends(get_user)]):
    """Respond to a ping request with the current Python version and UTC time."""

    return {
        "python_version": platform.python_version(),
        "datetime": datetime.datetime.utcnow(),
        "request_headers": dict(request.headers),
        "user": user.to_dict() if user else None,
    }
