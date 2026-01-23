"""Tests for file storage"""

import pytest
from datetime import datetime, timezone, timedelta

from yougen.storage.file_store import FileStore
from yougen.storage.models import Tweet, Comment, Influencer, Author


class TestFileStore:
    @pytest.fixture
    def store(self, temp_data_dir):
        return FileStore(temp_data_dir)

    def test_store_initialization(self, store, temp_data_dir):
        # Check directories are created
        assert (temp_data_dir / "influencers").exists()
        assert (temp_data_dir / "tweets").exists()
        assert (temp_data_dir / "comments" / "pending").exists()
        assert (temp_data_dir / "comments" / "approved").exists()

    def test_save_and_load_influencers(self, store, sample_influencer):
        influencers = [sample_influencer]
        store.save_influencers(influencers)
        
        loaded = store.load_influencers()
        assert len(loaded) == 1
        assert loaded[0].username == sample_influencer.username

    def test_update_influencer_last_checked(self, store, sample_influencer):
        store.save_influencers([sample_influencer])
        
        # Update last checked
        store.update_influencer_last_checked(sample_influencer.username)
        
        loaded = store.load_influencers()
        assert loaded[0].last_checked is not None

    def test_save_tweet(self, store, sample_tweet):
        store.save_tweet(sample_tweet)
        
        # Verify tweet exists
        assert store.tweet_exists(sample_tweet.id)

    def test_tweet_exists(self, store, sample_tweet):
        # Initially doesn't exist
        assert not store.tweet_exists(sample_tweet.id)
        
        # After saving, should exist
        store.save_tweet(sample_tweet)
        assert store.tweet_exists(sample_tweet.id)

    def test_save_and_load_comment(self, store, sample_comment):
        store.save_comment(sample_comment)
        
        # Load by status
        pending = store.load_comments_by_status('pending')
        assert len(pending) == 1
        assert pending[0].id == sample_comment.id

    def test_load_pending_comments(self, store, sample_comment):
        store.save_comment(sample_comment)
        
        pending = store.load_pending_comments()
        assert len(pending) == 1

    def test_load_comment_by_id(self, store, sample_comment):
        store.save_comment(sample_comment)
        
        loaded = store.load_comment_by_id(sample_comment.id)
        assert loaded is not None
        assert loaded.id == sample_comment.id

    def test_update_comment_status(self, store, sample_comment):
        # Save as pending
        store.save_comment(sample_comment)
        
        # Update to approved
        store.update_comment_status(sample_comment.id, 'approved')
        
        # Verify moved
        pending = store.load_comments_by_status('pending')
        approved = store.load_comments_by_status('approved')
        
        assert len(pending) == 0
        assert len(approved) == 1
        assert approved[0].status == 'approved'

    def test_update_to_published_adds_timestamp(self, store, sample_comment):
        store.save_comment(sample_comment)
        
        # Update to published
        store.update_comment_status(sample_comment.id, 'published')
        
        published = store.load_comments_by_status('published')
        assert len(published) == 1
        assert published[0].published_at is not None

    def test_delete_comment(self, store, sample_comment):
        store.save_comment(sample_comment)
        
        # Verify exists
        assert store.load_comment_by_id(sample_comment.id) is not None
        
        # Delete
        store.delete_comment(sample_comment.id)
        
        # Verify deleted
        assert store.load_comment_by_id(sample_comment.id) is None

    def test_get_recent_commented_authors(self, store):
        author1 = Author("user1", "123", "User 1")
        author2 = Author("user2", "456", "User 2")
        
        tweet1 = Tweet(
            id="1",
            author=author1,
            text="test1",
            created_at=datetime.now(timezone.utc),
            like_count=10,
            retweet_count=5,
            reply_count=2,
            conversation_id="1"
        )
        
        tweet2 = Tweet(
            id="2",
            author=author2,
            text="test2",
            created_at=datetime.now(timezone.utc),
            like_count=10,
            retweet_count=5,
            reply_count=2,
            conversation_id="2"
        )
        
        # Create comments and approve them
        comment1 = Comment(
            id="c1",
            tweet_id=tweet1.id,
            content="comment1",
            generated_at=datetime.now(timezone.utc),
            status="approved",
            tweet_author=author1.user_id
        )
        
        comment2 = Comment(
            id="c2",
            tweet_id=tweet2.id,
            content="comment2",
            generated_at=datetime.now(timezone.utc) - timedelta(hours=48),  # Old
            status="approved",
            tweet_author=author2.user_id
        )
        
        store.save_comment(comment1)
        store.save_comment(comment2)
        
        # Get recent authors (24 hours)
        recent = store.get_recent_commented_authors(hours=24)
        
        # Only author1 should be recent
        assert author1.user_id in recent
        assert author2.user_id not in recent

    def test_get_comment_stats(self, store, sample_comment):
        # Create comments with different statuses
        comment1 = Comment(
            id="c1",
            tweet_id="t1",
            content="test1",
            generated_at=datetime.now(timezone.utc),
            status="pending"
        )
        comment2 = Comment(
            id="c2",
            tweet_id="t2",
            content="test2",
            generated_at=datetime.now(timezone.utc),
            status="approved"
        )
        comment3 = Comment(
            id="c3",
            tweet_id="t3",
            content="test3",
            generated_at=datetime.now(timezone.utc),
            status="published",
            published_at=datetime.now(timezone.utc)
        )
        
        store.save_comment(comment1)
        store.save_comment(comment2)
        store.save_comment(comment3)
        
        stats = store.get_comment_stats()
        
        assert stats['pending'] == 1
        assert stats['approved'] == 1
        assert stats['published'] == 1
        assert stats['rejected'] == 0

    def test_get_recent_published_count(self, store):
        # Create old and new published comments
        old_comment = Comment(
            id="c1",
            tweet_id="t1",
            content="old",
            generated_at=datetime.now(timezone.utc) - timedelta(hours=48),
            status="published",
            published_at=datetime.now(timezone.utc) - timedelta(hours=48)
        )
        
        new_comment = Comment(
            id="c2",
            tweet_id="t2",
            content="new",
            generated_at=datetime.now(timezone.utc),
            status="published",
            published_at=datetime.now(timezone.utc) - timedelta(minutes=30)
        )
        
        store.save_comment(old_comment)
        store.save_comment(new_comment)
        
        # Count last 1 hour
        count_1h = store.get_recent_published_count(hours=1)
        assert count_1h == 1
        
        # Count last 24 hours
        count_24h = store.get_recent_published_count(hours=24)
        assert count_24h == 1
        
        # Count last 72 hours
        count_72h = store.get_recent_published_count(hours=72)
        assert count_72h == 2

    def test_empty_loads(self, store):
        # Test loading from empty store
        assert store.load_influencers() == []
        assert store.load_pending_comments() == []
        assert store.load_comment_by_id("nonexistent") is None
