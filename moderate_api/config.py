import logging
from typing import Annotated
from urllib.parse import urlencode

from fastapi import Depends
from pydantic import BaseModel, BaseSettings

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

    def build_url(self, *parts: str) -> str:
        return self.endpoint_url.strip("/") + "/" + "/".join(parts)

    def url_create_did(self) -> str:
        return self.build_url("api", "dids")

    def url_create_proof(self) -> str:
        return self.build_url("api", "proofs")

    def url_get_proof(self) -> str:
        return self.url_create_proof()


class OpenMetadataService(BaseModel):
    endpoint_url: str  # Scheme, host and port without paths
    bearer_token: str

    def build_url(self, *parts: str) -> str:
        return self.endpoint_url.strip("/") + "/" + "/".join(parts)

    def url_search_query(self) -> str:
        return self.build_url("api", "v1", "search", "query")

    def url_get_table_profile(self, fqn: str) -> str:
        return self.build_url("api", "v1", "tables", fqn, "tableProfile", "latest")


class DivaSettings(BaseModel):
    """Settings for DIVA data quality validation integration."""

    enabled: bool = False
    kafka_rest_url: str | None = None
    quality_reporter_url: str | None = None
    basic_auth_user: str | None = None
    basic_auth_password: str | None = None
    ingestion_topic: str = "data-ingestion-trigger"
    supported_extensions: list[str] = ["csv"]
    request_timeout: int = 30
    presigned_url_ttl: int = 3600  # 1 hour default
    completion_threshold: float = 0.90  # 90%
    completion_timeout_seconds: int = 300  # 5 minutes

    def build_kafka_url(self, *parts: str) -> str:
        """Build URL for Kafka REST Gateway."""
        if not self.kafka_rest_url:
            raise ValueError("kafka_rest_url is not configured")
        return self.kafka_rest_url.strip("/") + "/" + "/".join(parts)

    def build_reporter_url(self, *parts: str) -> str:
        """Build URL for Quality Reporter API."""
        if not self.quality_reporter_url:
            raise ValueError("quality_reporter_url is not configured")
        return self.quality_reporter_url.strip("/") + "/" + "/".join(parts)

    def url_publish_topic(self) -> str:
        """URL for publishing to Kafka ingestion topic."""
        return self.build_kafka_url("topics", self.ingestion_topic)

    def url_report(self, validator: str | None = None) -> str:
        """URL for fetching validation report.

        Args:
            validator: Optional validator ID to filter results server-side.

        Returns:
            Report URL, optionally with validator query parameter.
        """
        base_url = self.build_reporter_url("report")
        if validator is not None:
            return f"{base_url}?{urlencode({'validator': validator})}"
        return base_url


class Settings(BaseSettings):
    class Config:
        env_prefix = _ENV_PREFIX
        env_nested_delimiter = _ENV_NESTED_DELIMITER

    s3: S3Model | None = None
    oauth_names: OAuthNamesModel = OAuthNamesModel()

    openid_config_url: str = (
        "https://keycloak.moderate.cloud/realms/moderate/.well-known/openid-configuration"
    )

    disable_token_verification: bool = False
    verbose_errors: bool = False
    max_objects_per_asset: int = 100
    trust_service: TrustService | None = None
    visualization_max_size_mib: float = 10.0
    visualization_expires_in_seconds: int = 1800
    response_total_count_header = "X-Total-Count"

    postgres_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/moderateapi/"
    )

    open_metadata_service: OpenMetadataService | None = None
    rabbit_router_url: str | None = None
    diva: DivaSettings = DivaSettings()

    @property
    def role_admin(self) -> str:
        return f"{self.oauth_names.api_gw_client_id}:{self.oauth_names.role_admin}"

    @property
    def role_basic_access(self) -> str:
        return (
            f"{self.oauth_names.api_gw_client_id}:{self.oauth_names.role_basic_access}"
        )


def get_settings() -> Settings:
    settings = Settings()
    return settings


SettingsDep = Annotated[Settings, Depends(get_settings)]
