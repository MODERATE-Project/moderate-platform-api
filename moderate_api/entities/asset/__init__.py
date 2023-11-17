import logging
import os
import uuid
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Query, UploadFile
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, Relationship, SQLModel

from moderate_api.authz import UserDep, UserSelectorBuilder
from moderate_api.authz.user import User
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.crud import (
    CrudFiltersQuery,
    CrudSortsQuery,
    create_one,
    delete_one,
    read_many,
    read_one,
    select_one,
    update_one,
)
from moderate_api.enums import Actions, Entities
from moderate_api.object_storage import S3ClientDep, ensure_bucket

_logger = logging.getLogger(__name__)

_TAG = "Data assets"
_ENTITY = Entities.ASSET
_CHUNK_SIZE = 16 * 1024**2


class UploadedS3Object(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bucket: str
    etag: str
    key: str
    location: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    asset_id: Optional[int] = Field(default=None, foreign_key="asset.id")

    # It is necessary to set "lazy" to "selectin"
    # for relationships to work with the async interface
    # https://github.com/tiangolo/sqlmodel/issues/74
    asset: Optional["Asset"] = Relationship(
        back_populates="objects",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class AssetBase(SQLModel):
    uuid: str
    name: str


class Asset(AssetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str

    objects: List[UploadedS3Object] = Relationship(
        back_populates="asset", sa_relationship_kwargs={"lazy": "selectin"}
    )


class AssetCreate(AssetBase):
    pass


class AssetRead(AssetBase):
    id: int
    objects: List[UploadedS3Object]


class AssetUpdate(SQLModel):
    name: Optional[str] = None


async def build_selector(user: User, session: AsyncSession) -> UserSelectorBuilder:
    return [Asset.username == user.username]


async def build_create_patch(
    user: User, session: AsyncSession
) -> Optional[Dict[str, Any]]:
    return {Asset.username.key: user.username}


router = APIRouter()


def build_object_key(obj: UploadFile) -> str:
    ext = os.path.splitext(obj.filename)[1]
    safe_name = slugify(obj.filename)
    return "{}-{}{}".format(safe_name, uuid.uuid4().hex, ext)


def get_user_assets_bucket(user: User) -> str:
    return f"moderate-{user.username}-assets"


@router.post("/{entity_id}/object", response_model=AssetRead, tags=[_TAG])
async def upload_object(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    entity_id: int,
    s3: S3ClientDep,
    obj: UploadFile = File(...),
):
    """Uploads a new object (e.g. a CSV dataset file) to MODERATE's
    object storage service and associates it with the _Asset_ given by `entity_id`.
    Note that an _Asset_ may have many objects."""

    user.enforce_raise(obj=_ENTITY.value, act=Actions.UPDATE.value)
    user_selector = await build_selector(user=user, session=session)

    the_asset = await select_one(
        sql_model=Asset,
        entity_id=entity_id,
        session=session,
        user_selector=user_selector,
    )

    obj_key = build_object_key(obj=obj)
    _logger.info("Uploading object to S3: %s", obj_key)

    user_bucket = get_user_assets_bucket(user=user)
    _logger.debug("Ensuring user assets bucket exists: %s", user_bucket)
    await ensure_bucket(s3=s3, bucket=user_bucket)

    _logger.debug("Creating multipart upload (object=%s)", obj_key)
    multipart_upload = await s3.create_multipart_upload(Bucket=user_bucket, Key=obj_key)

    parts = []
    part_number = 1

    while True:
        chunk = await obj.read(_CHUNK_SIZE)

        if not chunk:
            break

        part = await s3.upload_part(
            Bucket=user_bucket,
            Key=obj_key,
            PartNumber=part_number,
            UploadId=multipart_upload["UploadId"],
            Body=BytesIO(chunk),
        )

        parts.append({"PartNumber": part_number, "ETag": part["ETag"]})
        part_number += 1

    _logger.debug(
        "Completing multipart upload (object=%s) (chunks=%s)", obj_key, len(parts)
    )

    result_s3_upload = await s3.complete_multipart_upload(
        Bucket=user_bucket,
        Key=obj_key,
        UploadId=multipart_upload["UploadId"],
        MultipartUpload={"Parts": parts},
    )

    uploaded_s3_object = UploadedS3Object(
        bucket=result_s3_upload["Bucket"],
        etag=result_s3_upload["ETag"],
        key=result_s3_upload["Key"],
        location=result_s3_upload["Location"],
        asset_id=the_asset.id,
    )

    session.add(uploaded_s3_object)
    await session.commit()
    await session.refresh(the_asset)

    return the_asset


@router.post("/", response_model=AssetRead, tags=[_TAG])
async def create_asset(*, user: UserDep, session: AsyncSessionDep, entity: AssetCreate):
    """Create a new asset."""

    entity_create_patch = await build_create_patch(user=user, session=session)

    return await create_one(
        user=user,
        entity=_ENTITY,
        sql_model=Asset,
        session=session,
        entity_create=entity,
        entity_create_patch=entity_create_patch,
    )


@router.get("/", response_model=List[AssetRead], tags=[_TAG])
async def read_assets(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    filters: Optional[str] = CrudFiltersQuery,
    sorts: Optional[str] = CrudSortsQuery,
):
    """Read many assets."""

    user_selector = await build_selector(user=user, session=session)

    return await read_many(
        user=user,
        entity=_ENTITY,
        sql_model=Asset,
        session=session,
        offset=offset,
        limit=limit,
        user_selector=user_selector,
        json_filters=filters,
        json_sorts=sorts,
    )


@router.get("/{entity_id}", response_model=AssetRead, tags=[_TAG])
async def read_asset(*, user: UserDep, session: AsyncSessionDep, entity_id: int):
    """Read one asset."""

    user_selector = await build_selector(user=user, session=session)

    return await read_one(
        user=user,
        entity=_ENTITY,
        sql_model=Asset,
        session=session,
        entity_id=entity_id,
        user_selector=user_selector,
    )


@router.patch("/{entity_id}", response_model=AssetRead, tags=[_TAG])
async def update_asset(
    *, user: UserDep, session: AsyncSessionDep, entity_id: int, entity: AssetUpdate
):
    """Update one asset."""

    user_selector = await build_selector(user=user, session=session)

    return await update_one(
        user=user,
        entity=_ENTITY,
        sql_model=Asset,
        session=session,
        entity_id=entity_id,
        entity_update=entity,
        user_selector=user_selector,
    )


@router.delete("/{entity_id}", tags=[_TAG])
async def delete_asset(*, user: UserDep, session: AsyncSessionDep, entity_id: int):
    """Delete one asset."""

    user_selector = await build_selector(user=user, session=session)

    return await delete_one(
        user=user,
        entity=_ENTITY,
        sql_model=Asset,
        session=session,
        entity_id=entity_id,
        user_selector=user_selector,
    )
