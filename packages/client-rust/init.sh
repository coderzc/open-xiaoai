#!/bin/sh

cat << 'EOF'

▄▖      ▖▖▘    ▄▖▄▖
▌▌▛▌█▌▛▌▚▘▌▀▌▛▌▌▌▐ 
▙▌▙▌▙▖▌▌▌▌▌█▌▙▌▛▌▟▖
  ▌                 

v1.0.0  by: https://del.wang

EOF

set -e


DOWNLOAD_BASE_URL="https://gitee.com/coderzc/open-xiaoai/releases/download/open-xiaoai-client"


WORK_DIR="/data/open-xiaoai"
CLIENT_BIN="$WORK_DIR/client"
SERVER_ADDRESS="ws://127.0.0.1:4399" # 默认不会连接到任何 server

if [ ! -d "$WORK_DIR" ]; then
    mkdir -p "$WORK_DIR"
fi

# 检查是否仅更新模式
UPDATE_ONLY=false
for arg in "$@"; do
    if [ "$arg" = "-u" ] || [ "$arg" = "--update" ]; then
        UPDATE_ONLY=true
    fi
done

# 下载/更新逻辑
if [ ! -f "$CLIENT_BIN" ] || [ "$UPDATE_ONLY" = true ]; then
    echo "🔥 正在下载 Client 端补丁程序..."
    TEMP_BIN="$CLIENT_BIN.tmp"
    if curl -L -# -o "$TEMP_BIN" "$DOWNLOAD_BASE_URL/client" && [ -f "$TEMP_BIN" ]; then
        chmod +x "$TEMP_BIN"
        mv "$TEMP_BIN" "$CLIENT_BIN"
        echo "✅ Client 端补丁程序下载完毕"
    else
        rm -f "$TEMP_BIN"
        if [ -f "$CLIENT_BIN" ]; then
            echo "⚠️ 下载失败，使用现有版本"
        else
            echo "❌ 下载失败且本地无可用版本，退出"
            exit 1
        fi
    fi
fi

# 如果仅更新模式，更新完成后退出
if [ "$UPDATE_ONLY" = true ]; then
    echo "✅ 仅更新模式，不启动程序"
    exit 0
fi

if [ -f "$WORK_DIR/server.txt" ]; then
    SERVER_ADDRESS=$(cat "$WORK_DIR/server.txt")
fi

echo "🔥 正在启动 Client 端补丁程序..."

kill -9 `ps|grep "open-xiaoai/client"|grep -v grep|awk '{print $1}'` > /dev/null 2>&1 || true

"$CLIENT_BIN" "$SERVER_ADDRESS"
