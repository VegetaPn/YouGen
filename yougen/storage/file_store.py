"""JSON文件存储管理"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Set, Optional
from yougen.storage.models import Tweet, Comment, Influencer


class FileStore:
    """JSON文件存储"""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保所有必要的目录存在"""
        dirs = [
            self.data_dir / "influencers",
            self.data_dir / "tweets",
            self.data_dir / "filtered_tweets",
            self.data_dir / "comments" / "pending",
            self.data_dir / "comments" / "approved",
            self.data_dir / "comments" / "rejected",
            self.data_dir / "comments" / "published",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    # ============ Influencers管理 ============

    def load_influencers(self) -> List[Influencer]:
        """加载大V列表"""
        file_path = self.data_dir / "influencers" / "managed.json"
        if not file_path.exists():
            return []

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [Influencer.from_dict(item) for item in data.get('influencers', [])]

    def save_influencers(self, influencers: List[Influencer]):
        """保存大V列表"""
        file_path = self.data_dir / "influencers" / "managed.json"
        data = {
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'influencers': [inf.to_dict() for inf in influencers]
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def update_influencer_last_checked(self, username: str):
        """更新大V的最后检查时间"""
        influencers = self.load_influencers()
        for inf in influencers:
            if inf.username == username:
                inf.last_checked = datetime.now(timezone.utc)
                break
        self.save_influencers(influencers)

    # ============ Tweets存储 ============

    def save_tweet(self, tweet: Tweet):
        """保存推文"""
        date_str = tweet.created_at.strftime("%Y-%m-%d")
        date_dir = self.data_dir / "tweets" / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        file_path = date_dir / f"{tweet.author.username}_{tweet.id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(tweet.to_dict(), f, indent=2, ensure_ascii=False)

    def tweet_exists(self, tweet_id: str) -> bool:
        """检查推文是否已存在"""
        # 在最近7天的目录中搜索
        for i in range(7):
            date = datetime.now(timezone.utc) - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            date_dir = self.data_dir / "tweets" / date_str

            if not date_dir.exists():
                continue

            for file_path in date_dir.glob(f"*_{tweet_id}.json"):
                return True

        return False

    def save_filtered_tweet(self, tweet: Tweet):
        """保存被过滤的推文

        按日期和过滤原因组织：filtered_tweets/{date}/{reason_slug}/
        用于后续分析和优化过滤规则
        """
        date_str = tweet.created_at.strftime("%Y-%m-%d")

        # 生成原因slug（用于目录名）
        reason_slug = "unknown"
        if tweet.filtered_reason:
            # 简化原因字符串作为目录名
            reason_slug = tweet.filtered_reason.replace(' ', '_').replace('/', '_')[:50]
        elif tweet.quality_issues:
            reason_slug = '_'.join(tweet.quality_issues[:2])

        filter_dir = self.data_dir / "filtered_tweets" / date_str / reason_slug
        filter_dir.mkdir(parents=True, exist_ok=True)

        file_path = filter_dir / f"{tweet.author.username}_{tweet.id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(tweet.to_dict(), f, indent=2, ensure_ascii=False)

    # ============ Comments管理 ============

    def save_comment(self, comment: Comment):
        """保存评论"""
        status_dir = self.data_dir / "comments" / comment.status
        status_dir.mkdir(parents=True, exist_ok=True)

        file_path = status_dir / f"{comment.id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(comment.to_dict(), f, indent=2, ensure_ascii=False)

    def load_comments_by_status(self, status: str) -> List[Comment]:
        """加载指定状态的评论"""
        status_dir = self.data_dir / "comments" / status
        if not status_dir.exists():
            return []

        comments = []
        for file_path in sorted(status_dir.glob("*.json")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    comments.append(Comment.from_dict(data))
            except Exception as e:
                print(f"⚠️  Failed to load comment {file_path}: {e}")

        return comments

    def load_pending_comments(self) -> List[Comment]:
        """加载待审核评论"""
        return self.load_comments_by_status('pending')

    def load_comment_by_id(self, comment_id: str) -> Optional[Comment]:
        """通过ID加载评论"""
        for status in ['pending', 'approved', 'rejected', 'published']:
            status_dir = self.data_dir / "comments" / status
            file_path = status_dir / f"{comment_id}.json"

            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return Comment.from_dict(data)

        return None

    def update_comment_status(self, comment_id: str, new_status: str):
        """更新评论状态"""
        # 查找并移动文件
        for old_status in ['pending', 'approved', 'rejected', 'published']:
            old_path = self.data_dir / "comments" / old_status / f"{comment_id}.json"

            if old_path.exists():
                # 读取评论数据
                with open(old_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 更新状态
                data['status'] = new_status

                # 如果是发布状态，更新发布时间
                if new_status == 'published' and not data.get('published_at'):
                    data['published_at'] = datetime.now(timezone.utc).isoformat()

                # 保存到新位置
                new_dir = self.data_dir / "comments" / new_status
                new_dir.mkdir(parents=True, exist_ok=True)
                new_path = new_dir / f"{comment_id}.json"

                with open(new_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # 删除旧文件
                old_path.unlink()
                break

    def delete_comment(self, comment_id: str):
        """删除评论"""
        for status in ['pending', 'approved', 'rejected', 'published']:
            file_path = self.data_dir / "comments" / status / f"{comment_id}.json"
            if file_path.exists():
                file_path.unlink()
                break

    # ============ 去重检查 ============

    def get_recent_commented_authors(self, hours: int = 24) -> Set[str]:
        """获取最近评论过的作者ID（用于去重）"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        authors = set()

        for status in ['approved', 'published']:
            comments = self.load_comments_by_status(status)

            for comment in comments:
                if comment.generated_at > cutoff and comment.tweet_author:
                    authors.add(comment.tweet_author)

        return authors

    # ============ 统计信息 ============

    def get_comment_stats(self) -> dict:
        """获取评论统计信息"""
        return {
            'pending': len(self.load_comments_by_status('pending')),
            'approved': len(self.load_comments_by_status('approved')),
            'rejected': len(self.load_comments_by_status('rejected')),
            'published': len(self.load_comments_by_status('published')),
        }

    def get_recent_published_count(self, hours: int = 1) -> int:
        """获取最近N小时内发布的评论数"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        published = self.load_comments_by_status('published')

        return sum(
            1 for c in published
            if c.published_at and c.published_at > cutoff
        )
