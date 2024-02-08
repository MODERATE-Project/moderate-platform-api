import logging
import os

import pandas as pd
import pygwalker as pyg
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlmodel import or_, select

from moderate_api.authz import UserDep
from moderate_api.config import SettingsDep
from moderate_api.db import AsyncSessionDep
from moderate_api.entities.asset.models import (
    Asset,
    AssetAccessLevels,
    UploadedS3Object,
    get_s3object_size_mib,
)
from moderate_api.object_storage import S3ClientDep

_logger = logging.getLogger(__name__)

_TAG = "Visualization"

router = APIRouter()


@router.get("/object/{object_id}", tags=[_TAG], response_class=HTMLResponse)
async def run_pygwalker_on_asset_object(
    *,
    user: UserDep,
    session: AsyncSessionDep,
    settings: SettingsDep,
    s3: S3ClientDep,
    object_id: int,
):
    """Returns an HTML template for exploring an asset object built with PyGWalker."""

    stmt = select(UploadedS3Object).where(UploadedS3Object.id == object_id)

    if not user.is_admin:
        stmt = stmt.where(
            or_(
                Asset.username == user.username,
                Asset.access_level == AssetAccessLevels.PUBLIC,
            )
        )

    result = await session.execute(stmt)
    s3_object = result.scalar_one_or_none()

    if not s3_object:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    size_in_mib = await get_s3object_size_mib(s3_object=s3_object, s3=s3)
    _logger.info("S3 object size (%s): %s MiB", s3_object.key, round(size_in_mib, 2))

    if size_in_mib >= settings.visualization_max_size_mib:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Object size ({round(size_in_mib, 2)} MiB) exceeds maximum "
                f"allowed size ({settings.visualization_max_size_mib} MiB)"
            ),
        )

    download_url = await s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": s3_object.bucket, "Key": s3_object.key},
        ExpiresIn=settings.visualization_expires_in_seconds,
    )

    ext = os.path.splitext(s3_object.key)[1]

    readers = {
        ".csv": pd.read_csv,
        ".parquet": pd.read_parquet,
    }

    if ext not in readers:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file extension: {ext}",
        )

    df = readers[ext](download_url)
    html_content = pyg.to_html(df)
    return HTMLResponse(content=html_content)
