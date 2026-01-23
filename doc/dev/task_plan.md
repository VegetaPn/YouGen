# Task Plan: X涨粉助手系统

## Goal
构建一个智能X涨粉助手，通过多源发现热门推文、智能生成评论、人工审核后发布，实现有效涨粉。

## Phases
- [ ] Phase 1: 系统架构设计和规划
- [ ] Phase 2: 多源推文发现系统
- [ ] Phase 3: 趋势分析和评分系统
- [ ] Phase 4: Claude Agent评论生成
- [ ] Phase 5: 审核和发布流程
- [ ] Phase 6: CLI命令和用户界面
- [ ] Phase 7: 测试和优化

## 核心需求
1. **运行模式**: 半自动模式 + 手动模式
2. **X访问**: bird CLI（浏览器cookies，无API密钥）
3. **趋势判断**: 快速互动指标 + 历史数据模式
4. **用户画像**: 结构化配置文件 + 示例学习
5. **LLM**: Claude Agent SDK
6. **存储**: 轻量化JSON文件

## 关键设计决策

### 决策1: 多源推文发现策略
**问题**: 仅依赖大V列表可能推文数量不足
**方案**: 5种推文来源，保证充足的候选推文
1. **大V列表监控** (managed influencers) - 精准但数量有限
2. **话题关键词搜索** - 主动发现相关热门话题
3. **热门推文流** - 捕获正在trending的推文
4. **关注网络互动** - 从关注者的互动中发现机会
5. **智能推荐** - 基于历史成功模式推荐

**优先级排序**:
- High: 管理的大V新推文
- Medium: 话题搜索热门推文
- Low: 发现的推文和推荐

### 决策2: 存储方案
**选择**: JSON文件存储
**理由**: 无依赖、灵活、易于版本控制

### 决策3: LLM集成
**选择**: Claude Agent SDK
**理由**: 支持工具调用、记忆、多轮对话

## 项目结构
```
argo/growth/
├── config/
│   ├── user_profile.yaml        # 用户画像
│   ├── settings.yaml            # 系统设置
│   └── search_topics.yaml       # 搜索话题配置
├── discovery/
│   ├── influencer_finder.py     # 大V自动发现
│   ├── tweet_sources.py         # 多源推文发现
│   └── network_analyzer.py      # 社交网络分析
├── monitor/
│   ├── tweet_collector.py       # 推文收集器
│   └── engagement_tracker.py    # 互动追踪
├── analyzer/
│   ├── trend_analyzer.py        # 趋势分析
│   ├── scoring_engine.py        # 评分引擎
│   └── history_analyzer.py      # 历史数据分析
├── agents/
│   ├── comment_agent.py         # Claude Agent评论生成
│   └── context_builder.py       # 上下文构建
├── reviewer/
│   ├── approval_queue.py        # 审核队列
│   └── notification.py          # 通知系统
├── publisher/
│   └── tweet_publisher.py       # 发布器
├── storage/
│   └── file_manager.py          # 文件管理
└── cli/
    └── commands.py              # CLI命令
```

## Errors Encountered

### Phase 0 - bird CLI测试
- bird read --limit参数不存在 → 解决：使用user-tweets -n命令
- bird不支持min_likes等高级搜索过滤 → 解决：客户端过滤

## Phase 0 验证结果

### ✅ bird CLI测试完成
**结论**: 完全可行，满足所有MVP需求

**核心发现**:
1. 认证：自动从Chrome提取cookies，无需API密钥
2. 数据完整：包含所有需要的字段（点赞、转发、评论、时间）
3. 功能齐全：user-tweets（获取推文）、search（搜索）、reply（评论）
4. 性能可接受：2-3秒/请求

**详细报告**: bird_cli_test_report.md

### ✅ Claude Agent SDK测试完成
**结论**: 完全满足评论生成需求

**核心发现**:
1. 用户画像注入：通过system_prompt参数
2. 示例学习：集成在system_prompt中
3. Session记忆：支持多轮迭代优化
4. 生成质量：高质量、符合风格

**详细报告**: agent_sdk_research.md

### 最终技术栈
```yaml
推文获取: bird CLI
评论生成: Claude Agent SDK
存储: JSON文件
事件驱动: EventBus (已有)
定时任务: APScheduler
```

## Status
**Phase 1 Complete** - 已完成架构设计和MVP规划

详细设计见: notes.md
MVP开发计划见: mvp_plan.md

**下一步**: 需要用户确认MVP计划，然后进入Phase 0（可行性验证）
