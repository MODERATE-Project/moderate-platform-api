import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import asc, case, desc, func, or_
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import BinaryExpression
from sqlmodel import select

from moderate_api.authz.user import OptionalUserDep, User
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.asset.models import (
    Asset,
    AssetAccessLevels,
    AssetRead,
    UploadedS3Object,
    UploadedS3ObjectRead,
    UploadedS3ObjectReadWithAsset,
)

_logger = logging.getLogger(__name__)


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


def user_asset_visibility_selector(
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
                match_score=None,
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
    user_selector = user_asset_visibility_selector(user=user)

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


async def search_assets_wrapper(
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


def _apply_visibility_filters(
    stmt: Select,
    *,
    user: OptionalUserDep,
    exclude_mine: bool,
) -> Select:
    """Apply user visibility and ownership filters."""

    user_selector = user_asset_visibility_selector(user=user)

    if user_selector is not None:
        stmt = stmt.where(user_selector)

    if exclude_mine and user:
        stmt = stmt.where(
            or_(
                Asset.username != user.username,
                Asset.username == None,
            )
        )  # type: ignore

    return stmt


def _apply_search_filter(stmt: Select, *, query: Optional[str]) -> Select:
    """Apply textual search across object and asset names."""

    if not query:
        return stmt

    search_pattern = f"%{query.lower()}%"

    return stmt.where(
        or_(  # type: ignore
            func.lower(UploadedS3Object.name).ilike(search_pattern),  # type: ignore
            func.lower(UploadedS3Object.key).ilike(search_pattern),  # type: ignore
            func.lower(UploadedS3Object.description).ilike(search_pattern),  # type: ignore
            func.lower(Asset.name).ilike(search_pattern),  # type: ignore
        )
    )


def _apply_format_filter(stmt: Select, *, file_format: Optional[str]) -> Select:
    """Limit objects to a subset of file extensions."""

    if not file_format:
        return stmt

    formats = [fmt.strip().lower() for fmt in file_format.split(",") if fmt.strip()]

    if not formats:
        return stmt

    format_conditions = [
        func.lower(UploadedS3Object.key).like(f"%.{fmt}")  # type: ignore
        for fmt in formats
    ]

    if not format_conditions:
        return stmt

    return stmt.where(or_(*format_conditions))  # type: ignore


def _parse_date_filter(date_from: Optional[str]) -> Optional[datetime]:
    """Parse date_from query param into a naive UTC datetime."""

    if not date_from:
        return None

    try:
        parsed_date = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        _logger.warning("Invalid date_from format: %s", date_from)
        return None

    if parsed_date.tzinfo is not None:
        parsed_date = parsed_date.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed_date


def _apply_date_filter(stmt: Select, *, date_from: Optional[str]) -> Select:
    """Apply created_at lower bound if provided."""

    parsed_date = _parse_date_filter(date_from)

    if parsed_date is None:
        return stmt

    return stmt.where(UploadedS3Object.created_at >= parsed_date)  # type: ignore


def _apply_sorting(stmt: Select, *, sort: str) -> Select:
    """Apply the requested ordering strategy."""

    if sort == "name":
        sort_col = func.coalesce(  # type: ignore
            UploadedS3Object.name,
            UploadedS3Object.key,
        )
        return stmt.order_by(asc(sort_col))

    if sort == "asset_name":
        return stmt.order_by(asc(Asset.name))  # type: ignore

    if sort == "format":
        substring = func.substring(  # type: ignore
            UploadedS3Object.key,
            r"\.([a-zA-Z0-9]+)$",
        )
        return stmt.order_by(asc(substring))

    # Default ordering is by newest first
    return stmt.order_by(desc(UploadedS3Object.created_at))  # type: ignore


async def search_objects(
    *,
    user: OptionalUserDep,
    session: AsyncSessionDep,
    query: str = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    sort: str = Query(default="date", regex="^(name|date|format|asset_name)$"),
    exclude_mine: bool = Query(default=False),
    file_format: str = Query(default=None),
    date_from: str = Query(default=None),
) -> List[UploadedS3ObjectReadWithAsset]:
    """Search for objects (datasets) directly."""

    # Base query joining Object and Asset
    stmt = select(UploadedS3Object, Asset).join(Asset)

    stmt = _apply_visibility_filters(
        stmt,
        user=user,
        exclude_mine=exclude_mine,
    )
    stmt = _apply_search_filter(stmt, query=query)
    stmt = _apply_format_filter(stmt, file_format=file_format)
    stmt = _apply_date_filter(stmt, date_from=date_from)
    stmt = _apply_sorting(stmt, sort=sort)

    # Pagination
    stmt = stmt.limit(limit).offset(offset)

    result = await session.execute(stmt)
    rows = result.all()

    ret = []
    for obj, asset in rows:
        # Create read model for object
        obj_read = UploadedS3ObjectRead(**obj.model_dump())

        # Create read model for asset, containing only this object
        asset_read = AssetRead(
            **asset.model_dump(exclude={"objects"}),
            objects=[obj_read],
        )

        ret.append(
            UploadedS3ObjectReadWithAsset(
                **obj_read.model_dump(),
                asset=asset_read,
            )
        )

    return ret
