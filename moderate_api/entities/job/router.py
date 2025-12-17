import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import aio_pika
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BinaryExpression
from sqlmodel import or_, select

from moderate_api.authz import User, UserDep
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.asset.models import UploadedS3Object
from moderate_api.entities.crud import (
    CrudFiltersQuery,
    CrudSortsQuery,
    create_one,
    read_many,
    read_one,
    set_response_count_header,
    update_one,
)
from moderate_api.entities.job.models import (
    ARGUMENTS_TYPE_MAP,
    MatrixProfileArguments,
    MatrixProfileMessage,
    WorkflowJob,
    WorkflowJobCreate,
    WorkflowJobRead,
    WorkflowJobUpdate,
    can_user_create_job,
    can_user_run_workflow_on_asset,
)
from moderate_api.enums import Entities, WorkflowJobTypes
from moderate_api.message_queue import RabbitDep
from moderate_api.object_storage import S3ClientDep

_logger = logging.getLogger(__name__)

_TAG = "Workflow jobs"
_ENTITY = Entities.WORKFLOW_JOB


async def build_selector(user: User, session: AsyncSession) -> list[BinaryExpression]:
    return [
        or_(
            WorkflowJob.creator_username == user.username,
        )
    ]


async def build_create_patch(
    user: User, session: AsyncSession
) -> dict[str, Any] | None:
    return {
        WorkflowJob.creator_username.key: user.username,
    }


router = APIRouter()


@router.get("", response_model=list[WorkflowJobRead], tags=[_TAG])
async def query_workflow_jobs(
    *,
    response: Response,
    user: UserDep,
    s3: S3ClientDep,
    session: AsyncSessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    filters: str | None = CrudFiltersQuery,
    sorts: str | None = CrudSortsQuery,
    with_extended_results: str | None = Query(default=None),
):
    user_selector = await build_selector(user=user, session=session)

    await set_response_count_header(
        response=response,
        sql_model=WorkflowJob,
        session=session,
    )

    jobs = await read_many(
        user=user,
        entity=_ENTITY,
        sql_model=WorkflowJob,
        session=session,
        offset=offset,
        limit=limit,
        user_selector=user_selector,
        json_filters=filters,
        json_sorts=sorts,
        skip_admin_bypass=True,
    )

    if not with_extended_results:
        return jobs

    result_jobs = []
    for job in jobs:
        job_read = WorkflowJobRead.model_validate(job)

        if (
            job.finalised_at
            and job.results
            and job.job_type == WorkflowJobTypes.MATRIX_PROFILE
        ):
            extended_results = await _add_matrix_profile_extended_results(
                workflow_job=job, s3=s3, expiration_secs=7200
            )
            if extended_results:
                job_read.extended_results = extended_results

        result_jobs.append(job_read)

    return result_jobs


async def _add_matrix_profile_extended_results(
    workflow_job: WorkflowJob, s3: S3ClientDep, expiration_secs: int = 3600
) -> dict | None:
    if not workflow_job.results:
        return None

    output_bucket = workflow_job.results.get("output_bucket")
    output_key = workflow_job.results.get("output_key")
    error_logs_key = workflow_job.results.get("error_logs_key")

    if not output_bucket:
        return None

    extended_results = {}

    if output_key:
        download_url = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": output_bucket, "Key": output_key},
            ExpiresIn=expiration_secs,
        )
        extended_results["download_url"] = download_url

    if error_logs_key:
        error_logs_download_url = await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": output_bucket, "Key": error_logs_key},
            ExpiresIn=expiration_secs,
        )
        extended_results["error_logs_download_url"] = error_logs_download_url

    return extended_results if extended_results else None


