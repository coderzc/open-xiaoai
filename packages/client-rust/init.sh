#!/bin/sh

cat << 'EOF'

▄▖      ▖▖▘    ▄▖▄▖
▌▌▛▌█▌▛▌▚▘▌▀▌▛▌▌▌▐ 
▙▌▙▌▙▖▌▌▌▌▌█▌▙▌▛▌▟▖
  ▌                 

v1.0.0  by: https://del.wang

EOF

set -e


DOWNLOAD_BASE_URL="https://github.com/coderzc/open-xiaoai/releases/download/open-xiaoai-client"


WORK_DIR="/data/open-xiaoai"
CLIENT_BIN="$WORK_DIR/client"
SERVER_ADDRESS="ws://127.0.0.1:4399" # 默认不会连接到任何 server

if [ ! -d "$WORK_DIR" ]; then
    mkdir -p "$WORK_DIR"
fi

# 获取远程 MD5
REMOTE_MD5=$(curl -sL "$DOWNLOAD_BASE_URL/client.md5" | awk '{print $1}')

# 检查本地文件 MD5
LOCAL_MD5=""
if [ -f "$CLIENT_BIN" ]; then
    LOCAL_MD5=$(md5sum "$CLIENT_BIN" 2>/dev/null | awk '{print $1}')
fi

# 对比 MD5，决定是否更新
if [ -n "$REMOTE_MD5" ] && [ "$REMOTE_MD5" = "$LOCAL_MD5" ]; then
    echo "✅ Client 端已是最新版本，跳过下载"
else
    echo "🔥 正在更新/下载 Client 端补丁程序..."
    TEMP_BIN="$CLIENT_BIN.tmp"
    if curl -L -# -o "$TEMP_BIN" "$DOWNLOAD_BASE_URL/client" && [ -f "$TEMP_BIN" ]; then
        chmod +x "$TEMP_BIN"
        mv "$TEMP_BIN" "$CLIENT_BIN"
        echo "✅ Client 端补丁程序更新/下载完毕"
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


if [ -f "$WORK_DIR/server.txt" ]; then
    SERVER_ADDRESS=$(cat "$WORK_DIR/server.txt")
fi

echo "🔥 正在启动 Client 端补丁程序..."

kill -9 `ps|grep "open-xiaoai/client"|grep -v grep|awk '{print $1}'` > /dev/null 2>&1 || true

"$CLIENT_BIN" "$SERVER_ADDRESS"
