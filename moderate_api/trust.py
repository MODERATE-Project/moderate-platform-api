import logging
import pprint
from functools import wraps
from typing import Optional, Union

import httpx
from fastapi.encoders import jsonable_encoder
from sqlmodel import select

from moderate_api.db import with_session
from moderate_api.entities.asset.models import find_s3object_by_key_or_id
from moderate_api.entities.user.models import UserMeta, get_did_for_username
from moderate_api.long_running import set_task_error, set_task_result

_TIMEOUT_SECS = 600

_logger = logging.getLogger(__name__)


def _handle_task_error(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as ex:
            _logger.debug("Error in %s", func.__name__, exc_info=ex)
            task_id = kwargs.get("task_id")

            if task_id is None:
                _logger.warning("No task_id found in kwargs")
                return

            async with with_session() as session:
                await set_task_error(session=session, task_id=task_id, ex=ex)

    return wrapper


@_handle_task_error
async def create_did_task(
    task_id: str, username: str, did_url: str, timeout_seconds: int = _TIMEOUT_SECS
):
    async with with_session() as session:
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

        await session.refresh(user_meta)

        if user_meta.trust_did:
            raise ValueError(
                f"The DID for user {username} seems to have been created in the meantime"
            )

        user_meta.trust_did = trust_did
        session.add(user_meta)
        await session.commit()
        await session.refresh(user_meta)
        _logger.debug("Updated model: %s", user_meta)

        result = jsonable_encoder(user_meta)
        await set_task_result(session=session, task_id=task_id, result=result)


@_handle_task_error
async def create_proof_task(
    task_id: str,
    create_proof_url: str,
    s3object_key_or_id: Union[str, int],
    requester_username: str,
    user_did: Optional[str] = None,
    timeout_seconds: int = _TIMEOUT_SECS,
):
    async with with_session() as session:
        s3obj = await find_s3object_by_key_or_id(
            val=s3object_key_or_id, session=session
        )

        if not s3obj:
            raise ValueError(f"Asset object '{s3object_key_or_id}' not found")

        if not s3obj.sha256_hash:
            raise ValueError(f"Asset object '{s3object_key_or_id}' has no hash")

        if s3obj.proof_id:
            raise ValueError(f"Asset object '{s3object_key_or_id}' already has a proof")

        default_proof_owner_username = (
            s3obj.asset.username if s3obj.asset.username else requester_username
        )

        if not user_did:
            _logger.debug(
                "No DID provided, using default proof owner username: %s",
                default_proof_owner_username,
            )

            user_did = await get_did_for_username(
                username=default_proof_owner_username, session=session
            )

            if not user_did:
                raise ValueError(
                    f"User {default_proof_owner_username} does not have a DID and thus cannot be a proof owner"
                )

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            json_payload = {
                "asset_hash": s3obj.key,
                "metadata_hash": s3obj.sha256_hash,
                "did": user_did,
            }

            _logger.debug(
                "Calling %s with payload:\n%s",
                create_proof_url,
                pprint.pformat(json_payload),
            )

            resp = await client.post(create_proof_url, json=json_payload)
            resp.raise_for_status()
            proof_id = resp.text
            _logger.debug("Got proof ID: %s", proof_id)

        await session.refresh(s3obj)

        if s3obj.proof_id:
            raise ValueError(
                f"The proof for object '{s3object_key_or_id}' seems to have been created in the meantime"
            )

        s3obj.proof_id = proof_id
        session.add(s3obj)
        await session.commit()
        await session.refresh(s3obj)
        _logger.debug("Updated model: %s", s3obj)

        result = jsonable_encoder(s3obj)
        await set_task_result(session=session, task_id=task_id, result=result)
