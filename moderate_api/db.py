from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from moderate_api.config import get_settings

engine = create_async_engine(
    get_settings().postgres_url,
    echo=True,
    future=True,
    pool_size=20,
    max_overflow=20,
    pool_recycle=3600,
)


@asynccontextmanager
async def get_session() -> AsyncSession:
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
