"""Availability checks for the applications listed on the UI home page."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
from fastapi import Depends

_CHECK_TIMEOUT_SECONDS = 5.0
_CHECK_TTL = timedelta(seconds=60)
_FIRST_ERROR_STATUS = 400

_logger = logging.getLogger(__name__)


class PlatformApplicationStatusChecker:
    """Probes live application URLs and caches each result per URL.

    Probes run inside the request that finds a stale entry, so there is no
    background task to manage. Keying the cache by URL means a changed URL
    is probed on the next request.
    """

    def __init__(self) -> None:
        self._cache: dict[str, tuple[bool, datetime]] = {}

    def _is_stale(self, url: str, now: datetime) -> bool:
        cached = self._cache.get(url)
        return cached is None or now - cached[1] > _CHECK_TTL

    async def _probe(self, client: httpx.AsyncClient, url: str) -> bool:
        try:
            response = await client.get(url)
        except httpx.HTTPError as ex:
            _logger.warning("Application at %s is unreachable: %r", url, ex)
            return False

        if response.status_code >= _FIRST_ERROR_STATUS:
            _logger.warning(
                "Application at %s returned HTTP %s", url, response.status_code
            )
            return False

        return True

    async def check(self, urls: list[str]) -> dict[str, bool]:
        """Return whether each URL is online, probing stale ones concurrently.

        Args:
            urls: Live deployment URLs.

        Returns:
            A mapping from each URL to True if it answered below HTTP 400
            after following redirects.
        """

        now = datetime.now(timezone.utc)
        stale = [url for url in set(urls) if self._is_stale(url, now)]

        if stale:
            async with httpx.AsyncClient(
                timeout=_CHECK_TIMEOUT_SECONDS, follow_redirects=True
            ) as client:
                results = await asyncio.gather(
                    *(self._probe(client, url) for url in stale)
                )

            for url, online in zip(stale, results, strict=False):
                self._cache[url] = (online, now)

        return {url: self._cache[url][0] for url in urls}


_status_checker = PlatformApplicationStatusChecker()


def get_status_checker() -> PlatformApplicationStatusChecker:
    """Return the process-wide checker, so cached results outlive requests."""

    return _status_checker


StatusCheckerDep = Annotated[
    PlatformApplicationStatusChecker, Depends(get_status_checker)
]
