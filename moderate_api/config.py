import logging
from functools import lru_cache

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


class Settings(BaseSettings):
    class Config:
        env_prefix = _ENV_PREFIX
        env_nested_delimiter = _ENV_NESTED_DELIMITER

    oauth_names: OAuthNamesModel = OAuthNamesModel()
    openid_config_url: str = "https://keycloak.moderate.cloud/realms/moderate/.well-known/openid-configuration"
    disable_token_verification: bool = False
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
