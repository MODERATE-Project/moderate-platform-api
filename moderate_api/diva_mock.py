"""Mock DIVA client for demos and testing.

This module provides a mock implementation of the DivaClient that simulates
DIVA's validation behavior without requiring actual DIVA services.
"""

import logging
from datetime import datetime
import random
import time
from typing import ClassVar

from moderate_api.config import DivaSettings
from moderate_api.diva import (
    DivaClient,
    ValidationEntry,
    ValidationResult,
    ValidationStatus,
)

_logger = logging.getLogger(__name__)

# Mock column types for realistic validation results
MOCK_COLUMNS: list[tuple[str, str]] = [
    ("Index", "int"),
    ("Name", "string"),
    ("Value", "float"),
    ("Date", "datetime"),
    ("Category", "categorical"),
    ("Description", "string"),
    ("Status", "categorical"),
    ("Amount", "float"),
]

# Validation rules that DIVA typically applies
MOCK_RULES: list[str] = ["missing", "datatype"]


class MockValidationState:
    """State for a mock validation job."""

    def __init__(self, s3_url: str, total_rows: int):
        """Initialize mock validation state.

        Args:
            s3_url: S3 URL of the dataset
            total_rows: Total rows to simulate
        """
        self.s3_url = s3_url
        self.total_rows = total_rows
        self.processed_rows = 0
        self.started_at = time.time()
        self.columns = random.sample(MOCK_COLUMNS, k=min(5, len(MOCK_COLUMNS)))

    @property
    def progress(self) -> float:
        """Progress percentage (0-100)."""
        if self.total_rows == 0:
            return 100.0
        return (self.processed_rows / self.total_rows) * 100

    @property
    def is_complete(self) -> bool:
        """Whether validation is complete."""
        return self.processed_rows >= self.total_rows


class MockDivaClient(DivaClient):
    """Mock DIVA client for demos and testing.

    This client simulates DIVA's validation behavior:
    - Stores validation state in memory
    - Simulates progressive processing of rows
    - Generates realistic validation results with mostly passing rules
    """

    # Class-level storage for validation states (shared across instances)
    _validations: ClassVar[dict[str, MockValidationState]] = {}

    def __init__(self, settings: DivaSettings):
        """Initialize mock client.

        Args:
            settings: DIVA settings (used for supported extensions check)
        """
        super().__init__(settings)
        _logger.info("Using MockDivaClient for DIVA integration")

    async def publish_for_validation(
        self,
        s3_url: str,
        dataset_id: str,
    ) -> bool:
        """Simulate publishing dataset for validation.

        Creates a mock validation state that will be progressively updated
        when get_validation_results is called.

        Args:
            s3_url: S3 URL of the dataset
            dataset_id: Unique dataset identifier

        Returns:
            Always True for mock
        """
        total_rows = random.randint(100, 1000)

        self._validations[dataset_id] = MockValidationState(
            s3_url=s3_url,
            total_rows=total_rows,
        )

        _logger.info(
            "Mock: Published dataset for validation: dataset_id=%s, total_rows=%d",
            dataset_id,
            total_rows,
        )

        return True

    async def get_validation_results(
        self,
        dataset_id: str,
        expected_rows: int | None = None,
        start_time: datetime | None = None,
    ) -> ValidationResult:
        """Simulate fetching validation results.

        Each call advances the progress by a random amount to simulate
        DIVA's incremental processing.

        Args:
            dataset_id: Dataset identifier

        Args:
            dataset_id: Dataset identifier
            expected_rows: Expected total rows (ignored in mock, kept for parity)
            start_time: Timestamp when validation was requested

        Returns:
            ValidationResult with current status and entries
        """
        if dataset_id not in self._validations:
            _logger.debug(
                "Mock: No validation found for dataset_id=%s",
                dataset_id,
            )
            return ValidationResult(status=ValidationStatus.NOT_STARTED)

        state = self._validations[dataset_id]

        # Simulate progress (advance by 15-35% each call)
        if not state.is_complete:
            progress_increment = random.randint(15, 35)
            new_processed = min(
                state.processed_rows + int(state.total_rows * progress_increment / 100),
                state.total_rows,
            )
            state.processed_rows = new_processed

            _logger.debug(
                "Mock: Updated progress for dataset_id=%s: %d/%d rows (%.1f%%)",
                dataset_id,
                state.processed_rows,
                state.total_rows,
                state.progress,
            )

        # Generate entries based on current progress
        entries = self._generate_mock_entries(
            dataset_id=dataset_id,
            columns=state.columns,
            rows=state.processed_rows,
        )

        status = (
            ValidationStatus.COMPLETE
            if state.is_complete
            else ValidationStatus.IN_PROGRESS
        )

        result = ValidationResult.from_entries(
            entries,
            status=status,
            is_mock=True,
            last_requested_at=start_time,
            processed_rows=min(
                state.processed_rows,
                expected_rows if expected_rows is not None else state.processed_rows,
            ),
        )

        return result

    def _generate_mock_entries(
        self,
        dataset_id: str,
        columns: list[tuple[str, str]],
        rows: int,
    ) -> list[ValidationEntry]:
        """Generate mock validation entries.

        Generates entries for each column/rule combination with realistic
        pass rates:
        - 90% chance of 100% pass rate
        - 8% chance of 95-99% pass rate
        - 2% chance of 70-95% pass rate

        Args:
            dataset_id: Dataset identifier for validator field
            columns: List of (column_name, column_type) tuples
            rows: Number of rows to simulate

        Returns:
            List of ValidationEntry objects
        """
        entries = []

        for column_name, _ in columns:
            for rule in MOCK_RULES:
                # Determine pass rate with weighted random choice
                pass_rate_choice = random.choices(
                    [1.0, random.uniform(0.95, 0.99), random.uniform(0.70, 0.95)],
                    weights=[0.90, 0.08, 0.02],
                )[0]

                valid = int(rows * pass_rate_choice)
                fail = rows - valid

                entries.append(
                    ValidationEntry(
                        validator=dataset_id,
                        rule=rule,
                        feature=f"metricValue.{column_name}",
                        valid=valid,
                        fail=fail,
                    )
                )

        return entries

    @classmethod
    def reset_mock_state(cls) -> None:
        """Reset all mock validation states.

        Useful for testing to ensure clean state between tests.
        """
        cls._validations.clear()
        _logger.info("Mock: Reset all validation states")

    @classmethod
    def get_mock_state(cls, dataset_id: str) -> MockValidationState | None:
        """Get the mock state for a dataset (for testing).

        Args:
            dataset_id: Dataset identifier

        Returns:
            MockValidationState or None if not found
        """
        return cls._validations.get(dataset_id)
