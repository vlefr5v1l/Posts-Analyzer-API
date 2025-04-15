from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class CategoryBase(BaseModel):
    """Base schema for Category data"""

    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    """Schema for creating a new Category"""

    pass


class CategoryUpdate(CategoryBase):
    """Schema for updating an existing Category"""

    name: Optional[str] = None


class CategoryResponse(CategoryBase):
    """Schema for Category response"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Post schemas
class PostBase(BaseModel):
    """Base schema for Post data"""

    title: Optional[str] = None
    content: str
    category_id: int


class PostCreate(PostBase):
    """Schema for creating a new Post"""

    pass


class PostUpdate(BaseModel):
    """Schema for updating an existing Post"""

    title: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[int] = None


class PostResponse(PostBase):
    """Schema for Post response"""

    id: int
    created_at: datetime
    updated_at: datetime
    category: CategoryResponse

    class Config:
        from_attributes = True


# Post Analysis schemas
class PostAnalysisBase(BaseModel):
    """Base schema for PostAnalysis data"""

    analysis_type: str
    result: str
    post_id: int


class PostAnalysisCreate(PostAnalysisBase):
    """Schema for creating a new PostAnalysis"""

    pass


class PostAnalysisResponse(PostAnalysisBase):
    """Schema for PostAnalysis response"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Pagination and filtering schemas
class PaginationParams(BaseModel):
    """Schema for pagination parameters"""

    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)


class PostFilterParams(PaginationParams):
    """Schema for post filtering and pagination"""

    category_id: Optional[int] = None
    category_name: Optional[str] = None
    search_query: Optional[str] = None
    use_fulltext: bool = True


class PaginatedResponse(BaseModel):
    """Base schema for paginated responses"""

    total: int
    limit: int
    offset: int
    next_offset: Optional[int] = None
    prev_offset: Optional[int] = None


class PaginatedPostsResponse(PaginatedResponse):
    """Schema for paginated posts response"""

    items: List[PostResponse]


# Analysis types and results
class WordFrequency(BaseModel):
    """Schema for word frequency analysis"""

    word: str
    count: int
    frequency: float


class TextStats(BaseModel):
    """Schema for text statistics"""

    word_count: int
    char_count: int
    sentence_count: int
    avg_word_length: float
    avg_sentence_length: float


class ExtractedTags(BaseModel):
    """Schema for extracted tags"""

    tags: List[str]


class PostAnalysisResult(BaseModel):
    """Schema for combined analysis results"""

    word_frequencies: Optional[List[WordFrequency]] = None
    text_stats: Optional[TextStats] = None
    extracted_tags: Optional[ExtractedTags] = None
    raw_analysis: Optional[Dict[str, Any]] = None
