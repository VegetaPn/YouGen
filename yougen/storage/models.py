"""数据模型定义"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


@dataclass
class Author:
    """推文作者"""
    username: str
    user_id: str
    name: str
    followers: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Author':
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class Tweet:
    """推文数据模型"""
    id: str
    author: Author
    text: str
    created_at: datetime
    like_count: int
    retweet_count: int
    reply_count: int
    conversation_id: str

    # 扩展字段
    trending_score: float = 0.0
    discovered_at: Optional[datetime] = None

    @classmethod
    def from_bird_json(cls, data: Dict[str, Any]) -> 'Tweet':
        """从bird CLI返回的JSON创建Tweet对象"""
        # bird返回格式：createdAt: "Mon Jan 19 15:18:00 +0000 2026"
        created_at_str = data['createdAt']
        created_at = datetime.strptime(
            created_at_str,
            "%a %b %d %H:%M:%S %z %Y"
        )

        author = Author(
            username=data['author']['username'],
            user_id=data['authorId'],
            name=data['author']['name']
        )

        return cls(
            id=data['id'],
            author=author,
            text=data['text'],
            created_at=created_at,
            like_count=data.get('likeCount', 0),
            retweet_count=data.get('retweetCount', 0),
            reply_count=data.get('replyCount', 0),
            conversation_id=data['conversationId'],
            discovered_at=datetime.now(timezone.utc)
        )

    def age_minutes(self) -> float:
        """推文年龄（分钟）"""
        now = datetime.now(timezone.utc)
        delta = now - self.created_at
        return delta.total_seconds() / 60

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        return {
            'id': self.id,
            'author': self.author.to_dict(),
            'text': self.text,
            'created_at': self.created_at.isoformat(),
            'like_count': self.like_count,
            'retweet_count': self.retweet_count,
            'reply_count': self.reply_count,
            'conversation_id': self.conversation_id,
            'trending_score': self.trending_score,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tweet':
        """从字典创建Tweet对象"""
        return cls(
            id=data['id'],
            author=Author.from_dict(data['author']),
            text=data['text'],
            created_at=datetime.fromisoformat(data['created_at']),
            like_count=data['like_count'],
            retweet_count=data['retweet_count'],
            reply_count=data['reply_count'],
            conversation_id=data['conversation_id'],
            trending_score=data.get('trending_score', 0.0),
            discovered_at=datetime.fromisoformat(data['discovered_at']) if data.get('discovered_at') else None
        )


@dataclass
class Comment:
    """生成的评论"""
    id: str
    tweet_id: str
    content: str
    generated_at: datetime
    status: str  # 'pending', 'approved', 'rejected', 'published'
    session_id: Optional[str] = None
    published_at: Optional[datetime] = None
    tweet_author: Optional[str] = None  # 用于去重检查

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'tweet_id': self.tweet_id,
            'content': self.content,
            'generated_at': self.generated_at.isoformat(),
            'status': self.status,
            'session_id': self.session_id,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'tweet_author': self.tweet_author
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Comment':
        """从字典创建Comment对象"""
        return cls(
            id=data['id'],
            tweet_id=data['tweet_id'],
            content=data['content'],
            generated_at=datetime.fromisoformat(data['generated_at']),
            status=data['status'],
            session_id=data.get('session_id'),
            published_at=datetime.fromisoformat(data['published_at']) if data.get('published_at') else None,
            tweet_author=data.get('tweet_author')
        )


@dataclass
class Influencer:
    """大V配置"""
    username: str
    user_id: str
    priority: str  # 'high', 'medium', 'low'
    check_interval: int  # 检查间隔（分钟）
    topics: List[str] = field(default_factory=list)
    notes: str = ""
    added_at: Optional[datetime] = None
    last_checked: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'username': self.username,
            'user_id': self.user_id,
            'priority': self.priority,
            'check_interval': self.check_interval,
            'topics': self.topics,
            'notes': self.notes,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Influencer':
        """从字典创建Influencer对象"""
        return cls(
            username=data['username'],
            user_id=data.get('user_id', ''),
            priority=data.get('priority', 'medium'),
            check_interval=data.get('check_interval', 15),
            topics=data.get('topics', []),
            notes=data.get('notes', ''),
            added_at=datetime.fromisoformat(data['added_at']) if data.get('added_at') else None,
            last_checked=datetime.fromisoformat(data['last_checked']) if data.get('last_checked') else None
        )
