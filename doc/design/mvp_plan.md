# MVP开发计划：X涨粉助手

## MVP目标
实现一个最简化但可用的版本，能够：
1. 监控2-3个大V的新推文
2. 自动生成评论建议
3. 用户审核后手动发布
4. 记录历史数据

## MVP范围（最小功能集）

### 包含功能 ✅
- [x] 手动模式（半自动暂不实现）
- [x] 大V列表监控（仅1个来源）
- [x] 基础趋势评分（简单的点赞/时间评分）
- [x] Claude生成评论（基础prompt）
- [x] 终端审核界面
- [x] bird CLI发布评论
- [x] JSON文件存储历史

### 暂不包含 ❌
- [ ] 话题搜索（来源2）
- [ ] 热门推文流（来源3）
- [ ] 大V自动发现
- [ ] 复杂的趋势分析算法
- [ ] 桌面通知
- [ ] 半自动后台模式
- [ ] 性能统计分析

## 不确定可行性的部分（需要先验证）

### 🔍 调研项1: bird CLI功能验证
**不确定点**：
- bird CLI能否获取推文的详细互动数据（点赞、转发、评论数）？
- bird CLI返回的JSON格式是什么？
- bird CLI能否筛选时间范围（如"最近1小时"）？
- bird CLI的限流策略是什么？调用频率限制？

**验证方法**：
```bash
# 测试命令
1. bird whoami  # 验证登录状态
2. bird read @elonmusk --limit 3  # 获取推文，查看返回格式
3. bird search "AI" --limit 5  # 测试搜索功能
4. bird thread <tweet-id>  # 查看单条推文详情
5. 连续调用测试限流
```

**预期产出**：
- bird_cli_test_report.md（包含返回格式示例、可用字段、限制等）
- 确定是否需要额外解析或补充数据

**优先级**: 🔴 HIGH - 这是整个系统的基础

---

### 🔍 调研项2: Claude Agent SDK使用方式
**不确定点**：
- Claude Agent SDK与普通API调用的区别？
- 如何实现"记忆"功能（学习用户风格）？
- 是否支持工具调用（如调用bird CLI）？
- 如何传入用户画像和示例？

**验证方法**：
```python
# 测试代码
1. 安装 anthropic SDK
2. 创建简单的Agent测试脚本
3. 测试多轮对话和上下文记忆
4. 测试风格学习（提供示例评论）
```

**预期产出**：
- agent_sdk_poc.py（概念验证代码）
- agent_integration_guide.md（集成指南）

**优先级**: 🟡 MEDIUM - 可以先用普通API替代，后续升级

---

### 🔍 调研项3: 趋势评分算法
**不确定点**：
- 如何判断推文的"流行潜力"？
- 需要哪些数据点？
- 如何计算"快速增长"（需要多个时间点的数据）？

**验证方法**：
```python
# 设计简单版本
1. 初版：只用点赞数/发布时间
2. 收集真实数据样本
3. 迭代改进评分公式
```

**预期产出**：
- scoring_algorithm_v1.py（初版算法）
- 可以先用简单版本，后续迭代

**优先级**: 🟢 LOW - MVP可用简化版本

---

### 🔍 调研项4: 推文时间筛选
**不确定点**：
- bird CLI返回的推文是否包含精确时间戳？
- 如何筛选"30分钟内的推文"？
- 时区处理？

**验证方法**：
- 调研项1中一并验证
- 解析返回的时间字段格式

**优先级**: 🟡 MEDIUM - 影响"早期评论"功能

---

## MVP开发阶段

### Phase 0: 可行性验证（1-2天）
- [ ] 调研项1: bird CLI功能全面测试
- [ ] 调研项2: Claude Agent SDK POC
- [ ] 确定技术方案可行性
- [ ] 更新开发计划

**交付物**：
- bird_cli_test_report.md
- agent_sdk_poc.py
- 技术可行性报告

---

### Phase 1: 项目脚手架（半天）
- [ ] 创建argo/growth目录结构
- [ ] 创建配置文件模板
- [ ] 设置依赖管理（pyproject.toml）
- [ ] 创建数据存储目录结构

**交付物**：
```
argo/growth/
├── config/
│   ├── user_profile.yaml
│   └── settings.yaml
├── data/
│   ├── influencers/
│   ├── tweets/
│   └── comments/
├── core/
│   ├── bird_client.py
│   ├── tweet_collector.py
│   └── storage.py
└── cli/
    └── main.py
```

---

### Phase 2: bird CLI集成（1天）
- [ ] 实现BirdClient封装类
- [ ] 实现获取用户推文功能
- [ ] 实现推文详情解析
- [ ] 实现发布评论功能
- [ ] 单元测试

**核心类**：
```python
class BirdClient:
    def get_user_tweets(username, limit=5) -> List[Tweet]
    def get_tweet_details(tweet_id) -> Tweet
    def post_reply(tweet_id, content) -> bool
```

