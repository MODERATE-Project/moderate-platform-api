import json
import logging
import re
import warnings
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Type, Union

import arrow
from fastapi import HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Text, asc, cast, desc, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute, flag_modified
from sqlalchemy.sql.elements import BinaryExpression, UnaryExpression
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


def _models_from_json(
    model_cls: Type[BaseModel],
    json_str: str,
    positional_args: Optional[List[str]] = None,
) -> List[BaseModel]:
    """Helper function to parse a JSON string into a list of models."""

    parsed = json.loads(json_str)

    if isinstance(parsed, list) and len(parsed) == 0:
        return []

    if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
        parsed = [parsed]

    _logger.debug("JSON CRUD filters: %s", parsed)

    ret = []

    for item in parsed:
        if isinstance(item, list) and positional_args:
            model_kwargs = dict(zip(positional_args, item))
            ret.append(model_cls(**model_kwargs))
        elif isinstance(item, dict):
            ret.append(model_cls(**item))
        else:
            raise ValueError(
                "Unsupported {} format: {}".format(CrudFilter.__name__, item)
            )

    return ret


class CrudSort(BaseModel):
    """Model that represents the sorting configuration for a CRUD operation.
    Inspired by: https://refine.dev/docs/api-reference/core/interfaceReferences/#crudsort
    """

    field: str
    order: Literal["asc", "desc"]

    @classmethod
    def from_json(cls, json_str: str) -> List["CrudSort"]:
        positional_args = ["field", "order"]

        try:
            return _models_from_json(
                model_cls=cls, json_str=json_str, positional_args=positional_args
            )
        except Exception as ex:
            _logger.debug("Failed to parse JSON-encoded CRUD sorters", exc_info=True)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex)
            ) from ex

    def get_expression(self, model: Type[SQLModel]) -> UnaryExpression:
        if self.order == "asc":
            return asc(getattr(model, self.field))
        elif self.order == "desc":
            return desc(getattr(model, self.field))
        else:
            raise ValueError(f"Unsupported order: {self.order}")


def _parse_value(val: Any) -> Union[datetime, int, float, str, bool, List]:
    """Helper function to parse a string into a value of the appropriate type."""

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
    value: Union[str, int, float, None]

    @classmethod
    def from_json(cls, json_str: str) -> List["CrudFilter"]:
        positional_args = ["field", "operator", "value"]

        try:
            return _models_from_json(
                model_cls=cls, json_str=json_str, positional_args=positional_args
            )
        except Exception as ex:
            _logger.debug("Failed to parse JSON-encoded CRUD filters", exc_info=True)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex)
            ) from ex

    @property
    def parsed_value(self) -> Union[datetime, int, float, str, bool, List, None]:
        if self.value is None:
            return None

        ret = _parse_value(self.value)

        if isinstance(ret, list):
            return [_parse_value(v) for v in ret]
        else:
            return ret

    def get_expression(self, model: Type[SQLModel]) -> BinaryExpression:
        mappers = {
            "eq": _map_eq,
            "ne": _map_ne,
            "lt": _map_lt,
            "gt": _map_gt,
            "lte": _map_lte,
            "gte": _map_gte,
            "in": _map_in,
            "nin": _map_nin,
            "contains": _map_contains,
        }

        if self.operator not in mappers:
            raise ValueError(f"Unsupported operator: {self.operator}")

        return mappers[self.operator](model, self)


def _map_eq(model: Type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) == crud_filter.parsed_value


def _map_ne(model: Type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) != crud_filter.parsed_value


def _map_lt(model: Type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) < crud_filter.parsed_value


def _map_gt(model: Type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) > crud_filter.parsed_value


def _map_lte(model: Type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) <= crud_filter.parsed_value


def _map_gte(model: Type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field) >= crud_filter.parsed_value


def _map_in(model: Type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field).in_(crud_filter.parsed_value)


