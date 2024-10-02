import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from aiobotocore.client import AioBaseClient
from aiobotocore.session import get_session
from botocore.exceptions import ClientError
from fastapi import Depends
from typing_extensions import Annotated

from moderate_api.config import Settings, SettingsDep

_logger = logging.getLogger(__name__)


async def ensure_bucket(s3: AioBaseClient, bucket: str):
    try:
        _logger.debug("Checking if S3 bucket exists: %s", bucket)
        await s3.head_bucket(Bucket=bucket)
    except ClientError as ex:
        _logger.debug("Error checking if S3 bucket exists: %s", ex)
        _logger.info("Creating S3 bucket: %s", bucket)
        await s3.create_bucket(Bucket=bucket)


@asynccontextmanager
async def with_s3(settings: Settings) -> AsyncGenerator[AioBaseClient, None]:
    if settings.s3 is None:
        raise Exception("Undefined object storage (S3) settings")

    session = get_session()

    async with session.create_client(
        "s3",
        endpoint_url=settings.s3.endpoint_url,
        region_name=settings.s3.region,
        aws_access_key_id=settings.s3.access_key,
        aws_secret_access_key=settings.s3.secret_key,
        use_ssl=settings.s3.use_ssl,
    ) as s3:
        await ensure_bucket(s3=s3, bucket=settings.s3.bucket)
        yield s3


async def get_s3(settings: SettingsDep) -> AsyncGenerator[AioBaseClient, None]:
    async with with_s3(settings=settings) as s3:
        yield s3


S3ClientDep = Annotated[AioBaseClient, Depends(get_s3)]
