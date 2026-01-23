# X涨粉助手 - 项目架构设计

## 1. 系统概览

### 1.1 核心目标
在其他大V的新推文下及时发布高质量评论，利用其流量获得曝光和关注。

### 1.2 工作流程
```
[监控大V] → [发现新推文] → [趋势分析] → [生成评论] → [用户审核] → [发布]
```

### 1.3 MVP范围
- **手动模式**：用户主动触发扫描
- **大V监控**：2-3个配置的大V
- **评论生成**：基于用户画像的个性化评论
- **终端审核**：简单的CLI交互
- **推文发布**：通过bird CLI

---

## 2. 模块架构

### 2.1 模块划分

```
argo/growth/
├── config/                   # 配置管理
│   ├── __init__.py
│   ├── user_profile.yaml     # 用户画像
│   ├── influencers.yaml      # 大V列表
│   └── settings.yaml         # 系统设置
│
├── core/                     # 核心业务逻辑
│   ├── __init__.py
│   ├── bird_client.py        # bird CLI封装
│   ├── tweet_collector.py    # 推文收集器
│   ├── trend_analyzer.py     # 趋势分析器
│   └── comment_generator.py  # 评论生成器
│
├── storage/                  # 数据存储
│   ├── __init__.py
│   ├── file_store.py         # JSON文件存储
│   └── models.py             # 数据模型
│
├── cli/                      # 命令行界面
│   ├── __init__.py
│   ├── main.py               # CLI入口
│   └── reviewer.py           # 交互式审核
│
├── utils/                    # 工具函数
│   ├── __init__.py
│   ├── time_utils.py         # 时间处理
│   └── text_utils.py         # 文本处理
│
└── data/                     # 数据目录（运行时）
    ├── influencers/
    │   └── managed.json
    ├── tweets/
    │   └── 2024-01-19/
    └── comments/
        ├── pending/
        ├── approved/
        └── published/
```

### 2.2 模块职责

| 模块 | 职责 | 依赖 |
|------|------|------|
| **config** | 加载和管理配置文件 | - |
| **bird_client** | 封装bird CLI调用 | subprocess |
| **tweet_collector** | 从大V收集新推文 | bird_client |
| **trend_analyzer** | 计算趋势评分 | - |
| **comment_generator** | 生成个性化评论 | Claude Agent SDK |
| **file_store** | JSON文件读写 | - |
| **cli** | 用户交互界面 | 所有核心模块 |

---

## 3. 核心类设计

### 3.1 数据模型 (storage/models.py)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Author:
    """推文作者"""
    username: str
    user_id: str
    name: str
    followers: Optional[int] = None

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

    # 扩展字段
    conversation_id: str
    trending_score: float = 0.0
    discovered_at: Optional[datetime] = None

    @classmethod
    def from_bird_json(cls, data: dict) -> 'Tweet':
        """从bird CLI返回的JSON创建Tweet对象"""
        pass

    def age_minutes(self) -> float:
        """推文年龄（分钟）"""
        pass

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

@dataclass
class Influencer:
    """大V配置"""
    username: str
    user_id: str
    priority: str  # 'high', 'medium', 'low'
    check_interval: int  # 检查间隔（分钟）
    topics: List[str]
    added_at: datetime
    last_checked: Optional[datetime] = None
```

### 3.2 BirdClient (core/bird_client.py)

```python
import subprocess
import json
import time
from typing import List, Optional
from ..storage.models import Tweet

