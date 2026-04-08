import asyncio
import csv
import io
import logging
import pprint
import re
import time
from collections import defaultdict
from functools import wraps
from typing import Any

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
    s3object_key_or_id: str | int,
    requester_username: str,
    user_did: str | None = None,
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
                "assetId": s3obj.key,
                "assetHash": s3obj.sha256_hash,
                "metadataHash": s3obj.sha256_hash,
                "did": user_did,
            }

            _logger.info(
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


@_handle_task_error
async def mint_nft_task(
    task_id: str,
    s3object_key_or_id: str | int,
    requester_username: str,
    license: str,
    mint_nft_url: str,
    timeout_seconds: int = _TIMEOUT_SECS_HIGH,
) -> None:
    """Background task to mint an NFT for an asset object via the trust service.

    Args:
        task_id: Long-running task identifier for status tracking.
        s3object_key_or_id: The S3 object key or database ID of the object to mint.
        requester_username: The username of the user requesting the mint.
        license: The license string to embed in the NFT (e.g. "CC-BY-4.0").
        mint_nft_url: The trust service endpoint URL for NFT minting (POST /api/nfts).
        timeout_seconds: HTTP request timeout in seconds.

    Raises:
        ValueError: If the object is not found, has no proof, or the owner has no DID.
    """
    async with with_session() as session:
        s3obj = await find_s3object_by_key_or_id(
            val=s3object_key_or_id, session=session
        )

        if not s3obj:
            raise ValueError(f"Asset object '{s3object_key_or_id}' not found")

        if not s3obj.proof_id:
            raise ValueError(
                f"Asset object '{s3object_key_or_id}' has no proof — "
                "a proof must exist before minting an NFT"
            )

        # Resolve the DID from the asset owner (platform compensates for the Trust
        # Service's unimplemented ownership check — the DID is never caller-supplied)
        owner_username = (
            s3obj.asset.username
            if s3obj.asset and s3obj.asset.username
            else requester_username
        )

        user_did = await get_did_for_username(username=owner_username, session=session)

        if not user_did:
            raise ValueError(
                f"User '{owner_username}' does not have a DID and cannot mint an NFT"
            )

        # Auto-derive nftAlias: prefer explicit object name, then parent asset name,
        # then fall back to the raw key. Sanitise to safe characters and truncate.
        raw_alias = (
            s3obj.name or (s3obj.asset.name if s3obj.asset else None) or s3obj.key
        )
        nft_alias = re.sub(r"[^a-zA-Z0-9 _\-]", "", raw_alias).strip()[:64] or "Asset"

        # Auto-derive nftSymbol: first 6 uppercase alphanumeric chars of asset name.
        # nftSymbol has no uniqueness or length constraint on the Trust Service side.
        raw_symbol = re.sub(
            r"[^a-zA-Z0-9]", "", s3obj.asset.name if s3obj.asset else ""
        ).upper()[:6]
        nft_symbol = raw_symbol or "ASSET"

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            json_payload = {
                "assetId": s3obj.key,
                "nftAlias": nft_alias,
                "nftSymbol": nft_symbol,
                "license": license,
                "did": user_did,
            }

            _logger.info(
                "Calling %s with payload:\n%s",
                mint_nft_url,
                pprint.pformat(json_payload),
            )

            resp = await client.post(mint_nft_url, json=json_payload)
            resp.raise_for_status()

        _logger.info("NFT minted successfully for object '%s'", s3object_key_or_id)

        await set_task_result(
            session=session,
            task_id=task_id,
            result={"status": "minted", "object_key": s3obj.key},
        )


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
    reason: str | None = None


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
            reason=f"Proof digest obtained from Trust API ({proof_resp.metadata_digest}) does not match expected ({expected_proof_digest})",
        )

    return ProofVerificationResult(valid=True)


class VerificationCountItem(BaseModel):
    """Verification count for a single asset object."""

    asset_id: str
    verification_count: int
    unique_dids: int
    cache_ttl_seconds: int


_CACHE_TTL_SECONDS = 3600
_CACHE_FETCH_TIMEOUT = 15

_cache_lock = asyncio.Lock()
_cache: dict[str, Any] = {
    "data": None,
    "timestamp": 0.0,
    "refreshing": False,
}


async def _do_fetch(log_url: str) -> None:
    async with httpx.AsyncClient(timeout=_CACHE_FETCH_TIMEOUT) as client:
        resp = await client.get(log_url)
        resp.raise_for_status()
        raw_text = resp.text

    counts: dict[str, int] = defaultdict(int)
    dids: dict[str, set] = defaultdict(set)

    reader = csv.reader(io.StringIO(raw_text))

    for row in reader:
        if len(row) < 2:
            continue
        did = row[0].strip()
        asset_id = row[1].strip()

        if not asset_id:
            continue

        counts[asset_id] += 1
        dids[asset_id].add(did)

    items = [
        VerificationCountItem(
            asset_id=asset_id,
            verification_count=counts[asset_id],
            unique_dids=len(dids[asset_id]),
            cache_ttl_seconds=_CACHE_TTL_SECONDS,
        )
        for asset_id in counts
    ]
    items.sort(key=lambda x: x.verification_count, reverse=True)

    _cache["data"] = items
    _cache["timestamp"] = time.monotonic()


