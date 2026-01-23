"""趋势分析器"""

from typing import List
from yougen.storage.models import Tweet


class TrendAnalyzer:
    """趋势分析器"""

    def __init__(
        self,
        like_weight: float = 1.0,
        retweet_weight: float = 2.0,
        reply_weight: float = 1.5
    ):
        """
        Args:
            like_weight: 点赞权重
            retweet_weight: 转发权重
            reply_weight: 评论权重
        """
        self.like_weight = like_weight
        self.retweet_weight = retweet_weight
        self.reply_weight = reply_weight

    def calculate_score(self, tweet: Tweet) -> float:
        """
        计算趋势评分 (0-100)

        算法:
        - 基于互动数和推文年龄
        - 互动率 = (点赞*w1 + 转发*w2 + 评论*w3) / 推文年龄(分钟)
        - 归一化到0-100

        Args:
            tweet: 推文对象

        Returns:
            趋势评分 (0-100)
        """
        age_minutes = max(tweet.age_minutes(), 1)

        # 加权互动数
        engagement = (
            tweet.like_count * self.like_weight +
            tweet.retweet_count * self.retweet_weight +
            tweet.reply_count * self.reply_weight
        )

        # 每分钟互动率
        engagement_rate = engagement / age_minutes

        # 归一化到0-100
        # 调整基准：每分钟5个加权互动 = 50分（更合理的阈值）
        score = min(engagement_rate / 5 * 50, 100)

        return round(score, 2)

    def rank_tweets(
        self,
        tweets: List[Tweet],
        min_score: float = 40.0,  # 降低默认阈值
        min_tweets: int = 3       # 保证至少返回N条
    ) -> List[Tweet]:
        """
        排序并过滤推文

        Args:
            tweets: 推文列表
            min_score: 最低评分（灵活阈值）
            min_tweets: 最少返回推文数（保护逻辑）

        Returns:
            排序后的推文列表
        """
        if not tweets:
            return []

        # 计算每条推文的评分
        for tweet in tweets:
            tweet.trending_score = self.calculate_score(tweet)

        # 按评分排序（降序）
        sorted_tweets = sorted(
            tweets,
            key=lambda t: t.trending_score,
            reverse=True
        )

        # 过滤低分推文
        filtered = [t for t in sorted_tweets if t.trending_score >= min_score]

        # 保护逻辑：如果过滤后少于min_tweets，放宽条件
        if len(filtered) < min_tweets:
            print(f"⚠️  Only {len(filtered)} tweets passed min_score={min_score}")
            print(f"   Relaxing filter to ensure at least {min_tweets} tweets...")
            filtered = sorted_tweets[:min_tweets]

        return filtered

    def analyze_tweet(self, tweet: Tweet) -> dict:
        """
        分析单条推文

        Args:
            tweet: 推文对象

        Returns:
            分析结果字典
        """
        score = self.calculate_score(tweet)

        return {
            'tweet_id': tweet.id,
            'trending_score': score,
            'age_minutes': round(tweet.age_minutes(), 1),
            'engagement': {
                'likes': tweet.like_count,
                'retweets': tweet.retweet_count,
                'replies': tweet.reply_count,
                'total': tweet.like_count + tweet.retweet_count + tweet.reply_count
            },
            'engagement_rate': round(
                (tweet.like_count + tweet.retweet_count + tweet.reply_count) /
                max(tweet.age_minutes(), 1),
                2
            )
        }
