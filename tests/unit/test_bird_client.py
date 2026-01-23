"""Tests for bird CLI client (mocked)"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import json

from yougen.core.bird_client import BirdClient, BirdClientError, BirdRateLimitError


class TestBirdClient:
    def test_client_initialization(self):
        client = BirdClient(delay=1.5)
        assert client.delay == 1.5
        assert client.last_call == 0

    @patch('subprocess.run')
    def test_get_user_tweets_success(self, mock_run, mock_bird_json):
        # Mock subprocess response
        mock_run.return_value = Mock(
            stdout=json.dumps([mock_bird_json]),
            returncode=0
        )

        client = BirdClient(delay=0)  # No delay for tests
        tweets = client.get_user_tweets("testuser", count=1)

        assert len(tweets) == 1
        assert tweets[0].id == "1234567890"
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_get_user_tweets_removes_at_symbol(self, mock_run, mock_bird_json):
        mock_run.return_value = Mock(
            stdout=json.dumps([mock_bird_json]),
            returncode=0
        )

        client = BirdClient(delay=0)
        client.get_user_tweets("@testuser")

        # Verify @symbol was removed in command
        call_args = mock_run.call_args[0][0]
        assert "@testuser" not in call_args
        assert "testuser" in call_args

    @patch('subprocess.run')
    def test_rate_limit_error(self, mock_run):
        # Mock rate limit error
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "bird", stderr="Rate limit exceeded: 429"
        )

        client = BirdClient(delay=0)
        with pytest.raises(BirdRateLimitError):
            client.get_user_tweets("testuser")

    @patch('subprocess.run')
    def test_timeout_error(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("bird", 30)

        client = BirdClient(delay=0)
        with pytest.raises(BirdClientError, match="timed out"):
            client.get_user_tweets("testuser")

    @patch('subprocess.run')
    def test_post_reply_success(self, mock_run):
        mock_run.return_value = Mock(stdout="Success", returncode=0)

        client = BirdClient(delay=0)
        success = client.post_reply("tweet123", "Great post!")

        assert success is True
        call_args = mock_run.call_args[0][0]
        assert "reply" in call_args
        assert "tweet123" in call_args
        assert "Great post!" in call_args

    @patch('subprocess.run')
    def test_post_reply_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "bird", stderr="Failed to post"
        )

        client = BirdClient(delay=0)
        success = client.post_reply("tweet123", "test")

        assert success is False

    @patch('subprocess.run')
    def test_check_auth_success(self, mock_run):
        mock_run.return_value = Mock(
            stdout="🙋 @testuser (Test User)",
            returncode=0
        )

        client = BirdClient(delay=0)
        success, username = client.check_auth()

        assert success is True
        assert username == "testuser"

    @patch('subprocess.run')
    def test_search_tweets(self, mock_run, mock_bird_json):
        mock_run.return_value = Mock(
            stdout=json.dumps([mock_bird_json]),
            returncode=0
        )

        client = BirdClient(delay=0)
        tweets = client.search_tweets("AI", count=1)

        assert len(tweets) == 1
        call_args = mock_run.call_args[0][0]
        assert "search" in call_args
        assert "AI" in call_args

    @patch('subprocess.run')
    def test_get_tweet_by_id(self, mock_run, mock_bird_json):
        mock_run.return_value = Mock(
            stdout=json.dumps(mock_bird_json),
            returncode=0
        )

        client = BirdClient(delay=0)
        tweet = client.get_tweet_by_id("1234567890")

        assert tweet is not None
        assert tweet.id == "1234567890"
