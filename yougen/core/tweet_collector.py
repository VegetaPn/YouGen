"""推文收集器"""

from typing import List, Optional
from datetime import datetime, timezone, timedelta
from yougen.core.bird_client import BirdClient, BirdClientError
from yougen.storage.models import Tweet, Influencer
from yougen.storage.file_store import FileStore


class TweetCollector:
    """推文收集器"""

    def __init__(
        self,
        bird_client: BirdClient,
        file_store: FileStore,
        quality_filter: Optional['TweetQualityFilter'] = None
    ):
        self.bird = bird_client
        self.store = file_store
        self.quality_filter = quality_filter

    def collect_from_influencers(
        self,
        influencers: List[Influencer],
        max_age_minutes: int = 30
    ) -> List[Tweet]:
        """
        从大V列表收集新推文

        Args:
            influencers: 大V列表
            max_age_minutes: 最大推文年龄（分钟）

        Returns:
            新推文列表
        """
        all_tweets = []

        for influencer in influencers:
            print(f"📡 Checking @{influencer.username}...")

            try:
                # 获取该大V的推文
                tweets = self.bird.get_user_tweets(
                    influencer.username,
                    count=20
                )

                # 过滤时间范围
                recent = self._filter_by_age(tweets, max_age_minutes)
                print(f"   Found {len(recent)} tweets within {max_age_minutes}min")

                # 去重（检查是否已处理）
                new_tweets = self._filter_processed(recent)
                print(f"   {len(new_tweets)} new tweets after deduplication")

                # 质量过滤
                if self.quality_filter and new_tweets:
                    passed, filtered = self.quality_filter.filter_batch(new_tweets)
                    print(f"   ✅ {len(passed)} passed quality filter, {len(filtered)} filtered")

                    # 保存被过滤的推文
                    for tweet in filtered:
                        self.store.save_filtered_tweet(tweet)

                    new_tweets = passed

                # 保存推文
                for tweet in new_tweets:
                    self.store.save_tweet(tweet)

                all_tweets.extend(new_tweets)

                # 更新最后检查时间
                self.store.update_influencer_last_checked(influencer.username)

            except BirdClientError as e:
                print(f"   ⚠️  Error: {e}")
                continue

        return all_tweets

    def _filter_by_age(
        self,
        tweets: List[Tweet],
        max_age_minutes: int
    ) -> List[Tweet]:
        """过滤出指定时间内的推文"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
        return [t for t in tweets if t.created_at > cutoff]

    def _filter_processed(
        self,
        tweets: List[Tweet]
    ) -> List[Tweet]:
        """过滤掉已处理的推文"""
        # 1. 检查推文是否已存在
        new_tweets = [t for t in tweets if not self.store.tweet_exists(t.id)]

        recent_authors = self.store.get_recent_commented_authors(hours=0)

        return [
            t for t in new_tweets
            if t.author.user_id not in recent_authors
        ]