def _map_nin(model: Type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:
    return getattr(model, crud_filter.field).notin_(crud_filter.parsed_value)


def _map_contains(model: Type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:
    return cast(getattr(model, crud_filter.field), Text).match(
        str(crud_filter.parsed_value)
    )


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
    db_entity = sql_model.model_validate(entity_create, update=entity_create_patch)
    _logger.debug("Creating %s: %s", sql_model, db_entity)
    session.add(db_entity)
    await session.commit()
    await session.refresh(db_entity)
    return db_entity


async def read_many(
    *,
    entity: Entities,
    sql_model: Type[SQLModel],
    session: AsyncSession,
    user: Optional[User] = None,
    offset: int = 0,
    limit: int = 100,
    user_selector: Optional[List[BinaryExpression]] = None,
    json_filters: Optional[str] = None,
    json_sorts: Optional[str] = None,
    select_in_load: Optional[List[InstrumentedAttribute]] = None,
):
    """Reusable helper function to read many entities."""

    if user:
        user.enforce_raise(obj=entity.value, act=Actions.READ.value)

    crud_filters: List[CrudFilter] = (
        CrudFilter.from_json(json_filters) if json_filters else []
    )

    crud_sorts: List[CrudSort] = CrudSort.from_json(json_sorts) if json_sorts else []

    statement = select(sql_model).offset(offset).limit(limit)

    select_in_load = select_in_load or []

    for item in select_in_load:
        _logger.debug("Applying selectinload: %s", item)
        statement = statement.options(selectinload(item))

    if user and not user.is_admin and user_selector:
        _logger.debug("Applying user selector as WHERE: %s", user_selector)
        statement = statement.where(*user_selector)

    _logger.debug("Applying WHERE filters: %s", crud_filters)

    statement = statement.where(
        *[crud_filter.get_expression(sql_model) for crud_filter in crud_filters]
    )

    _logger.debug("Applying ORDER BY sorts: %s", crud_sorts)

    statement = statement.order_by(
        *[crud_sort.get_expression(sql_model) for crud_sort in crud_sorts]
    )

    result = await session.execute(statement)
    entities = result.all()

    # Note that all() returns a list of tuples:
    # [
    # (Asset(username='andres.garcia', id=74, uuid='bc3048cf5ba0489e9781c1762e2c6b64'),),
    # (Asset(username='andres.garcia', id=75, uuid='ae0d444b3c3045f4a32f20dd7be450e1'),),
    # ...
    # ]
    return [item[0] for item in entities]


async def select_one(
    sql_model: Type[SQLModel],
    entity_id: int,
    session: AsyncSession,
    user_selector: Optional[List[BinaryExpression]] = None,
    select_in_load: Optional[List[InstrumentedAttribute]] = None,
) -> SQLModel:
    statement = select(sql_model).where(
        getattr(sql_model, _primary_key(sql_model)) == entity_id
    )

    select_in_load = select_in_load or []

    for item in select_in_load:
        _logger.debug("Applying selectinload: %s", item)
        statement = statement.options(selectinload(item))

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
    select_in_load: Optional[List[InstrumentedAttribute]] = None,
):
    """Reusable helper function to read one entity."""

    user.enforce_raise(obj=entity.value, act=Actions.READ.value)
    _logger.debug("Reading %s with id: %s", sql_model, entity_id)

    return await select_one(
        sql_model=sql_model,
        entity_id=entity_id,
        session=session,
        user_selector=user_selector if not user.is_admin else None,
        select_in_load=select_in_load,
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

    db_entity = await select_one(
        sql_model=sql_model,
        entity_id=entity_id,
        session=session,
        user_selector=user_selector if not user.is_admin else None,
    )

    entity_data = entity_update.model_dump(exclude_unset=True)

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

    db_entity = await select_one(
        sql_model=sql_model,
        entity_id=entity_id,
        session=session,
        user_selector=user_selector if not user.is_admin else None,
    )

    await session.delete(db_entity)
    await session.commit()

    return {"ok": True, "id": entity_id}


async def find_by_json_key(
    sql_model: Type[SQLModel],
    session: AsyncSession,
    json_column: str,
    json_key: str,
    json_value: Any,
    selector: Optional[List[BinaryExpression]] = None,
) -> List[SQLModel]:
    stmt = select(sql_model).filter(
        getattr(sql_model, json_column)[json_key] == cast(json_value, JSONB)
    )

    if selector and len(selector) > 0:
        stmt = stmt.where(*selector)

    result = await session.execute(stmt)
    return result.scalars().all()


async def update_json_key(
    sql_model: Type[SQLModel],
    session: AsyncSession,
    primary_keys: Union[List[int], int],
    json_column: str,
    json_key: str,
    json_value: Any,
):
    ids = primary_keys if isinstance(primary_keys, list) else [primary_keys]
    stmt = select(sql_model).where(sql_model.id.in_(ids))
    result = await session.execute(stmt)
    rows = result.scalars().all()

    for row in rows:
        jsonobj = getattr(row, json_column) or {}
        jsonobj.update({json_key: json_value})
        setattr(row, json_column, jsonobj)
        flag_modified(row, json_column)
        session.add(row)

    await session.commit()


_example_crud_filters = json.dumps(
    [
        ["the_date", "lte", arrow.utcnow().naive.isoformat()],
        ["the_name", "in", json.dumps(["foo", "bar"])],
    ]
)

_example_crud_sorts = json.dumps(
    [
        ["the_date", "asc"],
        ["the_name", "desc"],
    ]
)

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    CrudFiltersQuery = Query(
        default=None,
        description=(
            "A JSON-encoded array of arrays or objects that represent filters. "
            "A _filter element_ can be either an array like `[field, operator, value]`, "
            'or an object, like `{"field": field, "operator": operator, "value": value}`. '
            "Please check the [Refine documentation](https://refine.dev/docs/api-reference/core/interfaceReferences/#crudoperators) "
            "for additional context and to view the list of available operators. "
            "Also, note that not all operators are supported for every field."
        ),
        example="`{}`".format(_example_crud_filters),
        examples=[_example_crud_filters],
    )

    CrudSortsQuery = Query(
        default=None,
        description=(
            "A JSON-encoded array of arrays or objects that represent sorting fields and directions. "
            "A _sort element_ can be either an array like `[field, order]`, "
            'or an object, like `{"field": field, "order": order}`. '
            "The direction can be either `asc` or `desc`."
        ),
        example="`{}`".format(_example_crud_sorts),
        examples=[_example_crud_sorts],
    )
