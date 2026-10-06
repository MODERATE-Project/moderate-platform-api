from pathlib import Path

import yaml
from fastapi import APIRouter
from pydantic import parse_obj_as

from moderate_api.config import SettingsDep
from moderate_api.enums import Tags
from moderate_api.platform_application.models import (
    PlatformApplicationLinks,
    PlatformApplicationRead,
)
from moderate_api.platform_application.status import StatusCheckerDep

_TAG = "Platform applications"

router = APIRouter()


def _load_applications(path: Path | None) -> dict[str, PlatformApplicationLinks]:
    """Read the platform applications YAML file.

    The file is read on every request, so edits apply without a restart.

    Args:
        path: Path to the file, or None when no file is configured.

    Returns:
        Links keyed by application id, empty when no file is configured.

    Raises:
        OSError: If the file cannot be read.
        yaml.YAMLError: If the file is not valid YAML.
        pydantic.ValidationError: If an entry has invalid or missing links.
    """

    if path is None:
        return {}

    with path.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}

    return parse_obj_as(dict[str, PlatformApplicationLinks], data)


@router.get(
    "/public",
    response_model=list[PlatformApplicationRead],
    tags=[_TAG, Tags.PUBLIC.value],
    summary="List the applications shown on the UI home page",
)
async def list_platform_applications(
    settings: SettingsDep,
    checker: StatusCheckerDep,
) -> list[PlatformApplicationRead]:
    """Return each configured application with its links and availability.

    Only live URLs are probed. Applications with just a source URL report
    `online` as null.
    """

    applications = _load_applications(settings.platform_applications_file)
    live_urls = [item.url for item in applications.values() if item.url]
    statuses = await checker.check(live_urls)

    return [
        PlatformApplicationRead(
            id=app_id,
            url=item.url,
            source_url=item.source_url,
            online=statuses[item.url] if item.url else None,
        )
        for app_id, item in applications.items()
    ]
