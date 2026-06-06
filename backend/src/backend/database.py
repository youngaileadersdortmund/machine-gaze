from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .settings import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None) -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(database_url or settings.database_url, future=True)


engine = make_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db(db_engine: AsyncEngine = engine) -> None:
    from . import models  # noqa: F401

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
