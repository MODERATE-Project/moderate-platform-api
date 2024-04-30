import copy
import enum
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import validator
from sqlalchemy import Column, Index, Text, cast, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Field, Relationship, SQLModel

from moderate_api.db import AsyncSessionDep
from moderate_api.object_storage import S3ClientDep


class S3ObjectWellKnownMetaKeys(enum.Enum):
    PENDING_QUALITY_CHECK = "pending_quality_check"


class AssetAccessLevels(enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    VISIBLE = "visible"


def _uuid_factory() -> str:
    return str(uuid.uuid4())


class AssetBase(SQLModel):
    uuid: str = Field(default_factory=_uuid_factory)
    name: str
    meta: Optional[Dict] = Field(default=None, sa_column=Column(JSONB))


class UploadedS3ObjectBase(SQLModel):
    key: str = Field(unique=True)
    tags: Optional[Dict] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    series_id: Optional[str]
    sha256_hash: str
    proof_id: Optional[str]
    meta: Optional[Dict] = Field(default=None, sa_column=Column(JSONB))


class UploadedS3Object(UploadedS3ObjectBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bucket: str
    etag: str
    location: str
    asset_id: int = Field(foreign_key="asset.id")

    # It is necessary to set "lazy" to "selectin"
    # for relationships to work with the async interface
    # https://github.com/tiangolo/sqlmodel/issues/74
    asset: Optional["Asset"] = Relationship(
        back_populates="objects",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    # https://www.postgresql.org/docs/14/datatype-json.html#JSON-INDEXING
    __table_args__ = (
        Index("ix_s3obj_meta", "meta", postgresql_using="gin"),
        Index("ix_s3obj_tags", "tags", postgresql_using="gin"),
    )


class Asset(AssetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(default_factory=_uuid_factory, unique=True)
    username: Optional[str]
    access_level: AssetAccessLevels = Field(default=AssetAccessLevels.PRIVATE)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))

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

    __table_args__ = (Index("ix_asset_meta", "meta", postgresql_using="gin"),)


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


async def find_s3object_by_key_or_id(
    val: Union[str, int], session: AsyncSessionDep
) -> Union[UploadedS3Object, None]:
    where_items = [UploadedS3Object.key == str(val)]

    try:
        where_items.append(UploadedS3Object.id == int(val))
    except (ValueError, TypeError):
        pass

    stmt = select(UploadedS3Object).where(or_(*where_items))
    result = await session.execute(stmt)
    s3object: UploadedS3Object = result.scalar_one_or_none()
    return s3object


async def get_s3object_size_mib(s3_object: UploadedS3Object, s3: S3ClientDep) -> float:
    response = await s3.head_object(Bucket=s3_object.bucket, Key=s3_object.key)
    size_in_mib = response["ContentLength"] / (1024**2)
    return size_in_mib


async def find_s3object_pending_quality_check(
    session: AsyncSessionDep,
) -> List[UploadedS3Object]:
    stmt = select(UploadedS3Object).filter(
        UploadedS3Object.meta[S3ObjectWellKnownMetaKeys.PENDING_QUALITY_CHECK.value]
        == cast(True, JSONB)
    )

    result = await session.execute(stmt)
    s3objects: List[UploadedS3Object] = result.scalars().all()

    return s3objects


async def update_s3object_quality_check_flag(
    ids: List[int], session: AsyncSessionDep, value: bool
):
    ids = ids if isinstance(ids, list) else [ids]
    stmt = select(UploadedS3Object).where(UploadedS3Object.id.in_(ids))
    result = await session.execute(stmt)
    s3objects = result.scalars().all()

    for s3object in s3objects:
        meta = s3object.meta or {}
        meta.update({S3ObjectWellKnownMetaKeys.PENDING_QUALITY_CHECK.value: value})
        s3object.meta = meta
        flag_modified(s3object, "meta")
        session.add(s3object)

    await session.commit()
