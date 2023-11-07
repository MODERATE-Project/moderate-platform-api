import logging
from dataclasses import dataclass
from typing import Annotated, Dict

import httpx
import jwt
from asyncache import cached
from cachetools import TTLCache
from fastapi import Depends, HTTPException, Request
from jwt.algorithms import get_default_algorithms

from moderate_api.config import Settings, SettingsDep

_REALM_ACCESS = "realm_access"
_ROLES = "roles"
_CACHE_TTL_SECONDS = 60 * 60 * 24
_CACHE_MAXSIZE = 128

_logger = logging.getLogger(__name__)


@dataclass
class User:
    token_decoded: Dict
    _settings: Settings = None

    def has_role(self, role: str) -> bool:
        try:
            return role in self.token_decoded[_REALM_ACCESS][_ROLES]
        except Exception:
            _logger.warning("Error checking role", exc_info=True)
            return False

    @property
    def settings(self) -> Settings:
        return self._settings if self._settings else Settings()

    @property
    def is_admin(self) -> bool:
        return self.has_role(self.settings.oauth_names.role_admin)

    def to_dict(self) -> Dict:
        return {"token": self.token_decoded, "is_admin": self.is_admin}


async def _fetch_json(url: str) -> Dict:
    async with httpx.AsyncClient() as client:
        _logger.debug("GET JSON from: %s", url)
        response = await client.get(url)
        return response.json()


@cached(cache=TTLCache(ttl=_CACHE_TTL_SECONDS, maxsize=_CACHE_MAXSIZE))
async def _fetch_jwks(openid_config_url: str) -> Dict:
    _logger.debug("Fetching JWKS from: %s", openid_config_url)
    openid_config = await _fetch_json(openid_config_url)
    jwks_uri = openid_config["jwks_uri"]
    return await _fetch_json(jwks_uri)


async def _get_signing_key(alg: str, jwks: Dict, kid: str):
    for key in jwks["keys"]:
        if key["kid"] == kid:
            jwk = {k: key[k] for k in ("kty", "kid", "use", "n", "e")}
            return get_default_algorithms()[alg].from_jwk(jwk)


async def get_user(request: Request, settings: SettingsDep) -> User:
    """Get the user from the request."""

    try:
        auth_token = request.headers.get("Authorization")
        auth_token = auth_token.replace("Bearer ", "")
        header = jwt.get_unverified_header(auth_token)
        alg = header["alg"]
        kid = header["kid"]
        jwks = await _fetch_jwks(settings.openid_config_url)
        signing_key = await _get_signing_key(alg, jwks, kid)

        token_decoded = jwt.decode(
            auth_token, algorithms=[alg], key=signing_key, options={"verify_aud": False}
        )

        return User(token_decoded=token_decoded, _settings=settings)
    except Exception as ex:
        raise HTTPException(status_code=401, detail=str(ex)) from ex


UserDep = Annotated[User, Depends(get_user)]