@router.get("/{id}", response_model=WorkflowJobRead, tags=[_TAG])
async def read_workflow_job(
    *,
    user: UserDep,
    s3: S3ClientDep,
    session: AsyncSessionDep,
    id: int,
    with_extended_results: str | None = Query(default=None),
):
    user_selector = await build_selector(user=user, session=session)

    workflow_job: WorkflowJob = await read_one(
        user=user,
        entity=_ENTITY,
        sql_model=WorkflowJob,
        session=session,
        entity_id=id,
        user_selector=user_selector,
    )

    extended_results = None

    if (
        with_extended_results
        and workflow_job.results
        and workflow_job.finalised_at
        and workflow_job.job_type == WorkflowJobTypes.MATRIX_PROFILE
    ):
        extended_results = await _add_matrix_profile_extended_results(
            workflow_job=workflow_job, s3=s3, expiration_secs=7200
        )

    response = WorkflowJobRead.model_validate(workflow_job)

    if extended_results:
        response.extended_results = extended_results

    return response


MessageBuilderType = Callable[
    [User, AsyncSession, BaseModel, S3ClientDep, WorkflowJob],
    Awaitable[BaseModel],
]


async def _build_matrix_profile_message(
    user: User,
    session: AsyncSession,
    job_args: MatrixProfileArguments,
    s3: S3ClientDep,
    workflow_job: WorkflowJob,
) -> BaseModel:
    result = await session.execute(
        select(UploadedS3Object).where(
            UploadedS3Object.id == job_args.uploaded_s3_object_id
        )
    )

    s3_object: UploadedS3Object = result.scalar_one_or_none()

    if not s3_object:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset object not found.",
        )

    if not await can_user_run_workflow_on_asset(
        user=user, session=session, asset=s3_object.asset
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have permission to run a workflow on this asset.",
        )

    return MatrixProfileMessage(
        workflow_job_id=workflow_job.id,
        analysis_variable=job_args.analysis_variable,
        bucket=s3_object.bucket,
        key=s3_object.key,
    )


_MESSAGE_BUILDERS_MAP: dict[str, MessageBuilderType] = {
    WorkflowJobTypes.MATRIX_PROFILE.value: _build_matrix_profile_message,
}


@router.post("", response_model=WorkflowJobRead, tags=[_TAG])
async def create_workflow_job(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    rabbit: RabbitDep,
    s3: S3ClientDep,
    entity: WorkflowJobCreate,
):
    if rabbit is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Message broker connection not available.",
        )

    if not await can_user_create_job(user=user, job_create=entity, session=session):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not allowed to create job. Please try again later.",
        )

    args_model = ARGUMENTS_TYPE_MAP.get(entity.job_type.value)

    if not args_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown job type.",
        )

    try:
        job_args: BaseModel = args_model(**entity.arguments)
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid arguments for job type.",
        ) from err

    msg_builder = _MESSAGE_BUILDERS_MAP.get(entity.job_type.value)

    if not msg_builder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown job type.",
        )

    entity_create_patch = await build_create_patch(user=user, session=session)

    workflow_job: WorkflowJob = await create_one(
        user=user,
        entity=_ENTITY,
        sql_model=WorkflowJob,
        session=session,
        entity_create=entity,
        entity_create_patch=entity_create_patch,
    )

    try:
        message = await msg_builder(user, session, job_args, s3, workflow_job)
    except Exception:
        await session.delete(workflow_job)
        await session.commit()
        raise

    await rabbit.channel.default_exchange.publish(
        message=aio_pika.Message(body=message.json().encode()),
        routing_key=entity.job_type.value,
    )

    return workflow_job


@router.patch("/{id}", response_model=WorkflowJobRead, tags=[_TAG])
async def update_workflow_job(
    *, user: UserDep, session: AsyncSessionDep, id: int, entity: WorkflowJobUpdate
):
    if not entity.finalised_at:
        entity.finalised_at = datetime.now(tz=timezone.utc).replace(tzinfo=None)

    user_selector = await build_selector(user=user, session=session)

    return await update_one(
        user=user,
        entity=_ENTITY,
        sql_model=WorkflowJob,
        session=session,
        entity_id=id,
        entity_update=entity,
        user_selector=user_selector,
    )
