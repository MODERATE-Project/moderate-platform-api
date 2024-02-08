import logging
from functools import lru_cache
from typing import List, Optional

from fastapi import Depends
from pydantic import BaseModel, BaseSettings
from typing_extensions import Annotated

_ENV_PREFIX = "MODERATE_API_"
_ENV_NESTED_DELIMITER = "__"

_logger = logging.getLogger(__name__)


class OAuthNamesModel(BaseModel):
    api_gw_client_id: str = "apisix"
    role_admin: str = "api_admin"
    role_basic_access: str = "api_basic_access"


class S3Model(BaseModel):
    access_key: str
    secret_key: str
    endpoint_url: str = "https://storage.googleapis.com"
    use_ssl: bool = True
    region: str
    bucket: str


class TrustService(BaseModel):
    endpoint_url: str  # Scheme, host and port without paths

    def build_url(self, *parts: List[str]) -> str:
        return self.endpoint_url.strip("/") + "/" + "/".join(parts)

    def url_create_did(self) -> str:
        return self.build_url("api", "dids")

    def url_create_proof(self) -> str:
        return self.build_url("api", "proofs")

    def url_get_proof(self) -> str:
        return self.url_create_proof()


class Settings(BaseSettings):
    class Config:
        env_prefix = _ENV_PREFIX
        env_nested_delimiter = _ENV_NESTED_DELIMITER

    s3: Optional[S3Model] = None
    oauth_names: OAuthNamesModel = OAuthNamesModel()
    openid_config_url: str = (
        "https://keycloak.moderate.cloud/realms/moderate/.well-known/openid-configuration"
    )
    disable_token_verification: bool = False
    verbose_errors: bool = False
    max_objects_per_asset: int = 100
    trust_service: Optional[TrustService] = None
    visualization_max_size_mib: float = 15.0
    visualization_expires_in_seconds: int = 1800

    postgres_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/moderateapi/"
    )

    @property
    def role_admin(self) -> str:
        return f"{self.oauth_names.api_gw_client_id}:{self.oauth_names.role_admin}"

    @property
    def role_basic_access(self) -> str:
        return (
            f"{self.oauth_names.api_gw_client_id}:{self.oauth_names.role_basic_access}"
        )


def get_settings():
    settings = Settings()
    _logger.debug("Settings:\n%s", settings.json(indent=2))
    return settings


SettingsDep = Annotated[Settings, Depends(get_settings)]
