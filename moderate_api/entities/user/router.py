from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BinaryExpression
from sqlmodel import or_

from moderate_api.authz import User, UserDep
from moderate_api.authz.user import User
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.crud import (
    CrudFiltersQuery,
    CrudSortsQuery,
    create_one,
    delete_one,
    read_many,
    read_one,
    update_one,
)
from moderate_api.entities.user.models import (
    UserMeta,
    UserMetaCreate,
    UserMetaRead,
    UserMetaUpdate,
)
from moderate_api.enums import Entities

_TAG = "User metadata"
_ENTITY = Entities.USER


async def build_selector(user: User, session: AsyncSession) -> List[BinaryExpression]:
    return [
        or_(
            UserMeta.username == user.username,
        )
    ]


async def build_create_patch(
    user: User, session: AsyncSession
) -> Optional[Dict[str, Any]]:
    return {}


router = APIRouter()


@router.post("/", response_model=UserMetaRead, tags=[_TAG])
async def create_user_meta(
    *, user: UserDep, session: AsyncSessionDep, entity: UserMetaCreate
):
    entity_create_patch = await build_create_patch(user=user, session=session)

    return await create_one(
        user=user,
        entity=_ENTITY,
        sql_model=UserMeta,
        session=session,
        entity_create=entity,
        entity_create_patch=entity_create_patch,
    )


@router.get("/", response_model=List[UserMetaRead], tags=[_TAG])
async def query_user_meta(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    filters: Optional[str] = CrudFiltersQuery,
    sorts: Optional[str] = CrudSortsQuery,
):
    user_selector = await build_selector(user=user, session=session)

    return await read_many(
        user=user,
        entity=_ENTITY,
        sql_model=UserMeta,
        session=session,
        offset=offset,
        limit=limit,
        user_selector=user_selector,
        json_filters=filters,
        json_sorts=sorts,
    )


@router.get("/{id}", response_model=UserMetaRead, tags=[_TAG])
async def read_user_meta(*, user: UserDep, session: AsyncSessionDep, id: int):
    user_selector = await build_selector(user=user, session=session)

    return await read_one(
        user=user,
        entity=_ENTITY,
        sql_model=UserMeta,
        session=session,
        entity_id=id,
        user_selector=user_selector,
    )


@router.patch("/{id}", response_model=UserMetaRead, tags=[_TAG])
async def update_user_meta(
    *, user: UserDep, session: AsyncSessionDep, id: int, entity: UserMetaUpdate
):
    user_selector = await build_selector(user=user, session=session)

    return await update_one(
        user=user,
        entity=_ENTITY,
        sql_model=UserMeta,
        session=session,
        entity_id=id,
        entity_update=entity,
        user_selector=user_selector,
    )


@router.delete("/{id}", tags=[_TAG])
async def delete_user_meta(*, user: UserDep, session: AsyncSessionDep, id: int):
    user_selector = await build_selector(user=user, session=session)

    return await delete_one(
        user=user,
        entity=_ENTITY,
        sql_model=UserMeta,
        session=session,
        entity_id=id,
        user_selector=user_selector,
    )
