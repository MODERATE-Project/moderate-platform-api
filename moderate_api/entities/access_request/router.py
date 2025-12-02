import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BinaryExpression
from sqlmodel import or_, select

from moderate_api.authz import User, UserDep
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.access_request.models import (
    AccessRequest,
    AccessRequestCreate,
    AccessRequestRead,
    AccessRequestUpdate,
    can_approve_access_request,
)
from moderate_api.entities.crud import (
    CrudFiltersQuery,
    CrudSortsQuery,
    create_one,
    delete_one,
    read_many,
    read_one,
    set_response_count_header,
    update_one,
)
from moderate_api.enums import Entities

_logger = logging.getLogger(__name__)

_TAG = "Access requests"
_ENTITY = Entities.ACCESS_REQUEST


async def build_selector(user: User, session: AsyncSession) -> List[BinaryExpression]:
    return [
        or_(
            AccessRequest.requester_username == user.username,
            AccessRequest.asset.has(username=user.username),
        )
    ]


async def build_create_patch(
    user: User, session: AsyncSession
) -> Optional[Dict[str, Any]]:
    return {
        AccessRequest.requester_username.key: user.username,
    }


router = APIRouter()


class AccessRequestPermissionUpdateRequest(BaseModel):
    allowed: bool


@router.post("/{id}/permission", response_model=AccessRequestRead, tags=[_TAG])
async def update_permission(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    id: int,
    payload: AccessRequestPermissionUpdateRequest,
):
    user_selector = await build_selector(user=user, session=session)
    stmt = select(AccessRequest).where(AccessRequest.id == id)

    if not user.is_admin:
        stmt = stmt.where(*user_selector)

    result = await session.execute(stmt)
    access_request = result.scalars().one_or_none()

    if not access_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if not can_approve_access_request(user=user, access_request=access_request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    access_request.validated_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)
    access_request.validator_username = user.username
    access_request.allowed = payload.allowed

    session.add(access_request)
    await session.commit()

    return access_request


@router.get("", response_model=List[AccessRequestRead], tags=[_TAG])
async def query_access_requests(
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
        sql_model=AccessRequest,
        session=session,
    )

    return await read_many(
        user=user,
        entity=_ENTITY,
        sql_model=AccessRequest,
        session=session,
        offset=offset,
        limit=limit,
        user_selector=user_selector,
        json_filters=filters,
        json_sorts=sorts,
    )


@router.get("/{id}", response_model=AccessRequestRead, tags=[_TAG])
async def read_access_request(*, user: UserDep, session: AsyncSessionDep, id: int):
    user_selector = await build_selector(user=user, session=session)

    return await read_one(
        user=user,
        entity=_ENTITY,
        sql_model=AccessRequest,
        session=session,
        entity_id=id,
        user_selector=user_selector,
    )


@router.post("", response_model=AccessRequestRead, tags=[_TAG])
async def create_access_request(
    *, user: UserDep, session: AsyncSessionDep, entity: AccessRequestCreate
):
    entity_create_patch = await build_create_patch(user=user, session=session)

    return await create_one(
        user=user,
        entity=_ENTITY,
        sql_model=AccessRequest,
        session=session,
        entity_create=entity,
        entity_create_patch=entity_create_patch,
    )


@router.patch("/{id}", response_model=AccessRequestRead, tags=[_TAG])
async def update_access_request(
    *, user: UserDep, session: AsyncSessionDep, id: int, entity: AccessRequestUpdate
):
    user_selector = await build_selector(user=user, session=session)

    return await update_one(
        user=user,
        entity=_ENTITY,
        sql_model=AccessRequest,
        session=session,
        entity_id=id,
        entity_update=entity,
        user_selector=user_selector,
    )


@router.delete("/{id}", tags=[_TAG])
async def delete_access_request(*, user: UserDep, session: AsyncSessionDep, id: int):
    user_selector = await build_selector(user=user, session=session)

    return await delete_one(
        user=user,
        entity=_ENTITY,
        sql_model=AccessRequest,
        session=session,
        entity_id=id,
        user_selector=user_selector,
    )
