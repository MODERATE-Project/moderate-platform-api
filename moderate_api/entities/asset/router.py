import hashlib
import json
import logging
import os
import uuid
from io import BytesIO
from typing import Any, Dict, List, Optional, Union

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
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

from moderate_api.authz import User, UserDep
from moderate_api.authz.user import OptionalUserDep, User
from moderate_api.config import SettingsDep
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.asset.models import (
    Asset,
    AssetAccessLevels,
    AssetCreate,
    AssetRead,
    AssetUpdate,
    UploadedS3Object,
    UploadedS3ObjectRead,
    UploadedS3ObjectUpdate,
    filter_object_ids_by_username,
    find_s3object_by_key_or_id,
    find_s3object_pending_quality_check,
    update_s3object_quality_check_flag,
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
from moderate_api.long_running import LongRunningTask, get_task, init_task
from moderate_api.object_storage import S3ClientDep, ensure_bucket
from moderate_api.open_metadata import (
    OMProfile,
    get_asset_object_profile,
    search_asset_object,
)
from moderate_api.trust import (
    ProofVerificationResult,
    create_proof_task,
    fetch_verify_proof,
)

_logger = logging.getLogger(__name__)

_TAG = "Data assets"
_ENTITY = Entities.ASSET
_CHUNK_SIZE = 16 * 1024**2


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
    path_name, ext = os.path.splitext(obj.filename)
    safe_name = slugify(path_name)

    return os.path.join(
        f"{user.username}-assets",
        "{}-{}{}".format(safe_name, str(uuid.uuid4()), ext),
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


def _user_asset_visibility_selector(
    user: Union[User, None]
) -> Union[BinaryExpression, None]:
    public_visibility_levels = [
        AssetAccessLevels.VISIBLE,
        AssetAccessLevels.PUBLIC,
    ]

    if not user:
        return Asset.access_level.in_(public_visibility_levels)

    if user.is_admin:
        return None

    return or_(
        Asset.access_level.in_(public_visibility_levels),
        Asset.username == user.username,
    )


async def _query_search_assets(
    user: Union[User, None],
    session: AsyncSessionDep,
    query: str,
    limit: int,
    exclude_mine: bool,
    where_constraint: Union[BinaryExpression, None],
) -> List[Asset]:
    stmt = select(Asset).limit(limit)

    if query and len(query) > 0:
        stmt = stmt.where(Asset.search_vector.match(query))
    else:
        stmt = stmt.order_by(Asset.created_at.desc())

    if where_constraint is not None:
        stmt = stmt.where(where_constraint)

    if exclude_mine and user:
        stmt = stmt.where(or_(Asset.username != user.username, Asset.username == None))

    result = await session.execute(stmt)

    return result.scalars().all()


async def _query_search_assets_from_objects(
    user: Union[User, None],
    session: AsyncSessionDep,
    query: str,
    limit: int,
    exclude_mine: bool,
    asset_where_constraint: Union[BinaryExpression, None],
) -> List[Asset]:
    if not query:
        return []

    stmt = select(Asset).limit(limit)

    if asset_where_constraint is not None:
        stmt = stmt.where(asset_where_constraint)

    if exclude_mine and user:
        stmt = stmt.where(or_(Asset.username != user.username, Asset.username == None))

    stmt = (
        stmt.join(UploadedS3Object)
        .where(
            or_(
                UploadedS3Object.name.ilike("%{}%".format(query)),
                UploadedS3Object.key.ilike("%{}%".format(query)),
            ),
        )
        .distinct()
    )

    result = await session.execute(stmt)

    return result.scalars().all()


async def _search_assets(
    *,
    user: OptionalUserDep,
    session: AsyncSessionDep,
    query: str = Query(default=None),
    limit: int = Query(default=20, le=100),
    exclude_mine: bool = Query(default=False),
):
    user_selector = _user_asset_visibility_selector(user=user)

    assets = await _query_search_assets(
        user=user,
        session=session,
        query=query,
        limit=limit,
        exclude_mine=exclude_mine,
        where_constraint=user_selector,
    )

    assets_from_objects = await _query_search_assets_from_objects(
        user=user,
        session=session,
        query=query,
        limit=limit,
        exclude_mine=exclude_mine,
        asset_where_constraint=user_selector,
    )

    found_assets = [
        *assets,
        *[
            item
            for item in assets_from_objects
            if item.id not in {asset.id for asset in assets}
        ],
    ]

    return found_assets


router.add_api_route(
    "/search",
    _search_assets,
    methods=["GET"],
    response_model=List[AssetRead],
    tags=[_TAG],
)

router.add_api_route(
    "/public/search",
    _search_assets,
    methods=["GET"],
    response_model=List[AssetRead],
    tags=[_TAG, Tags.PUBLIC.value],
)


class AssetObjectProfileResponse(BaseModel):
    profile: Optional[OMProfile]
    reason: Optional[str]


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

    user_selector = _user_asset_visibility_selector(user=user)
    user_selector = user_selector if user_selector is not None else true()

    stmt = (
        select(UploadedS3Object, Asset)
        .join(Asset, and_(Asset.id == UploadedS3Object.asset_id, user_selector))
        .where(UploadedS3Object.id == object_id)
    )

    result = await session.execute(stmt)
    s3obj = result.scalars().one_or_none()

    if not s3obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        search_result = await search_asset_object(
            asset_object_key=s3obj.key, settings=settings
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
    "/object/quality-check", response_model=List[ObjectPendingQuality], tags=[_TAG]
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
    asset_object_id: Union[List[int], int]
    pending_quality_check: bool


class AssetObjectFlagQualityResponse(BaseModel):
    asset_object_id: List[int]


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

    if user.is_admin:
        asset_object_ids = body.asset_object_id
    else:
        asset_object_ids = await filter_object_ids_by_username(
            object_ids=body.asset_object_id,
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


@router.get("/object", response_model=List[UploadedS3Object], tags=[_TAG])
async def query_asset_objects(
    *,
    response: Response,
    user: UserDep,
    session: AsyncSessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    filters: Optional[str] = CrudFiltersQuery,
    sorts: Optional[str] = CrudSortsQuery,
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
    obj: UploadFile = File(...),
    tags: str = Form(default=None),
    series_id: str = Form(default=None),
):
    """Uploads a new object (e.g. a CSV dataset file) to MODERATE's
    object storage service and associates it with the _Asset_ given by `id`.
    Note that an _Asset_ may have many objects."""

    user.enforce_raise(obj=_ENTITY.value, act=Actions.UPDATE.value)
    user_selector = await build_selector(user=user, session=session)

    if tags:
        try:
            tags = json.loads(tags)
        except Exception as ex:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tags should be a valid JSON object: {}".format(ex),
            )

    the_asset = await select_one(
        sql_model=Asset,
        entity_id=id,
        session=session,
        user_selector=user_selector,
    )

    if len(the_asset.objects) >= settings.max_objects_per_asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset already has {} objects, cannot upload more than {}".format(
                len(the_asset.objects), settings.max_objects_per_asset
            ),
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
    hash_object = hashlib.sha256()

    while True:
        chunk = await obj.read(_CHUNK_SIZE)

        if not chunk:
            break

        hash_object.update(chunk)

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

    sha256_hash = hash_object.hexdigest()

    _logger.debug("SHA256 hash of object: %s", sha256_hash)

    uploaded_s3_object = UploadedS3Object(
        bucket=result_s3_upload["Bucket"],
        etag=result_s3_upload["ETag"],
        key=result_s3_upload["Key"],
        location=result_s3_upload["Location"],
        asset_id=the_asset.id,
        tags=tags,
        series_id=series_id,
        sha256_hash=sha256_hash,
    )

    session.add(uploaded_s3_object)
    await session.commit()

    return uploaded_s3_object


@router.post("", response_model=AssetRead, tags=[_TAG])
async def create_asset(*, user: UserDep, session: AsyncSessionDep, entity: AssetCreate):
    """Create a new asset."""

    entity_create_patch = await build_create_patch(user=user, session=session)

    if entity.is_public_ownerless:
        entity_create_patch.update(
            {
                Asset.username.key: None,
                Asset.access_level.key: AssetAccessLevels.PUBLIC,
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


class AssetObjectProofCreationRequest(BaseModel):
    object_key_or_id: Union[str, int]


class AssetObjectProofCreationResponse(BaseModel):
    task_id: Optional[int]
    obj: Optional[UploadedS3Object]


async def _find_enforce_s3obj(
    object_key_or_id: Union[str, int],
    session: AsyncSessionDep,
    user: UserDep,
    public_assets_allowed: bool = False,
) -> UploadedS3Object:
    s3object = await find_s3object_by_key_or_id(val=object_key_or_id, session=session)

    if not s3object:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    is_asset_owner = (
        s3object.asset.username and s3object.asset.username == user.username
    )

    is_public = (
        s3object.asset.access_level == AssetAccessLevels.PUBLIC
        and public_assets_allowed
    )

    is_allowed = user.is_admin or is_asset_owner or is_public

    if not is_allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return s3object


@router.post("/proof", response_model=AssetObjectProofCreationResponse, tags=[_TAG])
async def ensure_trust_proof(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    settings: SettingsDep,
    background_tasks: BackgroundTasks,
    body: AssetObjectProofCreationRequest,
):
    if not settings.trust_service or not settings.trust_service.endpoint_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    s3object = await _find_enforce_s3obj(
        object_key_or_id=body.object_key_or_id,
        session=session,
        user=user,
        public_assets_allowed=False,
    )

    if s3object.proof_id:
        return AssetObjectProofCreationResponse(obj=s3object)

    task_id = await init_task(session=session, username_owner=user.username)

    background_tasks.add_task(
        create_proof_task,
        task_id=task_id,
        s3object_key_or_id=body.object_key_or_id,
        requester_username=user.username,
        user_did=None,
        create_proof_url=settings.trust_service.url_create_proof(),
    )

    return AssetObjectProofCreationResponse(task_id=task_id)


@router.get("/proof/task/{task_id}", response_model=LongRunningTask, tags=[_TAG])
async def get_user_did_task_result(
    *, user: UserDep, session: AsyncSessionDep, task_id: int
):
    username_owner = None if user.is_admin else user.username

    task = await get_task(
        session=session, task_id=task_id, username_owner=username_owner
    )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return task


@router.get("/proof/integrity", response_model=ProofVerificationResult, tags=[_TAG])
async def verify_trust_proof(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    settings: SettingsDep,
    object_key_or_id: Union[str, int],
):
    if not settings.trust_service or not settings.trust_service.endpoint_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    s3object = await _find_enforce_s3obj(
        object_key_or_id=object_key_or_id,
        session=session,
        user=user,
        public_assets_allowed=True,
    )

    return await fetch_verify_proof(
        session=session,
        asset_obj_key=s3object.key,
        get_proof_url=settings.trust_service.url_get_proof(),
    )
