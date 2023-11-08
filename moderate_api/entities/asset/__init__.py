from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import Field, SQLModel, select

from moderate_api.db import AsyncSessionDep


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


@router.post("/", response_model=AssetRead)
def create_asset(*, session: AsyncSessionDep, entity: AssetCreate):
    db_entity = Asset.from_orm(entity)
    session.add(db_entity)
    session.commit()
    session.refresh(db_entity)
    return db_entity


@router.get("/", response_model=List[AssetRead])
def read_assets(
    *,
    session: AsyncSessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
):
    entities = session.exec(select(Asset).offset(offset).limit(limit)).all()
    return entities


@router.get("/{entity_id}", response_model=AssetRead)
def read_asset(*, session: AsyncSessionDep, entity_id: int):
    entity = session.get(Asset, entity_id)

    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return entity


@router.patch("/{entity_id}", response_model=AssetRead)
def update_asset(*, session: AsyncSessionDep, entity_id: int, entity: AssetUpdate):
    db_entity = session.get(Asset, entity_id)

    if not db_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    entity_data = entity.dict(exclude_unset=True)

    for key, value in entity_data.items():
        setattr(db_entity, key, value)

    session.add(db_entity)
    session.commit()
    session.refresh(db_entity)
    return db_entity


@router.delete("/{entity_id}")
def delete_asset(*, session: AsyncSessionDep, entity_id: int):
    entity = session.get(Asset, entity_id)

    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    session.delete(entity)
    session.commit()
    return {"ok": True}
