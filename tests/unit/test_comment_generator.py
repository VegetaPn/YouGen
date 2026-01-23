"""Tests for comment generator (mocked)"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from yougen.core.comment_generator import CommentGenerator
from yougen.storage.models import Tweet, Comment, Author


class TestCommentGenerator:
    @pytest.fixture
    def generator(self, user_profile_config):
        return CommentGenerator(user_profile_config)

    def test_generator_initialization(self, generator, user_profile_config):
        assert generator.user_profile == user_profile_config
        assert "你是X (Twitter)评论助手" in generator.system_prompt

    def test_build_system_prompt(self, generator):
        prompt = generator.system_prompt
        
        # Check that user profile is included
        assert "AI" in prompt
        assert "Tech" in prompt
        assert "评论风格示例" in prompt

    @pytest.mark.asyncio
    @patch('argo.growth.core.comment_generator.query')
    async def test_generate_comment(self, mock_query, generator, sample_tweet):
        # Mock Agent SDK response
        mock_message = Mock()
        mock_message.session_id = "session-123"
        mock_message.result = "这是一条测试评论"
        
        async def mock_query_gen(*args, **kwargs):
            yield mock_message
        
        mock_query.return_value = mock_query_gen()
        
        comment = await generator.generate(sample_tweet)
        
        assert isinstance(comment, Comment)
        assert comment.tweet_id == sample_tweet.id
        assert comment.content == "这是一条测试评论"
        assert comment.session_id == "session-123"
        assert comment.status == "pending"
        assert comment.tweet_author == sample_tweet.author.user_id

    @pytest.mark.asyncio
    @patch('argo.growth.core.comment_generator.query')
    async def test_generate_cleans_content(self, mock_query, generator, sample_tweet):
        # Mock response with prefix
        mock_message = Mock()
        mock_message.session_id = "session-123"
        mock_message.result = "评论：这是测试"
        
        async def mock_query_gen(*args, **kwargs):
            yield mock_message
        
        mock_query.return_value = mock_query_gen()
        
        comment = await generator.generate(sample_tweet)
        
        # Prefix should be removed
        assert comment.content == "这是测试"

    @pytest.mark.asyncio
    @patch('argo.growth.core.comment_generator.query')
    async def test_refine_comment(self, mock_query, generator, sample_comment):
        # Mock refined response
        mock_message = Mock()
        mock_message.result = "这是优化后的评论"
        
        async def mock_query_gen(*args, **kwargs):
            yield mock_message
        
        mock_query.return_value = mock_query_gen()
        
        refined = await generator.refine(sample_comment, "更幽默一点")
        
        assert isinstance(refined, Comment)
        assert refined.content == "这是优化后的评论"
        assert refined.tweet_id == sample_comment.tweet_id
        assert refined.session_id == sample_comment.session_id

    @pytest.mark.asyncio
    async def test_refine_without_session_id(self, generator):
        comment = Comment(
            id="123",
            tweet_id="456",
            content="test",
            generated_at=datetime.now(timezone.utc),
            status="pending",
            session_id=None
        )
        
        with pytest.raises(ValueError, match="no session_id"):
            await generator.refine(comment, "feedback")

    def test_clean_content_removes_prefixes(self, generator):
        test_cases = [
            ("评论：测试", "测试"),
            ("评论:测试", "测试"),
            ("Comment:测试", "测试"),
            ("回复：测试", "测试"),
            ("**评论：**测试", "测试"),
            ('"测试"', "测试"),
        ]
        
        for input_text, expected in test_cases:
            result = generator._clean_content(input_text)
            assert result == expected, f"Failed for input: {input_text}"

    @pytest.mark.asyncio
    @patch('argo.growth.core.comment_generator.query')
    async def test_generate_batch(self, mock_query, generator, sample_tweet):
        # Mock responses
        mock_message = Mock()
        mock_message.session_id = "session"
        mock_message.result = "测试评论"
        
        async def mock_query_gen(*args, **kwargs):
            yield mock_message
        
        mock_query.return_value = mock_query_gen()
        
        tweets = [sample_tweet, sample_tweet, sample_tweet]
        comments = await generator.generate_batch(tweets, max_concurrent=2)
        
        assert len(comments) == 3
        for comment in comments:
            assert isinstance(comment, Comment)

    @pytest.mark.asyncio
    @patch('argo.growth.core.comment_generator.query')
    async def test_generate_handles_errors(self, mock_query, generator, sample_tweet):
        # Mock error
        async def mock_query_gen(*args, **kwargs):
            raise Exception("API error")
        
        mock_query.return_value = mock_query_gen()
        
        with pytest.raises(Exception, match="Failed to generate comment"):
            await generator.generate(sample_tweet)
