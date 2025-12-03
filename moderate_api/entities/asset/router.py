import json
import logging
import os
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel
from slugify import slugify
from sqlalchemy import and_, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BinaryExpression
from sqlmodel import or_, select

from moderate_api.authz.user import OptionalUserDep, User, UserDep
from moderate_api.config import SettingsDep
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.asset import trust_routes
from moderate_api.entities.asset.models import (
    Asset,
    AssetAccessLevels,
    AssetCreate,
    AssetRead,
    AssetUpdate,
    UploadedS3Object,
    UploadedS3ObjectRead,
    UploadedS3ObjectReadWithAsset,
    UploadedS3ObjectUpdate,
    filter_object_ids_by_username,
    find_s3object_pending_quality_check,
    update_s3object_quality_check_flag,
)
from moderate_api.entities.asset.search import (
    search_assets_wrapper,
    search_objects,
    user_asset_visibility_selector,
)
from moderate_api.entities.crud import (
    CrudFiltersQuery,
    CrudSortsQuery,
    create_one,
    delete_one,
    read_many,
    read_one,
    select_one,
    set_response_count_header,
    update_one,
)
from moderate_api.enums import Actions, Entities, Tags
from moderate_api.object_storage import (
    S3ClientDep,
    ensure_bucket,
    upload_file_multipart,
)
from moderate_api.open_metadata import (
    OMProfile,
    get_asset_object_profile,
    search_asset_object,
)

_logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(trust_routes.router)

_TAG = "Data assets"
_ENTITY = Entities.ASSET
_CHUNK_SIZE = 16 * 1024**2


async def build_selector(user: User, session: AsyncSession) -> list[BinaryExpression]:
    # SQLAlchemy column expressions - type: ignore to handle type checker issues
    return [
        or_(  # type: ignore
            Asset.username == user.username,  # type: ignore
            Asset.access_level == AssetAccessLevels.PUBLIC,  # type: ignore
        )
    ]


async def build_create_patch(
    user: User, session: AsyncSession
) -> dict[str, Any] | None:
    return {Asset.username.key: user.username}  # type: ignore


def build_object_key(obj: UploadFile, user: User) -> str:
    if not obj.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File has no filename"
        )

    path_name, ext = os.path.splitext(obj.filename)
    safe_name = slugify(path_name)

    return os.path.join(
        f"{user.username}-assets",
        f"{safe_name}-{str(uuid.uuid4())}{ext}",
    )


class AssetDownloadURL(BaseModel):
    key: str
    download_url: str


async def get_asset_presigned_urls(
    s3: S3ClientDep, asset: Asset, expiration_secs: int | None = 3600
) -> list[AssetDownloadURL]:
    ret = []

    for s3_object in asset.objects:
        download_url = await s3.generate_presigned_url(  # type: ignore
            "get_object",
            Params={"Bucket": s3_object.bucket, "Key": s3_object.key},
            ExpiresIn=expiration_secs,
        )

        ret.append(AssetDownloadURL(key=s3_object.key, download_url=download_url))

    return ret


router.add_api_route(
    "/search",
    search_assets_wrapper,
    methods=["GET"],
    response_model=list[AssetRead],
    tags=[_TAG],
)

router.add_api_route(
    "/public/search",
    search_assets_wrapper,
    methods=["GET"],
    response_model=list[AssetRead],
    tags=[_TAG, Tags.PUBLIC.value],
)


router.add_api_route(
    "/objects/search",
    search_objects,
    methods=["GET"],
    response_model=list[UploadedS3ObjectReadWithAsset],
    tags=[_TAG],
)

router.add_api_route(
    "/public/objects/search",
    search_objects,
    methods=["GET"],
    response_model=list[UploadedS3ObjectReadWithAsset],
    tags=[_TAG, Tags.PUBLIC.value],
)


class AssetObjectProfileResponse(BaseModel):
    profile: OMProfile | None = None
    reason: str | None = None


