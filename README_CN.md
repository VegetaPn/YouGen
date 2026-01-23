# YouGen - X/Twitter Growth Automation

通过评论大V推文来增长X粉丝的半自动化工具。

[English Documentation](README.md)

## 特性

- 🤖 使用 Claude Opus 4.5 生成个性化评论
- 📊 趋势分析：自动筛选热门推文
- ✋ 半自动模式：人工审核后发布
- 🎯 智能去重：避免重复评论同一作者
- 💾 轻量存储：JSON文件存储，无需数据库

## 前置要求

1. **bird CLI** - X/Twitter 命令行工具
   ```bash
   brew install steipete/tap/bird
   bird login
   ```

2. **Python 3.10+** 和依赖
   ```bash
   uv venv --python 3.12
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

3. **Claude API Key**
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"
   ```

## 快速开始

### 1. 配置大V列表

编辑 `yougen/config/influencers.yaml`:

```yaml
influencers:
  - username: "example_user"
    priority: "high"
    check_interval: 15
    topics: ["AI", "Tech"]
```

**注意**：修改 `influencers.yaml` 后，下次运行 `scan` 命令时会自动重新加载。程序会比较文件修改时间，如果 YAML 比 `data/influencers/managed.json` 新，就会自动更新。

### 2. 配置用户画像

编辑 `yougen/config/user_profile.yaml` 来定制你的评论风格。

### 3. 运行工作流

```bash
# 1. 检查认证
python main.py auth

# 2. 扫描推文并生成评论
python main.py scan

# 3. 审核评论（交互式）
python main.py review

# 4. 发布已批准的评论
python main.py publish

# 5. 查看统计
python main.py stats
```

## 命令说明

### `python main.py scan`
扫描大V推文，分析趋势，生成评论。

- 只收集最近30分钟的推文
- 按趋势评分排序
- 最多生成10条评论
- 评论保存为 `pending` 状态

### `python main.py review`
交互式审核待处理评论。

可用操作：
- `[p]` Publish now - 立即发布
- `[a]` Approve - 批准稍后发布
- `[r]` Refine - 优化评论（使用Agent会话记忆）
- `[s]` Skip - 跳过
- `[q]` Quit - 退出审核

### `python main.py publish`
批量发布所有已批准的评论。

### `python main.py stats`
显示统计信息：
- 评论状态分布
- 最近发布数量
- 大V列表

## 目录结构

```
yougen/
├── config/               # 配置文件
│   ├── user_profile.yaml  # 用户画像
│   ├── influencers.yaml   # 大V列表
│   └── settings.yaml      # 系统设置
├── core/                 # 核心模块
│   ├── bird_client.py     # bird CLI封装
│   ├── tweet_collector.py # 推文收集
│   ├── trend_analyzer.py  # 趋势分析
│   └── comment_generator.py # 评论生成
├── storage/              # 存储模块
│   ├── models.py          # 数据模型
│   └── file_store.py      # JSON存储
├── cli/                  # CLI模块
│   ├── main.py            # 主入口
│   └── reviewer.py        # 交互审核
└── data/                 # 数据目录
    ├── influencers/       # 大V数据
    ├── tweets/            # 推文（按日期）
    └── comments/          # 评论（按状态）
        ├── pending/
        ├── approved/
        ├── rejected/
        └── published/
```

## 工作原理

### 1. 推文收集
- 从配置的大V列表获取最新推文
- 过滤最近30分钟内的推文
- 去重：排除已处理的推文和最近24小时评论过的作者

### 2. 趋势分析
计算趋势评分（0-100）：
```
加权互动数 = 点赞×1.0 + 转发×2.0 + 评论×1.5
每分钟互动率 = 加权互动数 / 推文年龄（分钟）
趋势评分 = min(每分钟互动率 / 5 × 50, 100)
```

过滤规则：
- 默认阈值：40分
- 保护逻辑：至少保留3条推文

### 3. 评论生成
使用 Claude Agent SDK：
- 模型：Claude Opus 4.5
- 系统提示：注入用户画像和风格示例
- 会话记忆：支持多轮优化

### 4. 人工审核
交互式CLI：
- 显示推文上下文和互动数据
- 预览生成的评论
- 支持实时优化（使用会话上下文）
- 批准后立即发布或稍后批量发布

## 配置说明

### settings.yaml
```yaml
collection:
  max_tweet_age_minutes: 30    # 推文最大年龄
  max_tweets_per_scan: 10      # 每次扫描最多推文数

trend_analysis:
  min_score: 40.0              # 最低趋势评分
  like_weight: 1.0             # 点赞权重
  retweet_weight: 2.0          # 转发权重
  reply_weight: 1.5            # 评论权重

rate_limit:
  delay_seconds: 2.0           # bird CLI请求间隔
  max_concurrent_generations: 3 # 最大并发生成数
```

## 最佳实践

1. **认证管理**
   - 确保 `bird login` 认证正常
   - 定期运行 `python main.py auth` 检查状态

2. **评论风格**
   - 在 `user_profile.yaml` 中添加真实的评论示例
   - 风格保持一致：有梗但不失专业

3. **发布频率**
   - 避免短时间大量发布
   - 使用 `python main.py stats` 监控发布频率

4. **大V管理**
   - 根据质量调整 `priority` 和 `check_interval`
   - 定期review并更新大V列表

