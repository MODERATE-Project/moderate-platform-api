import json
import random
from datetime import datetime

import arrow
import pytest
import sqlalchemy.exc
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, SQLModel, select

from moderate_api.db import DBEngine
from moderate_api.entities.crud import CrudFilter


class ModelTest(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    limit: int | None = None
    dttm: datetime | None = Field(sa_column=DateTime(timezone=True))


async def _exec(async_session, crud_filter: CrudFilter):
    async with async_session() as session:
        statement = select(ModelTest).where(crud_filter)
        results = (await session.execute(statement)).all()
        return results


@pytest.mark.asyncio
async def test_crud_filters():  # type: ignore[no-untyped-def]
    """Test the CRUD filters."""

    item_1 = ModelTest(name="Item 1", limit=10)
    item_2 = ModelTest(name="Item 2")
    item_3 = ModelTest(name="Item 3", limit=20)
    items = [item_1, item_2, item_3]

    assert item_1.limit < item_3.limit

    async with DBEngine.instance().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(
        DBEngine.instance(), class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        for item in items:
            session.add(item)
        await session.commit()

    results = await _exec(
        async_session,
        CrudFilter(field="name", operator="eq", value=item_1.name).get_expression(
            ModelTest
        ),
    )

    assert len(results) == 1
    assert results[0][0].model_dump() == item_1.model_dump()

    results = await _exec(
        async_session,
        CrudFilter(field="name", operator="ne", value=item_1.name).get_expression(
            ModelTest
        ),
    )

    assert len(results) == 2
    assert all(result[0].model_dump() != item_1.model_dump() for result in results)

    results = await _exec(
        async_session,
        CrudFilter(field="limit", operator="gt", value=item_1.limit).get_expression(
            ModelTest
        ),
    )

    assert len(results) == 1
    assert results[0][0].model_dump() == item_3.model_dump()

    results = await _exec(
        async_session,
        CrudFilter(field="limit", operator="gte", value=item_1.limit).get_expression(
            ModelTest
        ),
    )

    assert len(results) == 2
    assert all(result[0].model_dump() != item_2.model_dump() for result in results)

    results = await _exec(
        async_session,
        CrudFilter(field="limit", operator="lt", value=item_1.limit).get_expression(
            ModelTest
        ),
    )

    assert len(results) == 0

    results = await _exec(
        async_session,
        CrudFilter(field="limit", operator="lte", value=item_1.limit).get_expression(
            ModelTest
        ),
    )

    assert len(results) == 1
    assert results[0][0].model_dump() == item_1.model_dump()

    results = await _exec(
        async_session,
        CrudFilter(
            field="limit", operator="in", value=json.dumps([item_1.limit, item_3.limit])
        ).get_expression(ModelTest),
    )

    assert len(results) == 2
    assert all(result[0].model_dump() != item_2.model_dump() for result in results)

    results = await _exec(
        async_session,
        CrudFilter(
            field="name", operator="nin", value=json.dumps([item_1.name, item_3.name])
        ).get_expression(ModelTest),
    )

    assert len(results) == 1
    assert results[0][0].model_dump() == item_2.model_dump()


@pytest.mark.asyncio
async def test_parse_values():  # type: ignore[no-untyped-def]
    """Test that values contained in the filter are parsed correctly to the proper type."""

    item_1 = ModelTest(name="Item 1", limit=10)
    item_2 = ModelTest(name="Item 2")
    item_3 = ModelTest(name="Item 3", limit=20)
    items = [item_1, item_2, item_3]

    async with DBEngine.instance().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(
        DBEngine.instance(), class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        for item in items:
            session.add(item)
        await session.commit()

    results_numbers = await _exec(
        async_session,
        CrudFilter(
            field="limit",
            operator="in",
            value=json.dumps(
                [
                    str(item_1.limit),
                    item_3.limit,
                    str(random.random()),
                ]
            ),
        ).get_expression(ModelTest),
    )

    assert len(results_numbers) == 2

    assert all(
        result[0].model_dump() != item_2.model_dump() for result in results_numbers
    )

    with pytest.raises(sqlalchemy.exc.ProgrammingError):
        await _exec(
            async_session,
            CrudFilter(
                field="limit",
                operator="in",
                value=json.dumps(["NotANumber"]),
            ).get_expression(ModelTest),
        )

    results_strings = await _exec(
        async_session,
        CrudFilter(
            field="name",
            operator="in",
            value=json.dumps([item_2.name]),
        ).get_expression(ModelTest),
    )

    assert len(results_strings) == 1
    assert results_strings[0][0].model_dump() == item_2.model_dump()


@pytest.mark.asyncio
async def test_parse_datetimes():  # type: ignore[no-untyped-def]
    """Test that datetime filters are parsed correctly."""

    now = arrow.utcnow().naive

    item_1 = ModelTest(name="Item 1", limit=10)
    item_2 = ModelTest(name="Item 2")
    item_3 = ModelTest(name="Item 3", limit=20, dttm=now)
    items = [item_1, item_2, item_3]

    async with DBEngine.instance().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(
        DBEngine.instance(), class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        for item in items:
            session.add(item)
        await session.commit()

    results_dttm = await _exec(
        async_session,
        CrudFilter(
            field="dttm",
            operator="in",
            value=json.dumps([now.isoformat()]),
        ).get_expression(ModelTest),
    )

    assert len(results_dttm) == 1
    assert results_dttm[0][0].model_dump() == item_3.model_dump()
