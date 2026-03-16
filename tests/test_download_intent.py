"""Unit tests for the download intent feature in moderate_api.trust.

Covers cooldown logic (should_record_download_intent) and the
record_download_intent coroutine, including proof-fetch gating,
exception swallowing, and per-(user, object) cooldown independence.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from moderate_api.trust import (
    _DOWNLOAD_INTENT_COOLDOWN_SECS,
    _download_intent_cooldown,
    record_download_intent,
    should_record_download_intent,
)

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obj(key: str, proof_id: str | None = "some-proof-id") -> MagicMock:
    """Return a minimal asset-object mock with ``key`` and ``proof_id``."""
    obj = MagicMock()
    obj.key = key
    obj.proof_id = proof_id
    return obj


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_cooldown() -> None:  # type: ignore[return]
    """Clear the global cooldown dict before (and after) every test.

    This ensures that tests are fully isolated from one another regardless
    of execution order.
    """
    _download_intent_cooldown.clear()
    yield
    _download_intent_cooldown.clear()


# ---------------------------------------------------------------------------
# Tests for should_record_download_intent
# ---------------------------------------------------------------------------


class TestShouldRecordDownloadIntent:
    """Tests for the cooldown gate function."""

    def test_first_call_returns_true(self) -> None:
        """First call for a user+object pair should return True."""
        result = should_record_download_intent("user-1", "obj/key-1")
        assert result is True

    def test_immediate_repeat_returns_false(self) -> None:
        """Second call within the cooldown window should return False."""
        should_record_download_intent("user-1", "obj/key-1")
        result = should_record_download_intent("user-1", "obj/key-1")
        assert result is False

    def test_after_cooldown_expires_returns_true(self) -> None:
        """Call after the cooldown period elapses should return True again."""
        # Record first intent at t=0
        with patch("moderate_api.trust.time.monotonic", return_value=0.0):
            should_record_download_intent("user-1", "obj/key-1")

        # Advance time past the cooldown window
        future_time = _DOWNLOAD_INTENT_COOLDOWN_SECS + 1.0
        with patch("moderate_api.trust.time.monotonic", return_value=future_time):
            result = should_record_download_intent("user-1", "obj/key-1")

        assert result is True

    def test_just_before_cooldown_expires_returns_false(self) -> None:
        """Call just inside the cooldown window should still return False."""
        with patch("moderate_api.trust.time.monotonic", return_value=0.0):
            should_record_download_intent("user-1", "obj/key-1")

        # One second before the cooldown expires
        almost_future = _DOWNLOAD_INTENT_COOLDOWN_SECS - 1.0
        with patch("moderate_api.trust.time.monotonic", return_value=almost_future):
            result = should_record_download_intent("user-1", "obj/key-1")

        assert result is False

    def test_none_user_id_uses_anon_key(self) -> None:
        """Anonymous users (user_id=None) should be tracked under 'anon'."""
        result = should_record_download_intent(None, "obj/key-anon")
        assert result is True

        # Same anonymous user, same object — must be throttled
        result = should_record_download_intent(None, "obj/key-anon")
        assert result is False

    def test_anon_and_named_user_are_independent(self) -> None:
        """Anonymous and named users must have separate cooldown entries."""
        should_record_download_intent(None, "obj/key-shared")
        # Named user for the same object is a distinct entry
        result = should_record_download_intent("user-A", "obj/key-shared")
        assert result is True

    def test_different_objects_are_independent(self) -> None:
        """Cooldown for one object must not affect a different object."""
        should_record_download_intent("user-1", "obj/key-A")
        # Different object should be unaffected
        result = should_record_download_intent("user-1", "obj/key-B")
        assert result is True

    def test_different_users_same_object_are_independent(self) -> None:
        """Cooldown for user-1 must not block user-2 on the same object."""
        should_record_download_intent("user-1", "obj/key-X")
        result = should_record_download_intent("user-2", "obj/key-X")
        assert result is True

    def test_expired_entries_are_evicted(self) -> None:
        """Expired entries must be removed from the cooldown dict."""
        # Seed an entry at t=0
        with patch("moderate_api.trust.time.monotonic", return_value=0.0):
            should_record_download_intent("user-evict", "obj/evict-key")

        assert len(_download_intent_cooldown) == 1

        # Advance past the cooldown; the stale entry should be evicted
        future_time = _DOWNLOAD_INTENT_COOLDOWN_SECS + 1.0
        with patch("moderate_api.trust.time.monotonic", return_value=future_time):
            should_record_download_intent("user-other", "obj/other-key")

        # The original expired entry must have been pruned
        expired_key = "user-evict:obj/evict-key"
        assert expired_key not in _download_intent_cooldown

    def test_updates_timestamp_on_true_return(self) -> None:
        """Timestamp in the dict must be refreshed when True is returned."""
        with patch("moderate_api.trust.time.monotonic", return_value=100.0):
            should_record_download_intent("user-ts", "obj/ts-key")

        entry_key = "user-ts:obj/ts-key"
        assert _download_intent_cooldown[entry_key] == pytest.approx(100.0)

        # After cooldown expires, re-record updates the timestamp
        new_time = 100.0 + _DOWNLOAD_INTENT_COOLDOWN_SECS + 1.0
        with patch("moderate_api.trust.time.monotonic", return_value=new_time):
            should_record_download_intent("user-ts", "obj/ts-key")

        assert _download_intent_cooldown[entry_key] == pytest.approx(new_time)


# ---------------------------------------------------------------------------
# Tests for record_download_intent
# ---------------------------------------------------------------------------


class TestRecordDownloadIntent:
    """Tests for the async fire-and-forget intent recorder."""

    @pytest.mark.asyncio
    async def test_calls_fetch_proof_for_objects_with_proof_id(self) -> None:
        """fetch_proof must be invoked for every object that has a proof_id."""
        objects = [
            _make_obj("key-1", proof_id="proof-aaa"),
            _make_obj("key-2", proof_id="proof-bbb"),
        ]

        mock_fetch = AsyncMock(return_value=MagicMock())

        with patch("moderate_api.trust.fetch_proof", mock_fetch):
            await record_download_intent(
                asset_objects=objects,
                get_proof_url="https://trust.example.com/proof",
                user_id="user-1",
            )

        assert mock_fetch.call_count == 2
        called_keys = {
            call.kwargs["asset_obj_key"] for call in mock_fetch.call_args_list
        }
        assert called_keys == {"key-1", "key-2"}

    @pytest.mark.asyncio
    async def test_skips_objects_without_proof_id(self) -> None:
        """Objects with a falsy proof_id must not trigger a fetch_proof call."""
        objects = [
            _make_obj("key-no-proof", proof_id=None),
            _make_obj("key-empty-proof", proof_id=""),
        ]

        mock_fetch = AsyncMock(return_value=MagicMock())

        with patch("moderate_api.trust.fetch_proof", mock_fetch):
            await record_download_intent(
                asset_objects=objects,
                get_proof_url="https://trust.example.com/proof",
                user_id="user-1",
            )

        mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_objects_only_fetches_for_proof_id_present(self) -> None:
        """Only objects that carry a truthy proof_id should be processed."""
        objects = [
            _make_obj("key-with-proof", proof_id="proof-xyz"),
            _make_obj("key-without-proof", proof_id=None),
        ]

        mock_fetch = AsyncMock(return_value=MagicMock())

        with patch("moderate_api.trust.fetch_proof", mock_fetch):
            await record_download_intent(
                asset_objects=objects,
                get_proof_url="https://trust.example.com/proof",
                user_id="user-1",
            )

        assert mock_fetch.call_count == 1
        mock_fetch.assert_called_once_with(
            asset_obj_key="key-with-proof",
            get_proof_url="https://trust.example.com/proof",
        )

    @pytest.mark.asyncio
    async def test_swallows_exceptions_from_fetch_proof(self) -> None:
        """Exceptions raised by fetch_proof must not propagate to the caller."""
        objects = [_make_obj("key-fail", proof_id="proof-fail")]

        mock_fetch = AsyncMock(side_effect=RuntimeError("Trust service unavailable"))

        with patch("moderate_api.trust.fetch_proof", mock_fetch):
            # Must not raise
            await record_download_intent(
                asset_objects=objects,
                get_proof_url="https://trust.example.com/proof",
                user_id="user-1",
            )

    @pytest.mark.asyncio
    async def test_swallows_exception_for_one_object_continues_others(
        self,
    ) -> None:
        """A failure for one object must not prevent fetches for other objects.

        asyncio.gather with return_exceptions=True collects all results;
        verify that fetch_proof is still called for every eligible object
        even when one raises.
        """
        objects = [
            _make_obj("key-ok", proof_id="proof-ok"),
            _make_obj("key-bad", proof_id="proof-bad"),
        ]

        async def _side_effect(asset_obj_key: str, **kwargs: object) -> object:
            if asset_obj_key == "key-bad":
                raise ValueError("Simulated trust-service error")
            return MagicMock()

        mock_fetch = AsyncMock(side_effect=_side_effect)

        with patch("moderate_api.trust.fetch_proof", mock_fetch):
            await record_download_intent(
                asset_objects=objects,
                get_proof_url="https://trust.example.com/proof",
                user_id="user-1",
            )

        assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_respects_cooldown_does_not_call_for_recent_user_object(
        self,
    ) -> None:
        """fetch_proof must not be called again within the cooldown window."""
        objects = [_make_obj("key-cd", proof_id="proof-cd")]

        mock_fetch = AsyncMock(return_value=MagicMock())

        with patch("moderate_api.trust.fetch_proof", mock_fetch):
            await record_download_intent(
                asset_objects=objects,
                get_proof_url="https://trust.example.com/proof",
                user_id="user-cd",
            )
            # Second call within the cooldown window
            await record_download_intent(
                asset_objects=objects,
                get_proof_url="https://trust.example.com/proof",
                user_id="user-cd",
            )

        # fetch_proof should only have been called once
        assert mock_fetch.call_count == 1

    @pytest.mark.asyncio
    async def test_calls_fetch_proof_after_cooldown_expires(self) -> None:
        """fetch_proof must be called again once the cooldown window has passed."""
        objects = [_make_obj("key-exp", proof_id="proof-exp")]

        mock_fetch = AsyncMock(return_value=MagicMock())

        with patch("moderate_api.trust.fetch_proof", mock_fetch):
            with patch("moderate_api.trust.time.monotonic", return_value=0.0):
                await record_download_intent(
                    asset_objects=objects,
                    get_proof_url="https://trust.example.com/proof",
                    user_id="user-exp",
                )

            future_time = _DOWNLOAD_INTENT_COOLDOWN_SECS + 1.0
            with patch("moderate_api.trust.time.monotonic", return_value=future_time):
                await record_download_intent(
                    asset_objects=objects,
                    get_proof_url="https://trust.example.com/proof",
                    user_id="user-exp",
                )

        assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_anonymous_user_respects_cooldown(self) -> None:
        """Cooldown must apply to anonymous callers (user_id=None) as well."""
        objects = [_make_obj("key-anon", proof_id="proof-anon")]

        mock_fetch = AsyncMock(return_value=MagicMock())

        with patch("moderate_api.trust.fetch_proof", mock_fetch):
            await record_download_intent(
                asset_objects=objects,
                get_proof_url="https://trust.example.com/proof",
                user_id=None,
            )
            await record_download_intent(
                asset_objects=objects,
                get_proof_url="https://trust.example.com/proof",
                user_id=None,
            )

        assert mock_fetch.call_count == 1

    @pytest.mark.asyncio
    async def test_empty_object_list_does_not_raise(self) -> None:
        """Passing an empty list must succeed without calling fetch_proof."""
        mock_fetch = AsyncMock(return_value=MagicMock())

        with patch("moderate_api.trust.fetch_proof", mock_fetch):
            await record_download_intent(
                asset_objects=[],
                get_proof_url="https://trust.example.com/proof",
                user_id="user-empty",
            )

        mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_passes_correct_get_proof_url(self) -> None:
        """The get_proof_url argument must be forwarded verbatim to fetch_proof."""
        expected_url = "https://trust.example.com/custom-path/proof"
        objects = [_make_obj("key-url", proof_id="proof-url")]

        mock_fetch = AsyncMock(return_value=MagicMock())

        with patch("moderate_api.trust.fetch_proof", mock_fetch):
            await record_download_intent(
                asset_objects=objects,
                get_proof_url=expected_url,
                user_id="user-url",
            )

        mock_fetch.assert_called_once_with(
            asset_obj_key="key-url",
            get_proof_url=expected_url,
        )
