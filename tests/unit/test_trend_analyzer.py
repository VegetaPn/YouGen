"""Tests for trend analyzer"""

import pytest
from datetime import datetime, timezone, timedelta

from yougen.core.trend_analyzer import TrendAnalyzer
from yougen.storage.models import Tweet, Author


class TestTrendAnalyzer:
    def test_analyzer_initialization(self):
        analyzer = TrendAnalyzer(
            like_weight=1.0,
            retweet_weight=2.0,
            reply_weight=1.5
        )
        assert analyzer.like_weight == 1.0
        assert analyzer.retweet_weight == 2.0
        assert analyzer.reply_weight == 1.5

    def test_calculate_score_new_tweet(self):
        """Test score for a brand new highly engaging tweet"""
        analyzer = TrendAnalyzer()
        
        # Create a tweet from 1 minute ago with high engagement
        author = Author("user1", "123", "User 1")
        tweet = Tweet(
            id="1",
            author=author,
            text="test",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            like_count=100,
            retweet_count=50,
            reply_count=30,
            conversation_id="1"
        )
        
        score = analyzer.calculate_score(tweet)
        
        # Weighted engagement = 100*1 + 50*2 + 30*1.5 = 245
        # Per minute = 245/1 = 245
        # Score = min(245/5 * 50, 100) = 100 (capped)
        assert score == 100.0

    def test_calculate_score_older_tweet(self):
        """Test score for an older tweet"""
        analyzer = TrendAnalyzer()
        
        author = Author("user1", "123", "User 1")
        tweet = Tweet(
            id="1",
            author=author,
            text="test",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=60),
            like_count=100,
            retweet_count=50,
            reply_count=30,
            conversation_id="1"
        )
        
        score = analyzer.calculate_score(tweet)
        
        # Weighted engagement = 245
        # Per minute = 245/60 = 4.08
        # Score = 4.08/5 * 50 = 40.8
        assert 40 < score < 42

    def test_rank_tweets_basic(self):
        """Test basic ranking"""
        analyzer = TrendAnalyzer()
        author = Author("user1", "123", "User 1")
        
        # Create tweets with different scores
        tweets = []
        for i in range(5):
            tweet = Tweet(
                id=str(i),
                author=author,
                text=f"tweet {i}",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                like_count=100 * (i + 1),  # Increasing engagement
                retweet_count=50 * (i + 1),
                reply_count=25 * (i + 1),
                conversation_id=str(i)
            )
            tweets.append(tweet)
        
        ranked = analyzer.rank_tweets(tweets, min_score=0, min_tweets=0)
        
        # Should be sorted by score (descending)
        assert len(ranked) == 5
        for i in range(len(ranked) - 1):
            assert ranked[i].trending_score >= ranked[i + 1].trending_score

    def test_rank_tweets_min_score_filter(self):
        """Test minimum score filtering"""
        analyzer = TrendAnalyzer()
        author = Author("user1", "123", "User 1")
        
        tweets = []
        for i in range(5):
            # Old tweets with low engagement
            tweet = Tweet(
                id=str(i),
                author=author,
                text=f"tweet {i}",
                created_at=datetime.now(timezone.utc) - timedelta(hours=2),
                like_count=10,
                retweet_count=5,
                reply_count=2,
                conversation_id=str(i)
            )
            tweets.append(tweet)
        
        # With high min_score, should get protection logic
        ranked = analyzer.rank_tweets(tweets, min_score=80, min_tweets=3)
        
        # Protection logic should ensure at least 3 tweets
        assert len(ranked) >= 3

    def test_rank_tweets_protection_logic(self):
        """Test that protection logic works"""
        analyzer = TrendAnalyzer()
        author = Author("user1", "123", "User 1")
        
        # Create low-scoring tweets
        tweets = []
        for i in range(10):
            tweet = Tweet(
                id=str(i),
                author=author,
                text=f"tweet {i}",
                created_at=datetime.now(timezone.utc) - timedelta(hours=10),
                like_count=1,
                retweet_count=0,
                reply_count=0,
                conversation_id=str(i)
            )
            tweets.append(tweet)
        
        # With high threshold, should still get min_tweets
        ranked = analyzer.rank_tweets(tweets, min_score=90, min_tweets=5)
        assert len(ranked) == 5

    def test_analyze_tweet(self):
        """Test single tweet analysis"""
        analyzer = TrendAnalyzer()
        author = Author("user1", "123", "User 1")
        
        tweet = Tweet(
            id="1",
            author=author,
            text="test",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            like_count=50,
            retweet_count=25,
            reply_count=10,
            conversation_id="1"
        )
        
        analysis = analyzer.analyze_tweet(tweet)
        
        assert analysis['tweet_id'] == "1"
        assert 'trending_score' in analysis
        assert 'age_minutes' in analysis
        assert analysis['engagement']['likes'] == 50
        assert analysis['engagement']['total'] == 85
        assert 'engagement_rate' in analysis

    def test_empty_tweets_list(self):
        """Test with empty list"""
        analyzer = TrendAnalyzer()
        ranked = analyzer.rank_tweets([], min_score=40, min_tweets=3)
        assert ranked == []
