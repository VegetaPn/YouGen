#!/bin/bash

CDP_PORT=9222

echo "🛑 Stopping Chrome..."

# 检查是否在运行
if lsof -Pi :$CDP_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    # 获取 PID
    PID=$(lsof -ti :$CDP_PORT)

    echo "   Found Chrome process: PID $PID"

    # 尝试优雅关闭
    kill $PID 2>/dev/null

    # 等待进程结束
    sleep 2

    # 检查是否还在运行
    if lsof -Pi :$CDP_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "   Process still running, force killing..."
        kill -9 $PID 2>/dev/null
        sleep 1
    fi

    # 最终检查
    if lsof -Pi :$CDP_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "❌ Failed to stop Chrome"
        exit 1
    else
        echo "✅ Chrome stopped"
    fi
else
    echo "ℹ️  Chrome is not running on port $CDP_PORT"
fi
