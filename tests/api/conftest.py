import pytest
from typing import AsyncGenerator, Generator, Callable
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.api.dependencies import get_db


# Override database dependency for tests
@pytest.fixture
def override_get_db(db_session: AsyncSession) -> Callable:
    """
    Returns a function to override the original get_db dependency
    """

    async def _override_get_db():
        yield db_session

    return _override_get_db


@pytest.fixture
def test_app(override_get_db: Callable) -> FastAPI:
    """Returns the app with overridden dependencies"""
    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def test_client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """Synchronous test client for FastAPI"""
    with TestClient(test_app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def app_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Asynchronous test client for FastAPI
    Uses ASGITransport to call the app directly without HTTP
    """
    transport = ASGITransport(app=test_app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
