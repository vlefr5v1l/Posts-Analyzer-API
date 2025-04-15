"""
Tests for the post analysis service
"""

import json
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.posts_analyzer import PostsAnalyzer
from src.schemas.posts import PostFilterParams
from src.db.crud.posts import get_latest_post_analysis


@pytest.mark.asyncio
async def test_word_frequency_analysis(db_session: AsyncSession, posts):
    """Test word frequency analysis"""
    analyzer = PostsAnalyzer(batch_size=2, max_workers=2)

    post = posts[0]
    result = analyzer._analyze_word_frequency(post.content)

    assert "total_unique_words" in result
    assert "total_words_after_filtering" in result
    assert "word_frequencies" in result
    assert isinstance(result["word_frequencies"], list)
    assert len(result["word_frequencies"]) > 0

    for item in result["word_frequencies"]:
        assert "word" in item
        assert "count" in item
        assert "frequency" in item
        assert isinstance(item["word"], str)
        assert isinstance(item["count"], int)
        assert isinstance(item["frequency"], float)
        assert 0 <= item["frequency"] <= 1


@pytest.mark.asyncio
async def test_text_stats_analysis(db_session: AsyncSession, posts):
    """Test text statistics analysis"""
    analyzer = PostsAnalyzer(batch_size=2, max_workers=2)

    post = posts[0]
    result = analyzer._analyze_text_stats(post.content)

    assert "word_count" in result
    assert "char_count" in result
    assert "sentence_count" in result
    assert "avg_word_length" in result
    assert "avg_sentence_length" in result

    assert isinstance(result["word_count"], int)
    assert isinstance(result["char_count"], int)
    assert isinstance(result["sentence_count"], int)
    assert isinstance(result["avg_word_length"], float)
    assert isinstance(result["avg_sentence_length"], float)

    assert result["word_count"] > 0
    assert result["char_count"] > 0
    assert result["sentence_count"] > 0


@pytest.mark.asyncio
async def test_extract_tags(db_session: AsyncSession, posts):
    """Test tag extraction from text"""
    analyzer = PostsAnalyzer(batch_size=2, max_workers=2)

    post = posts[0]
    result = analyzer._extract_tags(post.content)

    assert "extracted_tags" in result
    assert "hashtags" in result

    assert isinstance(result["extracted_tags"], list)
    assert isinstance(result["hashtags"], list)

    if result["extracted_tags"]:
        assert all(isinstance(tag, str) for tag in result["extracted_tags"])


@pytest.mark.asyncio
async def test_analyze_post(db_session: AsyncSession, posts):
    """Test full post analysis"""
    analyzer = PostsAnalyzer(batch_size=2, max_workers=2)

    post = posts[0]
    analysis_types = ["word_frequency", "text_stats", "tags"]
    result = await analyzer._analyze_post(
        db_session, post, analysis_types, save_results=True
    )

    assert "post_id" in result
    assert "analyses" in result
    assert result["post_id"] == post.id

    for analysis_type in analysis_types:
        assert analysis_type in result["analyses"]

        analysis = await get_latest_post_analysis(db_session, post.id, analysis_type)
        assert analysis is not None
        assert analysis.analysis_type == analysis_type
        assert analysis.post_id == post.id

        parsed_result = json.loads(analysis.result)
        assert isinstance(parsed_result, dict)


@pytest.mark.asyncio
async def test_get_post_analysis_result(db_session: AsyncSession, posts):
    """Test retrieving post analysis results"""
    analyzer = PostsAnalyzer(batch_size=2, max_workers=2)

    post = posts[0]
    analysis_result = await analyzer.get_post_analysis_result(
        db_session, post.id, run_if_missing=True
    )

    assert analysis_result is not None

    if analysis_result.word_frequencies:
        assert len(analysis_result.word_frequencies) > 0
        for freq in analysis_result.word_frequencies:
            assert hasattr(freq, "word")
            assert hasattr(freq, "count")
            assert hasattr(freq, "frequency")

    if analysis_result.text_stats:
        assert hasattr(analysis_result.text_stats, "word_count")
        assert hasattr(analysis_result.text_stats, "char_count")
        assert hasattr(analysis_result.text_stats, "sentence_count")
        assert hasattr(analysis_result.text_stats, "avg_word_length")
        assert hasattr(analysis_result.text_stats, "avg_sentence_length")

    if analysis_result.extracted_tags:
        assert hasattr(analysis_result.extracted_tags, "tags")
        assert isinstance(analysis_result.extracted_tags.tags, list)


@pytest.mark.asyncio
async def test_analyze_filtered_posts(db_session: AsyncSession, posts):
    """Test analysis of filtered posts"""
    analyzer = PostsAnalyzer(batch_size=2, max_workers=2)

    filters = PostFilterParams(limit=10, offset=0)
    results, metadata = await analyzer.analyze_filtered_posts(
        db_session,
        filters,
        analysis_types=["word_frequency", "text_stats"],
        save_results=True,
    )

    assert isinstance(results, list)
    assert len(results) > 0
    assert isinstance(metadata, dict)
    assert "total_posts" in metadata
    assert "processed_posts" in metadata
    assert "analysis_types" in metadata

    for result in results:
        assert "post_id" in result
        assert "analyses" in result
        assert "word_frequency" in result["analyses"]
        assert "text_stats" in result["analyses"]


@pytest.mark.asyncio
async def test_analyze_filtered_posts_with_category_filter(
    db_session: AsyncSession, posts, categories
):
    """Test analysis of posts with category filter"""
    analyzer = PostsAnalyzer(batch_size=2, max_workers=2)

    category = categories[0]
    filters = PostFilterParams(limit=10, offset=0, category_id=category.id)

    results, metadata = await analyzer.analyze_filtered_posts(
        db_session, filters, analysis_types=["word_frequency"], save_results=True
    )

    assert isinstance(results, list)
    assert isinstance(metadata, dict)

    for result in results:
        post = next((p for p in posts if p.id == result["post_id"]), None)
        assert post is not None
        assert post.category_id == category.id

        assert "analyses" in result
        assert "word_frequency" in result["analyses"]


@pytest.mark.asyncio
async def test_analyze_filtered_posts_with_search_filter(
    db_session: AsyncSession, posts
):
    """Test analysis of posts with search query filter"""
    analyzer = PostsAnalyzer(batch_size=2, max_workers=2)

    search_term = "технологии"

    filters = PostFilterParams(
        limit=10, offset=0, search_query=search_term, use_fulltext=False
    )
    results, metadata = await analyzer.analyze_filtered_posts(
        db_session, filters, analysis_types=["tags"], save_results=True
    )

    assert isinstance(results, list)
    assert isinstance(metadata, dict)

    for result in results:
        post = next((p for p in posts if p.id == result["post_id"]), None)
        assert post is not None
        assert search_term.lower() in post.content.lower() or (
            post.title and search_term.lower() in post.title.lower()
        )

        assert "analyses" in result
        assert "tags" in result["analyses"]
