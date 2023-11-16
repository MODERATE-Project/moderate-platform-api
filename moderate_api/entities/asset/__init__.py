import logging
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import JSON
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel

from moderate_api.authz import UserDep, UserSelectorBuilder
from moderate_api.authz.user import User
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
from moderate_api.enums import Actions, Entities
from moderate_api.object_storage import S3ClientDep

_logger = logging.getLogger(__name__)

_TAG = "Data assets"
_ENTITY = Entities.ASSET


class AssetBase(SQLModel):
    uuid: str
    name: str


class UploadedS3Object(BaseModel):
    Bucket: str
    ETag: str
    Key: str
    Location: str


class Asset(AssetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    objects: Optional[List[UploadedS3Object]] = Field(sa_type=JSON)


class AssetCreate(AssetBase):
    pass


class AssetRead(AssetBase):
    id: int


class AssetUpdate(SQLModel):
    name: Optional[str] = None


async def build_selector(user: User, session: AsyncSession) -> UserSelectorBuilder:
    return [Asset.username == user.username]


async def build_create_patch(
    user: User, session: AsyncSession
) -> Optional[Dict[str, Any]]:
    return {Asset.username.key: user.username}


router = APIRouter()


@router.post("/{entity_id}/object", tags=[_TAG])
async def upload_object(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    entity_id: int,
    s3: S3ClientDep,
    settings: SettingsDep,
    obj: UploadFile = File(...),
):
    user.enforce_raise(obj=_ENTITY.value, act=Actions.UPDATE.value)
    user_selector = await build_selector(user=user, session=session)

    the_asset = await select_one(
        sql_model=Asset,
        entity_id=entity_id,
        session=session,
        user_selector=user_selector,
    )

    chunk_size = 6 * 1024**2
    parts = []
    part_number = 1
    # ToDo: Slugify the object name
    obj_key = obj.filename
    # ToDo: Use a different bucket for each user
    bucket_name = settings.s3.bucket

    multipart_upload = await s3.create_multipart_upload(
        Bucket=settings.s3.bucket, Key=obj_key
    )

    while True:
        chunk = await obj.read(chunk_size)

        if not chunk:
            break

        part = await s3.upload_part(
            Bucket=bucket_name,
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
        Bucket=bucket_name,
        Key=obj_key,
        UploadId=multipart_upload["UploadId"],
        MultipartUpload={"Parts": parts},
    )

    the_asset.objects = the_asset.objects or []
    the_asset.objects.append(UploadedS3Object(**result_s3_upload).dict())
    session.add(the_asset)
    await session.commit()
    refreshed = await session.get(Asset, entity_id)

    return refreshed.objects


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