5. **趋势评分调优**
   - 根据实际效果调整 `min_score`
   - 调整权重以匹配你的目标人群

## 故障排查

### bird CLI认证失败
```bash
bird logout
bird login
```

### Claude API错误
检查API key和base URL：
```bash
echo $ANTHROPIC_API_KEY
echo $ANTHROPIC_BASE_URL  # 如果使用自定义endpoint
```

### 导入错误
确保在项目根目录运行：
```bash
cd /path/to/YouGen
python main.py scan
```

### 推文过滤过于严格
降低 `settings.yaml` 中的 `min_score`，或增加 `max_tweet_age_minutes`。

## 开发说明

### 导入规范
使用绝对导入：
```python
from yougen.storage.models import Tweet
from yougen.core.bird_client import BirdClient
```

### 运行测试
```bash
# TODO: 添加测试
pytest tests/
```

## License

MIT

## 配置管理

### Influencers配置自动重载

程序会自动检测 `influencers.yaml` 的修改：

1. **首次运行**：从 `influencers.yaml` 加载配置，保存到 `data/influencers/managed.json`
2. **后续运行**：比较两个文件的修改时间
   - 如果 YAML 比 JSON 新 → 自动重新加载 ✅
   - 如果 YAML 未修改 → 使用现有的 JSON

这意味着：
- ✅ 修改 `influencers.yaml` 后直接运行即可，无需手动删除 JSON
- ✅ 如果只是手动修改了 `managed.json`（不推荐），不会被覆盖
- ⚠️  建议始终修改 YAML 配置文件，不要直接修改 JSON

### 评论语言匹配

评论生成器会自动检测推文语言，并使用相同语言回复：

- 推文是英文 → 评论用英文
- 推文是中文 → 评论用中文
- 推文是日文 → 评论用日文

这是通过在 system prompt 中明确指示 Claude 匹配语言实现的。

## 使用 agent-browser 发布评论

由于 bird CLI 容易被 Twitter 检测为自动化操作（HTTP 403错误），系统默认使用 **agent-browser** 来模拟真实浏览器操作发布评论。

### 首次使用设置

1. **安装 agent-browser skill** （应该已安装）
   
2. **手动登录 Twitter**
   ```bash
   agent-browser --session argo-growth open https://twitter.com/login --headed
   ```
   在弹出的浏览器中登录Twitter，然后保持会话

3. **运行工作流**
   ```bash
   # 正常使用
   python main.py review   # 审核并发布（使用浏览器）
   python main.py publish  # 发布已批准的评论（使用浏览器）
   ```

### 工作原理

- **review/publish 命令默认使用 agent-browser**
- 首次发布评论时会检查 Twitter 登录状态
- 使用浏览器自动化操作（点击Reply按钮、填写内容、发布）
- 比 bird CLI 更不容易被检测为 bot

### agent-browser 优势

✅ **模拟真实用户行为** - 使用真实浏览器，不会被识别为API调用
✅ **保持登录状态** - 通过cookies保持会话
✅ **支持复杂交互** - 处理各种前端逻辑
✅ **避免限流** - 不会触发API rate limit

### 故障排查

#### 登录检查失败
```bash
# 重新登录
agent-browser --session argo-growth open https://twitter.com/login --headed
# 手动登录后重试
```

#### 找不到Reply按钮
Twitter的页面结构可能更新。如果发生这种情况：
1. 手动在浏览器中打开推文
2. 使用 `agent-browser snapshot -i` 查看元素
3. 根据实际元素调整 `browser_client.py` 中的选择器

#### 回退到 bird CLI
如果需要使用 bird CLI（不推荐，容易被限流）：
```bash
# 修改代码，在 main.py 的 review_comments 和 publish_approved 方法中
# 将 use_browser=True 改为 use_browser=False
```

---

## 🔑 Twitter 登录设置（重要）

**推荐方式：使用真实 Chrome 浏览器（Headless 模式，后台运行）**

### 首次使用

```bash
# 1. 启动 Chrome 并显示窗口（首次需要登录）
./start_chrome.sh --show-window

# 2. 在 Chrome 中手动登录 Twitter

# 3. 登录后切换到后台模式（不显示窗口）
./stop_chrome.sh
./start_chrome.sh

# 4. 正常使用
python main.py publish
```

### 日常使用

```bash
# 1. 启动 Chrome（后台运行，不显示窗口）
./start_chrome.sh

# 2. 正常使用
python main.py review
```

详细说明请查看 [SETUP_TWITTER_REAL_CHROME.md](doc/SETUP_TWITTER_REAL_CHROME.md)

### 工作原理
- 使用真实的 Chrome 浏览器 Headless 模式（`--headless=new`）
- Chrome 在后台运行，**不显示窗口，不影响使用**
- agent-browser 通过 CDP (Chrome DevTools Protocol) 连接
- Twitter 看到的是正常的 Chrome，不会检测为自动化
- 登录状态保存在 `~/.argo/chrome-profile/`
- 需要调试时可以切换到窗口模式

### 替代方案（不推荐）

如果你想使用 agent-browser 的自动化模式（可能被 Twitter 检测）：

```bash
# 禁用 CDP 模式
python main.py publish --no-cdp
```

参考 [SETUP_TWITTER_LOGIN.md](doc/SETUP_TWITTER_LOGIN.md)（可能遇到"浏览器不安全"错误）
