"""Tests for tweet collector"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

from yougen.core.tweet_collector import TweetCollector
from yougen.core.bird_client import BirdClient, BirdClientError
from yougen.storage.file_store import FileStore
from yougen.storage.models import Tweet, Author, Influencer


class TestTweetCollector:
    @pytest.fixture
    def mock_bird_client(self):
        return Mock(spec=BirdClient)

    @pytest.fixture
    def mock_file_store(self, temp_data_dir):
        return FileStore(temp_data_dir)

    @pytest.fixture
    def collector(self, mock_bird_client, mock_file_store):
        return TweetCollector(mock_bird_client, mock_file_store)

    def test_collect_from_influencers_success(self, collector, mock_bird_client, sample_influencer):
        # Mock bird client to return tweets
        author = Author("testuser", "123", "Test User")
        tweet = Tweet(
            id="1",
            author=author,
            text="test tweet",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            like_count=10,
            retweet_count=5,
            reply_count=2,
            conversation_id="1"
        )
        mock_bird_client.get_user_tweets.return_value = [tweet]

        influencers = [sample_influencer]
        tweets = collector.collect_from_influencers(influencers, max_age_minutes=30)

        assert len(tweets) == 1
        assert tweets[0].id == "1"
        mock_bird_client.get_user_tweets.assert_called_once()

    def test_collect_filters_old_tweets(self, collector, mock_bird_client, sample_influencer):
        # Create old tweet
        author = Author("testuser", "123", "Test User")
        old_tweet = Tweet(
            id="1",
            author=author,
            text="old tweet",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            like_count=10,
            retweet_count=5,
            reply_count=2,
            conversation_id="1"
        )
        mock_bird_client.get_user_tweets.return_value = [old_tweet]

        tweets = collector.collect_from_influencers([sample_influencer], max_age_minutes=30)

        # Old tweet should be filtered out
        assert len(tweets) == 0

    def test_collect_handles_bird_error(self, collector, mock_bird_client, sample_influencer):
        # Mock bird client error
        mock_bird_client.get_user_tweets.side_effect = BirdClientError("API error")

        # Should not raise, but continue
        tweets = collector.collect_from_influencers([sample_influencer], max_age_minutes=30)
        assert len(tweets) == 0

    def test_filter_by_age(self, collector):
        author = Author("user1", "123", "User 1")
        
        # Recent tweet
        recent = Tweet(
            id="1",
            author=author,
            text="recent",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            like_count=10,
            retweet_count=5,
            reply_count=2,
            conversation_id="1"
        )
        
        # Old tweet
        old = Tweet(
            id="2",
            author=author,
            text="old",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            like_count=10,
            retweet_count=5,
            reply_count=2,
            conversation_id="2"
        )
        
        filtered = collector._filter_by_age([recent, old], max_age_minutes=30)
        assert len(filtered) == 1
        assert filtered[0].id == "1"

    def test_filter_processed_tweets(self, collector, mock_file_store):
        author = Author("user1", "123", "User 1")
        tweet1 = Tweet(
            id="1",
            author=author,
            text="tweet1",
            created_at=datetime.now(timezone.utc),
            like_count=10,
            retweet_count=5,
            reply_count=2,
            conversation_id="1"
        )
        
        # Save tweet1 to store (mark as processed)
        mock_file_store.save_tweet(tweet1)
        
        tweet2 = Tweet(
            id="2",
            author=author,
            text="tweet2",
            created_at=datetime.now(timezone.utc),
            like_count=10,
            retweet_count=5,
            reply_count=2,
            conversation_id="2"
        )
        
        # Filter should remove tweet1
        filtered = collector._filter_processed([tweet1, tweet2])
        assert len(filtered) == 1
        assert filtered[0].id == "2"
