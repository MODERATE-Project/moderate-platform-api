import enum
import logging
import os
import uuid
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from slugify import slugify
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BinaryExpression
from sqlmodel import Field, Relationship, SQLModel, or_, select

from moderate_api.authz import User, UserDep
from moderate_api.authz.user import OptionalUserDep, User
from moderate_api.config import SettingsDep
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
from moderate_api.enums import Actions, Entities, Tags
from moderate_api.object_storage import S3ClientDep, ensure_bucket

_logger = logging.getLogger(__name__)

_TAG = "Data assets"
_ENTITY = Entities.ASSET
_CHUNK_SIZE = 16 * 1024**2


class AssetAccessLevels(enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    VISIBLE = "visible"


class UploadedS3ObjectBase(SQLModel):
    key: str


class UploadedS3Object(UploadedS3ObjectBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bucket: str
    etag: str
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


class UploadedS3ObjectRead(UploadedS3ObjectBase):
    id: int
    created_at: datetime


class AssetBase(SQLModel):
    uuid: str
    name: str


class Asset(AssetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    access_level: AssetAccessLevels = Field(default=AssetAccessLevels.PRIVATE)

    objects: List[UploadedS3Object] = Relationship(
        back_populates="asset",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "delete"},
    )


class AssetCreate(AssetBase):
    access_level: AssetAccessLevels = AssetAccessLevels.PRIVATE


class AssetRead(AssetBase):
    id: int
    objects: List[UploadedS3ObjectRead]
    access_level: AssetAccessLevels


class AssetUpdate(SQLModel):
    name: Optional[str] = None
    access_level: Optional[AssetAccessLevels] = None


async def build_selector(user: User, session: AsyncSession) -> List[BinaryExpression]:
    return [
        or_(
            Asset.username == user.username,
            Asset.access_level == AssetAccessLevels.PUBLIC,
        )
    ]


async def build_create_patch(
    user: User, session: AsyncSession
) -> Optional[Dict[str, Any]]:
    return {Asset.username.key: user.username}


router = APIRouter()


def build_object_key(obj: UploadFile, user: User) -> str:
    ext = os.path.splitext(obj.filename)[1]
    safe_name = slugify(obj.filename)

    return os.path.join(
        f"{user.username}-assets",
        "{}-{}{}".format(safe_name, uuid.uuid4().hex, ext),
    )


class AssetDownloadURL(BaseModel):
    key: str
    download_url: str


async def get_asset_presigned_urls(
    s3: S3ClientDep, asset: Asset, expiration_secs: Optional[int] = 3600
) -> List[AssetDownloadURL]:
    ret = []

    for s3_object in asset.objects:
        download_url = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": s3_object.bucket, "Key": s3_object.key},
            ExpiresIn=expiration_secs,
        )

        ret.append(AssetDownloadURL(key=s3_object.key, download_url=download_url))

    return ret


async def _download_asset(
    *,
    user: OptionalUserDep,
    session: AsyncSessionDep,
    s3: S3ClientDep,
    id: int,
    expiration_secs: int = Query(default=600, ge=60, le=int(3600 * 24)),
):
    stmt = select(Asset).where(Asset.id == id)
    or_constraints = []

    if user and user.is_admin:
        _logger.debug("User is admin, allowing access to all assets")
    else:
        or_constraints.append(Asset.access_level == AssetAccessLevels.PUBLIC)

        if user:
            or_constraints.append(Asset.username == user.username)

    stmt = stmt.where(or_(*or_constraints))
    result = await session.execute(stmt)
    asset = result.one_or_none()

    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    asset = asset[0]

    return await get_asset_presigned_urls(
        s3=s3, asset=asset, expiration_secs=expiration_secs
    )


router.add_api_route(
    "/{id}/download-urls",
    _download_asset,
    methods=["GET"],
    response_model=List[AssetDownloadURL],
    tags=[_TAG],
)

router.add_api_route(
    "/public/{id}/download-urls",
    _download_asset,
    methods=["GET"],
    response_model=List[AssetDownloadURL],
    tags=[_TAG, Tags.PUBLIC.value],
)


@router.post("/{id}/object", response_model=UploadedS3Object, tags=[_TAG])
async def upload_object(
    user: UserDep,
    session: AsyncSessionDep,
    id: int,
    s3: S3ClientDep,
    settings: SettingsDep,
    obj: UploadFile = File(...),
):
    """Uploads a new object (e.g. a CSV dataset file) to MODERATE's
    object storage service and associates it with the _Asset_ given by `id`.
    Note that an _Asset_ may have many objects."""

    user.enforce_raise(obj=_ENTITY.value, act=Actions.UPDATE.value)
    user_selector = await build_selector(user=user, session=session)

    the_asset = await select_one(
        sql_model=Asset,
        entity_id=id,
        session=session,
        user_selector=user_selector,
    )

    obj_key = build_object_key(obj=obj, user=user)
    _logger.info("Uploading object to S3: %s", obj_key)

    user_bucket = settings.s3.bucket
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

    return uploaded_s3_object


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


async def _read_assets(
    *,
    user: OptionalUserDep,
    session: AsyncSessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    filters: Optional[str] = CrudFiltersQuery,
    sorts: Optional[str] = CrudSortsQuery,
):
    """Query the catalog for assets."""

    if user:
        user_selector = await build_selector(user=user, session=session)
    else:
        user_selector: List[BinaryExpression] = [
            Asset.access_level == AssetAccessLevels.PUBLIC
        ]

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


router.add_api_route(
    "/",
    _read_assets,
    methods=["GET"],
    response_model=List[AssetRead],
    tags=[_TAG],
)

router.add_api_route(
    "/public",
    _read_assets,
    methods=["GET"],
    response_model=List[AssetRead],
    tags=[_TAG, Tags.PUBLIC.value],
)


@router.get("/{id}", response_model=AssetRead, tags=[_TAG])
async def read_asset(*, user: UserDep, session: AsyncSessionDep, id: int):
    """Read one asset."""

    user_selector = await build_selector(user=user, session=session)

    return await read_one(
        user=user,
        entity=_ENTITY,
        sql_model=Asset,
        session=session,
        entity_id=id,
        user_selector=user_selector,
    )


@router.patch("/{id}", response_model=AssetRead, tags=[_TAG])
async def update_asset(
    *, user: UserDep, session: AsyncSessionDep, id: int, entity: AssetUpdate
):
    """Update one asset."""

    user_selector = await build_selector(user=user, session=session)

    return await update_one(
        user=user,
        entity=_ENTITY,
        sql_model=Asset,
        session=session,
        entity_id=id,
        entity_update=entity,
        user_selector=user_selector,
    )


@router.delete("/{id}", tags=[_TAG])
async def delete_asset(*, user: UserDep, session: AsyncSessionDep, id: int):
    """Delete one asset."""

    user_selector = await build_selector(user=user, session=session)

    return await delete_one(
        user=user,
        entity=_ENTITY,
        sql_model=Asset,
        session=session,
        entity_id=id,
        user_selector=user_selector,
    )


@router.delete("/{id}/object/{object_id}", tags=[_TAG])
async def delete_asset_object(
    *, user: UserDep, session: AsyncSessionDep, id: int, object_id: int
):
    """Delete an object from a given data asset."""

    user.enforce_raise(obj=Entities.ASSET.value, act=Actions.DELETE.value)
    user_selector = await build_selector(user=user, session=session)

    the_asset = await read_one(
        user=user,
        entity=_ENTITY,
        sql_model=Asset,
        session=session,
        entity_id=id,
        user_selector=user_selector,
    )

    if not the_asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    select_object = select(UploadedS3Object).where(UploadedS3Object.id == object_id)
    result_object = await session.execute(select_object)
    the_asset_object = result_object.one_or_none()

    if not the_asset_object:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    the_asset_object = the_asset_object[0]
    _logger.info("Deleting asset object: %s", the_asset_object)
    await session.delete(the_asset_object)
    await session.commit()

    return {"ok": True, "asset_id": id, "object_id": object_id}
