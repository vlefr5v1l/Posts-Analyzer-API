from fastapi import APIRouter

from src.api.v1.endpoints import posts

api_router = APIRouter()

# Include routers from endpoints
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
