"""Tests for data models"""

import pytest
from datetime import datetime, timezone, timedelta

from yougen.storage.models import Tweet, Comment, Author, Influencer


class TestAuthor:
    def test_author_creation(self, sample_author):
        assert sample_author.username == "testuser"
        assert sample_author.user_id == "123456789"
        assert sample_author.name == "Test User"

    def test_author_to_dict(self, sample_author):
        data = sample_author.to_dict()
        assert data["username"] == "testuser"
        assert data["user_id"] == "123456789"

    def test_author_from_dict(self):
        data = {"username": "user1", "user_id": "111", "name": "User One"}
        author = Author.from_dict(data)
        assert author.username == "user1"


class TestTweet:
    def test_tweet_creation(self, sample_tweet):
        assert sample_tweet.id == "1234567890"
        assert sample_tweet.author.username == "testuser"
        assert sample_tweet.like_count == 100

    def test_tweet_age_minutes(self, sample_author):
        # Create tweet 10 minutes ago
        past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        tweet = Tweet(
            id="123",
            author=sample_author,
            text="test",
            created_at=past_time,
            like_count=0,
            retweet_count=0,
            reply_count=0,
            conversation_id="123"
        )
        age = tweet.age_minutes()
        assert 9 < age < 11  # Should be around 10 minutes

    def test_tweet_from_bird_json(self, mock_bird_json):
        tweet = Tweet.from_bird_json(mock_bird_json)
        assert tweet.id == "1234567890"
        assert tweet.author.username == "testuser"
        assert tweet.like_count == 100

    def test_tweet_to_dict_and_back(self, sample_tweet):
        data = sample_tweet.to_dict()
        reconstructed = Tweet.from_dict(data)
        assert reconstructed.id == sample_tweet.id
        assert reconstructed.text == sample_tweet.text


class TestComment:
    def test_comment_creation(self, sample_comment):
        assert sample_comment.id == "comment-123"
        assert sample_comment.status == "pending"
        assert sample_comment.content == "Great insights! 👍"

    def test_comment_to_dict_and_back(self, sample_comment):
        data = sample_comment.to_dict()
        reconstructed = Comment.from_dict(data)
        assert reconstructed.id == sample_comment.id
        assert reconstructed.content == sample_comment.content


class TestInfluencer:
    def test_influencer_creation(self, sample_influencer):
        assert sample_influencer.username == "influencer1"
        assert sample_influencer.priority == "high"
        assert "AI" in sample_influencer.topics

    def test_influencer_to_dict_and_back(self, sample_influencer):
        data = sample_influencer.to_dict()
        reconstructed = Influencer.from_dict(data)
        assert reconstructed.username == sample_influencer.username
        assert reconstructed.topics == sample_influencer.topics
