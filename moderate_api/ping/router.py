import datetime
import platform

from fastapi import APIRouter, Request

from moderate_api.ping.models import PingResponse

_TAG_PING = "Ping"

router = APIRouter()


@router.get("/", response_model=PingResponse, tags=[_TAG_PING])
async def respond_to_ping(request: Request):
    """Respond to a ping request with the current Python version and UTC time."""

    return {
        "python_version": platform.python_version(),
        "datetime": datetime.datetime.utcnow(),
        "request_headers": dict(request.headers),
    }
