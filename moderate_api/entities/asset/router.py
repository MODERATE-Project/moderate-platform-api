import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
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
from sqlalchemy import and_, case, desc, func, true
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


class AssetSearchResult(BaseModel):
    """Enhanced search result that includes only matching objects for each asset."""

    id: int
    uuid: str
    name: str
    description: Optional[str]
    meta: Optional[Dict]
    created_at: str
    access_level: AssetAccessLevels
    username: Optional[str]
    objects: List[UploadedS3ObjectRead]
    match_type: str  # 'asset' or 'object' - indicates what matched the search
    match_score: Optional[float] = None  # For future ranking improvements


async def build_selector(user: User, session: AsyncSession) -> List[BinaryExpression]:
    # SQLAlchemy column expressions - type: ignore to handle type checker issues
    return [
        or_(  # type: ignore
            Asset.username == user.username,  # type: ignore
            Asset.access_level == AssetAccessLevels.PUBLIC,  # type: ignore
        )
    ]


async def build_create_patch(
    user: User, session: AsyncSession
) -> Optional[Dict[str, Any]]:
    return {Asset.username.key: user.username}  # type: ignore


router = APIRouter()


def build_object_key(obj: UploadFile, user: User) -> str:
    if not obj.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File has no filename"
        )

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
        download_url = await s3.generate_presigned_url(  # type: ignore
            "get_object",
            Params={"Bucket": s3_object.bucket, "Key": s3_object.key},
            ExpiresIn=expiration_secs,
        )

        ret.append(AssetDownloadURL(key=s3_object.key, download_url=download_url))

    return ret


def _user_asset_visibility_selector(
    user: Union[User, None],
) -> Union[BinaryExpression, None]:
    public_visibility_levels = [
        AssetAccessLevels.VISIBLE,
        AssetAccessLevels.PUBLIC,
    ]

    if not user:
        return Asset.access_level.in_(public_visibility_levels)  # type: ignore

    if user.is_admin:
        return None

    return or_(  # type: ignore
        Asset.access_level.in_(public_visibility_levels),  # type: ignore
        Asset.username == user.username,  # type: ignore
    )


async def _query_search_assets(
    user: Union[User, None],
    session: AsyncSessionDep,
    query: str,
    limit: int,
    exclude_mine: bool,
    where_constraint: Union[BinaryExpression, None],
) -> List[AssetSearchResult]:
    """Search assets by name/description and return results with all their objects."""
    stmt = select(Asset).limit(limit)

    if query and len(query) > 0:
        stmt = stmt.where(Asset.search_vector.match(query))  # type: ignore
        # Order by search rank for better relevance
        stmt = stmt.order_by(desc(func.ts_rank(Asset.search_vector, func.plainto_tsquery(query))))  # type: ignore
    else:
        stmt = stmt.order_by(Asset.created_at.desc())  # type: ignore

    if where_constraint is not None:
        stmt = stmt.where(where_constraint)

    if exclude_mine and user:
        stmt = stmt.where(or_(Asset.username != user.username, Asset.username == None))  # type: ignore

    result = await session.execute(stmt)
    assets = list(result.scalars().all())

    # Convert to AssetSearchResult format
    search_results = []

    for asset in assets:
        if asset.id is None:
            continue  # Skip assets without IDs

        # Convert objects, filtering out any without IDs
        objects = []

        for obj in asset.objects:
            if obj.id is not None:
                objects.append(UploadedS3ObjectRead(**obj.__dict__))

        search_results.append(
            AssetSearchResult(
                id=asset.id,
                uuid=asset.uuid,
                name=asset.name,
                description=asset.description,
                meta=asset.meta,
                created_at=asset.created_at.isoformat(),
                access_level=asset.access_level,
                username=asset.username,
                objects=objects,
                match_type="asset",
                match_score=None,  # Could be enhanced with actual ts_rank value
            )
        )

    return search_results


