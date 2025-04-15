from typing import List, Optional, Tuple, Any

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models.posts import Post, Category, PostAnalysis
from src.schemas.posts import (
    PostCreate,
    PostUpdate,
    CategoryCreate,
    CategoryUpdate,
    PostFilterParams,
    PostAnalysisCreate,
)


# Category CRUD operations
async def create_category(db: AsyncSession, category_in: CategoryCreate) -> Category:
    """Create a new category"""
    category = Category(**category_in.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def get_category(db: AsyncSession, category_id: int) -> Optional[Category]:
    """Get category by ID"""
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalars().first()


async def get_category_by_name(db: AsyncSession, name: str) -> Optional[Category]:
    """Get category by name"""
    result = await db.execute(select(Category).where(Category.name == name))
    return result.scalars().first()


async def update_category(
    db: AsyncSession, category_id: int, category_in: CategoryUpdate
) -> Optional[Category]:
    """Update an existing category"""
    category = await get_category(db, category_id)
    if not category:
        return None

    update_data = category_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: int) -> bool:
    """Delete a category by ID"""
    category = await get_category(db, category_id)
    if not category:
        return False

    await db.delete(category)
    await db.commit()
    return True


# Post CRUD operations
async def create_post(db: AsyncSession, post_in: PostCreate) -> Post:
    """Create a new post"""
    post = Post(**post_in.model_dump())
    db.add(post)
    await db.flush()

    # Update search vector
    stmt = (
        Post.__table__.update()
        .where(Post.id == post.id)
        .values(
            search_vector=func.to_tsvector(
                "russian", func.coalesce(post.title, "") + " " + post.content
            )
        )
    )
    await db.execute(stmt)

    await db.commit()
    await db.refresh(post, ["category"])
    return post


async def get_post(
    db: AsyncSession, post_id: int, load_category: bool = True
) -> Optional[Post]:
    """Get post by ID"""
    query = select(Post).where(Post.id == post_id)

    if load_category:
        query = query.options(selectinload(Post.category))

    result = await db.execute(query)
    return result.scalars().first()


async def update_post(
    db: AsyncSession, post_id: int, post_in: PostUpdate
) -> Optional[Post]:
    """Update an existing post"""
    post = await get_post(db, post_id, load_category=False)
    if not post:
        return None

    update_data = post_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await db.flush()

    # Update search vector if content or title changed
    if "content" in update_data or "title" in update_data:
        stmt = (
            Post.__table__.update()
            .where(Post.id == post.id)
            .values(
                search_vector=func.to_tsvector(
                    "russian", func.coalesce(post.title, "") + " " + post.content
                )
            )
        )
        await db.execute(stmt)

    await db.commit()
    await db.refresh(post)
    return post


async def delete_post(db: AsyncSession, post_id: int) -> bool:
    """Delete a post by ID"""
    post = await get_post(db, post_id, load_category=False)
    if not post:
        return False

    await db.delete(post)
    await db.commit()
    return True


async def get_posts_count(db: AsyncSession, filters: PostFilterParams) -> int:
    """Get total count of posts with applied filters"""
    # Start with base query
    query = select(func.count(Post.id))

    # Apply filters
    query = _apply_post_filters(query, filters)

    # Execute query and get count
    result = await db.execute(query)
    return result.scalar_one()


async def get_filtered_posts(
    db: AsyncSession, filters: PostFilterParams
) -> Tuple[List[Post], int]:
    """
    Get filtered and paginated posts

    Returns:
        Tuple containing list of posts and total count
    """
    # Get total count first
    total = await get_posts_count(db, filters)

    # Build main query with joins and filters
    query = select(Post).options(selectinload(Post.category))

    # Apply filters
    query = _apply_post_filters(query, filters)

    # Apply pagination
    query = query.offset(filters.offset).limit(filters.limit)

    # Execute query
    result = await db.execute(query)
    posts = result.scalars().all()

    return posts, total


def _apply_post_filters(query: Any, filters: PostFilterParams) -> Any:
    """Apply filters to a post query"""
    filter_conditions = []

    # Filter by category ID
    if filters.category_id is not None:
        filter_conditions.append(Post.category_id == filters.category_id)

    # Filter by category name
    if filters.category_name is not None:
        query = query.join(Category)
        filter_conditions.append(Category.name == filters.category_name)

    # Filter by search query
    if filters.search_query:
        if filters.use_fulltext:
            # Use PostgreSQL full-text search
            search_query = func.plainto_tsquery("russian", filters.search_query)
            filter_conditions.append(Post.search_vector.op("@@")(search_query))
        else:
            # Use ILIKE for simple text search
            search_pattern = f"%{filters.search_query}%"
            filter_conditions.append(
                or_(
                    Post.content.ilike(search_pattern), Post.title.ilike(search_pattern)
                )
            )

    # Apply all filter conditions
    if filter_conditions:
        query = query.where(and_(*filter_conditions))

    return query


# Post analysis CRUD operations
async def create_post_analysis(
    db: AsyncSession, analysis_in: PostAnalysisCreate
) -> PostAnalysis:
    """Create a new post analysis record"""
    analysis = PostAnalysis(**analysis_in.model_dump())
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


async def get_post_analyses(
    db: AsyncSession, post_id: int, analysis_type: Optional[str] = None
) -> List[PostAnalysis]:
    """Get all analyses for a post, optionally filtered by type"""
    query = select(PostAnalysis).where(PostAnalysis.post_id == post_id)

    if analysis_type:
        query = query.where(PostAnalysis.analysis_type == analysis_type)

    result = await db.execute(query)
    return result.scalars().all()


async def get_latest_post_analysis(
    db: AsyncSession, post_id: int, analysis_type: str
) -> Optional[PostAnalysis]:
    """Get the latest analysis of a specific type for a post"""
    query = (
        select(PostAnalysis)
        .where(
            PostAnalysis.post_id == post_id, PostAnalysis.analysis_type == analysis_type
        )
        .order_by(PostAnalysis.created_at.desc())
        .limit(1)
    )

    result = await db.execute(query)
    return result.scalars().first()
