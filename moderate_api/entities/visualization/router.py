import logging
import os
from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd
import pygwalker as pyg
from fastapi import APIRouter, HTTPException, Query, status
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
    sample_size: int = Query(
        default=2000,
        ge=1000,
        le=1000000,
        description="Number of rows to sample when file exceeds maximum size",
    ),
    sample_fraction: Optional[float] = Query(
        default=None,
        ge=0.01,
        le=0.9,
        description="Fraction of data to sample when file exceeds maximum size",
    ),
):
    """
    Returns an interactive HTML visualization dashboard for exploring asset objects.

    This endpoint:
    1. Retrieves the S3 object metadata based on the provided object_id
    2. Checks user permissions
    3. Handles large files by sampling instead of returning an error
    4. Supports CSV and Parquet file formats
    """

    # Fetch S3 object with permission check
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

    # Get object size and log
    size_in_mib = await get_s3object_size_mib(s3_object=s3_object, s3=s3)
    _logger.info("S3 object size (%s): %s MiB", s3_object.key, round(size_in_mib, 2))

    # Generate download URL
    download_url = await s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": s3_object.bucket, "Key": s3_object.key},
        ExpiresIn=settings.visualization_expires_in_seconds,
    )  # type: ignore

    # Determine file extension and appropriate reader
    ext = os.path.splitext(s3_object.key)[1]

    readers = _get_file_readers(
        size_in_mib=size_in_mib,
        max_size_mib=settings.visualization_max_size_mib,
        sample_size=sample_size,
        sample_fraction=sample_fraction,
    )

    if ext not in readers:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file extension: {ext}",
        )

    # Read data with appropriate reader (regular or sampling)
    try:
        df = readers[ext](download_url)
        _logger.info(f"Loaded dataframe with shape: {df.shape}")
        html_content = pyg.to_html(df)
        response = HTMLResponse(content=html_content)

        # Add sampling headers if the dataset was sampled
        if size_in_mib >= settings.visualization_max_size_mib:
            response.headers["X-Sampled-Data"] = "true"

            response.headers.update(
                {"X-Sampling-Fraction": str(sample_fraction)}
                if sample_fraction
                else {"X-Sampling-Size": str(sample_size)}
            )

        return response
    except Exception as e:
        _logger.error(f"Error processing visualization: {str(e)}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating visualization: {str(e)}",
        )


def _get_file_readers(
    size_in_mib: float,
    max_size_mib: float,
    sample_size: int,
    sample_fraction: Optional[float] = None,
    random_seed: int = 42,
) -> Dict[str, Callable[[str], pd.DataFrame]]:
    """
    Returns appropriate file readers based on file extension and size.
    For files larger than max_size_mib, returns readers that will sample
    the data instead of loading the entire file.
    """

    # Check if we need to sample or can read normally
    if size_in_mib < max_size_mib:
        # For small files, use normal readers
        return {
            ".csv": pd.read_csv,
            ".parquet": pd.read_parquet,
        }
    else:
        readers: Dict[str, Callable[[Any], pd.DataFrame]] = {}

        # CSV sampling function - simple for specific size, random for fraction
        def sample_csv(url: str) -> pd.DataFrame:
            if sample_fraction:
                # Sample by fraction
                np.random.seed(random_seed)

                return pd.read_csv(
                    url,
                    skiprows=lambda i: i > 0 and np.random.random() > sample_fraction,  # type: ignore
                )
            else:
                # Most efficient method: just read the first N rows
                return pd.read_csv(url, nrows=sample_size)

        # Parquet sampling function
        def sample_parquet(url: str) -> pd.DataFrame:
            if sample_fraction:
                # Sample by fraction
                df = pd.read_parquet(url)
                return df.sample(frac=sample_fraction, random_state=random_seed)
            else:
                # For Parquet, we can efficiently filter rows after reading
                df = pd.read_parquet(url)
                return df.sample(n=min(sample_size, len(df)), random_state=random_seed)

        readers[".csv"] = sample_csv
        readers[".parquet"] = sample_parquet

        return readers
