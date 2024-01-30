import logging
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import Column, select
from sqlmodel import JSON, Field, SQLModel

from moderate_api.db import AsyncSessionDep

_logger = logging.getLogger(__name__)


class UserMetaBase(SQLModel):
    meta: Optional[Dict] = Field(default=None, sa_column=Column(JSON))


class UserMeta(UserMetaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    trust_did: Optional[str] = Field(default=None, unique=True)


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
