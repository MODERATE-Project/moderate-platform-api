from datetime import datetime, timezone
from typing import Dict, Optional

from pydantic import BaseModel
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select

from moderate_api.authz import User
from moderate_api.authz.user import User
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.access_request.models import valid_access_request_exists
from moderate_api.entities.asset.models import Asset, AssetAccessLevels
from moderate_api.enums import WorkflowJobTypes

_DEFAULT_JOB_DEBOUNCE_SECS = 10


def _now_factory() -> datetime:
    return datetime.now(tz=timezone.utc).replace(tzinfo=None)


class WorkflowJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_type: WorkflowJobTypes
    arguments: Optional[Dict] = Field(default=None, sa_column=Column(JSONB))
    results: Optional[Dict] = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=_now_factory, index=True)
    finalised_at: Optional[datetime] = Field(default=None, index=True)
    creator_username: str


class WorkflowJobRead(SQLModel):
    id: int
    job_type: WorkflowJobTypes
    arguments: Optional[Dict]
    results: Optional[Dict]
    created_at: datetime
    finalised_at: Optional[datetime]
    creator_username: str


class WorkflowJobCreate(SQLModel):
    job_type: WorkflowJobTypes
    arguments: Optional[Dict]


class WorkflowJobUpdate(SQLModel):
    results: Dict
    finalised_at: Optional[datetime]


class MatrixProfileArguments(BaseModel):
    uploaded_s3_object_id: int
    analysis_variable: str


class MatrixProfileMessage(BaseModel):
    workflow_job_id: int
    file_url: str
    analysis_variable: str


ARGUMENTS_TYPE_MAP: Dict[str, BaseModel] = {
    WorkflowJobTypes.MATRIX_PROFILE.value: MatrixProfileArguments,
}

MESSAGES_TYPE_MAP: Dict[str, BaseModel] = {
    WorkflowJobTypes.MATRIX_PROFILE.value: MatrixProfileMessage,
}


async def can_user_run_workflow_on_asset(
    user: User, session: AsyncSessionDep, asset: Asset
) -> bool:
    if user.is_admin:
        return True

    if asset.username and asset.username == user.username:
        return True

    if asset.access_level == AssetAccessLevels.PUBLIC:
        return True

    if await valid_access_request_exists(
        requester_username=user.username, asset=asset, session=session
    ):
        return True

    return False


async def can_user_create_job(
    user: User,
    job_create: WorkflowJobCreate,
    session: AsyncSession,
    job_debounce_secs: int = _DEFAULT_JOB_DEBOUNCE_SECS,
) -> bool:
    latest_job = await session.execute(
        select(WorkflowJob)
        .where(WorkflowJob.creator_username == user.username)
        .where(WorkflowJob.job_type == job_create.job_type)
        .order_by(WorkflowJob.created_at.desc())
        .limit(1)
    )

    latest_job = latest_job.scalars().first()
    now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
    diff_secs = (now - latest_job.created_at).total_seconds() if latest_job else None

    return diff_secs is None or diff_secs >= job_debounce_secs
