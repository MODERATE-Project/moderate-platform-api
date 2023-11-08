import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing_extensions import Annotated

from moderate_api.config import get_settings

_logger = logging.getLogger(__name__)

engine = create_async_engine(get_settings().postgres_url, echo=True, future=True)


async def get_session() -> AsyncSession:
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _logger.debug("Initialized session factory: %s", async_session)

    async with async_session() as session:
        yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_session)]
