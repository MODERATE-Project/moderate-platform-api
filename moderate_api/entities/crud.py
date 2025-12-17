import enum as python_enum
import json
import logging
import re
import warnings
from datetime import datetime
from typing import (
    Any,
    Literal,
    TypeVar,
)

import arrow
from fastapi import Query, Response
from pydantic import BaseModel
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Text, asc, desc, func
from sqlalchemy import cast as sql_cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute, flag_modified
from sqlalchemy.sql.elements import (
    BinaryExpression,
    ColumnElement,
    UnaryExpression,
)
from sqlmodel import SQLModel, select

from moderate_api.authz import User
from moderate_api.config import get_settings
from moderate_api.enums import Actions, Entities
from moderate_api.utils.exceptions import raise_bad_request, raise_not_found

_logger = logging.getLogger(__name__)

_REGEX_DTTM_ISO = (
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(([+-]\d{2}:\d{2})|Z)?$"
)

# Matches a list of elements separated by commas,
# where spaces are allowed before and after the comma,
# but not within the elements themselves,
# and the string should not start or end with brackets.
_REGEX_LIST = r"(?<!\[)\b\w+\b(?:(?:\s*,\s*\b\w+\b)+)(?!\])"

# Generic type variable for better type safety
T = TypeVar("T", bound=BaseModel)


def _models_from_json(
    model_cls: type[T],
    json_str: str,
    positional_args: list[str] | None = None,
) -> list[T]:
    """Helper function to parse a JSON string into a list of models."""

    parsed = json.loads(json_str)

    if isinstance(parsed, list) and len(parsed) == 0:
        return []

    if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
        parsed = [parsed]

    _logger.debug("JSON CRUD filters: %s", parsed)

    ret: list[T] = []

    for item in parsed:
        if isinstance(item, list) and positional_args:
            model_kwargs = dict(zip(positional_args, item, strict=False))
            ret.append(model_cls(**model_kwargs))
        elif isinstance(item, dict):
            ret.append(model_cls(**item))
        else:
            raise ValueError(f"Unsupported {CrudFilter.__name__} format: {item}")

    return ret


class CrudSort(BaseModel):
    """Model that represents the sorting configuration for a CRUD operation.
    Inspired by: https://refine.dev/docs/api-reference/core/interfaceReferences/#crudsort
    """

    field: str
    order: Literal["asc", "desc"]

    @classmethod
    def from_json(cls, json_str: str) -> list["CrudSort"]:
        positional_args = ["field", "order"]

        try:
            return _models_from_json(
                model_cls=cls, json_str=json_str, positional_args=positional_args
            )
        except Exception as ex:
            _logger.debug("Failed to parse JSON-encoded CRUD sorters", exc_info=True)
            raise_bad_request(detail=str(ex))

    def get_expression(self, model: type[SQLModel]) -> UnaryExpression[Any]:  # type: ignore[type-arg]
        if self.order == "asc":
            return asc(getattr(model, self.field))
        elif self.order == "desc":
            return desc(getattr(model, self.field))
        else:
            raise ValueError(f"Unsupported order: {self.order}")


def _parse_value(val: Any) -> datetime | int | float | str | bool | list[Any]:
    """Helper function to parse a string into a value of the appropriate type."""

    try:
        if re.match(_REGEX_LIST, val):
            return json.loads(f"[{val}]")  # type: ignore[no-any-return]
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


def _normalize_enum_value(model: type[SQLModel], field: str, value: Any) -> Any:
    """Normalize enum filter values to proper enum members for SQLAlchemy queries.

    **Context: Enum Case Mismatch Issue**

    This function solves a critical mismatch between how PostgreSQL enums, Python enums,
    and Pydantic serialization work together:

    1. **PostgreSQL Enum Storage**: Stores the enum MEMBER NAME (e.g., 'MATRIX_PROFILE')
    2. **Python Enum Definition**: Has a value property (e.g., WorkflowJobTypes.MATRIX_PROFILE = "matrix_profile")
    3. **Pydantic Serialization**: Uses the `.value` when converting to JSON (returns "matrix_profile")
    4. **SQLAlchemy Querying**: Expects the enum member, then uses the NAME in SQL queries

    **The Problem:**
    - Frontend receives: `{"job_type": "matrix_profile"}` (Pydantic serialized value)
    - Frontend sends filter: `["job_type", "eq", "matrix_profile"]` (using received value)
    - Backend tries to query: `WHERE job_type = 'matrix_profile'` (direct value)
    - PostgreSQL rejects: Invalid enum value (expects 'MATRIX_PROFILE')

    **The Solution:**
    This function intercepts filter values and converts them back to enum members:
    - Input: "matrix_profile" (string value from API)
    - Output: WorkflowJobTypes.MATRIX_PROFILE (enum member)
    - SQLAlchemy then uses: 'MATRIX_PROFILE' (member name) in the SQL query

    **Why This Approach:**
    - ✅ Backwards compatible: No database migrations required
    - ✅ No breaking changes: API contract remains unchanged
    - ✅ Handles edge cases: Works if value is already an enum member
    - ✅ Database-level filtering: More efficient than client-side filtering
    - ✅ Future-proof: Automatically handles new enum types

    Args:
        model: The SQLModel class being queried
        field: The field name being filtered
        value: The filter value (potentially an enum value string)

    Returns:
        The normalized value - either the enum member or the original value if not an enum field
    """
    # Get the column from the model
    column = getattr(model, field, None)
    if column is None:
        return value

    # Check if this column is an enum type
    if hasattr(column, "type") and isinstance(column.type, SQLEnum):
        enum_class = column.type.enum_class

        # Only process if it's a Python enum
        if enum_class and issubclass(enum_class, python_enum.Enum):
            # If value is already an enum member, return as-is
            if isinstance(value, enum_class):
                return value

            # If value is a list, normalize each item
            if isinstance(value, list):
                return [_normalize_enum_value(model, field, v) for v in value]

            # Try to convert string value to enum member
            try:
                # This converts "matrix_profile" → WorkflowJobTypes.MATRIX_PROFILE
                enum_member = enum_class(value)
                _logger.debug(
                    "Normalized enum filter: field=%s, value=%s → member=%s",
                    field,
                    value,
                    enum_member,
                )
                return enum_member
            except (ValueError, KeyError):
                # If conversion fails, return original value (let SQLAlchemy handle the error)
                _logger.warning(
                    "Failed to normalize enum value for field=%s, value=%s",
                    field,
                    value,
                )
                pass

    return value


