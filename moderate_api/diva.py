"""DIVA data quality validation client.

This module provides the client interface for integrating with the DIVA
(Data Integrity and Validation Architecture) platform for data quality validation.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, Field

from moderate_api.config import DivaSettings

_logger = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    """Status of a validation job."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class ValidationEntry(BaseModel):
    """A single validation result entry from DIVA Quality Reporter."""

    validator: str = Field(description="Dataset identifier used in validation")
    rule: str = Field(description="Validation rule type (missing, datatype, etc.)")
    feature: str = Field(description="Data field being validated")
    valid: int = Field(description="Count of valid values", ge=0)
    fail: int = Field(description="Count of failed values", ge=0)

    @property
    def total(self) -> int:
        """Total number of values checked."""
        return self.valid + self.fail

    @property
    def pass_rate(self) -> float:
        """Pass rate as percentage (0-100)."""
        if self.total == 0:
            return 0.0
        return (self.valid / self.total) * 100


class ValidationResult(BaseModel):
    """Complete validation result with status and entries."""

    status: ValidationStatus = Field(description="Current validation status")
    entries: list[ValidationEntry] = Field(
        default_factory=list, description="List of validation entries"
    )
    total_valid: int = Field(default=0, description="Sum of all valid counts", ge=0)
    total_fail: int = Field(default=0, description="Sum of all fail counts", ge=0)
    overall_pass_rate: float = Field(
        default=0.0, description="Overall pass rate percentage", ge=0, le=100
    )
    error_message: str | None = Field(
        default=None, description="Error message if validation failed"
    )
    processed_rows: int | None = Field(
        default=None, description="Number of rows processed so far"
    )
    is_mock: bool = Field(
        default=False, description="Whether these results are from a mock service"
    )
    last_requested_at: datetime | None = Field(
        default=None, description="Timestamp when validation was last requested"
    )

    @classmethod
    def from_entries(
        cls,
        entries: list[ValidationEntry],
        status: ValidationStatus = ValidationStatus.COMPLETE,
        is_mock: bool = False,
        last_requested_at: datetime | None = None,
        processed_rows: int | None = None,
    ) -> "ValidationResult":
        """Create ValidationResult from a list of entries."""
        total_valid = sum(e.valid for e in entries)
        total_fail = sum(e.fail for e in entries)
        total = total_valid + total_fail
        overall_pass_rate = (total_valid / total * 100) if total > 0 else 0.0

        return cls(
            status=status,
            entries=entries,
            total_valid=total_valid,
            total_fail=total_fail,
            overall_pass_rate=overall_pass_rate,
            is_mock=is_mock,
            last_requested_at=last_requested_at,
            processed_rows=processed_rows,
        )


