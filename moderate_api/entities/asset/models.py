import enum
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from pydantic import validator
from sqlalchemy import Column, Index, Text, or_, select
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlmodel import Field, Relationship, SQLModel

from moderate_api.db import AsyncSessionDep, build_tsvector_computed
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


def _now_factory() -> datetime:
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


class AssetBase(SQLModel):
    uuid: str = Field(default_factory=_uuid_factory)
    name: str
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    meta: Optional[Dict] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_now_factory, index=True)


class UploadedS3ObjectBase(SQLModel):
    key: str = Field(unique=True)
    tags: Optional[Dict] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_now_factory, index=True)
    series_id: Optional[str]
    sha256_hash: str
    proof_id: Optional[str]
    meta: Optional[Dict] = Field(default=None, sa_column=Column(JSONB))
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))


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

    _targs = [
        Index("ix_s3obj_meta", "meta", postgresql_using="gin"),
        Index("ix_s3obj_tags", "tags", postgresql_using="gin"),
    ]

    # Only create these indexes if we are not running tests to avoid
    # having to deal with creating extensions in the test database.
    # These indexes are here to speed up LIKE queries.
    if not os.getenv("PYTEST_VERSION"):
        _targs.extend(
            [
                Index(
                    "ix_s3obj_like_key",
                    "key",
                    postgresql_using="gin",
                    postgresql_ops={"description": "gin_trgm_ops"},
                ),
                Index(
                    "ix_s3obj_like_name",
                    "name",
                    postgresql_using="gin",
                    postgresql_ops={"description": "gin_trgm_ops"},
                ),
            ]
        )

    # https://www.postgresql.org/docs/14/datatype-json.html#JSON-INDEXING
    __table_args__ = tuple(_targs)


class Asset(AssetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(default_factory=_uuid_factory, unique=True)
    username: Optional[str]
    access_level: AssetAccessLevels = Field(default=AssetAccessLevels.PRIVATE)

    objects: List[UploadedS3Object] = Relationship(
        back_populates="asset",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "delete"},
    )

    search_vector: Any = Field(
        default=None,
        sa_column=Column(
            TSVECTOR,
            build_tsvector_computed(columns=["name", "description"]),
        ),
    )

    access_requests: List["AccessRequest"] = Relationship(  # type: ignore
        back_populates="asset",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    @validator("access_level", always=True)
    def username_and_access_level_check(cls, access_level, values):
        username = values.get("username")
        if username is None and access_level != AssetAccessLevels.PUBLIC:
            raise ValueError("If username is None then access_level must be PUBLIC")
        return access_level

    __table_args__ = (
        Index("ix_asset_meta", "meta", postgresql_using="gin"),
        Index("ix_asset_search_vector", "search_vector", postgresql_using="gin"),
    )

    class Config:
        arbitrary_types_allowed = True


class UploadedS3ObjectRead(UploadedS3ObjectBase):
    id: int


class UploadedS3ObjectUpdate(SQLModel):
    tags: Optional[Dict]
    meta: Optional[Dict]
    name: Optional[str]
    description: Optional[str]


class AssetCreate(AssetBase):
    access_level: AssetAccessLevels = AssetAccessLevels.PRIVATE
    is_public_ownerless: bool = False


class AssetRead(AssetBase):
    id: int
    objects: List[UploadedS3ObjectRead]
    access_level: AssetAccessLevels
    username: Optional[str]


class AssetUpdate(SQLModel):
    name: Optional[str] = None
    access_level: Optional[AssetAccessLevels] = None


async def find_s3object_by_key_or_id(
    val: Union[str, int], session: AsyncSessionDep
) -> Optional[UploadedS3Object]:
    # Build SQLAlchemy column expressions - type checker may not recognize these as ColumnElement
    where_items = [UploadedS3Object.key == str(val)]  # type: ignore

    try:
        where_items.append(UploadedS3Object.id == int(val))  # type: ignore
    except (ValueError, TypeError):
        pass

    # Use or_ with the column expressions
    stmt = select(UploadedS3Object).where(or_(*where_items))  # type: ignore
    result = await session.execute(stmt)
    s3object: Optional[UploadedS3Object] = result.scalar_one_or_none()
    return s3object


async def get_s3object_size_mib(s3_object: UploadedS3Object, s3: S3ClientDep) -> float:
    # Note: This function signature suggests s3 should be an actual S3 client
    # The type error indicates S3ClientDep might not be properly configured
    # For now, we'll add a type ignore to preserve existing business logic
    response = await s3.head_object(Bucket=s3_object.bucket, Key=s3_object.key)  # type: ignore
    size_in_mib = response["ContentLength"] / (1024**2)
    return size_in_mib


async def find_s3object_pending_quality_check(
    session: AsyncSessionDep, username_filter: Optional[str] = None
) -> List[UploadedS3Object]:
    if username_filter:
        # Select Asset.id column specifically
        stmt = select(Asset.id).where(Asset.username == username_filter)  # type: ignore
        result = await session.execute(stmt)
        asset_ids = list(result.scalars().all())
        # Create selector with proper column expression
        selector = [UploadedS3Object.asset_id.in_(asset_ids)]  # type: ignore
    else:
        selector = None

    # Type cast the result to the expected type since we know it returns UploadedS3Object instances
    results = await find_by_json_key(
        sql_model=UploadedS3Object,
        session=session,
        json_column="meta",
        json_key=S3ObjectWellKnownMetaKeys.PENDING_QUALITY_CHECK.value,
        json_value=True,
        selector=selector,
    )
    return [result for result in results if isinstance(result, UploadedS3Object)]


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
    object_ids: List[int],
    session: AsyncSessionDep,
    username_filter: Optional[str] = None,
) -> List[Asset]:
    stmt = (
        select(Asset).join(UploadedS3Object).where(UploadedS3Object.id.in_(object_ids))  # type: ignore
    )

    if username_filter:
        stmt = stmt.where(Asset.username == username_filter)  # type: ignore

    result = await session.execute(stmt)
    assets = result.scalars().all()
    # Convert Sequence to List for type compatibility
    return list(assets)


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
