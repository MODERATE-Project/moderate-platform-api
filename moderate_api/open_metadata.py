import logging
import pprint
import urllib.parse
from typing import Any, Dict, List, Union

import httpx
from pydantic import BaseModel, Field

from moderate_api.config import Settings, get_settings

_DEFAULT_TIMEOUT_SECS = 30

_logger = logging.getLogger(__name__)


class UndefinedOpenMetadataServiceError(Exception):
    pass


class AssetObjectSearchResponse(BaseModel):
    id: str
    name: str
    fqn: str
    updated_at: int


class OMSearchHitsTotal(BaseModel):
    value: int


class OMSearchHitsHitsSource(BaseModel):
    id: str
    name: str
    fullyQualifiedName: str
    updatedAt: int


class OMSearchHitsHit(BaseModel):
    source: OMSearchHitsHitsSource = Field(..., alias="_source")


class OMSearchHits(BaseModel):
    total: OMSearchHitsTotal
    hits: List[OMSearchHitsHit]


class OMSearch(BaseModel):
    hits: OMSearchHits


async def _search_asset_object(
    asset_object_key: str,
    endpoint_url: str,
    bearer_token: str,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECS,
) -> Union[AssetObjectSearchResponse, None]:
    q = asset_object_key.replace("/", r"\/").replace("-", r"\-")
    params = {"q": q}
    headers = {"Authorization": f"Bearer {bearer_token}"}

    _logger.debug(
        "GET %s with params:\n%s",
        endpoint_url,
        pprint.pformat(params),
    )

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        resp = await client.get(endpoint_url, params=params, headers=headers)
        _logger.debug("GET %s response: %s", endpoint_url, resp.text)

        try:
            resp.raise_for_status()
            resp_dict = resp.json()
        except Exception as exc:
            raise RuntimeError("{}".format(resp.text)) from exc

    _logger.debug("Search response (q=%s):\n%s", q, pprint.pformat(resp_dict))
    search_result = OMSearch(**resp_dict)
    _logger.debug("Parsed search response: %s", search_result)
    total_hits = search_result.hits.total.value

    if total_hits > 1:
        _logger.warning(
            "More than one OpenMetadata search hit for asset object key: %s",
            asset_object_key,
        )

    if total_hits == 0:
        _logger.info(
            "No OpenMetadata search hits for asset object key: %s", asset_object_key
        )

        return None

    result_hit = next(
        (
            item
            for item in search_result.hits.hits
            if item.source.name == asset_object_key
        ),
        None,
    )

    if result_hit is None:
        _logger.warning(
            "Got OpenMetadata search hits but none matched asset object key: %s",
            asset_object_key,
        )

        return None

    return AssetObjectSearchResponse(
        id=result_hit.source.id,
        name=result_hit.source.name,
        fqn=result_hit.source.fullyQualifiedName,
        updated_at=result_hit.source.updatedAt,
    )


async def search_asset_object(
    asset_object_key: str,
    settings: Settings = None,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECS,
) -> Union[AssetObjectSearchResponse, None]:
    settings = settings or get_settings()

    if (
        settings.open_metadata_service is None
        or not settings.open_metadata_service.endpoint_url
        or not settings.open_metadata_service.bearer_token
    ):
        raise UndefinedOpenMetadataServiceError()

    endpoint_url = settings.open_metadata_service.url_search_query()

    return await _search_asset_object(
        asset_object_key=asset_object_key,
        endpoint_url=endpoint_url,
        bearer_token=settings.open_metadata_service.bearer_token,
        timeout_seconds=timeout_seconds,
    )


class OMProfileColumn(BaseModel):
    name: str
    displayName: str
    dataType: str
    dataTypeDisplay: str
    fullyQualifiedName: str
    profile: Dict[str, Any]


class OMProfile(BaseModel):
    id: str
    name: str
    fullyQualifiedName: str
    updatedAt: int
    columns: List[OMProfileColumn]
    profile: Dict[str, Any]
    fileFormat: str


async def _get_asset_object_profile(
    endpoint_url: str,
    bearer_token: str,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECS,
) -> OMProfile:
    headers = {"Authorization": f"Bearer {bearer_token}"}
    _logger.debug("GET %s", endpoint_url)

    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        resp = await client.get(endpoint_url, headers=headers)
        _logger.debug("GET %s response: %s", endpoint_url, resp.text)

        try:
            resp.raise_for_status()
            resp_dict = resp.json()
        except Exception as exc:
            raise RuntimeError("{}".format(resp.text)) from exc

    return OMProfile(**resp_dict)


async def get_asset_object_profile(
    asset_object_fqn: str,
    settings: Settings = None,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECS,
) -> OMProfile:
    settings = settings or get_settings()

    if (
        settings.open_metadata_service is None
        or settings.open_metadata_service.endpoint_url is None
        or settings.open_metadata_service.bearer_token is None
    ):
        raise UndefinedOpenMetadataServiceError()

    fqn = urllib.parse.quote(asset_object_fqn, safe="")
    endpoint_url = settings.open_metadata_service.url_get_table_profile(fqn=fqn)

    return await _get_asset_object_profile(
        endpoint_url=endpoint_url,
        bearer_token=settings.open_metadata_service.bearer_token,
        timeout_seconds=timeout_seconds,
    )
