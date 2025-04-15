from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.db.models.base import Base

engine = create_async_engine(
    str(settings.database_url),
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async DB session"""
    session = async_session_maker()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_models():
    """Initialize database models (used during testing)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_models():
    """Drop all database models (used during testing)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)