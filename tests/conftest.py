import asyncio
from typing import AsyncGenerator, Generator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_maker, init_models, drop_models
from src.db.models.posts import Category, Post


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create a global event loop for async tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a clean database for each test and clean it up after.
    """
    await init_models()

    async with async_session_maker() as session:
        try:
            await session.execute(text("SELECT 1"))
        except Exception as e:
            pytest.skip(f"Database is not available: {e}")

        yield session

        await session.rollback()

    await drop_models()


@pytest.fixture
async def categories(db_session: AsyncSession) -> list[Category]:
    """
    Create test categories.
    """
    categories_data = [
        Category(name="News", description="Current news"),
        Category(name="Technology", description="Articles about technology"),
        Category(name="Health", description="Healthy lifestyle articles"),
    ]

    db_session.add_all(categories_data)
    await db_session.commit()

    for category in categories_data:
        await db_session.refresh(category)

    return categories_data


@pytest.fixture
async def posts(db_session: AsyncSession, categories: list[Category]) -> list[Post]:
    """
    Create test posts.
    """
    posts_data = [
        Post(
            title="New AI Technology",
            content="OpenAI has introduced a new AI model capable of writing code and generating images using machine learning to analyze large datasets.",
            category_id=categories[1].id,  # Technology
        ),
        Post(
            title="Important Political News",
            content="Today, G7 leaders met to discuss economic issues and climate change. Several important agreements were signed.",
            category_id=categories[0].id,  # News
        ),
        Post(
            title="How to Eat Healthy",
            content="Healthy eating is key to good health. It's recommended to eat more fruits and vegetables, limit sweets and fast food. Water plays a vital role in metabolism.",
            category_id=categories[2].id,  # Health
        ),
        Post(
            title="New Developments in Web Tech",
            content="The React framework released a new version with improved performance. Developers report faster rendering and new interface-building features.",
            category_id=categories[1].id,  # Technology
        ),
        Post(
            title="International Relations Today",
            content="Diplomatic relations remain tense. Experts suggest new approaches to resolving conflicts and establishing dialogue.",
            category_id=categories[0].id,  # News
        ),
    ]

    db_session.add_all(posts_data)
    await db_session.commit()

    for post in posts_data:
        await db_session.refresh(post)

    return posts_data
