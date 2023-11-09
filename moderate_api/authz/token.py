import logging
from typing import Dict

import httpx
import jwt
from asyncache import cached
from cachetools import TTLCache
from fastapi import Request
from jwt.algorithms import get_default_algorithms

from moderate_api.config import Settings

_CACHE_TTL_SECONDS = 60 * 60 * 24
_CACHE_MAXSIZE = 128

_logger = logging.getLogger(__name__)


async def _fetch_json(url: str) -> Dict:
    async with httpx.AsyncClient() as client:
        _logger.debug("GET JSON: %s", url)
        response = await client.get(url)
        return response.json()


@cached(cache=TTLCache(ttl=_CACHE_TTL_SECONDS, maxsize=_CACHE_MAXSIZE))
async def _fetch_jwks(openid_config_url: str) -> Dict:
    _logger.info("Fetching OpenID configuration from: %s", openid_config_url)
    openid_config = await _fetch_json(openid_config_url)
    jwks_uri = openid_config["jwks_uri"]
    return await _fetch_json(jwks_uri)


async def _get_signing_key(alg: str, jwks: Dict, kid: str):
    for key in jwks["keys"]:
        if key["kid"] == kid:
            jwk = {k: key[k] for k in ("kty", "kid", "use", "n", "e")}
            return get_default_algorithms()[alg].from_jwk(jwk)


async def get_request_token(request: Request, settings: Settings) -> Dict:
    auth_token = request.headers.get("Authorization")

    if not auth_token:
        raise ValueError("Missing Authorization header")

    auth_token = auth_token.replace("Bearer ", "")
    header = jwt.get_unverified_header(auth_token)
    alg = header["alg"]

    if settings.disable_token_verification:
        _logger.warning("Token verification is disabled")
        signing_key = None
        kid = None
        options = {"verify_signature": False}
    else:
        kid = header["kid"]
        jwks = await _fetch_jwks(settings.openid_config_url)
        signing_key = await _get_signing_key(alg, jwks, kid)
        options = {"verify_aud": False}

    _logger.debug("Decoding token with alg=%s, kid=%s, options=%s", alg, kid, options)

    token_decoded = jwt.decode(
        auth_token,
        algorithms=[alg],
        key=signing_key,
        options=options,
    )

    return token_decoded
