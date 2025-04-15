import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_category(app_client: AsyncClient):
    """Test creating a category via API"""
    category_data = {
        "name": "API Test Category",
        "description": "Category for API testing",
    }

    response = await app_client.post("/api/v1/posts/categories/", json=category_data)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == category_data["name"]
    assert data["description"] == category_data["description"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_get_category(app_client: AsyncClient, categories):
    """Test retrieving a category by ID via API"""
    category_id = categories[0].id

    response = await app_client.get(f"/api/v1/posts/categories/{category_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == category_id
    assert data["name"] == categories[0].name
    assert data["description"] == categories[0].description


@pytest.mark.asyncio
async def test_update_category(app_client: AsyncClient, categories):
    """Test updating a category via API"""
    category_id = categories[1].id
    update_data = {
        "name": "Updated Category Name",
        "description": "Updated Category Description",
    }

    response = await app_client.put(
        f"/api/v1/posts/categories/{category_id}", json=update_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == category_id
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]


@pytest.mark.asyncio
async def test_delete_category(app_client: AsyncClient, categories):
    """Test deleting a category via API"""
    category_id = categories[2].id

    response = await app_client.delete(f"/api/v1/posts/categories/{category_id}")

    assert response.status_code == 204
    assert response.content == b""  # Empty response

    # Check that the category is actually deleted
    response = await app_client.get(f"/api/v1/posts/categories/{category_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_category_duplicate_name(app_client: AsyncClient, categories):
    """Test creating a category with a duplicate name"""
    existing_name = categories[0].name
    category_data = {
        "name": existing_name,
        "description": "Description for category with duplicate name",
    }

    response = await app_client.post("/api/v1/posts/categories/", json=category_data)

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert (
        existing_name in data["detail"]
    )  # Check that the error message contains the name


@pytest.mark.asyncio
async def test_get_nonexistent_category(app_client: AsyncClient):
    """Test retrieving a non-existent category"""
    nonexistent_id = 9999

    response = await app_client.get(f"/api/v1/posts/categories/{nonexistent_id}")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert str(nonexistent_id) in data["detail"]
