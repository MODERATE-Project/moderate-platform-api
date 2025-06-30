"""
Trust service integration for asset proofs and DID operations.

This module handles interactions with the Trust API microservice for creating
asset proofs and managing user DIDs (Decentralized Identifiers).

TEMPORARY WORKAROUND NOTICE:
This module contains a temporary workaround for username resolution issues in
the asset system. The workaround infers usernames from S3 key patterns when
the database-level asset username doesn't match the actual uploader.

Key functions with workaround logic:
- _infer_username_from_asset_key(): Extracts username from '<username>-assets/*' pattern
- create_proof_task(): Uses inferred username when database username is inconsistent

TODO: Remove the workaround once the underlying asset ownership issue is resolved.
The root cause is that assets can have multiple objects uploaded by different users,
but the username is currently stored at the asset level in the database.

Search for "TEMPORARY WORKAROUND" comments to locate all related code.
"""

import logging
import pprint
import re
from functools import wraps
from typing import Optional, Union

import httpx
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlmodel import select

from moderate_api.db import AsyncSessionDep, with_session
from moderate_api.entities.asset.models import (
    UploadedS3Object,
    find_s3object_by_key_or_id,
)
from moderate_api.entities.user.models import UserMeta, get_did_for_username
from moderate_api.long_running import set_task_error, set_task_result

_TIMEOUT_SECS_HIGH = 600
_TIMEOUT_SECS_LOW = 30

_logger = logging.getLogger(__name__)


def _infer_username_from_asset_key(asset_key: str) -> Optional[str]:
    """
    TEMPORARY WORKAROUND: Infer username from asset key pattern.

    This function attempts to extract the username from asset keys that follow
    the pattern '<username>-assets/*'. This is a temporary solution to address
    cases where the database-level asset username doesn't match the actual
    uploader of individual asset objects.

    TODO: Remove this workaround once the underlying asset ownership issue
    is properly fixed. The root cause is that assets can have multiple objects
    uploaded by different users, but the username is stored at the asset level.

    Args:
        asset_key (str): The S3 object key to analyze

    Returns:
        Optional[str]: The inferred username if pattern matches, None otherwise
    """

    # Pattern: <username>-assets/*
    # Note: Username can contain hyphens, but must end with '-assets/'
    pattern = r"^(.+?)-assets/"
    match = re.match(pattern, asset_key)

    if match:
        username = match.group(1)

        # Ensure username is not empty
        if username:
            _logger.debug(
                "Inferred username '%s' from asset key pattern: %s", username, asset_key
            )
            return username

    _logger.debug("Could not infer username from asset key: %s", asset_key)
    return None


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
    task_id: str, username: str, did_url: str, timeout_seconds: int = _TIMEOUT_SECS_HIGH
):
    async with with_session() as session:
        _logger.debug("Creating DID for %s", username)
        stmt = select(UserMeta).where(UserMeta.username == username)
        result = await session.execute(stmt)
        user_meta = result.scalar_one_or_none()
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
    timeout_seconds: int = _TIMEOUT_SECS_HIGH,
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

        # TEMPORARY WORKAROUND: Check if we should use username inferred from key pattern
        # TODO: Remove this workaround once asset ownership is properly handled
        # The issue is that assets can have multiple objects uploaded by different users,
        # but the username is stored at the asset level in the database.

        inferred_username = _infer_username_from_asset_key(s3obj.key)
        database_username = s3obj.asset.username  # type: ignore

        if (
            inferred_username
            and database_username
            and inferred_username != database_username
        ):
            _logger.warning(
                "TEMPORARY WORKAROUND: Using inferred username '%s' from key pattern instead of "
                "database username '%s' for asset object '%s'. This indicates a data consistency issue.",
                inferred_username,
                database_username,
                s3obj.key,
            )

            default_proof_owner_username = inferred_username
        elif inferred_username and not database_username:
            _logger.info(
                "TEMPORARY WORKAROUND: Using inferred username '%s' from key pattern for "
                "asset object '%s' with no database username.",
                inferred_username,
                s3obj.key,
            )

            default_proof_owner_username = inferred_username
        else:
            # Use original logic as fallback
            default_proof_owner_username = (
                database_username if database_username else requester_username
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
                "assetId": s3obj.key,
                "assetHash": s3obj.sha256_hash,
                "metadataHash": s3obj.sha256_hash,
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


class ProofResponse(BaseModel):
    metadata_digest: str


async def fetch_proof(
    asset_obj_key: str, get_proof_url: str, timeout_seconds: int = _TIMEOUT_SECS_LOW
) -> ProofResponse:
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        params = {"assetId": asset_obj_key}

        _logger.debug(
            "Calling %s with params:\n%s",
            get_proof_url,
            pprint.pformat(params),
        )

        resp = await client.get(get_proof_url, params=params)
        resp.raise_for_status()
        resp_dict = resp.json()

        return ProofResponse(metadata_digest=resp_dict["metadataDigest"])


class ProofVerificationResult(BaseModel):
    valid: bool
    reason: Optional[str] = None


async def fetch_verify_proof(
    session: AsyncSessionDep,
    asset_obj_key: str,
    get_proof_url: str,
    timeout_seconds: int = _TIMEOUT_SECS_LOW,
) -> ProofVerificationResult:
    stmt = select(UploadedS3Object).where(UploadedS3Object.key == asset_obj_key)
    result = await session.execute(stmt)
    s3obj = result.scalar_one_or_none()

    if not s3obj:
        return ProofVerificationResult(
            valid=False, reason=f"Asset object {asset_obj_key} not found"
        )

    if not s3obj.sha256_hash:
        return ProofVerificationResult(
            valid=False, reason=f"Asset object {asset_obj_key} has no hash"
        )

    try:
        proof_resp = await fetch_proof(
            asset_obj_key=asset_obj_key,
            get_proof_url=get_proof_url,
            timeout_seconds=timeout_seconds,
        )
    except Exception as ex:
        return ProofVerificationResult(
            valid=False,
            reason=f"Error fetching proof for {asset_obj_key}: {ex}",
        )

    expected_proof_digest = s3obj.sha256_hash

    if proof_resp.metadata_digest != expected_proof_digest:
        return ProofVerificationResult(
            valid=False,
            reason="Proof digest obtained from Trust API ({}) does not match expected ({})".format(
                proof_resp.metadata_digest, expected_proof_digest
            ),
        )

    return ProofVerificationResult(valid=True)