class CrudFilter(BaseModel):
    """Model that represents a filter for a CRUD operation.
    Inspired by: https://refine.dev/docs/api-reference/core/interfaceReferences/#crudfilters
    """

    field: str
    operator: str
    value: str | int | float | None

    @classmethod
    def from_json(cls, json_str: str) -> list["CrudFilter"]:
        positional_args = ["field", "operator", "value"]

        try:
            return _models_from_json(
                model_cls=cls, json_str=json_str, positional_args=positional_args
            )
        except Exception as ex:
            _logger.debug("Failed to parse JSON-encoded CRUD filters", exc_info=True)
            raise_bad_request(detail=str(ex))

    @property
    def parsed_value(self) -> datetime | int | float | str | bool | list | None:
        if self.value is None:
            return None

        ret = _parse_value(self.value)

        if isinstance(ret, list):
            return [_parse_value(v) for v in ret]
        else:
            return ret

    def get_expression(self, model: type[SQLModel]) -> BinaryExpression:  # type: ignore[type-arg]
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


def _map_eq(model: type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:  # type: ignore[type-arg]
    # Normalize enum values before comparison (fixes PostgreSQL enum case mismatch)
    value = _normalize_enum_value(model, crud_filter.field, crud_filter.parsed_value)
    return getattr(model, crud_filter.field) == value


def _map_ne(model: type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:  # type: ignore[type-arg]
    # Normalize enum values before comparison (fixes PostgreSQL enum case mismatch)
    value = _normalize_enum_value(model, crud_filter.field, crud_filter.parsed_value)
    return getattr(model, crud_filter.field) != value


def _map_lt(model: type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:  # type: ignore[type-arg]
    # Normalize enum values before comparison (fixes PostgreSQL enum case mismatch)
    value = _normalize_enum_value(model, crud_filter.field, crud_filter.parsed_value)
    return getattr(model, crud_filter.field) < value


def _map_gt(model: type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:  # type: ignore[type-arg]
    # Normalize enum values before comparison (fixes PostgreSQL enum case mismatch)
    value = _normalize_enum_value(model, crud_filter.field, crud_filter.parsed_value)
    return getattr(model, crud_filter.field) > value


def _map_lte(model: type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:  # type: ignore[type-arg]
    # Normalize enum values before comparison (fixes PostgreSQL enum case mismatch)
    value = _normalize_enum_value(model, crud_filter.field, crud_filter.parsed_value)
    return getattr(model, crud_filter.field) <= value


def _map_gte(model: type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:  # type: ignore[type-arg]
    # Normalize enum values before comparison (fixes PostgreSQL enum case mismatch)
    value = _normalize_enum_value(model, crud_filter.field, crud_filter.parsed_value)
    return getattr(model, crud_filter.field) >= value


def _map_in(model: type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:  # type: ignore[type-arg]
    # Normalize enum values before comparison (fixes PostgreSQL enum case mismatch)
    value = _normalize_enum_value(model, crud_filter.field, crud_filter.parsed_value)
    return getattr(model, crud_filter.field).in_(value)


def _map_nin(model: type[SQLModel], crud_filter: CrudFilter) -> BinaryExpression:  # type: ignore[type-arg]
    # Normalize enum values before comparison (fixes PostgreSQL enum case mismatch)
    value = _normalize_enum_value(model, crud_filter.field, crud_filter.parsed_value)
    return getattr(model, crud_filter.field).notin_(value)


def _map_contains(
    model: type[SQLModel], crud_filter: CrudFilter
) -> ColumnElement[bool]:
    return sql_cast(getattr(model, crud_filter.field), Text).match(
        str(crud_filter.parsed_value)
    )


def _primary_key(sql_model: type[SQLModel]) -> str:
    for column in sql_model.__table__.primary_key:
        return column.name
    # Fallback for models without explicit primary key
    raise ValueError(f"No primary key found for model {sql_model}")


async def set_response_count_header(
    response: Response, sql_model: type[SQLModel], session: AsyncSession
) -> None:
    stmt = select(func.count()).select_from(sql_model)
    result = await session.execute(stmt)
    count = result.scalar_one()
    settings = get_settings()
    response.headers[settings.response_total_count_header] = str(count)


async def create_one(
    *,
    user: User,
    entity: Entities,
    sql_model: type[SQLModel],
    session: AsyncSession,
    entity_create: SQLModel,
    entity_create_patch: dict[str, Any] | None = None,
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
    sql_model: type[SQLModel],
    session: AsyncSession,
    user: User | None = None,
    offset: int = 0,
    limit: int = 100,
    user_selector: list[BinaryExpression] | None = None,
    json_filters: str | None = None,
    json_sorts: str | None = None,
    select_in_load: list[InstrumentedAttribute] | None = None,
    skip_admin_bypass: bool = False,
):
    """Reusable helper function to read many entities."""

    if user:
        user.enforce_raise(obj=entity.value, act=Actions.READ.value)

    crud_filters: list[CrudFilter] = (
        CrudFilter.from_json(json_filters) if json_filters else []
    )

    crud_sorts: list[CrudSort] = CrudSort.from_json(json_sorts) if json_sorts else []

    statement = select(sql_model).offset(offset).limit(limit)

    select_in_load = select_in_load or []

    for item in select_in_load:
        _logger.debug("Applying selectinload: %s", item)
        statement = statement.options(selectinload(item))

    must_apply_user_selector = (
        user and (not user.is_admin or skip_admin_bypass)
    ) or not user

    if must_apply_user_selector and user_selector:
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
    result_items = result.scalars().all()

    return result_items


async def select_one(
    sql_model: type[SQLModel],
    entity_id: int,
    session: AsyncSession,
    user_selector: list[BinaryExpression] | None = None,
    select_in_load: list[InstrumentedAttribute] | None = None,
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
        raise_not_found()

    return entity[0]


async def read_one(
    *,
    user: User,
    entity: Entities,
    sql_model: type[SQLModel],
    session: AsyncSession,
    entity_id: int,
    user_selector: list[BinaryExpression] | None = None,
    select_in_load: list[InstrumentedAttribute] | None = None,
):
    """Reusable helper function to read one entity."""

    user.enforce_raise(obj=entity.value, act=Actions.READ.value)
    _logger.debug("Reading %s with id: %s", sql_model, entity_id)

    return await select_one(
        sql_model=sql_model,
        entity_id=entity_id,
        session=session,
        user_selector=user.apply_admin_bypass(user_selector),
        select_in_load=select_in_load,
    )


async def update_one(
    *,
    user: User,
    entity: Entities,
    sql_model: type[SQLModel],
    session: AsyncSession,
    entity_id: int,
    entity_update: SQLModel,
    user_selector: list[BinaryExpression] | None = None,
):
    """Reusable helper function to update one entity."""

    user.enforce_raise(obj=entity.value, act=Actions.UPDATE.value)
    _logger.debug("Updating %s with id: %s", sql_model, entity_id)

    db_entity = await select_one(
        sql_model=sql_model,
        entity_id=entity_id,
        session=session,
        user_selector=user.apply_admin_bypass(user_selector),
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
    sql_model: type[SQLModel],
    session: AsyncSession,
    entity_id: int,
    user_selector: list[BinaryExpression] | None = None,
):
    """Reusable helper function to delete one entity."""

    user.enforce_raise(obj=entity.value, act=Actions.DELETE.value)
    _logger.debug("Deleting %s with id: %s", sql_model, entity_id)

    db_entity = await select_one(
        sql_model=sql_model,
        entity_id=entity_id,
        session=session,
        user_selector=user.apply_admin_bypass(user_selector),
    )

    await session.delete(db_entity)
    await session.commit()

    return {"ok": True, "id": entity_id}


async def find_by_json_key(
    sql_model: type[SQLModel],
    session: AsyncSession,
    json_column: str,
    json_key: str,
    json_value: Any,
    selector: list[BinaryExpression] | None = None,
) -> list[SQLModel]:
    stmt = select(sql_model).filter(
        getattr(sql_model, json_column)[json_key] == sql_cast(json_value, JSONB)
    )

    if selector and len(selector) > 0:
        stmt = stmt.where(*selector)

    result = await session.execute(stmt)
    # Convert Sequence to List for type compatibility
    return list(result.scalars().all())


async def update_json_key(
    sql_model: type[SQLModel],
    session: AsyncSession,
    primary_keys: list[int] | int,
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
        example=f"`{_example_crud_filters}`",
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
        example=f"`{_example_crud_sorts}`",
        examples=[_example_crud_sorts],
    )
