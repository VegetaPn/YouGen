# 设计笔记: X涨粉助手多源推文发现系统

## 问题分析

### 仅靠大V列表的局限性
1. **数量不足**: 大V发推频率有限（平均2-5条/天）
2. **时机问题**: 可能错过非大V的爆款推文
3. **覆盖面窄**: 只关注已知大V，错过新兴影响者
4. **竞争激烈**: 大V推文下评论众多，曝光机会小

### 理想的推文发现系统
- **数量充足**: 每小时至少10-20条候选推文
- **质量保证**: 有流行潜力，符合用户兴趣
- **时机精准**: 发布后5-15分钟内（早期评论曝光最高）
- **多样性**: 不同来源，降低风险

## 精简版：3个核心推文来源

### 来源1: 大V列表监控 (Managed Influencers) ⭐️
```python
优先级: HIGH
频率: 每10分钟检查一次
每次获取: 最多3-5条新推文

流程:
1. 遍历managed influencers列表（建议5-10个精选大V）
2. 使用bird CLI获取每个用户的最新推文
3. 筛选出30分钟内的新推文
4. 自动进入候选池

bird命令:
- bird read @username --limit 3

优势:
- 精准相关，符合你的兴趣
- 质量有保证
- API调用少，不易限流
```

### 来源2: 话题关键词搜索 (Topic Search) ⭐️
```python
优先级: MEDIUM
频率: 每15分钟一轮
每次获取: 3-5条热门推文

话题配置示例:
topics:
  - keywords: ["AI", "Claude"]
    min_likes: 200
  - keywords: ["startup", "building"]
    min_likes: 100

流程:
1. 选择1-2个关键话题（轮询）
2. bird search "AI OR Claude" --min-likes 200 --limit 10
3. 过滤出1小时内的推文
4. 按互动率排序，取Top 3-5

优势:
- 主动发现热门内容
- 作者更多样化
- 可灵活配置话题
```

### 来源3: 热门推文流 (Trending Stream)
```python
优先级: LOW
频率: 每30分钟
每次获取: 2-3条爆款推文

流程:
1. bird search "min_likes:1000" --limit 20
2. 过滤出2小时内的推文
3. 计算病毒式传播指数（retweet_rate）
4. 取Top 2-3

指标:
- 转发/点赞比例 (>0.3表示传播力强)
- 评论/点赞比例 (>0.1表示讨论度高)

优势:
- 捕获正在爆火的推文
- 潜在曝光量大
```

## 推文收集器实现（精简版）

### 核心类设计
```python
class TweetCollector:
    def __init__(self):
        self.sources = [
            ManagedInfluencerSource(),     # 大V监控
            TopicSearchSource(),            # 话题搜索
            # TrendingStreamSource() 可选，初期不启用
        ]

    async def collect_tweets(self, max_tweets=10) -> List[Tweet]:
        """收集少量高质量推文"""
        all_tweets = []

        # 来源1: 大V监控 (优先，最多5条)
        managed_tweets = await self.sources[0].fetch(limit=5)
        all_tweets.extend(managed_tweets)

        # 如果大V推文不足，补充话题搜索
        if len(all_tweets) < max_tweets:
            remaining = max_tweets - len(all_tweets)
            topic_tweets = await self.sources[1].fetch(limit=remaining)
            all_tweets.extend(topic_tweets)

        # 去重、过滤、排序
        tweets = self.filter_and_rank(all_tweets)
        return tweets[:max_tweets]  # 最多返回10条

    def filter_and_rank(self, tweets):
        """过滤和排序"""
        # 1. 去重（同一推文ID）
        # 2. 过滤已评论过的（24小时内）
        # 3. 过滤黑名单作者
        # 4. 按优先级排序：大V > 话题搜索
        # 5. 二次排序：trending_score
```

### 数据流（精简版）
```
[大V监控] ─────→ 3-5条推文
     ↓
[话题搜索] ─────→ 补充到10条
     ↓
[去重过滤] ─────→ 移除已处理、黑名单
     ↓
[趋势评分] ─────→ trending_score排序
     ↓
[返回Top 10] ───→ 推送给用户审核
```

### 运行频率控制
```python
# 手动模式
每次执行命令时收集10条 → 生成评论 → 用户审核

# 半自动模式
每30分钟收集一次 → 最多10条新推文
→ 自动生成评论
→ 推送通知
→ 用户审核批准
→ 发布

# 限流保护
- 每个来源限制请求频率
- bird CLI调用间隔 >= 2秒
- 每小时最多收集30条推文
```

## 配置文件设计

### search_topics.yaml
```yaml
# 话题搜索配置
topics:
  - name: "AI和机器学习"
    keywords: ["AI", "LLM", "Claude", "ChatGPT", "machine learning"]
    min_likes: 100
    max_age_minutes: 30
    priority: high

  - name: "创业和产品"
    keywords: ["startup", "founder", "building", "launch", "product"]
    min_likes: 50
    max_age_minutes: 20
    priority: medium

  - name: "编程技术"
    keywords: ["Python", "JavaScript", "coding", "developer"]
    min_likes: 80
    max_age_minutes: 25
    priority: medium

# 搜索策略
search_strategy:
  enable_topic_search: true
  enable_trending_stream: true
  enable_network_analysis: true
  enable_smart_recommendations: false  # 初期关闭

  # 去重策略
  deduplication:
    time_window_hours: 24  # 24小时内不重复评论同一作者

  # 黑名单
  blacklist:
    authors: []  # 不想互动的账号
    keywords: ["政治", "争议"]  # 避免的关键词
```

### settings.yaml
```yaml
# 系统设置
collection:
  managed_influencers_interval: 5  # 分钟
  topic_search_interval: 10
  trending_stream_interval: 15
  network_analysis_interval: 30

  max_tweets_per_cycle: 50
  concurrent_sources: true

analysis:
  min_trending_score: 60  # 最低趋势分数
  early_bird_window_minutes: 15  # 最佳评论时间窗口

agent:
  model: "claude-3-5-sonnet-20241022"
  max_tokens: 1024
  temperature: 0.7

notification:
  enable_desktop: true
  enable_terminal: true
  sound: true
```

## 预期效果（精简版）

### 推文数量控制
**手动模式**：
- 每次执行收集10条候选推文
- 用户可以自由选择评论哪几条
- 建议：每次评论2-3条即可

**半自动模式**：
- 每30分钟收集一次，最多10条
- 自动生成评论后推送通知
- 用户审核批准后发布
- 预计：每小时2-3条评论（保持自然频率）

### 质量优于数量
- 优先大V列表（精准相关）
- 补充话题搜索（扩大覆盖）
- 严格过滤（trending_score > 60）
- 最终呈现：10条高质量候选/次

### API调用限制
- 大V监控：5-10个大V × 每次3条 = 15-30条/次
- 话题搜索：1-2个话题 × 每次10条 = 10-20条/次
- bird CLI调用间隔2秒，避免限流
- 总计：每小时约60-80次bird调用（安全范围）

## 下一步
1. 实现基础的TweetCollector框架
2. 先实现来源1和来源2（大V监控+话题搜索）
3. 集成bird CLI
4. 测试推文收集效果