async def _get_asset_object_profile(
    *,
    user: OptionalUserDep,
    session: AsyncSessionDep,
    settings: SettingsDep,
    object_id: int,
):
    """Retrieves the table profile of an asset object."""

    if (
        settings.open_metadata_service is None
        or not settings.open_metadata_service.endpoint_url
        or not settings.open_metadata_service.bearer_token
    ):
        return AssetObjectProfileResponse(
            reason="Metadata platform service not configured"
        )

    user_selector = user_asset_visibility_selector(user=user)
    user_selector = user_selector if user_selector is not None else true()

    stmt = (
        select(UploadedS3Object, Asset)
        .join(Asset, and_(Asset.id == UploadedS3Object.asset_id, user_selector))  # type: ignore
        .where(UploadedS3Object.id == object_id)  # type: ignore
    )

    result = await session.execute(stmt)
    s3obj = result.scalars().one_or_none()

    if not s3obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        search_result = await search_asset_object(
            asset_object_key=s3obj.key, settings=settings  # type: ignore
        )
    except Exception as exc:
        return AssetObjectProfileResponse(
            reason=f"The request to the metadata service failed: {exc}"
        )

    if not search_result:
        return AssetObjectProfileResponse(
            reason="No matching record found in the metadata service"
        )

    try:
        profile = await get_asset_object_profile(
            asset_object_fqn=search_result.fqn, settings=settings
        )
    except Exception as exc:
        return AssetObjectProfileResponse(
            reason=f"The request to the metadata service failed: {exc}"
        )

    return AssetObjectProfileResponse(profile=profile)


router.add_api_route(
    "/object/{object_id}/profile",
    _get_asset_object_profile,
    methods=["GET"],
    response_model=AssetObjectProfileResponse,
    tags=[_TAG],
)

router.add_api_route(
    "/public/object/{object_id}/profile",
    _get_asset_object_profile,
    methods=["GET"],
    response_model=AssetObjectProfileResponse,
    tags=[_TAG, Tags.PUBLIC.value],
)


class ObjectPendingQuality(BaseModel):
    key: str
    asset_id: int
    id: int


@router.get(
    "/object/quality-check", response_model=list[ObjectPendingQuality], tags=[_TAG]
)
async def get_asset_objects_pending_quality(
    *,
    user: UserDep,
    session: AsyncSessionDep,
):
    """Retrieves the list of asset objects that are pending quality check."""

    if user.is_admin:
        username_filter = None
    else:
        username_filter = user.username

    s3objs = await find_s3object_pending_quality_check(
        session=session, username_filter=username_filter
    )

    return [ObjectPendingQuality(**full_object.model_dump()) for full_object in s3objs]


class AssetObjectFlagQualityRequest(BaseModel):
    asset_object_id: list[int] | int
    pending_quality_check: bool


class AssetObjectFlagQualityResponse(BaseModel):
    asset_object_id: list[int]


@router.post(
    "/object/quality-check", response_model=AssetObjectFlagQualityResponse, tags=[_TAG]
)
async def flag_asset_objects_quality_check(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    body: AssetObjectFlagQualityRequest,
):
    """Update the quality check flag for a list of asset objects."""

    # Normalize to list
    object_ids = (
        body.asset_object_id
        if isinstance(body.asset_object_id, list)
        else [body.asset_object_id]
    )

    if user.is_admin:
        asset_object_ids = object_ids
    else:
        asset_object_ids = await filter_object_ids_by_username(
            object_ids=object_ids,
            session=session,
            username=user.username,
        )

    await update_s3object_quality_check_flag(
        ids=asset_object_ids, session=session, value=body.pending_quality_check
    )

    return AssetObjectFlagQualityResponse(asset_object_id=asset_object_ids)


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

    if len(or_constraints) > 0:
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
    response_model=list[AssetDownloadURL],
    tags=[_TAG],
)

router.add_api_route(
    "/public/{id}/download-urls",
    _download_asset,
    methods=["GET"],
    response_model=list[AssetDownloadURL],
    tags=[_TAG, Tags.PUBLIC.value],
)


@router.get("/object", response_model=list[UploadedS3Object], tags=[_TAG])
async def query_asset_objects(
    *,
    response: Response,
    user: UserDep,
    session: AsyncSessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    filters: str | None = CrudFiltersQuery,
    sorts: str | None = CrudSortsQuery,
):
    user_selector = await build_selector(user=user, session=session)

    await set_response_count_header(
        response=response,
        sql_model=UploadedS3Object,
        session=session,
    )

    return await read_many(
        user=user,
        entity=Entities.UPLOADED_OBJECT,
        sql_model=UploadedS3Object,
        session=session,
        offset=offset,
        limit=limit,
        user_selector=user_selector,
        json_filters=filters,
        json_sorts=sorts,
    )


