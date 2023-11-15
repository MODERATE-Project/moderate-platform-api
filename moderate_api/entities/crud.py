import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

import arrow
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BinaryExpression
from sqlmodel import SQLModel, select

from moderate_api.authz import User
from moderate_api.enums import Actions, Entities

_logger = logging.getLogger(__name__)

_REGEX_DTTM_ISO = (
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(([+-]\d{2}:\d{2})|Z)?$"
)

# Matches a list of elements separated by commas,
# where spaces are allowed before and after the comma,
# but not within the elements themselves,
# and the string should not start or end with brackets.
_REGEX_LIST = r"(?<!\[)\b\w+\b(?:(?:\s*,\s*\b\w+\b)+)(?!\])"


def _parse_value(val: Any) -> Union[datetime, int, float, str, bool, List]:
    try:
        if re.match(_REGEX_LIST, val):
            return json.loads(f"[{val}]")
    except (TypeError, json.JSONDecodeError):
        pass

    try:
        parsed_list = json.loads(val)
        if isinstance(parsed_list, list):
            return parsed_list
    except (TypeError, json.JSONDecodeError):
        pass

    try:
        if re.match(_REGEX_DTTM_ISO, val):
            return arrow.get(val).naive
    except (TypeError, arrow.parser.ParserError):
        pass

    try:
        return int(val)
    except (TypeError, ValueError):
        pass

    try:
        return float(val)
    except (TypeError, ValueError):
        pass

    try:
        if val.lower() == "true":
            return True
        elif val.lower() == "false":
            return False
    except AttributeError:
        pass

    return val


class CrudFilter(BaseModel):
    """Model that represents a filter for a CRUD operation.
    Inspired by: https://refine.dev/docs/api-reference/core/interfaceReferences/#crudfilters
    """

    field: str
    operator: str
    value: str

    @property
    def parsed_value(self) -> Union[datetime, int, float, str, bool, List]:
        ret = _parse_value(self.value)

        if isinstance(ret, list):
            return [_parse_value(v) for v in ret]
        else:
            return ret


def _map_eq(model: SQLModel, crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) == crud_filter.parsed_value


def _map_ne(model: SQLModel, crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) != crud_filter.parsed_value


def _map_lt(model: SQLModel, crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) < crud_filter.parsed_value


def _map_gt(model: SQLModel, crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) > crud_filter.parsed_value


def _map_lte(model: SQLModel, crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) <= crud_filter.parsed_value


def _map_gte(model: SQLModel, crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) >= crud_filter.parsed_value


def _map_in(model: SQLModel, crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field).in_(crud_filter.parsed_value)


def _map_nin(model: SQLModel, crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field).notin_(crud_filter.parsed_value)


def filter_to_sqlmodel_expr(
    model: SQLModel, crud_filter: CrudFilter
) -> BinaryExpression:
    mappers = {
        "eq": _map_eq,
        "ne": _map_ne,
        "lt": _map_lt,
        "gt": _map_gt,
        "lte": _map_lte,
        "gte": _map_gte,
        "in": _map_in,
        "nin": _map_nin,
    }

    if crud_filter.operator not in mappers:
        raise ValueError(f"Unsupported operator: {crud_filter.operator}")

    return mappers[crud_filter.operator](model, crud_filter)


def _primary_key(sql_model: Type[SQLModel]) -> str:
    for column in sql_model.__table__.primary_key:
        return column.name


async def create_one(
    *,
    user: User,
    entity: Entities,
    sql_model: Type[SQLModel],
    session: AsyncSession,
    entity_create: SQLModel,
    entity_create_patch: Optional[Dict[str, Any]] = None,
):
    """Reusable helper function to create a new entity."""

    user.enforce_raise(obj=entity.value, act=Actions.CREATE.value)
    db_entity = sql_model.from_orm(entity_create, update=entity_create_patch)
    _logger.debug("Creating %s: %s", sql_model, db_entity)
    session.add(db_entity)
    await session.commit()
    await session.refresh(db_entity)
    return db_entity


async def read_many(
    *,
    user: User,
    entity: Entities,
    sql_model: Type[SQLModel],
    session: AsyncSession,
    offset: int = 0,
    limit: int = 100,
    user_selector: Optional[List[BinaryExpression]] = None,
):
    """Reusable helper function to read many entities."""

    user.enforce_raise(obj=entity.value, act=Actions.READ.value)
    statement = select(sql_model).offset(offset).limit(limit)

    if user_selector:
        statement = statement.where(*user_selector)

    result = await session.execute(statement)
    entities = result.all()

    return entities


async def _select_one(
    sql_model: Type[SQLModel],
    entity_id: int,
    session: AsyncSession,
    user_selector: Optional[List[BinaryExpression]] = None,
) -> SQLModel:
    statement = select(sql_model).where(
        getattr(sql_model, _primary_key(sql_model)) == entity_id
    )

    if user_selector:
        statement = statement.where(*user_selector)

    result = await session.execute(statement)
    entity = result.one_or_none()

    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return entity[0]


async def read_one(
    *,
    user: User,
    entity: Entities,
    sql_model: Type[SQLModel],
    session: AsyncSession,
    entity_id: int,
    user_selector: Optional[List[BinaryExpression]] = None,
):
    """Reusable helper function to read one entity."""

    user.enforce_raise(obj=entity.value, act=Actions.READ.value)
    _logger.debug("Reading %s with id: %s", sql_model, entity_id)

    return await _select_one(
        sql_model=sql_model,
        entity_id=entity_id,
        session=session,
        user_selector=user_selector,
    )


async def update_one(
    *,
    user: User,
    entity: Entities,
    sql_model: Type[SQLModel],
    session: AsyncSession,
    entity_id: int,
    entity_update: SQLModel,
    user_selector: Optional[List[BinaryExpression]] = None,
):
    """Reusable helper function to update one entity."""

    user.enforce_raise(obj=entity.value, act=Actions.UPDATE.value)
    _logger.debug("Updating %s with id: %s", sql_model, entity_id)

    db_entity = await _select_one(
        sql_model=sql_model,
        entity_id=entity_id,
        session=session,
        user_selector=user_selector,
    )

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
    sql_model: Type[SQLModel],
    session: AsyncSession,
    entity_id: int,
    user_selector: Optional[List[BinaryExpression]] = None,
):
    """Reusable helper function to delete one entity."""

    user.enforce_raise(obj=entity.value, act=Actions.DELETE.value)
    _logger.debug("Deleting %s with id: %s", sql_model, entity_id)

    db_entity = await _select_one(
        sql_model=sql_model,
        entity_id=entity_id,
        session=session,
        user_selector=user_selector,
    )

    await session.delete(db_entity)
    await session.commit()

    return {"ok": True}
