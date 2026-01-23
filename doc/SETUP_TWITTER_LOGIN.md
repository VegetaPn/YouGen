# Twitter 登录设置指南

## 🎯 一次设置，永久使用

使用 agent-browser 的状态保存功能，只需登录一次即可永久使用。

## 📝 首次设置步骤

### 1. 登录 Twitter

```bash
agent-browser open https://twitter.com/login --headed
```

这会打开一个浏览器窗口，**手动登录** Twitter：
- 输入用户名/邮箱
- 输入密码
- 完成任何二步验证

### 2. 保存登录状态

登录成功后，在命令行运行：

```bash
agent-browser state save ~/.argo/twitter_state.json
```

你会看到：
```
✅ State saved successfully
```

### 3. 关闭浏览器

```bash
agent-browser close
```

### 4. 完成！

现在可以正常使用了：

```bash
python main.py publish
```

程序会自动：
1. 清理任何旧的浏览器会话
2. 加载保存的状态（包含登录信息）
3. 打开推文页面
4. 发布评论

## 🔄 工作原理

**状态文件** (`~/.argo/twitter_state.json`) 包含：
- Cookies
- LocalStorage
- SessionStorage
- 其他浏览器状态

每次运行时，程序会：
```
1. state load ~/.argo/twitter_state.json  ← 恢复登录状态
2. open <tweet_url>                       ← 已经登录
3. 执行评论操作                          ← 成功！
```

## ✨ 优势

✅ **只需登录一次** - 状态持久化保存
✅ **无需保持浏览器** - 状态保存后可以关闭
✅ **自动会话管理** - 程序自动清理旧会话
✅ **Debug 模式也能用** - 状态在所有模式下生效
✅ **安全** - 状态文件保存在本地 `~/.argo/`

## 🔍 验证状态

检查状态文件是否存在：

```bash
ls -lh ~/.argo/twitter_state.json
```

应该显示：
```
-rw-r--r--  1 user  staff   123K Jan 22 10:00 /Users/user/.argo/twitter_state.json
```

## 🐛 Debug 模式

如果遇到问题，使用 debug 模式查看详细过程：

```bash
python main.py publish --debug
```

这会：
- 显示浏览器窗口
- 输出 snapshot 信息
- 失败时暂停以便检查

## 🆘 故障排查

### Q: 状态文件不存在

**症状**：
```
❌ Twitter session not found. Please login first:
```

**解决**：按照上面的步骤 1-3 重新登录并保存状态

### Q: 状态加载失败

**症状**：
```
❌ Failed to load session state: ...
```

**解决**：
```bash
# 删除旧状态
rm ~/.argo/twitter_state.json

# 重新登录并保存
agent-browser open https://twitter.com/login --headed
# ... 登录 ...
agent-browser state save ~/.argo/twitter_state.json
agent-browser close
```

### Q: 登录过期了

Twitter 登录状态可能会过期（通常很长时间），如果过期：

1. 删除旧状态：`rm ~/.argo/twitter_state.json`
2. 重新执行设置步骤 1-3

### Q: "Browser not launched" 错误

**症状**：
```
✗ Browser not launched. Call launch first.
```

**原因**：有旧的浏览器会话在后台

**解决**：
```bash
# 关闭所有会话
agent-browser close

# 然后重新运行
python main.py publish
```

程序现在会自动清理旧会话，这个问题应该不会再出现。

### Q: 想用不同的 Twitter 账号

```bash
# 方法: 使用不同的状态文件
agent-browser open https://twitter.com/login --headed
# ... 登录另一个账号 ...
agent-browser state save ~/.argo/twitter_state_alt.json
agent-browser close

# 在代码中指定不同的 state_file
# 修改 cli/main.py，传入不同的 state_file 参数
```

## 📋 完整命令参考

```bash
# 首次设置（只需一次）
agent-browser open https://twitter.com/login --headed
agent-browser state save ~/.argo/twitter_state.json
agent-browser close

# 日常使用
python main.py scan      # 扫描并生成评论
python main.py review    # 审核并发布
python main.py publish   # 批量发布

# Debug 模式
python main.py publish --debug

# 检查状态
ls -lh ~/.argo/twitter_state.json

# 清除状态（重新登录）
rm ~/.argo/twitter_state.json

# 如果遇到"Browser not launched"错误
agent-browser close
```

## 🎉 现在开始

```bash
# 1. 首次设置
agent-browser open https://twitter.com/login --headed
# 登录...
agent-browser state save ~/.argo/twitter_state.json
agent-browser close

# 2. 正常使用
python main.py review
```

就是这么简单！🚀
