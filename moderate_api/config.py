from functools import lru_cache

from fastapi import Depends
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated

_ENV_PREFIX = "MODERATE_API_"
_ENV_NESTED_DELIMITER = "__"


class OAuthNamesModel(BaseModel):
    role_admin: str = "moderate_api_admin"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix=_ENV_PREFIX, env_nested_delimiter=_ENV_NESTED_DELIMITER
    )

    oauth_names: OAuthNamesModel = OAuthNamesModel()
    openid_config_url: str = "https://keycloak.moderate.cloud/realms/moderate/.well-known/openid-configuration"
    disable_token_verification: bool = False


@lru_cache()
def get_settings():
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
