import pytest


@pytest.mark.asyncio
async def test_s3_client_dep(s3):
    assert s3
