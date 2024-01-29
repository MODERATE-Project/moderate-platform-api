import enum
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import validator
from sqlalchemy import Column, Text
from sqlmodel import JSON, Field, Relationship, SQLModel


class AssetAccessLevels(enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    VISIBLE = "visible"


class AssetBase(SQLModel):
    uuid: str = Field(default_factory=uuid.uuid4)
    name: str


class UploadedS3ObjectBase(SQLModel):
    key: str = Field(unique=True)
    tags: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    series_id: Optional[str]


class UploadedS3Object(UploadedS3ObjectBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bucket: str
    etag: str
    location: str
    asset_id: Optional[int] = Field(default=None, foreign_key="asset.id")

    # It is necessary to set "lazy" to "selectin"
    # for relationships to work with the async interface
    # https://github.com/tiangolo/sqlmodel/issues/74
    asset: Optional["Asset"] = Relationship(
        back_populates="objects",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class Asset(AssetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(default_factory=uuid.uuid4, unique=True)
    username: Optional[str]
    access_level: AssetAccessLevels = Field(default=AssetAccessLevels.PRIVATE)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    meta: Optional[Dict] = Field(default=None, sa_column=Column(JSON))

    objects: List[UploadedS3Object] = Relationship(
        back_populates="asset",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "delete"},
    )

    @validator("access_level", always=True)
    def username_and_access_level_check(cls, access_level, values):
        username = values.get("username")
        if username is None and access_level != AssetAccessLevels.PUBLIC:
            raise ValueError("If username is None then access_level must be PUBLIC")
        return access_level


class UploadedS3ObjectRead(UploadedS3ObjectBase):
    id: int


class AssetCreate(AssetBase):
    access_level: AssetAccessLevels = AssetAccessLevels.PRIVATE
    is_public_ownerless: bool = False


class AssetRead(AssetBase):
    id: int
    objects: List[UploadedS3ObjectRead]
    access_level: AssetAccessLevels


class AssetUpdate(SQLModel):
    name: Optional[str] = None
    access_level: Optional[AssetAccessLevels] = None
