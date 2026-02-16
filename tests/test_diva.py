"""Tests for DIVA data quality validation integration."""

import logging
import pprint
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from moderate_api.config import DivaSettings
from moderate_api.diva import (
    DivaClient,
    ValidationEntry,
    ValidationResult,
    ValidationStatus,
)
from moderate_api.diva_mock import MockDivaClient
from moderate_api.main import app
from tests.utils import create_asset, upload_test_files

_logger = logging.getLogger(__name__)


class TestValidationModels:
    """Test validation data models."""

    def test_validation_entry_computed_fields(self) -> None:
        """Test that ValidationEntry computes total and pass_rate correctly."""
        entry = ValidationEntry(
            validator="test",
            rule="missing",
            feature="col1",
            valid=90,
            fail=10,
        )

        assert entry.total == 100
        assert entry.pass_rate == 90.0

    def test_validation_entry_zero_total(self) -> None:
        """Test that ValidationEntry handles zero total gracefully."""
        entry = ValidationEntry(
            validator="test",
            rule="missing",
            feature="col1",
            valid=0,
            fail=0,
        )

        assert entry.total == 0
        assert entry.pass_rate == 0.0

    def test_validation_result_defaults(self) -> None:
        """Test ValidationResult default values."""
        result = ValidationResult(status=ValidationStatus.NOT_STARTED)

        assert result.entries == []
        assert result.total_valid == 0
        assert result.total_fail == 0
        assert result.overall_pass_rate == 0.0
        assert result.error_message is None
        assert result.processed_rows is None


class TestDivaClient:
    """Test DIVA client functionality."""

    def test_generate_dataset_id(self) -> None:
        """Test dataset ID generation."""
        settings = DivaSettings()
        client = DivaClient(settings)

        dataset_id = client.generate_dataset_id(123, 456)
        assert dataset_id == "moderate-asset-123-object-456"

    def test_generate_dataset_id_with_unique_suffix(self) -> None:
        """Test dataset ID generation with unique suffixes."""
        settings = DivaSettings()
        client = DivaClient(settings)

        dataset_id_1 = client.generate_dataset_id(123, 456, unique_suffix="first")
        dataset_id_2 = client.generate_dataset_id(123, 456, unique_suffix="second")

        assert dataset_id_1 != dataset_id_2
        assert dataset_id_1.startswith("moderate-asset-123-object-456-")
        assert dataset_id_2.startswith("moderate-asset-123-object-456-")

    def test_is_supported_extension(self) -> None:
        """Test file extension support checking."""
        settings = DivaSettings(supported_extensions=["csv", "json", "parquet"])
        client = DivaClient(settings)

        assert client.is_supported_extension("data.csv") is True
        assert client.is_supported_extension("data.CSV") is True
        assert client.is_supported_extension("data.json") is True
        assert client.is_supported_extension("data.parquet") is True
        assert client.is_supported_extension("data.xlsx") is False
        assert client.is_supported_extension("data.txt") is False
        assert client.is_supported_extension("noextension") is False

    def test_url_report_with_validator(self) -> None:
        """Test that url_report includes validator query param."""
        settings = DivaSettings(quality_reporter_url="https://reporter.example.com")
        url = settings.url_report(validator="my-dataset-123")
        assert url == (
            "https://reporter.example.com/report" "?validator=my-dataset-123"
        )

    def test_url_report_without_validator(self) -> None:
        """Test that url_report has no query param when None."""
        settings = DivaSettings(quality_reporter_url="https://reporter.example.com")
        url = settings.url_report()
        assert url == "https://reporter.example.com/report"
        assert "?" not in url

    def test_url_report_validator_special_chars(self) -> None:
        """Test that url_report properly encodes special characters."""
        settings = DivaSettings(quality_reporter_url="https://reporter.example.com")
        url = settings.url_report(validator="asset 1&object=2")
        assert "validator=asset+1%26object%3D2" in url

    @pytest.mark.asyncio
    async def test_get_validation_results_invalid_json(self) -> None:
        """Test that invalid JSON from Quality Reporter returns FAILED."""
        settings = DivaSettings(quality_reporter_url="https://reporter.example.com")
        client = DivaClient(settings)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "moderate_api.diva.httpx.AsyncClient", return_value=mock_http_client
        ):
            result = await client.get_validation_results("test-dataset")

        assert result.status == ValidationStatus.FAILED
        assert "Invalid response from Quality Reporter" in result.error_message

    @pytest.mark.asyncio
    async def test_get_validation_results_passes_validator_param(self) -> None:
        """Test that get_validation_results passes dataset_id to url_report."""
        settings = DivaSettings(quality_reporter_url="https://reporter.example.com")
        client = DivaClient(settings)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = []

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "moderate_api.diva.httpx.AsyncClient", return_value=mock_http_client
        ):
            await client.get_validation_results("my-dataset-42")

        called_url = mock_http_client.get.call_args[0][0]
        assert "validator=my-dataset-42" in called_url

    @pytest.mark.asyncio
    async def test_publish_for_validation_fails_when_offsets_missing(self) -> None:
        """Test publish failure when Kafka response does not include offsets."""
        settings = DivaSettings(kafka_rest_url="https://kafka.example.com")
        client = DivaClient(settings)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"status": "ok"}

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "moderate_api.diva.httpx.AsyncClient", return_value=mock_http_client
        ):
            with pytest.raises(RuntimeError, match="missing offsets"):
                await client.publish_for_validation(
                    s3_url="https://example.com/test.csv",
                    dataset_id="test-dataset",
                )

    @pytest.mark.asyncio
    async def test_publish_for_validation_fails_when_kafka_reports_error(self) -> None:
        """Test publish failure when Kafka response has per-record errors."""
        settings = DivaSettings(kafka_rest_url="https://kafka.example.com")
        client = DivaClient(settings)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "offsets": [
                {
                    "partition": 0,
                    "offset": 123,
                    "error": 1,
                    "message": "Invalid record",
                }
            ]
        }

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "moderate_api.diva.httpx.AsyncClient", return_value=mock_http_client
        ):
            with pytest.raises(RuntimeError, match="Kafka publish failed"):
                await client.publish_for_validation(
                    s3_url="https://example.com/test.csv",
                    dataset_id="test-dataset",
                )


