# https://fastapi.tiangolo.com/advanced/settings/#settings-in-a-dependency

from functools import lru_cache

from fastapi import Depends
from pydantic import BaseSettings
from typing_extensions import Annotated


class Settings(BaseSettings):
    pass


@lru_cache()
def get_settings():
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