async def _background_refresh(log_url: str) -> None:
    try:
        await _do_fetch(log_url)
    except Exception:
        _logger.warning("Failed to refresh verification metrics from %s", log_url)
    finally:
        async with _cache_lock:
            _cache["refreshing"] = False


async def fetch_verification_metrics(
    log_url: str,
) -> list[VerificationCountItem] | None:
    async with _cache_lock:
        data = _cache["data"]
        age = time.monotonic() - _cache["timestamp"]
        is_fresh = data is not None and age < _CACHE_TTL_SECONDS
        should_spawn = not is_fresh and not _cache["refreshing"]
        if should_spawn:
            _cache["refreshing"] = True

    if is_fresh:
        return data

    if should_spawn:
        asyncio.create_task(_background_refresh(log_url))

    return data


async def get_verification_count_for_key(
    object_key: str, log_url: str
) -> VerificationCountItem | None:
    items = await fetch_verification_metrics(log_url)

    if items is None:
        return None

    for item in items:
        if item.asset_id == object_key:
            return item

    return VerificationCountItem(
        asset_id=object_key,
        verification_count=0,
        unique_dids=0,
        cache_ttl_seconds=_CACHE_TTL_SECONDS,
    )


_DOWNLOAD_INTENT_COOLDOWN_SECS = 300

_download_intent_cooldown: dict[str, float] = {}


def should_record_download_intent(user_id: str | None, object_key: str) -> bool:
    """Check whether a download intent should be recorded for the given key.

    Applies a per-(user, object) cooldown to avoid flooding the trust
    service with repeated proof-read calls for the same download event.

    Args:
        user_id: The authenticated user's identifier, or None for
            anonymous requests.
        object_key: The S3 object key being downloaded.

    Returns:
        True if enough time has elapsed since the last recorded intent
        (or if no intent has been recorded yet); False otherwise.
    """
    key = f"{user_id or 'anon'}:{object_key}"
    now = time.monotonic()

    expired = [
        k
        for k, ts in _download_intent_cooldown.items()
        if now - ts > _DOWNLOAD_INTENT_COOLDOWN_SECS
    ]
    for k in expired:
        _download_intent_cooldown.pop(k, None)

    last_time = _download_intent_cooldown.get(key)

    if last_time is None or now - last_time > _DOWNLOAD_INTENT_COOLDOWN_SECS:
        _download_intent_cooldown[key] = now
        return True

    return False


async def record_download_intent(
    asset_objects: list,
    get_proof_url: str,
    user_id: str | None,
) -> None:
    """Fire-and-forget: trigger proof reads for objects that have a proof.

    Iterates over ``asset_objects``, and for each one that carries a
    ``proof_id`` attribute and whose cooldown has elapsed, schedules a
    ``fetch_proof`` call.  All calls are gathered concurrently; any
    exceptions are logged at WARNING level and never re-raised.

    Args:
        asset_objects: Iterable of asset object model instances.  Each
            must expose ``proof_id`` and ``key`` attributes.
        get_proof_url: The trust-service endpoint URL for retrieving a
            proof by asset ID.
        user_id: The authenticated user's identifier, or None for
            anonymous callers.
    """
    tasks = [
        fetch_proof(
            asset_obj_key=obj.key,
            get_proof_url=get_proof_url,
        )
        for obj in asset_objects
        if obj.proof_id and should_record_download_intent(user_id, obj.key)
    ]

    if not tasks:
        return

    results = await asyncio.gather(*tasks, return_exceptions=True)

    exceptions = [r for r in results if isinstance(r, Exception)]
    if exceptions:
        _logger.warning(
            "Failed to record download intent for some objects: %s",
            exceptions,
        )


class NftMetadata(BaseModel):
    """NFT metadata associated with an asset."""

    address: str | None = None
    asset_id: str | None = None
    owner_did: str | None = None
    license: str | None = None


async def fetch_nft_metadata(
    asset_id: str,
    get_nfts_url: str,
    timeout_seconds: int = _TIMEOUT_SECS_LOW,
) -> NftMetadata | None:
    """Fetch NFT metadata from the trust service for a given asset.

    Args:
        asset_id: The asset UUID to query NFTs for.
        get_nfts_url: The trust service endpoint URL for NFT retrieval.
        timeout_seconds: HTTP request timeout.

    Returns:
        The NFT metadata if found, or None if no NFT exists for this
        asset or the response is empty.
    """

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        params = {"assetId": asset_id}

        _logger.debug(
            "Calling %s with params:\n%s",
            get_nfts_url,
            pprint.pformat(params),
        )

        resp = await client.get(get_nfts_url, params=params)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            return None

        item = data[0] if isinstance(data, list) else data

        return NftMetadata(
            address=item.get("nftAddress"),
            asset_id=item.get("assetId"),
            owner_did=item.get("did"),
            license=item.get("license"),
        )
