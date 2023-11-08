import datetime
from typing import Optional

from pydantic import BaseModel


class PingResponse(BaseModel):
    python_version: str
    datetime: datetime.datetime
    request_headers: dict
    user: Optional[dict]
