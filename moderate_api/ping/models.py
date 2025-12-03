import datetime
from typing import Any

from pydantic import BaseModel


class PingResponse(BaseModel):
    python_version: str
    datetime: datetime.datetime
    request_headers: dict[str, Any]
    user: dict[str, Any] | None
    broker_connection: bool | None
