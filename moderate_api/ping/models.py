import datetime

from pydantic import BaseModel


class PingResponse(BaseModel):
    python_version: str
    datetime: datetime.datetime
