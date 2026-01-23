# 使用真实 Chrome 浏览器避免 Twitter 检测

## 问题

Twitter 能检测到 Playwright/自动化浏览器，显示"此浏览器或应用可能不安全"错误。

## 解决方案

使用真实的 Chrome 浏览器 + CDP (Chrome DevTools Protocol) 连接，支持两种模式：

1. **Headless 模式（推荐）**：Chrome 在后台运行，不显示窗口，不影响使用
2. **Headed 模式**：显示窗口，用于首次登录

## 快速开始

### 首次使用（需要登录）

```bash
# 1. 启动 Chrome 并显示窗口（首次需要登录）
./start_chrome.sh --show-window

# 2. 在 Chrome 窗口中手动登录 Twitter

# 3. 登录成功后，关闭并切换到后台模式
./stop_chrome.sh
./start_chrome.sh

# 4. 正常使用（Chrome 在后台，不显示窗口）
python main.py review
```

### 日常使用（已登录）

```bash
# 1. 启动 Chrome（后台模式，不显示窗口）
./start_chrome.sh

# 2. 正常使用
python main.py scan
python main.py review
python main.py publish

# 3. 使用完毕后（可选）
./stop_chrome.sh
```

## 详细说明

### Headless vs Headed 模式

**Headless 模式（默认）**：
- Chrome 在后台运行，不显示窗口
- 使用 `--headless=new` 参数（新版 headless，更接近真实浏览器）
- 不影响用户使用电脑
- 登录状态保存在 `~/.argo/chrome-profile/`

**Headed 模式（首次登录用）**：
- 显示 Chrome 窗口
- 用于首次登录 Twitter
- 登录后可以关闭，切换回 headless 模式

### 启动脚本使用

```bash
# Headless 模式（默认，后台运行）
./start_chrome.sh

# Headed 模式（显示窗口）
./start_chrome.sh --show-window
# 或
./start_chrome.sh --headed

# 停止 Chrome
./stop_chrome.sh
```

### 手动启动 Chrome（如果不用脚本）

**Headless 模式：**
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.argo/chrome-profile" \
  --disable-gpu \
  --no-sandbox \
  https://twitter.com/home &

# Linux
google-chrome \
  --headless=new \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.argo/chrome-profile" \
  --disable-gpu \
  --no-sandbox \
  https://twitter.com/home &

# Windows (PowerShell)
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --headless=new `
  --remote-debugging-port=9222 `
  --user-data-dir="$env:USERPROFILE\.argo\chrome-profile" `
  https://twitter.com/home
```

**Headed 模式（首次登录）：**
```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.argo/chrome-profile" \
  https://twitter.com/login
```

### 工作原理

1. **首次登录（Headed 模式）**：
   - 启动 Chrome 窗口
   - 手动登录 Twitter
   - 登录信息保存在 `~/.argo/chrome-profile/`

2. **日常使用（Headless 模式）**：
   - Chrome 在后台运行，不显示窗口
   - 从 profile 加载登录状态（已经登录）
   - agent-browser 通过 CDP 连接控制
   - Twitter 看到的是真实的 Chrome 浏览器

### 为什么 Headless 模式不会被检测？

- **传统 headless 问题**：容易被检测（缺少某些浏览器特征）
- **新版 headless (`--headless=new`)**：Chrome 96+ 引入，与真实浏览器几乎完全相同
- **使用 user profile**：保留完整的浏览器状态和登录信息
- **CDP 连接**：不使用 Playwright 的自动化注入

## 优势

✅ **不会被检测** - Twitter 看到的是真实的 Chrome 浏览器（使用 `--headless=new`）
✅ **后台运行** - Headless 模式不显示窗口，不影响使用
✅ **保持登录** - 使用 user-data-dir 保存配置和登录状态
✅ **手动控制** - 需要时可以切换到 headed 模式查看窗口
✅ **调试方便** - 出问题时可以启动窗口模式排查

## 故障排查

### Q: 端口 9222 已被占用

```bash
# 查找占用的进程
lsof -i :9222

# 关闭占用的进程
./stop_chrome.sh
```

### Q: agent-browser 无法连接

```bash
# 检查 Chrome 是否在 9222 端口监听
lsof -i :9222

# 如果没有，重新启动 Chrome
./stop_chrome.sh
./start_chrome.sh
```

### Q: Headless 模式下 Twitter 还是显示"浏览器不安全"

这不应该发生，因为我们使用的是真实的 Chrome + `--headless=new`。如果还是出现：

1. 确认 Chrome 版本是否足够新（96+）：
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version
   ```

2. 尝试先用 headed 模式登录，然后切换回 headless：
   ```bash
   ./stop_chrome.sh
   ./start_chrome.sh --show-window
   # 登录...
   ./stop_chrome.sh
   ./start_chrome.sh
   ```

3. 清除 profile 重新登录：
   ```bash
   ./stop_chrome.sh
   rm -rf ~/.argo/chrome-profile
   ./start_chrome.sh --show-window
   # 重新登录
   ```

### Q: 想查看 Chrome 窗口（调试）

```bash
# 停止 headless 模式
./stop_chrome.sh

# 启动 headed 模式
./start_chrome.sh --show-window

# 然后运行程序，可以看到实际操作
python main.py review
```

### Q: 想关闭 Chrome 但保持登录

直接关闭 Chrome 即可：
```bash
./stop_chrome.sh
```

登录状态会保存在 `~/.argo/chrome-profile` 中。下次启动时会自动恢复。

## 完整工作流

### 首次使用

```bash
# 1. 启动 Chrome 并显示窗口（用于登录）
./start_chrome.sh --show-window

# 2. 在 Chrome 窗口中手动登录 Twitter

# 3. 确认登录成功后，切换到后台模式
./stop_chrome.sh
./start_chrome.sh

# 4. 正常使用（Chrome 在后台，不显示窗口）
python main.py scan
python main.py review
python main.py publish
```

### 日常使用

```bash
# 1. 启动 Chrome（后台模式，不显示窗口）
./start_chrome.sh

# 2. 正常使用
python main.py scan
python main.py review
python main.py publish

# 3. 使用完毕后（可选，Chrome 可以一直在后台运行）
./stop_chrome.sh
```

### 调试模式

```bash
# 1. 启动 Chrome 并显示窗口
./start_chrome.sh --show-window

# 2. 运行程序，可以看到浏览器操作
python main.py review

# 3. 调试完成后，切换回后台模式
./stop_chrome.sh
./start_chrome.sh
```

就是这样！🚀

现在你可以：
- ✅ 后台运行 Chrome，不影响使用
- ✅ 避免 Twitter 检测
- ✅ 随时切换到窗口模式调试
