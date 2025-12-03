"""
A simple Postgres-backed system for managing long-running tasks without dealing with a full Celery setup.
The expectation is that the tasks will be fairly short-lived, and that the results will be small enough.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import Column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import JSON, Field, SQLModel, select

_logger = logging.getLogger(__name__)


class LongRunningTask(SQLModel, table=True):  # type: ignore[call-arg, misc]
    id: int | None = Field(default=None, primary_key=True)
    username_owner: str | None = Field(default=None)
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = Field(default=None)


async def init_task(session: AsyncSession, username_owner: str | None = None) -> int:
    the_task = LongRunningTask(username_owner=username_owner)
    session.add(the_task)
    await session.commit()
    await session.refresh(the_task)
    assert the_task.id is not None
    return the_task.id


async def get_task(
    session: AsyncSession, task_id: int, username_owner: str | None = None
) -> LongRunningTask | None:
    stmt = select(LongRunningTask).where(LongRunningTask.id == task_id)

    if username_owner:
        stmt = stmt.where(LongRunningTask.username_owner == username_owner)

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def set_task_result(
    session: AsyncSession, task_id: int, result: dict[str, Any]
) -> LongRunningTask:
    the_task = await session.get(LongRunningTask, int(task_id))
    assert the_task is not None
    the_task.result = result
    the_task.finished_at = datetime.utcnow()
    _logger.debug("Task finished: %s", the_task)
    await session.commit()
    await session.refresh(the_task)
    return the_task


async def set_task_error(
    session: AsyncSession, task_id: int, ex: Exception
) -> LongRunningTask:
    the_task = await session.get(LongRunningTask, int(task_id))
    assert the_task is not None
    the_task.error = repr(ex)
    the_task.finished_at = datetime.utcnow()
    _logger.debug("Task errored: %s", the_task)
    await session.commit()
    await session.refresh(the_task)
    return the_task
