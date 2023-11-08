from typing import List, Optional

from fastapi import APIRouter, Query
from sqlmodel import Field, SQLModel

from moderate_api.db import AsyncSessionDep
from moderate_api.entities.crud import (
    create_one,
    delete_one,
    read_many,
    read_one,
    update_one,
)

_TAG = "Data assets"


class AssetBase(SQLModel):
    uuid: str
    name: str


class Asset(AssetBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class AssetCreate(AssetBase):
    pass


class AssetRead(AssetBase):
    id: int


class AssetUpdate(SQLModel):
    name: Optional[str] = None


router = APIRouter()


@router.post("/", response_model=AssetRead, tags=[_TAG])
async def create_asset(*, session: AsyncSessionDep, entity: AssetCreate):
    """Create a new asset."""

    return await create_one(sql_model=Asset, session=session, entity_create=entity)


@router.get("/", response_model=List[AssetRead], tags=[_TAG])
async def read_assets(
    *,
    session: AsyncSessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
):
    """Read many assets."""

    return await read_many(sql_model=Asset, session=session, offset=offset, limit=limit)


@router.get("/{entity_id}", response_model=AssetRead, tags=[_TAG])
async def read_asset(*, session: AsyncSessionDep, entity_id: int):
    """Read one asset."""

    return await read_one(sql_model=Asset, session=session, entity_id=entity_id)


@router.patch("/{entity_id}", response_model=AssetRead, tags=[_TAG])
async def update_asset(
    *, session: AsyncSessionDep, entity_id: int, entity: AssetUpdate
):
    """Update one asset."""

    return await update_one(
        sql_model=Asset, session=session, entity_id=entity_id, entity_update=entity
    )


@router.delete("/{entity_id}", tags=[_TAG])
async def delete_asset(*, session: AsyncSessionDep, entity_id: int):
    """Delete one asset."""

    return await delete_one(sql_model=Asset, session=session, entity_id=entity_id)