async def _query_search_assets_from_objects(
    user: Union[User, None],
    session: AsyncSessionDep,
    query: str,
    limit: int,
    exclude_mine: bool,
    asset_where_constraint: Union[BinaryExpression, None],
) -> List[AssetSearchResult]:
    """Search for assets by their object names/keys and return only matching objects."""
    if not query:
        return []

    # First, find matching objects with their assets
    stmt = select(UploadedS3Object, Asset).join(Asset)

    # Apply asset visibility constraints
    if asset_where_constraint is not None:
        stmt = stmt.where(asset_where_constraint)

    if exclude_mine and user:
        stmt = stmt.where(or_(Asset.username != user.username, Asset.username == None))  # type: ignore

    # Search in object names and keys (case-insensitive)
    search_pattern = "%{}%".format(query.lower())

    stmt = stmt.where(
        or_(  # type: ignore
            func.lower(UploadedS3Object.name).ilike(search_pattern),  # type: ignore
            func.lower(UploadedS3Object.key).ilike(search_pattern),  # type: ignore
            func.lower(UploadedS3Object.description).ilike(search_pattern),  # type: ignore
        )
    )

    # Order by relevance: exact matches first, then partial matches
    # Also consider object creation date for tie-breaking
    stmt = stmt.order_by(
        case(
            (func.lower(UploadedS3Object.name) == query.lower(), 1),  # type: ignore
            (func.lower(UploadedS3Object.key).contains(query.lower()), 2),  # type: ignore
            else_=3,
        ),
        desc(UploadedS3Object.created_at),  # type: ignore
    )

    result = await session.execute(stmt)
    object_asset_pairs = list(result.all())

    # Group matching objects by asset
    asset_objects_map: Dict[int, List[UploadedS3Object]] = {}
    assets_map: Dict[int, Asset] = {}

    for obj, asset in object_asset_pairs:
        if asset.id is None or obj.id is None:
            continue

        if asset.id not in asset_objects_map:
            asset_objects_map[asset.id] = []
            assets_map[asset.id] = asset

        asset_objects_map[asset.id].append(obj)

    # Convert to AssetSearchResult format with only matching objects
    search_results = []

    for asset_id, matching_objects in asset_objects_map.items():
        asset = assets_map[asset_id]

        # Convert only the matching objects
        objects = [UploadedS3ObjectRead(**obj.__dict__) for obj in matching_objects]

        # asset.id is guaranteed to be not None due to the continue check above
        search_results.append(
            AssetSearchResult(
                id=asset.id,  # type: ignore
                uuid=asset.uuid,
                name=asset.name,
                description=asset.description,
                meta=asset.meta,
                created_at=asset.created_at.isoformat(),
                access_level=asset.access_level,
                username=asset.username,
                objects=objects,
                match_type="object",
                match_score=None,
            )
        )

    # Apply limit to final results
    return search_results[:limit]


async def _search_assets(
    *,
    user: OptionalUserDep,
    session: AsyncSessionDep,
    query: str = Query(default=None),
    limit: int = Query(default=20, le=100),
    exclude_mine: bool = Query(default=False),
):
    """Enhanced search that returns assets with proper object filtering."""
    user_selector = _user_asset_visibility_selector(user=user)

    # Search for assets by name/description (returns all objects for matching assets)
    assets_by_name = await _query_search_assets(
        user=user,
        session=session,
        query=query,
        limit=limit,
        exclude_mine=exclude_mine,
        where_constraint=user_selector,
    )

    # Search for assets by object properties (returns only matching objects)
    assets_by_objects = await _query_search_assets_from_objects(
        user=user,
        session=session,
        query=query,
        limit=limit,
        exclude_mine=exclude_mine,
        asset_where_constraint=user_selector,
    )

    # Combine results, avoiding duplicates but preserving the better match
    # Priority: asset matches (with all objects) > object matches (with filtered objects)
    found_assets_map: Dict[int, AssetSearchResult] = {}

    # First add asset matches (these get priority and include all objects)
    for asset_result in assets_by_name:
        found_assets_map[asset_result.id] = asset_result

    # Then add object matches (only if asset wasn't already matched by name)
    for asset_result in assets_by_objects:
        if asset_result.id not in found_assets_map:
            found_assets_map[asset_result.id] = asset_result

    # Convert back to list and apply final limit
    found_assets = list(found_assets_map.values())[:limit]

    # Sort by match type (asset matches first) and then by creation date
    found_assets.sort(
        key=lambda x: (
            0 if x.match_type == "asset" else 1,  # Asset matches first
            -int(
                x.created_at.replace("T", "")
                .replace("-", "")
                .replace(":", "")
                .replace(".", "")[:14]
            ),  # Newer first
        )
    )

    return found_assets


