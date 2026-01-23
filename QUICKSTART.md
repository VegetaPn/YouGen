# Argo Growth - 快速开始指南

## 🚀 5分钟上手

### 1. 环境准备

```bash
# 创建虚拟环境
uv venv --python 3.12
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
uv pip install -r requirements.txt

# 设置API Key
export ANTHROPIC_API_KEY="your-api-key-here"
```

### 2. 配置大V列表

编辑 `argo/growth/config/influencers.yaml`:

```yaml
influencers:
  - username: "sama"  # Sam Altman
    priority: "high"
    check_interval: 15
    topics: ["AI", "OpenAI"]
    
  - username: "karpathy"  # Andrej Karpathy  
    priority: "high"
    check_interval: 15
    topics: ["AI", "Deep Learning"]
```

### 3. 登录 Twitter

```bash
# 使用 agent-browser 登录（保持会话）
agent-browser --session argo-growth open https://twitter.com/login --headed
# 在浏览器中手动登录，然后关闭浏览器窗口
```

### 4. 运行工作流

```bash
# 检查认证
python main.py auth

# 扫描推文并生成评论
python main.py scan

# 审核评论（交互式）
python main.py review
# 选择: [p]发布 [a]批准 [r]优化 [s]跳过 [q]退出

# 批量发布已批准的评论
python main.py publish

# 查看统计
python main.py stats
```

## 📖 完整工作流示例

```bash
# 1. 扫描并生成评论
python main.py scan
# 输出示例:
# 📡 Checking @sama...
#    Found 2 tweets within 30min
#    2 new tweets after filtering
# 🎯 Selected 2 trending tweet(s)
# 🤖 Generating comments...
#    ✅ Generated comment #1
#    ✅ Generated comment #2
# ✅ Generated 2 comment(s)

# 2. 审核评论
python main.py review
# 显示推文和生成的评论
# 输入 'p' 立即发布
# 或输入 'a' 批准稍后发布
# 或输入 'r' 然后输入反馈："更幽默一点"

# 3. 批量发布
python main.py publish
# 🔐 Checking Twitter login status...
# ✅ Already logged in to Twitter
# [1/2] Publishing comment abcd1234...
#    ✅ Published
```

## 🎯 核心特性

### 自动语言匹配
```
推文：AI is transforming our world
评论：Indeed! The pace of innovation is remarkable 🚀

推文：人工智能正在改变世界
评论：确实，创新的速度令人震撼 🚀
```

### 智能趋势分析
- 计算趋势评分（0-100）
- 基于互动率和推文年龄
- 自动过滤低质量推文
- 保护逻辑确保最少返回3条

### 评论生成
- 使用 Claude Opus 4.5
- 支持多轮优化
- 保持会话记忆
- 风格个性化

### 浏览器自动化
- 模拟真实用户行为
- 避免被检测为bot
- 支持复杂交互
- 保持登录状态

## ⚙️ 配置说明

### user_profile.yaml

```yaml
profile:
  expertise:
    - "AI"
    - "机器学习"
  tone: "有梗、幽默、专业但不装"
  
examples:
  - tweet: "AI能替代程序员吗"
    comment: "唯一替代不了的职业：背锅侠"
```

### settings.yaml

```yaml
collection:
  max_tweet_age_minutes: 30    # 只收集30分钟内的推文
  max_tweets_per_scan: 10      # 每次最多处理10条

trend_analysis:
  min_score: 40.0              # 最低趋势评分
  
rate_limit:
  delay_seconds: 2.0           # 请求间隔
  max_concurrent_generations: 3 # 并发生成数
```

## 🐛 常见问题

### Q: 评论发布失败（403错误）
**A:** 这就是为什么我们使用 agent-browser！确保：
1. 已经通过浏览器登录
2. 会话名称正确（argo-growth）
3. 浏览器窗口未关闭

### Q: 找不到待评论的推文
**A:** 检查：
1. `influencers.yaml` 配置是否正确
2. 是否有30分钟内的新推文
3. 趋势评分是否过低（降低 `min_score`）

### Q: 评论风格不对
**A:** 
1. 修改 `user_profile.yaml` 中的 examples
2. 使用 'r' 命令优化评论
3. 添加更多风格示例

### Q: agent-browser 找不到元素
**A:** Twitter可能更新了页面：
1. 运行 `agent-browser snapshot -i` 查看元素
2. 根据实际输出调整 `browser_client.py` 中的选择器

## 📊 测试

```bash
# 运行所有测试
./run_tests.sh

# 或
.venv/bin/python -m pytest tests/unit/ -v

# 58个测试，100%通过率
```

## 📚 更多文档

- [README.md](README.md) - 完整文档
- [README_TESTS.md](doc/dev/README_TESTS.md) - 测试文档  
- [CHANGELOG.md](doc/dev/CHANGELOG.md) - 更新日志

## 🎉 开始使用

```bash
python main.py scan
python main.py review
```

祝你涨粉成功！🚀
