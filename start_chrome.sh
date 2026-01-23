#!/bin/bash

# Chrome 路径（macOS）
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_DATA_DIR="$HOME/.argo/chrome-profile"
CDP_PORT=9222

# 解析参数
HEADLESS=true
SHOW_WINDOW=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --headed|--show-window)
            HEADLESS=false
            SHOW_WINDOW=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--headed|--show-window]"
            exit 1
            ;;
    esac
done

# 检查 Chrome 是否已经在运行
if lsof -Pi :$CDP_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "✅ Chrome is already running on port $CDP_PORT"

    # 测试连接
    echo "🔍 Testing connection..."
    if agent-browser --cdp $CDP_PORT get url >/dev/null 2>&1 ; then
        CURRENT_URL=$(agent-browser --cdp $CDP_PORT get url 2>/dev/null | head -1)
        echo "✅ Connected! Current URL: $CURRENT_URL"
    else
        echo "⚠️  Chrome is running but agent-browser cannot connect"
        echo "   Try restarting Chrome"
    fi
else
    if [ "$HEADLESS" = true ]; then
        echo "🚀 Starting Chrome in HEADLESS mode on port $CDP_PORT..."
        echo "   (No window will be shown - runs in background)"
    else
        echo "🚀 Starting Chrome with VISIBLE WINDOW on port $CDP_PORT..."
    fi

    # 检查 Chrome 是否存在
    if [ ! -f "$CHROME_PATH" ]; then
        echo "❌ Chrome not found at: $CHROME_PATH"
        echo "Please update CHROME_PATH in this script"
        exit 1
    fi

    # 创建用户数据目录
    mkdir -p "$USER_DATA_DIR"

    # 启动 Chrome
    if [ "$HEADLESS" = true ]; then
        # Headless 模式（后台运行，不显示窗口）
        "$CHROME_PATH" \
          --headless=new \
          --remote-debugging-port=$CDP_PORT \
          --user-data-dir="$USER_DATA_DIR" \
          --disable-gpu \
          --no-sandbox \
          --disable-dev-shm-usage \
          "https://twitter.com/home" &
    else
        # Headed 模式（显示窗口，用于首次登录）
        "$CHROME_PATH" \
          --remote-debugging-port=$CDP_PORT \
          --user-data-dir="$USER_DATA_DIR" \
          "https://twitter.com/home" &
    fi

    sleep 3

    # 测试连接
    echo "🔍 Testing connection..."
    if agent-browser --cdp $CDP_PORT get url >/dev/null 2>&1 ; then
        echo "✅ Chrome started and connected!"
        CURRENT_URL=$(agent-browser --cdp $CDP_PORT get url 2>/dev/null | head -1)
        echo "   Current URL: $CURRENT_URL"
        echo ""

        if [ "$HEADLESS" = true ]; then
            echo "✨ Chrome is running in the background (no window)"
            echo ""
            echo "📝 First time setup:"
            echo "   If you haven't logged in to Twitter yet:"
            echo "   1. Stop headless Chrome: ./stop_chrome.sh"
            echo "   2. Start with window: ./start_chrome.sh --show-window"
            echo "   3. Login manually in the Chrome window"
            echo "   4. Restart in headless: ./start_chrome.sh"
            echo ""
            echo "📝 If already logged in:"
            echo "   Run: python main.py review"
        else
            echo "📝 Next steps:"
            echo "   1. Login to Twitter in the Chrome window (if not already logged in)"
            echo "   2. After login, you can use headless mode: ./stop_chrome.sh && ./start_chrome.sh"
            echo "   3. Run: python main.py review"
        fi
    else
        echo "⚠️  Chrome started but connection failed"
        echo "   Please wait a moment and try again"
    fi
fi

echo ""
echo "ℹ️  To stop Chrome: ./stop_chrome.sh (or killall 'Google Chrome')"
echo "ℹ️  Chrome data is saved in: $USER_DATA_DIR"
