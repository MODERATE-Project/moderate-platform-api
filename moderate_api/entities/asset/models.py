import copy
import enum
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import validator
from sqlalchemy import Column, Index, Text, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from moderate_api.db import AsyncSessionDep
from moderate_api.entities.crud import find_by_json_key, update_json_key
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
    session: AsyncSessionDep, username_filter: str = None
) -> List[UploadedS3Object]:
    if username_filter:
        stmt = select(Asset.id).where(Asset.username == username_filter)
        result = await session.execute(stmt)
        asset_ids = result.scalars().all()
        selector = [UploadedS3Object.asset_id.in_(asset_ids)]
    else:
        selector = None

    return await find_by_json_key(
        sql_model=UploadedS3Object,
        session=session,
        json_column="meta",
        json_key=S3ObjectWellKnownMetaKeys.PENDING_QUALITY_CHECK.value,
        json_value=True,
        selector=selector,
    )


async def update_s3object_quality_check_flag(
    ids: List[int], session: AsyncSessionDep, value: bool
):
    return await update_json_key(
        sql_model=UploadedS3Object,
        session=session,
        primary_keys=ids,
        json_column="meta",
        json_key=S3ObjectWellKnownMetaKeys.PENDING_QUALITY_CHECK.value,
        json_value=value,
    )


async def find_assets_for_objects(
    object_ids: List[int], session: AsyncSessionDep, username_filter: str = None
) -> List[Asset]:
    stmt = (
        select(Asset).join(UploadedS3Object).where(UploadedS3Object.id.in_(object_ids))
    )

    if username_filter:
        stmt = stmt.where(Asset.username == username_filter)

    result = await session.execute(stmt)
    assets = result.scalars().all()
    return assets


async def filter_object_ids_by_username(
    object_ids: List[int], session: AsyncSessionDep, username: str
) -> List[int]:
    allowed_assets = await find_assets_for_objects(
        object_ids=object_ids,
        session=session,
        username_filter=username,
    )

    allowed_asset_object_ids = set(
        [obj.id for asset in allowed_assets for obj in asset.objects]
    )

    filtered_asset_object_ids = [
        obj_id for obj_id in object_ids if obj_id in allowed_asset_object_ids
    ]

    return filtered_asset_object_ids
