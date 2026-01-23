"""Pytest configuration and shared fixtures"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

from yougen.storage.models import Tweet, Comment, Author, Influencer


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_author():
    """Sample author data"""
    return Author(
        username="testuser",
        user_id="123456789",
        name="Test User",
        followers=10000
    )


@pytest.fixture
def sample_tweet(sample_author):
    """Sample tweet data"""
    return Tweet(
        id="1234567890",
        author=sample_author,
        text="This is a test tweet about AI and technology",
        created_at=datetime.now(timezone.utc),
        like_count=100,
        retweet_count=50,
        reply_count=25,
        conversation_id="1234567890",
        trending_score=0.0
    )


@pytest.fixture
def sample_comment(sample_tweet):
    """Sample comment data"""
    return Comment(
        id="comment-123",
        tweet_id=sample_tweet.id,
        content="Great insights! 👍",
        generated_at=datetime.now(timezone.utc),
        status="pending",
        session_id="session-123",
        tweet_author=sample_tweet.author.user_id
    )


@pytest.fixture
def sample_influencer():
    """Sample influencer data"""
    return Influencer(
        username="influencer1",
        user_id="987654321",
        priority="high",
        check_interval=15,
        topics=["AI", "Tech"],
        notes="Top AI researcher"
    )


@pytest.fixture
def mock_bird_json():
    """Mock bird CLI JSON response"""
    return {
        "id": "1234567890",
        "authorId": "123456789",
        "author": {
            "username": "testuser",
            "name": "Test User"
        },
        "text": "This is a test tweet",
        "createdAt": "Mon Jan 20 10:00:00 +0000 2026",
        "likeCount": 100,
        "retweetCount": 50,
        "replyCount": 25,
        "conversationId": "1234567890"
    }


@pytest.fixture
def user_profile_config():
    """Sample user profile configuration"""
    return {
        "profile": {
            "expertise": ["AI", "Tech"],
            "tone": "幽默、专业",
            "keywords": ["AI", "机器学习"],
            "avoid_keywords": ["政治"]
        },
        "examples": [
            {
                "tweet": "AI is the future",
                "comment": "确实，未来已来！"
            }
        ],
        "agent": {
            "model": "claude-opus-4-5-20251101"
        }
    }
