"""质量过滤器单元测试"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from yougen.core.quality_filter import TweetQualityFilter, QualityFilterResult
from yougen.storage.models import Tweet, Author


@pytest.fixture
def filter_config():
    """默认过滤器配置"""
    return {
        'enabled': True,
        'rules': {
            'min_text_length': 20,
            'filter_media_only': True,
            'filter_reply_without_context': True,
            'filter_external_references': True
        },
        'ai_analysis': {
            'enabled': False,  # 默认禁用AI以加快测试
            'min_quality_score': 60.0,
            'batch_size': 5,
            'max_concurrent': 3,
            'model': 'claude-sonnet-4-5-20250929',
            'timeout_seconds': 30,
            'on_failure': 'pass'
        }
    }


@pytest.fixture
def quality_filter(filter_config):
    """创建过滤器实例"""
    return TweetQualityFilter(filter_config)


@pytest.fixture
def sample_author():
    """示例作者"""
    return Author(
        username='testuser',
        user_id='123456',
        name='Test User',
        followers=1000
    )


def create_tweet(
    text: str,
    author: Author,
    is_reply: bool = False,
    has_quoted_content: bool = False,
    media: list = None,
    urls: list = None
) -> Tweet:
    """创建测试推文"""
    return Tweet(
        id='1234567890',
        author=author,
        text=text,
        created_at=datetime.now(timezone.utc),
        like_count=10,
        retweet_count=5,
        reply_count=2,
        conversation_id='conv123',
        is_reply=is_reply,
        has_quoted_content=has_quoted_content,
        media=media or [],
        urls=urls or []
    )


class TestMediaOnlyFilter:
    """测试仅媒体过滤规则"""

    def test_filter_media_only_tweet(self, quality_filter, sample_author):
        """测试过滤仅包含媒体的推文"""
        tweet = create_tweet(
            text="Nice! 👍",
            author=sample_author,
            media=[{'type': 'photo', 'url': 'http://example.com/photo.jpg'}]
        )

        result = quality_filter._check_rules(tweet)
        assert not result.passed
        assert 'media_only' in result.issues

    def test_allow_media_with_text(self, quality_filter, sample_author):
        """测试允许有足够文本的媒体推文"""
        tweet = create_tweet(
            text="This is a very detailed and comprehensive explanation of what's happening in this amazing photo and exactly why it matters so much to everyone involved in this discussion.",
            author=sample_author,
            media=[{'type': 'photo', 'url': 'http://example.com/photo.jpg'}]
        )

        result = quality_filter._check_rules(tweet)
        assert result.passed


class TestReplyFilter:
    """测试回复过滤规则"""

    def test_filter_reply_without_context(self, quality_filter, sample_author):
        """测试过滤无上下文的回复"""
        tweet = create_tweet(
            text="Agree!",
            author=sample_author,
            is_reply=True,
            has_quoted_content=False
        )

        result = quality_filter._check_rules(tweet)
        assert not result.passed
        assert 'reply_without_context' in result.issues

    def test_allow_reply_with_quote(self, quality_filter, sample_author):
        """测试允许有引用的回复"""
        tweet = create_tweet(
            text="I completely agree with this very important point about the future of AI development and its significant impact on our society today!",
            author=sample_author,
            is_reply=True,
            has_quoted_content=True
        )

        result = quality_filter._check_rules(tweet)
        assert result.passed

    def test_allow_reply_with_clear_context(self, quality_filter, sample_author):
        """测试允许有清晰上下文的回复"""
        tweet = create_tweet(
            text="I think this innovative approach makes a lot of sense because it addresses the core fundamental issue very effectively with practical solutions.",
            author=sample_author,
            is_reply=True,
            has_quoted_content=False
        )

        result = quality_filter._check_rules(tweet)
        assert result.passed


class TestLengthFilter:
    """测试长度过滤规则"""

    def test_filter_too_short_chinese(self, quality_filter, sample_author):
        """测试过滤过短的中文推文"""
        tweet = create_tweet(
            text="太棒了！",
            author=sample_author
        )

        result = quality_filter._check_rules(tweet)
        assert not result.passed
        assert 'too_short' in result.issues

    def test_allow_long_chinese(self, quality_filter, sample_author):
        """测试允许足够长的中文推文"""
        tweet = create_tweet(
            text="这是一个非常详细的推文，包含了足够的信息和上下文，让读者能够理解发生了什么。",
            author=sample_author
        )

        result = quality_filter._check_rules(tweet)
        assert result.passed

    def test_filter_too_short_english(self, quality_filter, sample_author):
        """测试过滤过短的英文推文"""
        tweet = create_tweet(
            text="Great stuff!",
            author=sample_author
        )

        result = quality_filter._check_rules(tweet)
        assert not result.passed
        assert 'too_short' in result.issues

    def test_allow_long_english(self, quality_filter, sample_author):
        """测试允许足够长的英文推文"""
        tweet = create_tweet(
            text="This is a comprehensive tweet that contains enough information and context for readers to understand what is happening and why it matters.",
            author=sample_author
        )

        result = quality_filter._check_rules(tweet)
        assert result.passed


class TestVagueReferenceFilter:
    """测试模糊引用过滤规则"""

    def test_filter_vague_chinese_reference(self, quality_filter, sample_author):
        """测试过滤模糊的中文引用"""
        # 需要足够长但仍然模糊
        tweet = create_tweet(
            text="这个真棒啊真是太棒了",  # 短于20字，会被长度过滤
            author=sample_author
        )

        result = quality_filter._check_rules(tweet)
        assert not result.passed
        # 因为太短，所以会被长度过滤，而不是模糊引用过滤
        assert 'too_short' in result.issues

    def test_filter_vague_english_reference(self, quality_filter, sample_author):
        """测试过滤模糊的英文引用"""
        tweet = create_tweet(
            text="This is so good wow amazing",  # 短于20词
            author=sample_author
        )

        result = quality_filter._check_rules(tweet)
        assert not result.passed
        # 因为太短，所以会被长度过滤
        assert 'too_short' in result.issues

    def test_allow_clear_reference(self, quality_filter, sample_author):
        """测试允许清晰的表达"""
        tweet = create_tweet(
            text="The new AI model announced today shows impressive performance on complex reasoning tasks and demonstrates significant improvements over previous versions.",
            author=sample_author
        )

        result = quality_filter._check_rules(tweet)
        assert result.passed


class TestChineseEnglishMixed:
    """测试中英文混合内容"""

    def test_mixed_content(self, quality_filter, sample_author):
        """测试中英文混合内容"""
        tweet = create_tweet(
            text="The new Claude AI 4.5 真的太强了，在各种复杂任务上的performance提升非常明显，特别是reasoning能力！",
            author=sample_author
        )

        result = quality_filter._check_rules(tweet)
        # 应该通过，因为内容足够长且有实质信息
        assert result.passed


class TestBatchFiltering:
    """测试批量过滤"""

    def test_filter_batch_multiple_tweets(self, quality_filter, sample_author):
        """测试批量过滤多条推文"""
        tweets = [
            create_tweet("This is a really good and comprehensive tweet with enough context and detailed information to be very valuable for readers.", sample_author),
            create_tweet("Nice!", sample_author),  # 太短
            create_tweet("这个真不错", sample_author),  # 太短
            create_tweet("这是一个包含足够详细信息和完整上下文的优质推文，能让读者充分理解发生了什么事情以及为什么重要。", sample_author),
        ]

        passed, filtered = quality_filter.filter_batch(tweets)

        assert len(passed) == 2
        assert len(filtered) == 2


class TestAIAnalysis:
    """测试AI分析功能"""

    @pytest.mark.asyncio
    async def test_ai_analysis_high_quality(self, filter_config, sample_author):
        """测试AI分析高质量推文"""
        filter_config['ai_analysis']['enabled'] = True
        quality_filter = TweetQualityFilter(filter_config)

        tweet = create_tweet(
            text="The latest developments in AI technology show promising results for real-world applications.",
            author=sample_author
        )

        # Mock AI response
        with patch('yougen.core.quality_filter.query', return_value='{"score": 85, "issues": [], "analysis": "High quality content"}'):
            result = await quality_filter._analyze_tweet_quality(tweet)
            assert result.passed
            assert result.score == 85.0

    @pytest.mark.asyncio
    async def test_ai_analysis_low_quality(self, filter_config, sample_author):
        """测试AI分析低质量推文"""
        filter_config['ai_analysis']['enabled'] = True
        quality_filter = TweetQualityFilter(filter_config)

        tweet = create_tweet(
            text="Wow!",
            author=sample_author
        )

        # Mock AI response
        with patch('yougen.core.quality_filter.query', return_value='{"score": 25, "issues": ["low_information"], "analysis": "Too vague"}'):
            result = await quality_filter._analyze_tweet_quality(tweet)
            assert not result.passed
            assert result.score == 25.0
            assert 'low_information' in result.issues

    @pytest.mark.asyncio
    async def test_ai_failure_handling_pass(self, filter_config, sample_author):
        """测试AI失败时通过"""
        filter_config['ai_analysis']['enabled'] = True
        filter_config['ai_analysis']['on_failure'] = 'pass'
        quality_filter = TweetQualityFilter(filter_config)

        tweet = create_tweet(
            text="Some tweet content",
            author=sample_author
        )

        # Mock AI error
        with patch('yougen.core.quality_filter.query', side_effect=Exception("API Error")):
            result = await quality_filter._analyze_tweet_quality(tweet)
            assert result.passed

    @pytest.mark.asyncio
    async def test_ai_failure_handling_filter(self, filter_config, sample_author):
        """测试AI失败时过滤"""
        filter_config['ai_analysis']['enabled'] = True
        filter_config['ai_analysis']['on_failure'] = 'filter'
        quality_filter = TweetQualityFilter(filter_config)

        tweet = create_tweet(
            text="Some tweet content",
            author=sample_author
        )

        # Mock AI error
        with patch('yougen.core.quality_filter.query', side_effect=Exception("API Error")):
            result = await quality_filter._analyze_tweet_quality(tweet)
            assert not result.passed


class TestHelperMethods:
    """测试辅助方法"""

    def test_remove_urls_from_text(self, quality_filter):
        """测试URL移除"""
        text = "Check this out https://example.com/article and http://another.com"
        clean = quality_filter._remove_urls_from_text(text)
        assert 'https://' not in clean
        assert 'http://' not in clean

    def test_is_chinese_text(self, quality_filter):
        """测试中文检测"""
        assert quality_filter._is_chinese_text("这是中文文本")
        assert quality_filter._is_chinese_text("这是 mixed 文本")
        assert not quality_filter._is_chinese_text("This is English text")

    def test_has_clear_context(self, quality_filter):
        """测试上下文检测"""
        # 长文本有上下文
        assert quality_filter._has_clear_context("This is a sufficiently long text with clear context")

        # 包含观点词
        assert quality_filter._has_clear_context("I think this is good")

        # 包含具体信息
        assert quality_filter._has_clear_context('He said "hello" yesterday')

        # 短且模糊
        assert not quality_filter._has_clear_context("Great!")

    def test_has_unclear_external_reference(self, quality_filter):
        """测试模糊引用检测"""
        # 中文模糊引用
        assert quality_filter._has_unclear_external_reference("这个真不错")
        assert quality_filter._has_unclear_external_reference("那个太棒了")

        # 英文模糊引用
        assert quality_filter._has_unclear_external_reference("This is so good")
        assert quality_filter._has_unclear_external_reference("That is very nice")

        # 清晰表达
        assert not quality_filter._has_unclear_external_reference("The new product launch was successful")
