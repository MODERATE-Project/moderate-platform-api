from typing import Any

from pydantic import AnyHttpUrl, BaseModel, root_validator


class PlatformApplicationLinks(BaseModel):
    """Links for one application in the platform applications file."""

    url: AnyHttpUrl | None = None  # Live deployment
    source_url: AnyHttpUrl | None = None  # Code repository

    @root_validator(skip_on_failure=True)
    def check_has_link(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not values.get("url") and not values.get("source_url"):
            raise ValueError("Set url, source_url or both")

        return values


class PlatformApplicationRead(BaseModel):
    """Links and availability of an application listed on the UI home page."""

    id: str
    url: AnyHttpUrl | None
    source_url: AnyHttpUrl | None
    online: bool | None  # None when there is no live URL to check
