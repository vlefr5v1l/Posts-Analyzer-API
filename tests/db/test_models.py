import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models.posts import Category, Post, PostAnalysis


@pytest.mark.asyncio
async def test_category_model(db_session: AsyncSession):
    """Test creating and retrieving a category"""
    category = Category(
        name="Test Category", description="Description of the test category"
    )
    db_session.add(category)
    await db_session.commit()

    result = await db_session.execute(
        select(Category).where(Category.name == "Test Category")
    )
    saved_category = result.scalars().first()

    assert saved_category is not None
    assert saved_category.name == "Test Category"
    assert saved_category.description == "Description of the test category"
    assert saved_category.created_at is not None
    assert saved_category.updated_at is not None


@pytest.mark.asyncio
async def test_post_model(db_session: AsyncSession):
    """Test creating and retrieving a post"""
    category = Category(name="Post Category", description="Category description")
    db_session.add(category)
    await db_session.commit()

    post = Post(
        title="Test Title",
        content="Content of the test post",
        category_id=category.id,
    )
    db_session.add(post)
    await db_session.commit()

    result = await db_session.execute(
        select(Post)
        .where(Post.title == "Test Title")
        .options(selectinload(Post.category))
    )
    saved_post = result.scalars().first()

    assert saved_post is not None
    assert saved_post.title == "Test Title"
    assert saved_post.content == "Content of the test post"
    assert saved_post.category_id == category.id
    assert saved_post.category.name == "Post Category"
    assert saved_post.created_at is not None
    assert saved_post.updated_at is not None


@pytest.mark.asyncio
async def test_post_analysis_model(db_session: AsyncSession):
    """Test creating and retrieving post analysis"""
    category = Category(name="Analysis Category", description="Category description")
    db_session.add(category)
    await db_session.commit()

    post = Post(
        title="Post for Analysis",
        content="Text content to be analyzed",
        category_id=category.id,
    )
    db_session.add(post)
    await db_session.commit()

    post_analysis = PostAnalysis(
        post_id=post.id,
        analysis_type="text_stats",
        result='{"word_count": 5, "char_count": 30, "sentence_count": 1}',
    )
    db_session.add(post_analysis)
    await db_session.commit()

    result = await db_session.execute(
        select(PostAnalysis).where(PostAnalysis.post_id == post.id)
    )
    saved_analysis = result.scalars().first()

    assert saved_analysis is not None
    assert saved_analysis.post_id == post.id
    assert saved_analysis.analysis_type == "text_stats"
    assert "word_count" in saved_analysis.result
    assert saved_analysis.created_at is not None
    assert saved_analysis.updated_at is not None


@pytest.mark.asyncio
async def test_relationships(db_session: AsyncSession, categories, posts):
    """Test relationships between models"""
    category = await db_session.get(Category, categories[0].id)
    assert category is not None

    await db_session.refresh(category, ["posts"])
    assert len(category.posts) > 0
    for post in category.posts:
        assert post.category_id == category.id

    post = await db_session.get(Post, posts[0].id)
    assert post is not None

    await db_session.refresh(post, ["category"])
    assert post.category is not None
    assert post.category.id == post.category_id
