import logging
import pprint

import pytest

_logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_s3_client_dep(s3):
    res_buckets = await s3.list_buckets()
    _logger.info("Buckets:\n%s", pprint.pformat(res_buckets))
    assert "Buckets" in res_buckets
