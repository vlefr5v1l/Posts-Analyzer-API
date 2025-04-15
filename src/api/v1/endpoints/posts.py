from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_category_by_id, get_post_by_id
from src.core.database import get_db
from src.db.crud.posts import (
    create_category,
    create_post,
    delete_category,
    delete_post,
    get_category_by_name,
    get_filtered_posts,
    update_category,
    update_post,
)
from src.db.models.posts import Category, Post
from src.schemas.posts import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    PaginatedPostsResponse,
    PostAnalysisResult,
    PostCreate,
    PostFilterParams,
    PostResponse,
    PostUpdate,
)
from src.services.posts_analyzer import posts_analyzer

router = APIRouter()


# Category endpoints
@router.post(
    "/categories/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category_endpoint(
    category_in: CategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new category"""
    # Check if category with same name already exists
    existing_category = await get_category_by_name(db, category_in.name)
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with name '{category_in.name}' already exists",
        )

    return await create_category(db, category_in)


@router.get(
    "/categories/{category_id}",
    response_model=CategoryResponse,
)
async def get_category_endpoint(
    category: Category = Depends(get_category_by_id),
):
    """Get category by ID"""
    return category


@router.put(
    "/categories/{category_id}",
    response_model=CategoryResponse,
)
async def update_category_endpoint(
    category_in: CategoryUpdate,
    category: Category = Depends(get_category_by_id),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing category"""
    # Check if new name conflicts with existing category
    if category_in.name and category_in.name != category.name:
        existing_category = await get_category_by_name(db, category_in.name)
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with name '{category_in.name}' already exists",
            )

    updated_category = await update_category(db, category.id, category_in)
    if not updated_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category.id} not found",
        )

    return updated_category


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_category_endpoint(
    category: Category = Depends(get_category_by_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a category"""
    await delete_category(db, category.id)
    return None


# Post endpoints
@router.post(
    "/",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post_endpoint(
    post_in: PostCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new post"""
    # Ensure category exists
    await get_category_by_id(post_in.category_id, db)

    return await create_post(db, post_in)


@router.get(
    "/{post_id}",
    response_model=PostResponse,
)
async def get_post_endpoint(
    post: Post = Depends(get_post_by_id),
):
    """Get post by ID"""
    return post


@router.put(
    "/{post_id}",
    response_model=PostResponse,
)
async def update_post_endpoint(
    post_in: PostUpdate,
    post: Post = Depends(get_post_by_id),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing post"""
    # Check if category exists if category_id is provided
    if post_in.category_id is not None:
        await get_category_by_id(post_in.category_id, db)

    updated_post = await update_post(db, post.id, post_in)
    if not updated_post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with ID {post.id} not found",
        )

    return updated_post


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_post_endpoint(
    post: Post = Depends(get_post_by_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a post"""
    await delete_post(db, post.id)
    return None


@router.get(
    "/",
    response_model=PaginatedPostsResponse,
)
async def get_posts_endpoint(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
    search_query: Optional[str] = None,
    use_fulltext: bool = True,
):
    """
    Get filtered and paginated posts

    - **limit**: Maximum number of posts to return
    - **offset**: Number of posts to skip
    - **category_id**: Filter by category ID
    - **category_name**: Filter by category name
    - **search_query**: Search in post content
    - **use_fulltext**: Use PostgreSQL full-text search (true) or ILIKE (false)
    """
    # Create filter params
    filters = PostFilterParams(
        limit=limit,
        offset=offset,
        category_id=category_id,
        category_name=category_name,
        search_query=search_query,
        use_fulltext=use_fulltext,
    )

    # Get posts with pagination
    posts, total = await get_filtered_posts(db, filters)

    # Calculate next and previous offsets
    next_offset = offset + limit if offset + limit < total else None
    prev_offset = offset - limit if offset > 0 else None

    return PaginatedPostsResponse(
        total=total,
        limit=limit,
        offset=offset,
        next_offset=next_offset,
        prev_offset=prev_offset,
        items=posts,
    )


@router.get(
    "/{post_id}/analyze",
    response_model=PostAnalysisResult,
)
async def analyze_post_endpoint(
    post: Post = Depends(get_post_by_id),
    db: AsyncSession = Depends(get_db),
    run_if_missing: bool = True,
):
    """
    Analyze post content

    - **run_if_missing**: Run analysis if not found in database
    """
    analysis_result = await posts_analyzer.get_post_analysis_result(
        db, post.id, run_if_missing
    )

    if not analysis_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis for post with ID {post.id} not found",
        )

    return analysis_result


@router.post(
    "/analyze",
    response_model=List[PostAnalysisResult],
)
async def analyze_filtered_posts_endpoint(
    filters: PostFilterParams,
    db: AsyncSession = Depends(get_db),
    analysis_types: List[str] = Query(["word_frequency", "text_stats", "tags"]),
    save_results: bool = True,
):
    """
    Analyze multiple posts based on filter criteria

    - **filters**: Filter parameters
    - **analysis_types**: Types of analysis to perform
    - **save_results**: Whether to save analysis results to database
    """
    # Validate analysis types
    valid_types = {"word_frequency", "text_stats", "tags"}
    for analysis_type in analysis_types:
        if analysis_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid analysis type: {analysis_type}. Valid types are: {valid_types}",
            )

    # Run analysis
    results, metadata = await posts_analyzer.analyze_filtered_posts(
        db, filters, analysis_types, save_results
    )

    # Process results
    post_analyses = []
    for result in results:
        post_id = result["post_id"]
        analysis_result = await posts_analyzer.get_post_analysis_result(
            db, post_id, run_if_missing=False
        )
        if analysis_result:
            post_analyses.append(analysis_result)

    return post_analyses
