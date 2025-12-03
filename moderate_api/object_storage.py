import hashlib
import logging
from contextlib import asynccontextmanager
from io import BytesIO
from typing import Any, AsyncGenerator, Dict

from aiobotocore.client import AioBaseClient
from aiobotocore.session import get_session
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import Depends, UploadFile
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


async def upload_file_multipart(
    s3: AioBaseClient,
    bucket: str,
    key: str,
    file_obj: UploadFile,
    chunk_size: int = 16 * 1024**2,
) -> Dict[str, Any]:
    """Uploads a file to S3 using multipart upload and calculates SHA256 hash."""

    _logger.debug("Creating multipart upload (object=%s)", key)
    multipart_upload = await s3.create_multipart_upload(Bucket=bucket, Key=key)  # type: ignore

    parts = []
    part_number = 1
    hash_object = hashlib.sha256()

    try:
        while True:
            chunk = await file_obj.read(chunk_size)

            if not chunk:
                break

            hash_object.update(chunk)

            part = await s3.upload_part(  # type: ignore
                Bucket=bucket,
                Key=key,
                PartNumber=part_number,
                UploadId=multipart_upload["UploadId"],
                Body=BytesIO(chunk),
            )

            parts.append({"PartNumber": part_number, "ETag": part["ETag"]})
            part_number += 1

        _logger.debug(
            "Completing multipart upload (object=%s) (chunks=%s)", key, len(parts)
        )

        result_s3_upload = await s3.complete_multipart_upload(  # type: ignore
            Bucket=bucket,
            Key=key,
            UploadId=multipart_upload["UploadId"],
            MultipartUpload={"Parts": parts},
        )

        sha256_hash = hash_object.hexdigest()
        _logger.debug("SHA256 hash of object: %s", sha256_hash)

        return {
            "Bucket": result_s3_upload["Bucket"],
            "Key": result_s3_upload["Key"],
            "ETag": result_s3_upload["ETag"],
            "Location": result_s3_upload["Location"],
            "SHA256": sha256_hash,
        }

    except Exception as e:
        _logger.error("Error during multipart upload, aborting: %s", e)
        await s3.abort_multipart_upload(
            Bucket=bucket, Key=key, UploadId=multipart_upload["UploadId"]
        )
        raise e


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
        # https://github.com/boto/boto3/issues/4400#issuecomment-2600742103
        config=Config(request_checksum_calculation="when_required", response_checksum_validation="when_required")
    ) as s3:
        await ensure_bucket(s3=s3, bucket=settings.s3.bucket)
        yield s3


async def get_s3(settings: SettingsDep) -> AsyncGenerator[AioBaseClient, None]:
    async with with_s3(settings=settings) as s3:
        yield s3


S3ClientDep = Annotated[AioBaseClient, Depends(get_s3)]
