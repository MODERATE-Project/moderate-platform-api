"""DIVA client dependency injection."""

from typing import Annotated

from fastapi import Depends

from moderate_api.config import SettingsDep
from moderate_api.diva import DivaClient
from moderate_api.diva_mock import MockDivaClient


def get_diva_client(settings: SettingsDep) -> DivaClient:
    """Get DIVA client based on configuration.

    Returns MockDivaClient when DIVA is not enabled (for demos/testing),
    or the real DivaClient when DIVA is enabled.

    Args:
        settings: Application settings

    Returns:
        DivaClient instance (real or mock)
    """
    if settings.diva.enabled:
        return DivaClient(settings.diva)
    return MockDivaClient(settings.diva)


DivaClientDep = Annotated[DivaClient, Depends(get_diva_client)]
