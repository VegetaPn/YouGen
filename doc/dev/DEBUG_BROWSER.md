# Browser 自动化调试指南

## 启用 Debug 模式

使用 `--debug` 参数来显示浏览器窗口并查看详细输出：

```bash
python main.py publish --debug
```

## Debug 模式特性

### 1. 浏览器窗口可见
- 显示真实浏览器窗口
- 可以看到自动化操作过程
- 失败时浏览器不会关闭，可以手动检查

### 2. Snapshot 输出
Debug 模式会输出每次快照的前 2000 字符，帮助你找到正确的元素：

```
=== Snapshot Output (first 2000 chars) ===
button "Reply" [role=button ref=@e1]
textbox "Tweet your reply" [role=textbox ref=@e2]
button "Reply" [role=button ref=@e3]
=== End Snapshot ===
```

### 3. 多种尝试方法
系统会自动尝试多种方法查找输入框：

```
✍️  Filling reply text...
   Trying: role=textbox
   Failed: Command failed: ...
   Trying: placeholder='Post your reply'
   Failed: Command failed: ...
   Trying: CSS selector for contenteditable
   Success!
```

### 4. 失败时暂停
如果发布失败，浏览器窗口会保持打开：

```
❌ Failed to post reply: Could not find reply input box

⚠️  Browser window is still open for inspection
Press Enter to continue...
```

此时你可以：
1. 在浏览器中手动检查页面元素
2. 使用开发者工具查看 DOM 结构
3. 找到正确的选择器
4. 修改 `browser_client.py` 中的代码

## 手动调试流程

### 1. 打开推文页面

```bash
agent-browser --session argo-growth open https://twitter.com/username/status/tweet_id --headed
```

### 2. 获取页面快照

```bash
agent-browser --session argo-growth snapshot -i
```

输出示例：
```
button "Reply" [role=button]
  heading "Post your reply" [role=heading level=2]
  textbox [role=textbox]
  button "Post" [role=button]
```

### 3. 测试选择器

```bash
# 测试点击Reply按钮
agent-browser --session argo-growth find role button click --name "Reply"

# 测试填充输入框
agent-browser --session argo-growth find role textbox fill "测试评论"

# 测试点击Post按钮
agent-browser --session argo-growth find role button click --name "Post"
```

### 4. 使用 ref 引用

```bash
# 如果snapshot输出显示 ref=@e2
agent-browser --session argo-growth fill @e2 "测试评论"
agent-browser --session argo-growth click @e3
```

## 常见问题

### Q: 找不到 Reply 按钮

**检查快照输出**，Reply 按钮可能有不同的名称：
- 英文：`Reply`
- 中文：`回复`
- 日文：`返信`

**解决方法**：修改 `browser_client.py` 添加更多语言支持：

```python
# 尝试多种语言
for reply_text in ["Reply", "回复", "返信"]:
    try:
        self._run_command([
            "find", "text", reply_text,
            "click"
        ])
        break
    except:
        continue
```

### Q: 找不到输入框

**可能的原因**：
1. 页面还在加载 → 增加 `time.sleep()` 时间
2. 需要先点击 Reply 按钮 → 检查是否成功点击
3. 输入框是 contenteditable div → 使用 JavaScript 注入

**调试方法**：

```bash
# 1. 手动打开页面
agent-browser --session argo-growth open <tweet_url> --headed

# 2. 手动点击 Reply
# （在浏览器窗口中点击）

# 3. 获取新快照
agent-browser --session argo-growth snapshot -i

# 4. 查找 textbox 或 contenteditable
```

### Q: 输入框找到了但填充失败

**可能是 contenteditable div**，使用 JavaScript：

```bash
agent-browser --session argo-growth eval "document.querySelector('[contenteditable=\"true\"]').textContent = '测试评论'"
```

或使用 `type` 而不是 `fill`：

```bash
agent-browser --session argo-growth find role textbox type "测试评论"
```

### Q: Post 按钮找不到

**Post 按钮可能有不同的状态**：
- 初始状态：`Reply`
- 填充后：`Post reply`
- 或者：`Tweet`

**检查快照**看实际的按钮文本。

## 修改代码

根据调试结果，你可能需要修改 `argo/growth/core/browser_client.py` 的 `post_reply()` 方法。

### 示例：添加更多选择器

```python
# 添加更多查找输入框的方法
if not input_filled:
    try:
        print("   Trying: aria-label")
        self._run_command([
            "eval",
            f"document.querySelector('[aria-label*=\"reply\"]').textContent = '{text}'"
        ])
        input_filled = True
    except Exception as e:
        print(f"   Failed: {e}")
```

## 完整调试示例

```bash
# 1. 启用 debug 模式发布
python main.py publish --debug

# 输出：
# 🐛 Debug mode enabled - browser window will be visible
# 🌐 Opening tweet: https://twitter.com/...
# 📸 Taking snapshot...
# 
# === Snapshot Output ===
# button "Reply" [role=button]
# ...
# === End Snapshot ===
#
# 💬 Opening reply box...
# 📸 Taking new snapshot after clicking Reply...
# 
# === Updated Snapshot ===
# textbox [role=textbox placeholder="Post your reply"]
# ...
# === End Snapshot ===
#
# ✍️  Filling reply text...
#    Trying: role=textbox
#    Success!
# 🚀 Posting reply...
#    Trying: button with name='Reply'
#    Failed: ...
#    Trying: button with name='Post'
#    Success!
# ✅ Reply posted successfully!

# 2. 如果失败，浏览器窗口会保持打开
#    查看实际的页面元素
#    修改代码后重试
```

## 提示

1. **保持会话**: 使用相同的 `--session argo-growth` 避免重复登录
2. **逐步测试**: 先测试每个步骤，确认可行后再整合
3. **查看快照**: snapshot 输出是最重要的调试信息
4. **等待加载**: Twitter 页面可能需要时间加载，适当增加 `time.sleep()`
5. **使用 eval**: 对于复杂场景，JavaScript 注入很有用

## 获取帮助

如果遇到问题：
1. 查看 snapshot 输出
2. 使用浏览器开发者工具检查元素
3. 尝试不同的选择器方法
4. 参考 agent-browser 文档：`.claude/skills/agent-browser/SKILL.md`