class TestMockDivaClient:
    """Test mock DIVA client implementation."""

    @pytest.mark.asyncio
    async def test_mock_client_not_started(self) -> None:
        """Test that mock client returns not_started for unknown datasets."""
        settings = DivaSettings()
        client = MockDivaClient(settings)

        result = await client.get_validation_results("unknown-dataset")

        assert result.status == ValidationStatus.NOT_STARTED

    @pytest.mark.asyncio
    async def test_mock_client_publish_starts_validation(self) -> None:
        """Test that publishing starts validation."""
        settings = DivaSettings()
        client = MockDivaClient(settings)
        dataset_id = "test-dataset-123"

        success = await client.publish_for_validation(
            s3_url="https://example.com/test.csv",
            dataset_id=dataset_id,
        )

        assert success is True
        assert dataset_id in MockDivaClient._validations

    @pytest.mark.asyncio
    async def test_mock_client_validation_progress(self) -> None:
        """Test that mock validation progresses over multiple calls."""
        settings = DivaSettings()
        client = MockDivaClient(settings)
        dataset_id = "test-dataset-progress"

        # Start validation
        await client.publish_for_validation(
            s3_url="https://example.com/test.csv",
            dataset_id=dataset_id,
        )

        # First call should show in_progress
        result1 = await client.get_validation_results(dataset_id)
        assert result1.status == ValidationStatus.IN_PROGRESS

        # Keep calling until complete
        max_iterations = 20
        for _ in range(max_iterations):
            result = await client.get_validation_results(dataset_id)
            if result.status == ValidationStatus.COMPLETE:
                break
        else:
            pytest.fail("Validation did not complete within expected iterations")

        # Verify complete result has entries
        assert result.status == ValidationStatus.COMPLETE
        assert len(result.entries) > 0
        assert result.total_valid > 0
        assert result.overall_pass_rate > 0

    @pytest.mark.asyncio
    async def test_mock_client_entries_structure(self) -> None:
        """Test that mock validation entries have correct structure."""
        settings = DivaSettings()
        client = MockDivaClient(settings)
        dataset_id = "test-dataset-structure"

        # Start and complete validation
        await client.publish_for_validation(
            s3_url="https://example.com/test.csv",
            dataset_id=dataset_id,
        )

        # Progress until complete
        result = None
        for _ in range(20):
            result = await client.get_validation_results(dataset_id)
            if result.status == ValidationStatus.COMPLETE:
                break

        assert result is not None
        assert result.status == ValidationStatus.COMPLETE

        # Check entry structure
        for entry in result.entries:
            assert entry.validator == dataset_id
            assert entry.rule in ["missing", "datatype", "range", "format"]
            assert entry.feature.startswith("metricValue.")
            assert entry.valid >= 0
            assert entry.fail >= 0
            assert entry.total == entry.valid + entry.fail