async def _search_assets_wrapper(
    *,
    user: OptionalUserDep,
    session: AsyncSessionDep,
    query: str = Query(default=None),
    limit: int = Query(default=20, le=100),
    exclude_mine: bool = Query(default=False),
) -> List[AssetRead]:
    """Backward-compatible wrapper that converts AssetSearchResult to AssetRead."""

    search_results = await _search_assets(
        user=user,
        session=session,
        query=query,
        limit=limit,
        exclude_mine=exclude_mine,
    )

    # Convert AssetSearchResult back to AssetRead for backward compatibility
    ret_results = []

    for result in search_results:
        # Convert ISO string back to datetime for AssetRead compatibility
        created_at_dt = datetime.fromisoformat(result.created_at)

        ret_results.append(
            AssetRead(
                id=result.id,
                uuid=result.uuid,
                name=result.name,
                description=result.description,
                meta=result.meta,
                created_at=created_at_dt,
                access_level=result.access_level,
                username=result.username,
                objects=result.objects,
            )
        )

    return ret_results


router.add_api_route(
    "/search",
    _search_assets_wrapper,
    methods=["GET"],
    response_model=List[AssetRead],
    tags=[_TAG],
)

router.add_api_route(
    "/public/search",
    _search_assets_wrapper,
    methods=["GET"],
    response_model=List[AssetRead],
    tags=[_TAG, Tags.PUBLIC.value],
)


class AssetObjectProfileResponse(BaseModel):
    profile: Optional[OMProfile] = None
    reason: Optional[str] = None


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

    # Parse tags from JSON string to dict
    parsed_tags: Optional[Dict] = None
    if tags:
        try:
            parsed_tags = json.loads(tags)
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

    # Handle potential None s3 settings
    if not settings.s3 or not settings.s3.bucket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3 configuration is missing",
        )

    user_bucket = settings.s3.bucket
    _logger.debug("Ensuring user assets bucket exists: %s", user_bucket)
    await ensure_bucket(s3=s3, bucket=user_bucket)

    _logger.debug("Creating multipart upload (object=%s)", obj_key)
    multipart_upload = await s3.create_multipart_upload(Bucket=user_bucket, Key=obj_key)  # type: ignore

    parts = []
    part_number = 1
    hash_object = hashlib.sha256()

    while True:
        chunk = await obj.read(_CHUNK_SIZE)

        if not chunk:
            break

        hash_object.update(chunk)

        part = await s3.upload_part(  # type: ignore
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

    result_s3_upload = await s3.complete_multipart_upload(  # type: ignore
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
        tags=parsed_tags,
        series_id=series_id,
        sha256_hash=sha256_hash,
        proof_id=None,  # Add missing required field
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
    filters: Optional[str] = CrudFiltersQuery,
    sorts: Optional[str] = CrudSortsQuery,
):
    """Query the catalog for assets."""

    if user:
        user_selector = await build_selector(user=user, session=session)
    else:
        # Use proper SQLAlchemy expression for public assets
        user_selector: List[BinaryExpression] = [
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

    # Handle potential None asset relationship
    if not s3object.asset:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

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
        return AssetObjectProofCreationResponse(task_id=None, obj=s3object)

    task_id = await init_task(session=session, username_owner=user.username)

    background_tasks.add_task(
        create_proof_task,
        task_id=str(task_id),  # Convert int to str as expected by the function
        s3object_key_or_id=body.object_key_or_id,
        requester_username=user.username,
        user_did=None,
        create_proof_url=settings.trust_service.url_create_proof(),
    )

    return AssetObjectProofCreationResponse(task_id=task_id, obj=None)


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
