import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BinaryExpression
from sqlmodel import or_, select

from moderate_api.authz import User, UserDep
from moderate_api.authz.user import User
from moderate_api.config import Settings, SettingsDep
from moderate_api.db import AsyncSessionDep, with_session
from moderate_api.entities.crud import (
    CrudFiltersQuery,
    CrudSortsQuery,
    create_one,
    delete_one,
    read_many,
    read_one,
    update_one,
)
from moderate_api.entities.user.models import (
    UserMeta,
    UserMetaCreate,
    UserMetaRead,
    UserMetaUpdate,
    ensure_user_meta,
)
from moderate_api.enums import Entities
from moderate_api.long_running import (
    LongRunningTask,
    get_task,
    init_task,
    set_task_error,
    set_task_result,
)

_TAG = "User metadata"
_ENTITY = Entities.USER

_logger = logging.getLogger(__name__)


async def build_selector(user: User, session: AsyncSession) -> List[BinaryExpression]:
    return [
        or_(
            UserMeta.username == user.username,
        )
    ]


async def build_create_patch(
    user: User, session: AsyncSession
) -> Optional[Dict[str, Any]]:
    return {}


router = APIRouter()


@router.post("/", response_model=UserMetaRead, tags=[_TAG])
async def create_user_meta(
    *, user: UserDep, session: AsyncSessionDep, entity: UserMetaCreate
):
    entity_create_patch = await build_create_patch(user=user, session=session)

    return await create_one(
        user=user,
        entity=_ENTITY,
        sql_model=UserMeta,
        session=session,
        entity_create=entity,
        entity_create_patch=entity_create_patch,
    )


@router.get("/", response_model=List[UserMetaRead], tags=[_TAG])
async def query_user_meta(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    offset: int = 0,
    limit: int = Query(default=100, le=100),
    filters: Optional[str] = CrudFiltersQuery,
    sorts: Optional[str] = CrudSortsQuery,
):
    user_selector = await build_selector(user=user, session=session)

    return await read_many(
        user=user,
        entity=_ENTITY,
        sql_model=UserMeta,
        session=session,
        offset=offset,
        limit=limit,
        user_selector=user_selector,
        json_filters=filters,
        json_sorts=sorts,
    )


@router.get("/{id}", response_model=UserMetaRead, tags=[_TAG])
async def read_user_meta(*, user: UserDep, session: AsyncSessionDep, id: int):
    user_selector = await build_selector(user=user, session=session)

    return await read_one(
        user=user,
        entity=_ENTITY,
        sql_model=UserMeta,
        session=session,
        entity_id=id,
        user_selector=user_selector,
    )


@router.patch("/{id}", response_model=UserMetaRead, tags=[_TAG])
async def update_user_meta(
    *, user: UserDep, session: AsyncSessionDep, id: int, entity: UserMetaUpdate
):
    user_selector = await build_selector(user=user, session=session)

    return await update_one(
        user=user,
        entity=_ENTITY,
        sql_model=UserMeta,
        session=session,
        entity_id=id,
        entity_update=entity,
        user_selector=user_selector,
    )


@router.delete("/{id}", tags=[_TAG])
async def delete_user_meta(*, user: UserDep, session: AsyncSessionDep, id: int):
    user_selector = await build_selector(user=user, session=session)

    return await delete_one(
        user=user,
        entity=_ENTITY,
        sql_model=UserMeta,
        session=session,
        entity_id=id,
        user_selector=user_selector,
    )


async def _create_did(
    task_id: str, username: str, did_url: str, timeout_seconds: int = 600
):
    async with with_session() as session:
        try:
            _logger.debug("Creating DID for %s", username)
            stmt = select(UserMeta).where(UserMeta.username == username)
            result = await session.execute(stmt)
            user_meta: UserMeta = result.scalar_one_or_none()
            _logger.debug("Found UserMeta: %s", user_meta)

            if not user_meta:
                raise ValueError(f"User {username} not found")

            if user_meta.trust_did:
                raise ValueError(f"User {username} already has a DID")

            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                _logger.debug("Calling %s", did_url)
                resp = await client.post(did_url)
                resp.raise_for_status()
                trust_did = resp.text
                _logger.debug("Got DID: %s", trust_did)

            user_meta.trust_did = trust_did
            session.add(user_meta)
            await session.commit()
            await session.refresh(user_meta)
            _logger.debug("Updated UserMeta: %s", user_meta)
            result = json.loads(user_meta.json())
            await set_task_result(session=session, task_id=task_id, result=result)
        except Exception as ex:
            _logger.debug("Error creating DID for %s", username, exc_info=ex)
            await set_task_error(session=session, task_id=task_id, ex=ex)


class UserDIDCreationRequest(BaseModel):
    username: str


class UserDIDCreationResponse(BaseModel):
    task_id: Optional[int]
    user_meta: Optional[UserMetaRead]


@router.post("/did", response_model=UserDIDCreationResponse, tags=[_TAG])
async def ensure_user_trust_did(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    settings: SettingsDep,
    background_tasks: BackgroundTasks,
    body: UserDIDCreationRequest,
):
    if not settings.trust_service or not settings.trust_service.endpoint_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    if user.username != body.username and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    user_meta = await ensure_user_meta(username=body.username, session=session)

    _logger.info("%s", user_meta)

    if user_meta.trust_did:
        return UserDIDCreationResponse(task_id=None, user_meta=user_meta)

    task_id = await init_task(session=session, username_owner=user.username)

    background_tasks.add_task(
        _create_did,
        task_id=task_id,
        username=user.username,
        did_url=settings.trust_service.url_create_did(),
    )

    return UserDIDCreationResponse(task_id=task_id)


@router.get("/did/task/{task_id}", response_model=LongRunningTask, tags=[_TAG])
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
