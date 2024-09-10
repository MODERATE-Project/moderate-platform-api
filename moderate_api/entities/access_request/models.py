import logging
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from moderate_api.authz.user import User
from moderate_api.entities.asset.models import Asset

_logger = logging.getLogger(__name__)


def _now_factory() -> datetime:
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


class AccessRequestBase(SQLModel):
    description: Optional[str]


class AccessRequest(AccessRequestBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    requester_username: str
    allowed: Optional[bool] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=_now_factory, index=True)
    validated_at: Optional[datetime] = Field(default=None, nullable=True)
    validator_username: Optional[str] = Field(default=None, nullable=True)
    asset_id: int = Field(foreign_key="asset.id")

    asset: Asset = Relationship(
        back_populates="access_requests",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "delete"},
    )


class AccessRequestCreate(AccessRequestBase):
    asset_id: int


class AccessRequestRead(AccessRequestBase):
    id: int
    requester_username: str
    allowed: Optional[bool]
    created_at: datetime
    validated_at: Optional[datetime]
    validator_username: Optional[str]
    asset_id: int


class AccessRequestUpdate(AccessRequestBase):
    pass


def can_approve_access_request(user: User, access_request: AccessRequest) -> bool:
    if user.is_admin:
        return True

    if access_request.asset.username == user.username:
        return True

    return False
