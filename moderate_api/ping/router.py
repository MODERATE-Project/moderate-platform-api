import datetime
import platform

from fastapi import APIRouter, Request

from moderate_api.authz import OptionalUserDep
from moderate_api.enums import Tags
from moderate_api.message_queue import RabbitDep
from moderate_api.ping.models import PingResponse

_TAG = "Ping"

router = APIRouter()


async def _respond_to_ping(request: Request, user: OptionalUserDep, rabbit: RabbitDep):
    """Respond to a ping request with the current Python version and UTC time."""

    return {
        "python_version": platform.python_version(),
        "datetime": datetime.datetime.now(datetime.timezone.utc),
        "request_headers": dict(request.headers),
        "user": user.to_dict() if user else None,
        "broker_connection": rabbit.channel.is_initialized if rabbit else False,
    }


router.add_api_route(
    "",
    _respond_to_ping,
    methods=["GET"],
    response_model=PingResponse,
    tags=[_TAG],
)

router.add_api_route(
    "/public",
    _respond_to_ping,
    methods=["GET"],
    response_model=PingResponse,
    tags=[_TAG, Tags.PUBLIC.value],
)
