import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import Column, Index, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from moderate_api.db import AsyncSessionDep

_logger = logging.getLogger(__name__)


def _now_factory() -> datetime:
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


class UserMetaBase(SQLModel):
    meta: Optional[Dict] = Field(default=None, sa_column=Column(JSONB))


class UserMeta(UserMetaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    created_at: datetime = Field(default_factory=_now_factory)
    trust_did: Optional[str] = Field(default=None, unique=True)

    __table_args__ = (Index("ix_usermeta_meta", "meta", postgresql_using="gin"),)


class UserMetaCreate(UserMetaBase):
    username: str
    trust_did: Optional[str]


class UserMetaRead(UserMetaBase):
    username: str
    created_at: datetime
    trust_did: Optional[str]


class UserMetaUpdate(UserMetaBase):
    pass


async def ensure_user_meta(username: str, session: AsyncSessionDep) -> UserMeta:
    stmt = select(UserMeta).where(UserMeta.username == username)
    result = await session.execute(stmt)
    user_meta: UserMeta = result.scalar_one_or_none()

    if not user_meta:
        _logger.info("Creating UserMeta for %s", username)
        user_meta = UserMeta(username=username)
        session.add(user_meta)
        await session.commit()
        await session.refresh(user_meta)

    return user_meta


async def get_did_for_username(
    username: str, session: AsyncSessionDep
) -> Optional[str]:
    stmt = select(UserMeta).where(UserMeta.username == username)
    result = await session.execute(stmt)
    user_meta: UserMeta = result.scalar_one_or_none()

    if not user_meta or not user_meta.trust_did:
        _logger.info(f"User {username} not found or does not have a DID")
        return None

    return user_meta.trust_did
