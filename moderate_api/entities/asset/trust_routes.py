import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from moderate_api.authz.user import UserDep
from moderate_api.config import SettingsDep
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.asset.models import (
    AssetAccessLevels,
    UploadedS3Object,
    find_s3object_by_key_or_id,
)
from moderate_api.long_running import LongRunningTask, get_task, init_task
from moderate_api.trust import (
    ProofVerificationResult,
    create_proof_task,
    fetch_verify_proof,
)

_logger = logging.getLogger(__name__)

router = APIRouter()

_TAG = "Data assets"


class AssetObjectProofCreationRequest(BaseModel):
    object_key_or_id: str | int


class AssetObjectProofCreationResponse(BaseModel):
    task_id: int | None
    obj: UploadedS3Object | None


async def _find_enforce_s3obj(
    object_key_or_id: str | int,
    session: AsyncSessionDep,
    user: UserDep,
    public_assets_allowed: bool = False,
) -> UploadedS3Object:
    s3object = await find_s3object_by_key_or_id(val=object_key_or_id, session=session)

    if not s3object:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Handle potential None asset relationship
    if not s3object.asset:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    is_asset_owner = (
        s3object.asset.username and s3object.asset.username == user.username
    )

    is_public = (
        s3object.asset.access_level == AssetAccessLevels.PUBLIC
        and public_assets_allowed
    )

    is_allowed = user.is_admin or is_asset_owner or is_public

    if not is_allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return s3object


@router.post("/proof", response_model=AssetObjectProofCreationResponse, tags=[_TAG])
async def ensure_trust_proof(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    settings: SettingsDep,
    background_tasks: BackgroundTasks,
    body: AssetObjectProofCreationRequest,
):
    if not settings.trust_service or not settings.trust_service.endpoint_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    s3object = await _find_enforce_s3obj(
        object_key_or_id=body.object_key_or_id,
        session=session,
        user=user,
        public_assets_allowed=False,
    )

    if s3object.proof_id:
        return AssetObjectProofCreationResponse(task_id=None, obj=s3object)

    task_id = await init_task(session=session, username_owner=user.username)

    background_tasks.add_task(
        create_proof_task,
        task_id=str(task_id),  # Convert int to str as expected by the function
        s3object_key_or_id=body.object_key_or_id,
        requester_username=user.username,
        user_did=None,
        create_proof_url=settings.trust_service.url_create_proof(),
    )

    return AssetObjectProofCreationResponse(task_id=task_id, obj=None)


@router.get("/proof/task/{task_id}", response_model=LongRunningTask, tags=[_TAG])
async def get_user_did_task_result(
    *, user: UserDep, session: AsyncSessionDep, task_id: int
):
    username_owner = None if user.is_admin else user.username

    task = await get_task(
        session=session, task_id=task_id, username_owner=username_owner
    )

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return task


@router.get("/proof/integrity", response_model=ProofVerificationResult, tags=[_TAG])
async def verify_trust_proof(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    settings: SettingsDep,
    object_key_or_id: str | int,
):
    if not settings.trust_service or not settings.trust_service.endpoint_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    s3object = await _find_enforce_s3obj(
        object_key_or_id=object_key_or_id,
        session=session,
        user=user,
        public_assets_allowed=True,
    )

    return await fetch_verify_proof(
        session=session,
        asset_obj_key=s3object.key,
        get_proof_url=settings.trust_service.url_get_proof(),
    )