class BirdClient:
    """bird CLI封装客户端"""

    def __init__(self, delay: float = 2.0):
        """
        Args:
            delay: 请求间隔（秒），防止限流
        """
        self.delay = delay
        self.last_call = 0

    def _rate_limit(self):
        """限流保护"""
        elapsed = time.time() - self.last_call
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_call = time.time()

    def _run_command(self, args: List[str]) -> dict:
        """执行bird命令并返回JSON结果"""
        self._rate_limit()

        result = subprocess.run(
            ["bird"] + args + ["--json"],
            capture_output=True,
            text=True,
            check=True
        )

        return json.loads(result.stdout)

    def get_user_tweets(
        self,
        username: str,
        count: int = 20
    ) -> List[Tweet]:
        """获取用户推文"""
        data = self._run_command([
            "user-tweets",
            username,
            "-n", str(count)
        ])

        return [Tweet.from_bird_json(t) for t in data]

    def search_tweets(
        self,
        query: str,
        count: int = 20
    ) -> List[Tweet]:
        """搜索推文"""
        data = self._run_command([
            "search",
            query,
            "-n", str(count)
        ])

        return [Tweet.from_bird_json(t) for t in data]

    def post_reply(
        self,
        tweet_id: str,
        text: str
    ) -> bool:
        """发布评论"""
        try:
            subprocess.run(
                ["bird", "reply", tweet_id, text],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
```

### 3.3 TweetCollector (core/tweet_collector.py)

```python
from typing import List
from datetime import datetime, timezone, timedelta
from .bird_client import BirdClient
from ..storage.models import Tweet, Influencer
from ..storage.file_store import FileStore

class TweetCollector:
    """推文收集器"""

    def __init__(
        self,
        bird_client: BirdClient,
        file_store: FileStore
    ):
        self.bird = bird_client
        self.store = file_store

    def collect_from_influencers(
        self,
        influencers: List[Influencer],
        max_age_minutes: int = 30
    ) -> List[Tweet]:
        """从大V列表收集新推文"""
        all_tweets = []

        for influencer in influencers:
            # 获取该大V的推文
            tweets = self.bird.get_user_tweets(
                influencer.username,
                count=20
            )

            # 过滤时间范围
            recent = self._filter_by_age(tweets, max_age_minutes)

            # 去重（检查是否已处理）
            new_tweets = self._filter_processed(recent)

            all_tweets.extend(new_tweets)

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
        # 检查是否在最近24小时内评论过同一作者
        processed_authors = self.store.get_recent_commented_authors(hours=24)

        return [
            t for t in tweets
            if t.author.user_id not in processed_authors
        ]
```

### 3.4 TrendAnalyzer (core/trend_analyzer.py)

```python
from ..storage.models import Tweet

class TrendAnalyzer:
    """趋势分析器"""

    def calculate_score(self, tweet: Tweet) -> float:
        """
        计算趋势评分 (0-100)

        算法:
        - 基于互动数和推文年龄
        - 互动率 = (点赞 + 转发*2 + 评论*1.5) / 推文年龄(分钟)
        - 归一化到0-100
        """
        age_minutes = max(tweet.age_minutes(), 1)

        # 加权互动数
        engagement = (
            tweet.like_count +
            tweet.retweet_count * 2 +
            tweet.reply_count * 1.5
        )

        # 每分钟互动率
        engagement_rate = engagement / age_minutes

        # 归一化（假设每分钟10个互动是高分）
        score = min(engagement_rate / 10 * 100, 100)

        return score

    def rank_tweets(
        self,
        tweets: List[Tweet],
        min_score: float = 60.0
    ) -> List[Tweet]:
        """排序并过滤推文"""
        # 计算每条推文的评分
        for tweet in tweets:
            tweet.trending_score = self.calculate_score(tweet)

        # 过滤低分推文
        filtered = [t for t in tweets if t.trending_score >= min_score]

        # 按评分排序
        return sorted(
            filtered,
            key=lambda t: t.trending_score,
            reverse=True
        )
```

### 3.5 CommentGenerator (core/comment_generator.py)

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from typing import Optional, Tuple
import asyncio
from ..storage.models import Tweet, Comment
from datetime import datetime
import uuid

class CommentGenerator:
    """评论生成器（使用Claude Agent SDK）"""

    def __init__(self, user_profile: dict):
        self.user_profile = user_profile
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        examples_text = '\n'.join([
            f"- 推文: \"{ex['tweet']}\"\n  评论: \"{ex['comment']}\""
            for ex in self.user_profile.get('examples', [])
        ])

        return f"""
你是X (Twitter)评论助手。

用户画像:
- 专业领域: {', '.join(self.user_profile['expertise'])}
- 语气风格: {self.user_profile['tone']}
- 关键词偏好: {', '.join(self.user_profile['keywords'])}

评论示例（学习风格）:
{examples_text}

任务: 为推文生成一条评论

要求:
1. 100-200字符
2. 符合用户风格和专业领域
3. 有价值，不空洞
4. 自然，不过度营销
5. 避免: {', '.join(self.user_profile.get('avoid_keywords', []))}
"""

    async def generate(self, tweet: Tweet) -> Comment:
        """生成单条评论"""
        prompt = f"""
请为以下推文生成评论：

作者: @{tweet.author.username}
内容: {tweet.text}
互动: {tweet.like_count}赞 | {tweet.retweet_count}转发 | {tweet.reply_count}评论

生成一条符合我风格的评论，直接输出评论内容即可。
"""

        content = ""
        session_id = None

        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                allowed_tools=[],
                system_prompt=self.system_prompt
            )
        ):
            if hasattr(message, "session_id"):
                session_id = message.session_id
            if hasattr(message, "result"):
                content = message.result
                break

        return Comment(
            id=str(uuid.uuid4()),
            tweet_id=tweet.id,
            content=content,
            generated_at=datetime.now(),
            status='pending',
            session_id=session_id
        )

    async def refine(
        self,
        comment: Comment,
        feedback: str
    ) -> Comment:
        """优化评论（使用Session）"""
        prompt = f"""
原评论: "{comment.content}"
反馈: {feedback}

请根据反馈优化评论，直接输出新评论内容。
"""

        refined_content = ""

        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                resume=comment.session_id
            )
        ):
            if hasattr(message, "result"):
                refined_content = message.result
                break

        # 创建新评论对象
        return Comment(
            id=str(uuid.uuid4()),
            tweet_id=comment.tweet_id,
            content=refined_content,
            generated_at=datetime.now(),
            status='pending',
            session_id=comment.session_id
        )
```

### 3.6 FileStore (storage/file_store.py)

```python
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Set
from .models import Tweet, Comment, Influencer

class FileStore:
    """JSON文件存储"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # Influencers管理
    def load_influencers(self) -> List[Influencer]:
        """加载大V列表"""
        file_path = self.data_dir / "influencers" / "managed.json"
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)
            return [Influencer(**item) for item in data['influencers']]

    # Tweets存储
    def save_tweet(self, tweet: Tweet):
        """保存推文"""
        date_dir = self.data_dir / "tweets" / tweet.created_at.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        file_path = date_dir / f"{tweet.author.username}_{tweet.id}.json"
        with open(file_path, 'w') as f:
            json.dump(tweet.__dict__, f, indent=2, default=str)

    # Comments管理
    def save_comment(self, comment: Comment):
        """保存评论"""
        status_dir = self.data_dir / "comments" / comment.status
        status_dir.mkdir(parents=True, exist_ok=True)

        file_path = status_dir / f"{comment.id}.json"
        with open(file_path, 'w') as f:
            json.dump(comment.__dict__, f, indent=2, default=str)

    def load_pending_comments(self) -> List[Comment]:
        """加载待审核评论"""
        pending_dir = self.data_dir / "comments" / "pending"
        if not pending_dir.exists():
            return []

        comments = []
        for file_path in pending_dir.glob("*.json"):
            with open(file_path) as f:
                data = json.load(f)
                comments.append(Comment(**data))

        return comments

    def update_comment_status(self, comment_id: str, new_status: str):
        """更新评论状态"""
        # 查找并移动文件
        for status in ['pending', 'approved', 'rejected']:
            old_path = self.data_dir / "comments" / status / f"{comment_id}.json"
            if old_path.exists():
                new_dir = self.data_dir / "comments" / new_status
                new_dir.mkdir(parents=True, exist_ok=True)
                new_path = new_dir / f"{comment_id}.json"
                old_path.rename(new_path)
                break

    def get_recent_commented_authors(self, hours: int = 24) -> Set[str]:
        """获取最近评论过的作者ID（用于去重）"""
        cutoff = datetime.now() - timedelta(hours=hours)
        authors = set()

        for status in ['approved', 'published']:
            status_dir = self.data_dir / "comments" / status
            if not status_dir.exists():
                continue

            for file_path in status_dir.glob("*.json"):
                with open(file_path) as f:
                    data = json.load(f)
                    generated_at = datetime.fromisoformat(data['generated_at'])
                    if generated_at > cutoff:
                        # 需要从tweet中获取author_id
                        # 简化版本：直接记录tweet_id
                        authors.add(data['tweet_id'])

        return authors
```

---

## 4. 数据流设计

### 4.1 主流程

```
用户执行: python -m argo.growth scan
    ↓
1. CLI加载配置
    - user_profile.yaml
    - influencers.yaml
    - settings.yaml
    ↓
2. TweetCollector收集推文
    - 遍历大V列表
    - 调用bird CLI获取推文
    - 过滤30分钟内的新推文
    - 去重（24小时内不重复评论同一作者）
    ↓
3. TrendAnalyzer分析趋势
    - 计算每条推文的trending_score
    - 过滤低分推文（score < 60）
    - 按分数排序，取Top 10
    ↓
4. CommentGenerator生成评论
    - 并发为每条推文生成评论
    - 使用Claude Agent SDK
    - 保存到comments/pending/
    ↓
5. Reviewer交互审核
    - 终端显示推文和评论
    - 用户选择: 发布/跳过/优化/退出
    - 如果优化: 重新生成并审核
    ↓
6. 发布评论
    - 调用bird CLI发布
    - 移动到comments/published/
    - 更新发布时间
    ↓
完成
```

### 4.2 数据依赖关系

```
配置文件
  ↓
Influencer → BirdClient → Tweet → TrendAnalyzer → Ranked Tweets
                                         ↓
UserProfile → CommentGenerator → Comment → Reviewer → Published
```

---

## 5. 配置文件设计

### 5.1 user_profile.yaml

```yaml
profile:
  name: "AI研究者"
  expertise:
    - "AI"
    - "机器学习"
    - "创业"
  tone: "专业但友好"
  keywords:
    - "技术"
    - "创新"
    - "效率"
  avoid_keywords:
    - "政治"
    - "争议话题"

examples:
  - tweet: "AI safety is crucial"
    comment: "完全同意！安全性研究必须同步跟进。"
  - tweet: "New LLM breakthrough"
    comment: "很有意思的进展！期待更多技术细节。"

agent:
  model: "claude-3-5-sonnet-20241022"
  max_tokens: 1024
  comment_length:
    min: 100
    max: 200
```

### 5.2 influencers.yaml

```yaml
influencers:
  - username: "elonmusk"
    user_id: "44196397"
    priority: "high"
    check_interval: 10  # 分钟
    topics: ["tech", "AI", "space"]

  - username: "sama"
    user_id: "123456"
    priority: "high"
    check_interval: 10
    topics: ["AI", "startup"]

  - username: "karpathy"
    user_id: "789012"
    priority: "medium"
    check_interval: 15
    topics: ["AI", "ML"]
```

### 5.3 settings.yaml

```yaml
collection:
  max_tweets_per_scan: 10
  max_age_minutes: 30
  bird_delay_seconds: 2

analysis:
  min_trending_score: 60.0

comments:
  max_per_hour: 3
  check_duplicate_hours: 24

paths:
  data_dir: "./argo/growth/data"
```

---

## 6. 错误处理策略

### 6.1 分层错误处理

```python
# 1. BirdClient层
class BirdClientError(Exception):
    """bird CLI调用错误"""
    pass

class BirdRateLimitError(BirdClientError):
    """限流错误"""
    pass

# 2. 业务逻辑层
class CollectionError(Exception):
    """推文收集错误"""
    pass

class GenerationError(Exception):
    """评论生成错误"""
    pass

# 3. 使用
try:
    tweets = collector.collect_from_influencers(...)
except BirdRateLimitError:
    # 等待后重试
    time.sleep(60)
    retry()
except BirdClientError as e:
    # 记录错误，跳过该大V
    logger.error(f"Bird client error: {e}")
except Exception as e:
    # 未知错误，终止
    logger.critical(f"Unexpected error: {e}")
    sys.exit(1)
```

---

## 7. 扩展性设计

### 7.1 推文来源扩展

```python
# 当前：只有大V监控
class ManagedInfluencerSource:
    def fetch(self) -> List[Tweet]:
        pass

# 未来扩展：话题搜索
class TopicSearchSource:
    def fetch(self) -> List[Tweet]:
        pass

# 统一接口
class TweetSource(ABC):
    @abstractmethod
    def fetch(self) -> List[Tweet]:
        pass

# TweetCollector可以支持多种来源
class TweetCollector:
    def __init__(self, sources: List[TweetSource]):
        self.sources = sources
```

### 7.2 评论生成策略扩展

```python
# 当前：Claude Agent SDK
class ClaudeCommentGenerator:
    async def generate(self, tweet: Tweet) -> Comment:
        pass

# 未来扩展：本地模型、其他API
class LocalModelGenerator:
    async def generate(self, tweet: Tweet) -> Comment:
        pass

# 统一接口
class CommentGenerator(ABC):
    @abstractmethod
    async def generate(self, tweet: Tweet) -> Comment:
        pass
```

---

## 8. 性能考虑

### 8.1 并发处理

```python
# 并发生成多条评论
async def generate_comments_batch(
    tweets: List[Tweet]
) -> List[Comment]:
    tasks = [generator.generate(t) for t in tweets]
    return await asyncio.gather(*tasks)
```

### 8.2 缓存策略

```python
# 缓存推文数据（避免重复获取）
class CachedBirdClient:
    def __init__(self, bird_client: BirdClient):
        self.client = bird_client
        self.cache = {}
        self.cache_ttl = 300  # 5分钟

    def get_user_tweets(self, username: str) -> List[Tweet]:
        cache_key = f"tweets:{username}"
        if cache_key in self.cache:
            cached_at, tweets = self.cache[cache_key]
            if time.time() - cached_at < self.cache_ttl:
                return tweets

        tweets = self.client.get_user_tweets(username)
        self.cache[cache_key] = (time.time(), tweets)
        return tweets
```

---

## 9. 测试策略

### 9.1 单元测试

```python
# tests/test_trend_analyzer.py
def test_calculate_score():
    tweet = Tweet(
        id="123",
        author=Author(...),
        text="test",
        created_at=datetime.now() - timedelta(minutes=10),
        like_count=100,
        retweet_count=20,
        reply_count=10
    )

    analyzer = TrendAnalyzer()
    score = analyzer.calculate_score(tweet)

    assert 0 <= score <= 100
```

### 9.2 集成测试

```python
# tests/test_integration.py
async def test_full_workflow():
    # 1. 收集推文
    collector = TweetCollector(...)
    tweets = collector.collect_from_influencers(...)
    assert len(tweets) > 0

    # 2. 分析趋势
    analyzer = TrendAnalyzer()
    ranked = analyzer.rank_tweets(tweets)
    assert ranked[0].trending_score >= ranked[-1].trending_score

    # 3. 生成评论
    generator = CommentGenerator(...)
    comment = await generator.generate(ranked[0])
    assert len(comment.content) >= 100
```

---

## 10. 部署考虑

### 10.1 依赖管理

```toml
# pyproject.toml
[project]
name = "argo"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "claude-agent-sdk>=0.1.20",
    "pyyaml>=6.0",
    "apscheduler>=3.10",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]
```

### 10.2 环境配置

```bash
# .env
ANTHROPIC_BASE_URL=https://moacode.org
ANTHROPIC_AUTH_TOKEN=your-token
GROWTH_DATA_DIR=./argo/growth/data
```

---

## 11. 下一步实施计划

### Phase 1: 创建项目脚手架
1. 创建目录结构
2. 创建配置文件模板
3. 设置依赖管理

### Phase 2: 实现核心模块（按依赖顺序）
1. storage/models.py - 数据模型
2. storage/file_store.py - 文件存储
3. core/bird_client.py - bird CLI封装
4. core/tweet_collector.py - 推文收集
5. core/trend_analyzer.py - 趋势分析
6. core/comment_generator.py - 评论生成

### Phase 3: 实现CLI
1. cli/reviewer.py - 交互审核
2. cli/main.py - 命令入口

### Phase 4: 测试和优化
1. 单元测试
2. 集成测试
3. 实际运行验证

---

**架构设计完成！准备开始实施。**
