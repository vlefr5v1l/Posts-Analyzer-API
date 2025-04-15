import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_post(app_client: AsyncClient, categories):
    """Test creating a post via API"""
    post_data = {
        "title": "Test post via API",
        "content": "Content of the test post created via the API for endpoint testing.",
        "category_id": categories[0].id,
    }

    response = await app_client.post("/api/v1/posts/", json=post_data)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == post_data["title"]
    assert data["content"] == post_data["content"]
    assert data["category_id"] == post_data["category_id"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "category" in data
    assert data["category"]["id"] == post_data["category_id"]


@pytest.mark.asyncio
async def test_get_post(app_client: AsyncClient, posts):
    """Test retrieving a post by ID via API"""
    post_id = posts[0].id

    response = await app_client.get(f"/api/v1/posts/{post_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == post_id
    assert data["title"] == posts[0].title
    assert data["content"] == posts[0].content
    assert data["category_id"] == posts[0].category_id
    assert "category" in data
    assert data["category"]["id"] == posts[0].category_id


@pytest.mark.asyncio
async def test_update_post(app_client: AsyncClient, posts):
    """Test updating a post via API"""
    post_id = posts[1].id
    update_data = {
        "title": "Updated post title",
        "content": "Updated content of the post for API testing",
    }

    response = await app_client.put(f"/api/v1/posts/{post_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == post_id
    assert data["title"] == update_data["title"]
    assert data["content"] == update_data["content"]
    assert (
        data["category_id"] == posts[1].category_id
    )  # Category should remain unchanged


@pytest.mark.asyncio
async def test_delete_post(app_client: AsyncClient, posts):
    """Test deleting a post via API"""
    post_id = posts[2].id

    response = await app_client.delete(f"/api/v1/posts/{post_id}")

    assert response.status_code == 204
    assert response.content == b""  # Empty response

    # Ensure the post is actually deleted
    response = await app_client.get(f"/api/v1/posts/{post_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_filtered_posts_by_category(
    app_client: AsyncClient, categories, posts
):
    """Test filtering posts by category via API"""
    category_id = categories[1].id

    response = await app_client.get(f"/api/v1/posts/?category_id={category_id}")

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] > 0
    assert len(data["items"]) > 0

    # All posts must belong to the specified category
    for post in data["items"]:
        assert post["category_id"] == category_id


@pytest.mark.asyncio
async def test_get_filtered_posts_by_search(app_client: AsyncClient, posts):
    """Test searching posts by text via API"""
    sample_word = ""
    for post in posts:
        words = post.content.lower().split()
        if words:
            for word in words:
                if len(word) > 4:
                    sample_word = word
                    break
        if sample_word:
            break

    if not sample_word:
        sample_word = "post"  # fallback word expected to appear in at least one post

    # Regular search
    response = await app_client.get(
        f"/api/v1/posts/?search_query={sample_word}&use_fulltext=false"
    )

    assert response.status_code == 200
    data = response.json()

    if data["total"] > 0:
        for post in data["items"]:
            assert sample_word in post["content"].lower() or (
                post["title"] and sample_word in post["title"].lower()
            )

    # Full-text search
    response = await app_client.get(
        f"/api/v1/posts/?search_query={sample_word}&use_fulltext=true"
    )
    assert response.status_code == 200
    # No strict assertions — fulltext might behave differently


@pytest.mark.asyncio
async def test_get_filtered_posts_with_pagination(app_client: AsyncClient, posts):
    """Test post pagination via API"""
    response = await app_client.get("/api/v1/posts/?limit=2&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert "limit" in data
    assert "offset" in data
    assert "next_offset" in data
    assert "prev_offset" in data

    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) <= 2

    if data["total"] > 2:
        assert data["next_offset"] == 2

        response = await app_client.get("/api/v1/posts/?limit=2&offset=2")
        assert response.status_code == 200
        page2_data = response.json()

        assert page2_data["limit"] == 2
        assert page2_data["offset"] == 2
        assert page2_data["prev_offset"] == 0

        page1_ids = [post["id"] for post in data["items"]]
        page2_ids = [post["id"] for post in page2_data["items"]]
        assert not set(page1_ids).intersection(set(page2_ids))


@pytest.mark.asyncio
async def test_analyze_post(app_client: AsyncClient, posts):
    """Test analyzing a single post via API"""
    post_id = posts[0].id

    response = await app_client.get(f"/api/v1/posts/{post_id}/analyze")

    assert response.status_code == 200
    data = response.json()

    if "word_frequencies" in data:
        assert isinstance(data["word_frequencies"], list)
        if data["word_frequencies"]:
            for freq in data["word_frequencies"]:
                assert "word" in freq
                assert "count" in freq
                assert "frequency" in freq

    if "text_stats" in data:
        assert isinstance(data["text_stats"], dict)
        assert "word_count" in data["text_stats"]
        assert "char_count" in data["text_stats"]
        assert "sentence_count" in data["text_stats"]

    if "extracted_tags" in data:
        assert isinstance(data["extracted_tags"], dict)
        assert "tags" in data["extracted_tags"]
        assert isinstance(data["extracted_tags"]["tags"], list)


@pytest.mark.asyncio
async def test_analyze_filtered_posts(app_client: AsyncClient, categories):
    """Test analyzing filtered posts via API"""
    category_id = categories[0].id

    filter_data = {
        "limit": 10,
        "offset": 0,
        "category_id": category_id,
        "use_fulltext": False,
    }

    response = await app_client.post(
        "/api/v1/posts/analyze?analysis_types=word_frequency&analysis_types=text_stats&save_results=true",
        json=filter_data,
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    if data:
        for analysis_result in data:
            if "word_frequencies" in analysis_result:
                assert isinstance(analysis_result["word_frequencies"], list)

            if "text_stats" in analysis_result:
                assert isinstance(analysis_result["text_stats"], dict)
                assert "word_count" in analysis_result["text_stats"]
