from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.db.crud.posts import get_category, get_post
from src.db.models.posts import Category, Post


async def get_category_by_id(
    category_id: int, db: AsyncSession = Depends(get_db)
) -> Category:
    """
    Dependency to get category by ID or raise 404
    """
    category = await get_category(db, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} not found",
        )
    return category


async def get_post_by_id(post_id: int, db: AsyncSession = Depends(get_db)) -> Post:
    """
    Dependency to get post by ID or raise 404
    """
    post = await get_post(db, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post_id} not found",
        )
    return post
