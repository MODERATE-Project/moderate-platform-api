import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

from moderate_api.authz import User
from moderate_api.enums import Actions, Entities

_logger = logging.getLogger(__name__)


async def create_one(
    *,
    user: User,
    entity: Entities,
    sql_model: SQLModel,
    session: AsyncSession,
    entity_create: SQLModel
):
    """Reusable helper function to create a new entity."""

    user.enforce_raise(obj=entity.value, act=Actions.CREATE.value)
    db_entity = sql_model.from_orm(entity_create)
    _logger.debug("Creating %s: %s", sql_model, db_entity)
    session.add(db_entity)
    await session.commit()
    await session.refresh(db_entity)
    return db_entity


async def read_many(
    *,
    user: User,
    entity: Entities,
    sql_model: SQLModel,
    session: AsyncSession,
    offset: int = 0,
    limit: int = 100
):
    """Reusable helper function to read many entities."""

    user.enforce_raise(obj=entity.value, act=Actions.READ.value)
    result = await session.execute(select(sql_model).offset(offset).limit(limit))
    entities = result.all()
    return entities


async def read_one(
    *,
    user: User,
    entity: Entities,
    sql_model: SQLModel,
    session: AsyncSession,
    entity_id: int
):
    """Reusable helper function to read one entity."""

    user.enforce_raise(obj=entity.value, act=Actions.READ.value)
    _logger.debug("Reading %s with id: %s", sql_model, entity_id)
    entity = await session.get(sql_model, entity_id)

    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return entity


async def update_one(
    *,
    user: User,
    entity: Entities,
    sql_model: SQLModel,
    session: AsyncSession,
    entity_id: int,
    entity_update: SQLModel
):
    """Reusable helper function to update one entity."""

    user.enforce_raise(obj=entity.value, act=Actions.UPDATE.value)
    _logger.debug("Updating %s with id: %s", sql_model, entity_id)
    db_entity = await session.get(sql_model, entity_id)

    if not db_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    entity_data = entity_update.dict(exclude_unset=True)

    for key, value in entity_data.items():
        setattr(db_entity, key, value)

    session.add(db_entity)
    await session.commit()
    await session.refresh(db_entity)
    return db_entity


async def delete_one(
    *,
    user: User,
    entity: Entities,
    sql_model: SQLModel,
    session: AsyncSession,
    entity_id: int
):
    """Reusable helper function to delete one entity."""

    user.enforce_raise(obj=entity.value, act=Actions.DELETE.value)
    _logger.debug("Deleting %s with id: %s", sql_model, entity_id)
    entity = await session.get(sql_model, entity_id)

    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await session.delete(entity)
    await session.commit()
    return {"ok": True}
