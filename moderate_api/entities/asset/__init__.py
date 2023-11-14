from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel

from moderate_api.authz import UserDep, UserSelectorBuilder
from moderate_api.authz.user import User
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.crud import (
    create_one,
    delete_one,
    read_many,
    read_one,
    update_one,
)
from moderate_api.enums import Entities

_TAG = "Data assets"
_ENTITY = Entities.ASSET


class AssetBase(SQLModel):
    uuid: str
    name: str


class Asset(AssetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str


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
