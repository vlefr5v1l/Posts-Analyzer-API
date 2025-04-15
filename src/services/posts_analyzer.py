import asyncio
import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logger import get_logger
from src.db.crud.posts import (
    get_filtered_posts,
    create_post_analysis,
    get_post,
    get_latest_post_analysis,
)
from src.db.models.posts import Post
from src.schemas.posts import (
    PostFilterParams,
    PostAnalysisCreate,
    PostAnalysisResult,
    WordFrequency,
    TextStats,
    ExtractedTags,
)

logger = get_logger(__name__)

# Download NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('punkt_tab')


class PostsAnalyzer:
    """Service for analyzing post content"""

    def __init__(self, batch_size: int = None, max_workers: int = None):
        """
        Initialize the analyzer with configuration

        Args:
            batch_size: Number of posts to process in a batch
            max_workers: Maximum number of concurrent workers
        """
        self.batch_size = batch_size or settings.BATCH_SIZE
        self.max_workers = max_workers or settings.MAX_WORKERS
        self.russian_stopwords = set(stopwords.words('russian'))
        self.english_stopwords = set(stopwords.words('english'))
        self.all_stopwords = self.russian_stopwords.union(self.english_stopwords)

    async def analyze_filtered_posts(
            self,
            db: AsyncSession,
            filters: PostFilterParams,
            analysis_types: List[str] = None,
            save_results: bool = True,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Analyze posts based on filter criteria

        Args:
            db: Database session
            filters: Filter parameters
            analysis_types: Types of analysis to perform
            save_results: Whether to save analysis results to database

        Returns:
            Tuple containing list of post analyses and metadata
        """
        if not analysis_types:
            analysis_types = ["word_frequency", "text_stats", "tags"]

        # Get posts with pagination
        posts, total_count = await get_filtered_posts(db, filters)

        # Process posts in batches
        results = []
        metadata = {
            "total_posts": total_count,
            "processed_posts": len(posts),
            "analysis_types": analysis_types,
        }

        # Use semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_post(post: Post) -> Dict[str, Any]:
            async with semaphore:
                return await self._analyze_post(db, post, analysis_types, save_results)

        # Process posts concurrently with controlled concurrency
        tasks = [process_post(post) for post in posts]
        results = await asyncio.gather(*tasks)

        return results, metadata

    async def _analyze_post(
            self,
            db: AsyncSession,
            post: Post,
            analysis_types: List[str],
            save_results: bool,
    ) -> Dict[str, Any]:
        """
        Analyze a single post with specified analysis types

        Args:
            db: Database session
            post: Post to analyze
            analysis_types: Types of analysis to perform
            save_results: Whether to save analysis results to database

        Returns:
            Dict containing post ID and analysis results
        """
        result = {
            "post_id": post.id,
            "analyses": {},
        }

        for analysis_type in analysis_types:
            if analysis_type == "word_frequency":
                analysis_result = self._analyze_word_frequency(post.content)
            elif analysis_type == "text_stats":
                analysis_result = self._analyze_text_stats(post.content)
            elif analysis_type == "tags":
                analysis_result = self._extract_tags(post.content)
            else:
                logger.warning(f"Unknown analysis type: {analysis_type}")
                continue

            result["analyses"][analysis_type] = analysis_result

            # Save to database if requested
            if save_results:
                analysis_data = PostAnalysisCreate(
                    post_id=post.id,
                    analysis_type=analysis_type,
                    result=json.dumps(analysis_result),
                )
                await create_post_analysis(db, analysis_data)

        return result

    def _analyze_word_frequency(self, text: str) -> Dict[str, Any]:
        """
        Analyze word frequency in text

        Args:
            text: Text to analyze

        Returns:
            Dict containing word frequency analysis
        """
        # Clean and tokenize text
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = word_tokenize(clean_text)

        # Remove stopwords
        filtered_words = [word for word in words if word.isalpha() and word not in self.all_stopwords]

        # Count word frequencies
        word_counts = Counter(filtered_words)
        total_words = len(filtered_words)

        # Calculate frequencies
        word_frequencies = [
            {
                "word": word,
                "count": count,
                "frequency": count / total_words if total_words > 0 else 0,
            }
            for word, count in word_counts.most_common(20)
        ]

        return {
            "total_unique_words": len(word_counts),
            "total_words_after_filtering": total_words,
            "word_frequencies": word_frequencies,
        }

    def _analyze_text_stats(self, text: str) -> Dict[str, Any]:
        """
        Analyze text statistics

        Args:
            text: Text to analyze

        Returns:
            Dict containing text statistics
        """
        # Tokenize sentences and words
        sentences = sent_tokenize(text)
        words = word_tokenize(text)

        # Filter out non-alphabetic tokens
        words = [word for word in words if word.isalpha()]

        # Calculate statistics
        word_count = len(words)
        char_count = len(text)
        sentence_count = len(sentences)

        # Avoid division by zero
        avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0

        return {
            "word_count": word_count,
            "char_count": char_count,
            "sentence_count": sentence_count,
            "avg_word_length": round(avg_word_length, 2),
            "avg_sentence_length": round(avg_sentence_length, 2),
        }

    def _extract_tags(self, text: str) -> Dict[str, Any]:
        """
        Extract potential tags from text

        Args:
            text: Text to analyze

        Returns:
            Dict containing extracted tags
        """
        # Clean and tokenize text
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = word_tokenize(clean_text)

        # Remove stopwords
        filtered_words = [word for word in words if word.isalpha() and word not in self.all_stopwords]

        # Count word frequencies
        word_counts = Counter(filtered_words)

        # Extract potential tags (most frequent words)
        tags = [word for word, _ in word_counts.most_common(10)]

        # Also look for hashtags in original text
        hashtags = re.findall(r'#(\w+)', text)

        return {
            "extracted_tags": tags,
            "hashtags": hashtags,
        }

    async def get_post_analysis_result(
            self,
            db: AsyncSession,
            post_id: int,
            run_if_missing: bool = True,
    ) -> Optional[PostAnalysisResult]:
        """
        Get combined analysis result for a post

        Args:
            db: Database session
            post_id: Post ID
            run_if_missing: Whether to run analysis if not found

        Returns:
            Combined analysis result or None if post not found
        """
        post = await get_post(db, post_id)
        if not post:
            return None

        # Try to get existing analyses
        word_freq_analysis = await get_latest_post_analysis(db, post_id, "word_frequency")
        text_stats_analysis = await get_latest_post_analysis(db, post_id, "text_stats")
        tags_analysis = await get_latest_post_analysis(db, post_id, "tags")

        # Check if we need to run analyses
        if run_if_missing and (not word_freq_analysis or not text_stats_analysis or not tags_analysis):
            analysis_types = []
            if not word_freq_analysis:
                analysis_types.append("word_frequency")
            if not text_stats_analysis:
                analysis_types.append("text_stats")
            if not tags_analysis:
                analysis_types.append("tags")

            # Run missing analyses
            await self._analyze_post(db, post, analysis_types, save_results=True)

            # Get updated analyses
            if not word_freq_analysis:
                word_freq_analysis = await get_latest_post_analysis(db, post_id, "word_frequency")
            if not text_stats_analysis:
                text_stats_analysis = await get_latest_post_analysis(db, post_id, "text_stats")
            if not tags_analysis:
                tags_analysis = await get_latest_post_analysis(db, post_id, "tags")

        # Parse results
        result = PostAnalysisResult()

        if word_freq_analysis:
            analysis_data = json.loads(word_freq_analysis.result)
            result.word_frequencies = [
                WordFrequency(**freq) for freq in analysis_data.get("word_frequencies", [])
            ]

        if text_stats_analysis:
            analysis_data = json.loads(text_stats_analysis.result)
            result.text_stats = TextStats(**analysis_data)

        if tags_analysis:
            analysis_data = json.loads(tags_analysis.result)
            result.extracted_tags = ExtractedTags(tags=analysis_data.get("extracted_tags", []))

        # Include raw analysis data
        result.raw_analysis = {}
        if word_freq_analysis:
            result.raw_analysis["word_frequency"] = json.loads(word_freq_analysis.result)
        if text_stats_analysis:
            result.raw_analysis["text_stats"] = json.loads(text_stats_analysis.result)
        if tags_analysis:
            result.raw_analysis["tags"] = json.loads(tags_analysis.result)

        return result


# Singleton instance
posts_analyzer = PostsAnalyzer()