import logging

import boto3
import botocore.client
import botocore.exceptions
from fastapi import Depends
from typing_extensions import Annotated

from moderate_api.config import SettingsDep

_logger = logging.getLogger(__name__)


def get_s3_client(settings: SettingsDep) -> botocore.client.BaseClient:
    """Build and return an S3 client."""

    if settings.s3 is None:
        raise Exception("Undefined object storage (S3) settings")

    _logger.debug("Building S3 client")

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.s3.endpoint_url,
        region_name=settings.s3.region,
        aws_access_key_id=settings.s3.access_key,
        aws_secret_access_key=settings.s3.secret_key,
        use_ssl=settings.s3.use_ssl,
    )

    try:
        _logger.debug("Checking if S3 bucket exists: %s", settings.s3.bucket)
        s3.head_bucket(Bucket=settings.s3.bucket)
    except botocore.exceptions.ClientError as ex:
        _logger.debug("Error checking if S3 bucket exists: %s", ex)
        _logger.info("Creating S3 bucket: %s", settings.s3.bucket)
        s3.create_bucket(Bucket=settings.s3.bucket)

    return s3


S3ClientDep = Annotated[botocore.client.BaseClient, Depends(get_s3_client)]
