from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import Column
from sqlmodel import JSON, Field, SQLModel


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
