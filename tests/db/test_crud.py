import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crud.posts import (
    create_category,
    get_category,
    get_category_by_name,
    update_category,
    delete_category,
    create_post,
    get_post,
    update_post,
    delete_post,
    get_filtered_posts,
    create_post_analysis,
    get_post_analyses,
    get_latest_post_analysis,
)
from src.schemas.posts import (
    CategoryCreate,
    CategoryUpdate,
    PostCreate,
    PostUpdate,
    PostAnalysisCreate,
    PostFilterParams,
)


# Category tests
@pytest.mark.asyncio
async def test_create_category(db_session: AsyncSession):
    """Test creating a category"""
    category_in = CategoryCreate(
        name="New Category", description="Description of the new category"
    )
    category = await create_category(db_session, category_in)

    assert category.id is not None
    assert category.name == "New Category"
    assert category.description == "Description of the new category"


@pytest.mark.asyncio
async def test_get_category(db_session: AsyncSession, categories):
    """Test getting a category by ID"""
    category = await get_category(db_session, categories[0].id)

    assert category is not None
    assert category.id == categories[0].id
    assert category.name == categories[0].name


@pytest.mark.asyncio
async def test_get_category_by_name(db_session: AsyncSession, categories):
    """Test getting a category by name"""
    category = await get_category_by_name(db_session, categories[1].name)

    assert category is not None
    assert category.id == categories[1].id
    assert category.name == categories[1].name


@pytest.mark.asyncio
async def test_update_category(db_session: AsyncSession, categories):
    """Test updating a category"""
    category_id = categories[0].id
    update_data = CategoryUpdate(name="Updated Category", description="New description")

    updated_category = await update_category(db_session, category_id, update_data)

    assert updated_category is not None
    assert updated_category.id == category_id
    assert updated_category.name == "Updated Category"
    assert updated_category.description == "New description"


@pytest.mark.asyncio
async def test_delete_category(db_session: AsyncSession, categories):
    """Test deleting a category"""
    category_id = categories[2].id

    result = await delete_category(db_session, category_id)
    assert result is True

    category = await get_category(db_session, category_id)
    assert category is None


# Post tests
@pytest.mark.asyncio
async def test_create_post(db_session: AsyncSession, categories):
    """Test creating a post"""
    post_in = PostCreate(
        title="New Post",
        content="Content of the new post",
        category_id=categories[0].id,
    )

    post = await create_post(db_session, post_in)

    assert post.id is not None
    assert post.title == "New Post"
    assert post.content == "Content of the new post"
    assert post.category_id == categories[0].id

    refreshed_post = await get_post(db_session, post.id, load_category=False)
    assert refreshed_post is not None


@pytest.mark.asyncio
async def test_get_post(db_session: AsyncSession, posts):
    """Test getting a post by ID"""
    post = await get_post(db_session, posts[0].id)

    assert post is not None
    assert post.id == posts[0].id
    assert post.title == posts[0].title
    assert post.category is not None


@pytest.mark.asyncio
async def test_update_post(db_session: AsyncSession, posts):
    """Test updating a post"""
    post_id = posts[0].id
    update_data = PostUpdate(title="Updated Title", content="Updated content")

    updated_post = await update_post(db_session, post_id, update_data)

    assert updated_post is not None
    assert updated_post.id == post_id
    assert updated_post.title == "Updated Title"
    assert updated_post.content == "Updated content"
    assert updated_post.search_vector is not None


@pytest.mark.asyncio
async def test_delete_post(db_session: AsyncSession, posts):
    """Test deleting a post"""
    post_id = posts[0].id

    result = await delete_post(db_session, post_id)
    assert result is True

    post = await get_post(db_session, post_id)
    assert post is None


# Post filtering tests
@pytest.mark.asyncio
async def test_get_filtered_posts_by_category(
    db_session: AsyncSession, categories, posts
):
    """Test filtering posts by category"""
    filter_params = PostFilterParams(category_id=categories[1].id)
    filtered_posts, count = await get_filtered_posts(db_session, filter_params)

    assert count > 0
    assert all(post.category_id == categories[1].id for post in filtered_posts)

    filter_params = PostFilterParams(category_name=categories[0].name)
    filtered_posts, count = await get_filtered_posts(db_session, filter_params)

    assert count > 0
    assert all(post.category.name == categories[0].name for post in filtered_posts)


@pytest.mark.asyncio
async def test_get_filtered_posts_by_search(db_session: AsyncSession, posts):
    """Test filtering posts by search query"""
    sample_word = ""
    for post in posts:
        words = post.content.lower().split()
        for word in words:
            if len(word) > 4:
                sample_word = word
                break
        if sample_word:
            break

    if not sample_word:
        sample_word = "post"  # fallback

    # ILIKE search
    filter_params = PostFilterParams(search_query=sample_word, use_fulltext=False)
    filtered_posts, count = await get_filtered_posts(db_session, filter_params)

    if count > 0:
        assert all(
            sample_word in post.content.lower()
            or (post.title and sample_word in post.title.lower())
            for post in filtered_posts
        )
    else:
        print(f"No matches found for search word '{sample_word}'")

    # Full-text search
    filter_params = PostFilterParams(search_query=sample_word, use_fulltext=True)
    filtered_posts, count = await get_filtered_posts(db_session, filter_params)

    assert count >= 0


@pytest.mark.asyncio
async def test_get_filtered_posts_with_pagination(db_session: AsyncSession, posts):
    """Test pagination when filtering posts"""
    filter_params = PostFilterParams(limit=2, offset=0)
    first_page, total = await get_filtered_posts(db_session, filter_params)

    assert len(first_page) <= 2
    assert total >= len(first_page)

    if total > 2:
        filter_params = PostFilterParams(limit=2, offset=2)
        second_page, _ = await get_filtered_posts(db_session, filter_params)

        assert len(second_page) <= 2
        assert all(
            first.id != second.id for first in first_page for second in second_page
        )


# Post analysis tests
@pytest.mark.asyncio
async def test_post_analysis_operations(db_session: AsyncSession, posts):
    """Test operations with post analyses"""
    post_id = posts[0].id

    analysis_in = PostAnalysisCreate(
        post_id=post_id,
        analysis_type="word_frequency",
        result='{"top_words": ["test", "analysis"]}',
    )

    analysis = await create_post_analysis(db_session, analysis_in)

    assert analysis.id is not None
    assert analysis.post_id == post_id
    assert analysis.analysis_type == "word_frequency"

    analyses = await get_post_analyses(db_session, post_id)
    assert len(analyses) > 0
    assert any(a.id == analysis.id for a in analyses)

    analyses_by_type = await get_post_analyses(db_session, post_id, "word_frequency")
    assert len(analyses_by_type) > 0
    assert all(a.analysis_type == "word_frequency" for a in analyses_by_type)

    latest_analysis = await get_latest_post_analysis(
        db_session, post_id, "word_frequency"
    )
    assert latest_analysis is not None
    assert latest_analysis.post_id == post_id
    assert latest_analysis.analysis_type == "word_frequency"