class DivaClient:
    """Client for DIVA Kafka REST Gateway and Quality Reporter APIs.

    This client handles communication with two DIVA services:
    1. Kafka REST Gateway - for publishing datasets for validation
    2. Quality Reporter API - for fetching validation results

    Args:
        settings: DIVA configuration settings
    """

    # HTTP headers for Kafka REST API
    KAFKA_CONTENT_TYPE = "application/vnd.kafka.json.v2+json"
    KAFKA_ACCEPT = "application/vnd.kafka.v2+json"

    def __init__(self, settings: DivaSettings):
        """Initialize the DIVA client.

        Args:
            settings: DIVA configuration settings
        """
        self.settings = settings
        self._auth: tuple[str, str] | None = None

        if settings.basic_auth_user and settings.basic_auth_password:
            self._auth = (settings.basic_auth_user, settings.basic_auth_password)

    def generate_dataset_id(
        self, asset_id: int, object_id: int, unique_suffix: str | None = None
    ) -> str:
        """Generate a deterministic dataset ID for DIVA.

        Args:
            asset_id: Asset ID
            object_id: Asset object ID
            unique_suffix: Optional unique suffix (e.g. timestamp or UUID) to ensure uniqueness

        Returns:
            Deterministic dataset ID string
        """
        base_id = f"moderate-asset-{asset_id}-object-{object_id}"
        if unique_suffix:
            return f"{base_id}-{unique_suffix}"
        return base_id

    def is_supported_extension(self, filename: str) -> bool:
        """Check if file extension is supported for validation.

        Args:
            filename: Filename or path to check

        Returns:
            True if extension is supported
        """
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[-1].lower()
        return ext in self.settings.supported_extensions

    async def publish_for_validation(
        self,
        s3_url: str,
        dataset_id: str,
    ) -> bool:
        """Publish a dataset to Kafka for validation by DIVA.

        Args:
            s3_url: Presigned S3 URL for the dataset
            dataset_id: Unique identifier for this dataset

        Returns:
            True if publish was successful

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        url = self.settings.url_publish_topic()

        payload = {
            "records": [
                {
                    "value": {
                        "s3_url": s3_url,
                        "dataset_id": dataset_id,
                    }
                }
            ]
        }

        headers = {
            "Content-Type": self.KAFKA_CONTENT_TYPE,
            "Accept": self.KAFKA_ACCEPT,
        }

        _logger.info(
            "Publishing dataset to DIVA: dataset_id=%s, topic=%s",
            dataset_id,
            self.settings.ingestion_topic,
        )

        async with httpx.AsyncClient(timeout=self.settings.request_timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                auth=self._auth,  # type: ignore[arg-type]
            )
            response.raise_for_status()
            response_data: dict[str, Any] = response.json()

        offsets = response_data.get("offsets")
        if not isinstance(offsets, list) or not offsets:
            raise RuntimeError("Kafka publish response missing offsets")

        publish_errors = [
            item
            for item in offsets
            if isinstance(item, dict) and item.get("error") is not None
        ]
        if publish_errors:
            first_error = publish_errors[0]
            error_code = first_error.get("error", "unknown")
            error_message = first_error.get("message", "No details from Kafka REST")
            raise RuntimeError(
                f"Kafka publish failed with error {error_code}: {error_message}"
            )

        _logger.info(
            "Successfully published dataset to DIVA: dataset_id=%s, records=%d",
            dataset_id,
            len(offsets),
        )
        return True

    async def get_validation_results(
        self,
        dataset_id: str,
        expected_rows: int | None = None,
        start_time: datetime | None = None,
    ) -> ValidationResult:
        """Fetch validation results from DIVA Quality Reporter.

        Args:
            dataset_id: Dataset identifier to fetch results for
            expected_rows: Total number of rows expected (for progress calculation)
            start_time: Timestamp when validation was started (for timeout calculation)

        Returns:
            ValidationResult with current status and entries
        """
        url = self.settings.url_report(validator=dataset_id)

        _logger.debug(
            "Fetching validation results from DIVA: dataset_id=%s, url=%s",
            dataset_id,
            url,
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.settings.request_timeout
            ) as client:
                response = await client.get(url, auth=self._auth)
                response.raise_for_status()
                data: list[dict[str, Any]] = response.json()
        except httpx.HTTPStatusError as e:
            _logger.error(
                "Failed to fetch validation results: dataset_id=%s, error=%s",
                dataset_id,
                str(e),
            )
            return ValidationResult(
                status=ValidationStatus.FAILED,
                error_message=f"Failed to fetch results: {e.response.status_code}",
                last_requested_at=start_time,
            )
        except httpx.RequestError as e:
            _logger.error(
                "Request error fetching validation results: dataset_id=%s, error=%s",
                dataset_id,
                str(e),
            )
            return ValidationResult(
                status=ValidationStatus.FAILED,
                error_message=f"Request error: {str(e)}",
                last_requested_at=start_time,
            )
        except (ValueError, KeyError) as e:
            _logger.error(
                "Invalid response from Quality Reporter: dataset_id=%s, error=%s",
                dataset_id,
                str(e),
            )
            return ValidationResult(
                status=ValidationStatus.FAILED,
                error_message=f"Invalid response from Quality Reporter: {str(e)}",
                last_requested_at=start_time,
            )

        _logger.debug(
            "Received %d entries from Quality Reporter for dataset_id=%s",
            len(data),
            dataset_id,
        )

        # Filter entries for this dataset_id
        entries = []
        for item in data:
            if item.get("validator") == dataset_id:
                entries.append(
                    ValidationEntry(
                        validator=item.get("validator", ""),
                        rule=item.get("rule", ""),
                        feature=item.get("feature", ""),
                        valid=item.get("VALID", 0),
                        fail=item.get("FAIL", 0),
                    )
                )

        if not entries:
            if start_time:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > self.settings.completion_timeout_seconds:
                    # No rows were reported within timeout; treat as a failed run.
                    return ValidationResult(
                        status=ValidationStatus.FAILED,
                        error_message=(
                            "Validation timed out with no results. "
                            "The pipeline may not have processed this file."
                        ),
                        last_requested_at=start_time,
                    )
                # Validation was triggered but DIVA may not have consumed the
                # Kafka message yet — keep polling.
                return ValidationResult(
                    status=ValidationStatus.IN_PROGRESS, last_requested_at=start_time
                )
            return ValidationResult(
                status=ValidationStatus.NOT_STARTED, last_requested_at=start_time
            )

        # Determine completion status
        processed_rows = max((e.total for e in entries), default=0)
        is_complete = False

        if expected_rows and expected_rows > 0:
            pct = processed_rows / expected_rows
            if pct >= 1.0:
                is_complete = True
            elif start_time:
                # Declare complete after timeout regardless of row coverage.
                # NiFi may stop below full coverage due to failures/partial data.
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > self.settings.completion_timeout_seconds:
                    is_complete = True
        else:
            # Fallback logic if expected_rows is unknown
            if start_time:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > self.settings.completion_timeout_seconds:
                    is_complete = True
            else:
                # If we don't know expected rows or start time, assume complete
                # if we have data (legacy behavior)
                is_complete = True

        status = (
            ValidationStatus.COMPLETE if is_complete else ValidationStatus.IN_PROGRESS
        )

        return ValidationResult.from_entries(
            entries,
            status=status,
            processed_rows=processed_rows,
            last_requested_at=start_time,
        )