**不确定项处理**：
- 如果bird CLI数据不完整，考虑补充方案
- 如果限流严重，调整请求策略

---

### Phase 3: 推文收集器（1天）
- [ ] 实现ManagedInfluencerSource
- [ ] 实现TweetCollector
- [ ] 实现去重和过滤逻辑
- [ ] 实现简单的趋势评分
- [ ] 单元测试

**核心功能**：
```python
# 配置3个大V
influencers:
  - username: "elonmusk"
  - username: "sama"
  - username: "karpathy"

# 运行
tweets = collector.collect_tweets(limit=10)
# 返回10条候选推文，按评分排序
```

---

### Phase 4: 评论生成（1天）
- [ ] 创建用户画像配置模板
- [ ] 实现Claude API调用（先用基础API）
- [ ] 实现评论生成prompt工程
- [ ] 测试评论质量
- [ ] （可选）升级到Agent SDK

**prompt设计**：
```python
system_prompt = """
你是一个X评论助手，根据用户画像生成评论。

用户信息：
- 领域：{expertise}
- 风格：{tone}
- 示例：{examples}

要求：
1. 评论有价值，不空洞
2. 符合用户风格
3. 避免过度营销
4. 100-200字符
"""
```

---

### Phase 5: 审核和发布流程（1天）
- [ ] 实现待审核队列
- [ ] 实现终端交互界面
- [ ] 实现评论发布功能
- [ ] 实现历史记录
- [ ] 测试完整流程

**CLI交互设计**：
```bash
$ python -m argo.growth scan

发现10条候选推文：

[1] @elonmusk (5分钟前) ⭐️ 评分: 85
    "AI will change everything..."
    点赞: 1.2K | 转发: 340 | 评论: 89

    建议评论：
    "完全同意！我们在{领域}已经看到AI带来的变革..."

    操作: [c]评论 [s]跳过 [n]下一条 [q]退出
    > c

    ✅ 评论已发布！

[2] @sama (12分钟前) ⭐️ 评分: 78
    ...
```

---

### Phase 6: CLI命令和文档（半天）
- [ ] 实现完整的CLI命令
- [ ] 编写使用文档
- [ ] 添加示例配置
- [ ] 创建快速开始指南

**CLI命令**：
```bash
# 初始化配置
python -m argo.growth init

# 扫描和评论
python -m argo.growth scan

# 查看历史
python -m argo.growth history

# 管理大V列表
python -m argo.growth influencers list
python -m argo.growth influencers add @username
```

---

## MVP验收标准

### 功能验收
- [ ] 能监控3个大V的新推文
- [ ] 能发现10条候选推文
- [ ] 能生成符合风格的评论
- [ ] 用户能审核并发布评论
- [ ] 历史记录可查询
- [ ] 不重复评论同一作者（24小时）

### 质量验收
- [ ] 评论质量：有价值、相关、自然
- [ ] 响应速度：扫描10条推文 < 30秒
- [ ] 错误处理：网络错误、限流友好提示
- [ ] 代码质量：有单元测试、有注释

### 文档验收
- [ ] README.md（快速开始）
- [ ] 配置文件有注释说明
- [ ] bird CLI测试报告
- [ ] 遇到的问题和解决方案

---

## 风险和应对

### 风险1: bird CLI功能不足
**应对**：
- 备选方案1: 使用Playwright浏览器自动化
- 备选方案2: 寻找其他X API封装工具
- 降级方案: 手动复制推文URL，半自动化

### 风险2: Claude API成本
**应对**：
- 使用Claude Haiku（更便宜）
- 限制每日评论数量
- 添加成本监控

### 风险3: X限流或封号
**应对**：
- 严格控制频率（每小时2-3条评论）
- 避免spam行为
- 评论内容高质量、多样化
- 人工审核每条评论

### 风险4: 趋势判断不准确
**应对**：
- MVP阶段允许不准确
- 收集数据后迭代改进
- 用户可手动选择推文

---

## 时间估算

- Phase 0: 可行性验证 - 1-2天
- Phase 1: 项目脚手架 - 0.5天
- Phase 2: bird CLI集成 - 1天
- Phase 3: 推文收集器 - 1天
- Phase 4: 评论生成 - 1天
- Phase 5: 审核发布 - 1天
- Phase 6: CLI和文档 - 0.5天

**总计: 6-7天**（如果可行性验证顺利）

---

## 下一步行动

1. ✅ 确认MVP计划（当前）
2. 🔴 执行Phase 0：可行性验证
   - 先测试bird CLI
   - 再测试Claude Agent SDK
3. 根据验证结果调整计划
4. 开始Phase 1实施

---

## 决策点

**现在需要决策：**
1. 是否先进行可行性验证？（建议：是）
2. 如果bird CLI不满足需求，是否接受使用Playwright？
3. 是否接受MVP阶段评论质量可能不完美？
4. 预期的开发时间窗口是多久？