class TestValidationEndpoints:
    """Test validation API endpoints."""

    @pytest.fixture(autouse=True)
    def reset_mock_state(self) -> None:
        """Reset mock state before each test."""
        MockDivaClient.reset_mock_state()

    @pytest.mark.asyncio
    async def test_get_supported_extensions(
        self, access_token: str  # type: ignore[no-untyped-def]
    ) -> None:
        """Test endpoint to get supported file extensions."""
        with TestClient(app) as client:
            response = client.get(
                "/asset/validation/supported-extensions",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert response.status_code == 200
            extensions = response.json()
            _logger.debug("Supported extensions: %s", extensions)

            assert isinstance(extensions, list)
            assert len(extensions) > 0
            assert "csv" in extensions

    @pytest.mark.asyncio
    async def test_start_validation(
        self, access_token: str  # type: ignore[no-untyped-def]
    ) -> None:
        """Test starting validation for an asset object."""
        asset_id = upload_test_files(access_token, num_files=1)

        with TestClient(app) as client:
            # Get asset to find object ID
            asset_response = client.get(
                f"/asset/{asset_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert asset_response.status_code == 200
            asset_data = asset_response.json()
            object_id = asset_data["objects"][0]["id"]
            _logger.debug("Asset data:\n%s", pprint.pformat(asset_data))

            # Start validation
            response = client.post(
                f"/asset/{asset_id}/object/{object_id}/validate",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            _logger.debug("Start validation response:\n%s", response.json())
            assert response.status_code == 200
            data = response.json()
            assert "dataset_id" in data
            assert f"asset-{asset_id}-object-{object_id}" in data["dataset_id"]

    @pytest.mark.asyncio
    async def test_start_validation_returns_503_when_publish_fails(
        self, access_token: str  # type: ignore[no-untyped-def]
    ) -> None:
        """Test starting validation fails when DIVA publish fails."""
        asset_id = upload_test_files(access_token, num_files=1)

        with TestClient(app) as client:
            asset_response = client.get(
                f"/asset/{asset_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert asset_response.status_code == 200
            asset_data = asset_response.json()
            object_id = asset_data["objects"][0]["id"]

            with patch(
                "moderate_api.diva_mock.MockDivaClient.publish_for_validation",
                new=AsyncMock(side_effect=RuntimeError("Kafka publish failed")),
            ):
                response = client.post(
                    f"/asset/{asset_id}/object/{object_id}/validate",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

            assert response.status_code == 503
            detail = response.json().get("detail", "")
            assert "Failed to start validation" in detail

    @pytest.mark.asyncio
    async def test_get_validation_status_not_started(
        self, access_token: str  # type: ignore[no-untyped-def]
    ) -> None:
        """Test getting validation status before validation started."""
        asset_id = upload_test_files(access_token, num_files=1)

        with TestClient(app) as client:
            # Get asset to find object ID
            asset_response = client.get(
                f"/asset/{asset_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert asset_response.status_code == 200
            asset_data = asset_response.json()
            object_id = asset_data["objects"][0]["id"]

            # Get status without starting validation
            response = client.get(
                f"/asset/{asset_id}/object/{object_id}/validation-status",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            _logger.debug("Validation status response:\n%s", response.json())
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_started"

    @pytest.mark.asyncio
    async def test_validation_flow(
        self, access_token: str  # type: ignore[no-untyped-def]
    ) -> None:
        """Test full validation flow: start -> poll -> complete."""
        asset_id = upload_test_files(access_token, num_files=1)

        with TestClient(app) as client:
            # Get asset to find object ID
            asset_response = client.get(
                f"/asset/{asset_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert asset_response.status_code == 200
            asset_data = asset_response.json()
            object_id = asset_data["objects"][0]["id"]

            # Start validation
            start_response = client.post(
                f"/asset/{asset_id}/object/{object_id}/validate",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert start_response.status_code == 200

            # Poll until complete
            max_polls = 25
            final_status = None

            for i in range(max_polls):
                status_response = client.get(
                    f"/asset/{asset_id}/object/{object_id}/validation-status",
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                assert status_response.status_code == 200
                final_status = status_response.json()
                _logger.debug("Poll %d status: %s", i, final_status["status"])

                if final_status["status"] == "complete":
                    break
            else:
                pytest.fail("Validation did not complete within expected polls")

            # Verify complete result
            assert final_status is not None
            assert final_status["status"] == "complete"
            assert len(final_status["entries"]) > 0
            assert final_status["total_valid"] > 0
            assert final_status["overall_pass_rate"] > 0

    @pytest.mark.asyncio
    async def test_validation_unsupported_extension(
        self, access_token: str  # type: ignore[no-untyped-def]
    ) -> None:
        """Test that unsupported file types return unsupported status."""
        # Create asset with a non-CSV file
        with TestClient(app) as client:
            # Create an asset
            asset = create_asset(client, access_token)
            asset_id = asset["id"]

            # Upload a file with unsupported extension
            import tempfile

            with tempfile.NamedTemporaryFile(
                suffix=".xlsx", delete=False, mode="wb"
            ) as f:
                f.write(b"dummy content")
                temp_path = f.name

            try:
                with open(temp_path, "rb") as fh:
                    response = client.post(
                        f"/asset/{asset_id}/object",
                        headers={"Authorization": f"Bearer {access_token}"},
                        files={"obj": ("test.xlsx", fh)},
                    )

                    assert response.status_code == 200
                    upload_data = response.json()
                    object_id = upload_data["id"]
            finally:
                import os

                os.unlink(temp_path)

            # Try to start validation for unsupported file
            start_response = client.post(
                f"/asset/{asset_id}/object/{object_id}/validate",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            # Should return unsupported status (400 Bad Request)
            _logger.debug("Unsupported validation response:\n%s", start_response.json())
            assert start_response.status_code == 400
            data = start_response.json()
            assert "detail" in data
            assert "File extension not supported" in data["detail"]

    @pytest.mark.asyncio
    async def test_public_validation_status_endpoint(
        self, access_token: str  # type: ignore[no-untyped-def]
    ) -> None:
        """Test public validation status endpoint."""
        asset_id = upload_test_files(access_token, num_files=1)

        with TestClient(app) as client:
            # Get asset to find object ID
            asset_response = client.get(
                f"/asset/{asset_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert asset_response.status_code == 200
            asset_data = asset_response.json()
            object_id = asset_data["objects"][0]["id"]

            # Start validation first
            start_response = client.post(
                f"/asset/{asset_id}/object/{object_id}/validate",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert start_response.status_code == 200

            # Make asset public so it can be accessed via public endpoint
            update_response = client.patch(
                f"/asset/{asset_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"access_level": "public"},
            )
            assert update_response.status_code == 200

            # Get public status (no auth header)
            public_response = client.get(
                f"/asset/public/{asset_id}/object/{object_id}/validation-status",
            )

            _logger.debug("Public validation status:\n%s", public_response.json())
            assert public_response.status_code == 200
            data = public_response.json()
            assert "status" in data
