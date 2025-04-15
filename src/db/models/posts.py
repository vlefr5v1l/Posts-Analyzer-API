from typing import List, Optional
from sqlalchemy import String, Text, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import TSVECTOR

from src.db.models.base import Base, TimestampMixin


class Category(Base, TimestampMixin):
    """Category model for post categorization"""
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship with Post model
    posts: Mapped[List["Post"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Category {self.name}>"


class Post(Base, TimestampMixin):
    """Post model representing content entries"""
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    search_vector: Mapped[Optional[TSVECTOR]] = mapped_column(
        TSVECTOR, nullable=True, index=True
    )

    # Relationship with Category model
    category: Mapped[Category] = relationship(back_populates="posts")

    # Relationship with PostAnalysis model
    analyses: Mapped[List["PostAnalysis"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Post {self.id}: {self.title or 'Untitled'}>"


# Creating a GIN index for full-text search
Index('ix_post_search_vector_gin', Post.search_vector, postgresql_using='gin')


class PostAnalysis(Base, TimestampMixin):
    """Model for storing post analysis results"""
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("post.id", ondelete="CASCADE"))
    analysis_type: Mapped[str] = mapped_column(String(50))
    result: Mapped[str] = mapped_column(Text)

    # Relationship with Post model
    post: Mapped[Post] = relationship(back_populates="analyses")

    def __repr__(self) -> str:
        return f"<PostAnalysis {self.id}: {self.analysis_type}>"


# Function to create or update search vector
def update_post_search_vector(session, post_id):
    """Update the search vector for a post"""
    stmt = (
        Post.__table__.update()
        .where(Post.id == post_id)
        .values(
            search_vector=func.to_tsvector('russian',
                                           func.coalesce(Post.title, '') + ' ' +
                                           func.coalesce(Post.content, '')
                                           )
        )
    )
    session.execute(stmt)