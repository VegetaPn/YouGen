# Argo Growth - 测试文档

## 测试概览

项目包含完整的单元测试套件，覆盖所有核心模块。所有测试使用 **mock** 确保不会发生真实的API调用或推文互动。

### 测试统计

- **总测试数**: 58
- **通过率**: 100%
- **覆盖模块**: 
  - 数据模型 (11 tests)
  - Bird CLI客户端 (10 tests)
  - 推文收集器 (5 tests)
  - 趋势分析器 (8 tests)
  - 评论生成器 (9 tests)
  - 文件存储 (15 tests)

## 运行测试

### 快速运行

```bash
# 使用测试脚本
./run_tests.sh

# 或者直接运行
.venv/bin/python -m pytest tests/unit/ -v
```

### 运行特定测试

```bash
# 只运行models测试
.venv/bin/python -m pytest tests/unit/test_models.py -v

# 运行特定测试类
.venv/bin/python -m pytest tests/unit/test_bird_client.py::TestBirdClient -v

# 运行特定测试方法
.venv/bin/python -m pytest tests/unit/test_models.py::TestTweet::test_tweet_age_minutes -v
```

## 测试架构

### Mock策略

所有可能产生外部副作用的操作都使用mock：

1. **Bird CLI调用** - 使用 `unittest.mock.patch('subprocess.run')`
2. **Claude Agent SDK** - 使用 `@patch('argo.growth.core.comment_generator.query')`
3. **文件系统** - 使用临时目录 `tempfile.mkdtemp()`

### 测试fixtures

在 `tests/conftest.py` 中定义了共享fixtures：

- `temp_data_dir` - 临时数据目录
- `sample_author` - 示例作者数据
- `sample_tweet` - 示例推文数据
- `sample_comment` - 示例评论数据
- `sample_influencer` - 示例大V数据
- `mock_bird_json` - Mock的bird CLI响应
- `user_profile_config` - 用户画像配置

### 测试结构

```
tests/
├── conftest.py              # Pytest配置和共享fixtures
└── unit/                    # 单元测试
    ├── test_models.py       # 数据模型测试
    ├── test_bird_client.py  # Bird客户端测试（mock）
    ├── test_tweet_collector.py  # 推文收集器测试
    ├── test_trend_analyzer.py   # 趋势分析器测试
    ├── test_comment_generator.py  # 评论生成器测试（mock）
    └── test_file_store.py   # 文件存储测试
```

## 关键测试用例

### 数据模型测试
- ✅ 模型创建和序列化
- ✅ JSON往返转换
- ✅ Bird CLI JSON解析
- ✅ 推文年龄计算

### Bird客户端测试
- ✅ 获取用户推文（mock）
- ✅ 搜索推文（mock）
- ✅ 发布回复（mock）
- ✅ 限流错误处理
- ✅ 超时错误处理
- ✅ @符号自动移除

### 推文收集器测试
- ✅ 从大V收集推文
- ✅ 按时间过滤
- ✅ 去重检查
- ✅ 错误处理

### 趋势分析器测试
- ✅ 趋势评分计算
- ✅ 推文排序
- ✅ 最低评分过滤
- ✅ 保护逻辑（确保最少推文数）

### 评论生成器测试
- ✅ 评论生成（mock Agent SDK）
- ✅ 评论优化（使用会话）
- ✅ 前缀清理
- ✅ 批量生成
- ✅ 错误处理

### 文件存储测试
- ✅ 目录结构创建
- ✅ 大V列表保存/加载
- ✅ 推文保存/查询
- ✅ 评论状态管理
- ✅ 去重检查
- ✅ 统计信息

## 安全保证

测试期间以下操作**绝对不会发生**：

- ❌ 真实的X/Twitter API调用
- ❌ 真实的推文发布
- ❌ 真实的评论互动
- ❌ Claude API计费调用
- ❌ 修改配置文件

所有文件操作使用临时目录，测试后自动清理。

## 故障排查

### Python版本问题
确保使用虚拟环境的Python 3.12：
```bash
.venv/bin/python --version  # 应该显示 3.12.x
```

### 缺少依赖
```bash
uv pip install pytest pytest-asyncio pytest-mock
```

### Import错误
确保在项目根目录运行：
```bash
cd /path/to/argo
.venv/bin/python -m pytest tests/unit/ -v
```
