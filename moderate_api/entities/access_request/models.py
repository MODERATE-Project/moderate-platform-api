import logging
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel, select

from moderate_api.authz.user import User
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.asset.models import Asset
from moderate_api.utils.factories import now_factory

_logger = logging.getLogger(__name__)


class AccessRequestBase(SQLModel):  # type: ignore[misc]
    description: str | None


class AccessRequest(AccessRequestBase, table=True):  # type: ignore[call-arg, misc]
    id: int | None = Field(default=None, primary_key=True)
    requester_username: str
    allowed: bool | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=now_factory, index=True)
    validated_at: datetime | None = Field(default=None, nullable=True)
    validator_username: str | None = Field(default=None, nullable=True)
    asset_id: int = Field(foreign_key="asset.id")

    asset: Asset = Relationship(
        back_populates="access_requests",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "delete"},
    )


class AccessRequestCreate(AccessRequestBase):  # type: ignore[misc]
    asset_id: int


class AccessRequestRead(AccessRequestBase):  # type: ignore[misc]
    id: int
    requester_username: str
    allowed: bool | None
    created_at: datetime
    validated_at: datetime | None
    validator_username: str | None
    asset_id: int


class AccessRequestUpdate(AccessRequestBase):  # type: ignore[misc]
    pass


def can_approve_access_request(user: User, access_request: AccessRequest) -> bool:
    if user.is_admin:
        return True

    if access_request.asset.username == user.username:
        return True

    return False


async def valid_access_request_exists(
    requester_username: str, asset: Asset, session: AsyncSessionDep
) -> bool:
    result = await session.execute(
        select(AccessRequest)
        .where(AccessRequest.requester_username == requester_username)
        .where(AccessRequest.asset_id == asset.id)
        .where(AccessRequest.allowed.is_(True))  # type: ignore[union-attr]
        .order_by(AccessRequest.validated_at.desc())  # type: ignore[union-attr]
        .limit(1)
    )

    access_request: AccessRequest | None = result.scalars().first()

    return access_request is not None