@router.post("/{id}/object", response_model=UploadedS3Object, tags=[_TAG])
async def upload_object(
    user: UserDep,
    session: AsyncSessionDep,
    id: int,
    s3: S3ClientDep,
    settings: SettingsDep,
    obj: UploadFile,
    tags: str = Form(default=None),
    series_id: str = Form(default=None),
    name: str = Form(default=None),
    description: str = Form(default=None),
):
    """Uploads a new object (e.g. a CSV dataset file) to MODERATE's
    object storage service and associates it with the _Asset_ given by `id`.
    Note that an _Asset_ may have many objects."""

    user.enforce_raise(obj=_ENTITY.value, act=Actions.UPDATE.value)
    user_selector = await build_selector(user=user, session=session)

    # Parse tags from JSON string to dict
    parsed_tags: dict[str, Any] | None = None
    if tags:
        try:
            parsed_tags = json.loads(tags)
        except Exception as ex:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tags should be a valid JSON object: {ex}",
            ) from ex

    the_asset = await select_one(
        sql_model=Asset,
        entity_id=id,
        session=session,
        user_selector=user_selector,
    )

    if len(the_asset.objects) >= settings.max_objects_per_asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset already has {len(the_asset.objects)} objects, cannot upload more than {settings.max_objects_per_asset}",
        )

    obj_key = build_object_key(obj=obj, user=user)
    _logger.info("Uploading object to S3: %s", obj_key)

    # Handle potential None s3 settings
    if not settings.s3 or not settings.s3.bucket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 configuration is missing",
        )

    user_bucket = settings.s3.bucket
    _logger.debug("Ensuring user assets bucket exists: %s", user_bucket)
    await ensure_bucket(s3=s3, bucket=user_bucket)

    result_s3_upload = await upload_file_multipart(
        s3=s3, bucket=user_bucket, key=obj_key, file_obj=obj, chunk_size=_CHUNK_SIZE
    )

    uploaded_s3_object = UploadedS3Object(
        bucket=result_s3_upload["Bucket"],
        etag=result_s3_upload["ETag"],
        key=result_s3_upload["Key"],
        location=result_s3_upload["Location"],
        asset_id=the_asset.id,
        tags=parsed_tags,
        series_id=series_id,
        sha256_hash=result_s3_upload["SHA256"],
        proof_id=None,  # Add missing required field
        name=name,
        description=description,
    )

    session.add(uploaded_s3_object)
    await session.commit()

    return uploaded_s3_object


@router.post("", response_model=AssetRead, tags=[_TAG])
async def create_asset(*, user: UserDep, session: AsyncSessionDep, entity: AssetCreate):
    """Create a new asset."""

    entity_create_patch = await build_create_patch(user=user, session=session)

    if entity.is_public_ownerless:
        entity_create_patch.update(  # type: ignore
            {
                Asset.username.key: None,  # type: ignore
                Asset.access_level.key: AssetAccessLevels.PUBLIC,  # type: ignore
            }
        )

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
    response: Response,
    user: OptionalUserDep,
    session: AsyncSessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    filters: str | None = CrudFiltersQuery,
    sorts: str | None = CrudSortsQuery,
):
    """Query the catalog for assets."""

    if user:
        user_selector = await build_selector(user=user, session=session)
    else:
        # Use proper SQLAlchemy expression for public assets
        user_selector: list[BinaryExpression] = [
            Asset.access_level == AssetAccessLevels.PUBLIC  # type: ignore
        ]

    await set_response_count_header(
        response=response,
        sql_model=Asset,
        session=session,
    )

    results = await read_many(
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

    return results


router.add_api_route(
    "",
    _read_assets,
    methods=["GET"],
    response_model=list[AssetRead],
    tags=[_TAG],
)

router.add_api_route(
    "/public",
    _read_assets,
    methods=["GET"],
    response_model=list[AssetRead],
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


@router.patch(
    "/{id}/object/{object_id}", response_model=UploadedS3ObjectRead, tags=[_TAG]
)
async def update_asset_object(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    id: int,
    object_id: int,
    entity_update: UploadedS3ObjectUpdate,
):
    """Update an object from a given data asset."""

    user.enforce_raise(obj=Entities.ASSET.value, act=Actions.UPDATE.value)
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
    the_asset_object = result_object.scalar_one_or_none()

    if not the_asset_object:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    entity_data = entity_update.model_dump(exclude_unset=True)

    for key, value in entity_data.items():
        setattr(the_asset_object, key, value)

    session.add(the_asset_object)
    await session.commit()
    await session.refresh(the_asset_object)

    return the_asset_object
