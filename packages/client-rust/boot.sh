#!/bin/sh

exec > /dev/null 2>&1

cat << 'EOF'

▄▖      ▖▖▘    ▄▖▄▖
▌▌▛▌█▌▛▌▚▘▌▀▌▛▌▌▌▐ 
▙▌▙▌▙▖▌▌▌▌▌█▌▙▌▛▌▟▖
  ▌                 

v1.0.0  by: https://del.wang

EOF

# 等待能够正常访问 baidu.com
while ! ping -c 1 baidu.com > /dev/null 2>&1; do
    echo "🤫 等待网络连接中..."
    sleep 1
done

sleep 3

echo "✅ 网络连接成功"

DOWNLOAD_BASE_URL="https://gitee.com/coderzc/open-xiaoai/releases/download/open-xiaoai-client"


WORK_DIR="/data/open-xiaoai"
CLIENT_BIN="$WORK_DIR/client"
SERVER_ADDRESS="ws://127.0.0.1:4399" # 默认不会连接到任何 server

if [ ! -d "$WORK_DIR" ]; then
    mkdir -p "$WORK_DIR"
fi

# 下载逻辑（仅当本地不存在时）
if [ ! -f "$CLIENT_BIN" ]; then
    echo "🔥 正在下载 Client 端补丁程序..."
    TEMP_BIN="$CLIENT_BIN.tmp"
    if curl -L -# -o "$TEMP_BIN" "$DOWNLOAD_BASE_URL/client" && [ -f "$TEMP_BIN" ]; then
        chmod +x "$TEMP_BIN"
        mv "$TEMP_BIN" "$CLIENT_BIN"
        echo "✅ Client 端补丁程序下载完毕"
    else
        rm -f "$TEMP_BIN"
        echo "❌ 下载失败，退出"
        exit 1
    fi
fi

if [ -f "$WORK_DIR/server.txt" ]; then
    SERVER_ADDRESS=$(cat "$WORK_DIR/server.txt")
fi

echo "🔥 正在启动 Client 端补丁程序..."

kill -9 `ps|grep "open-xiaoai/client"|grep -v grep|awk '{print $1}'` > /dev/null 2>&1 || true

"$CLIENT_BIN" "$SERVER_ADDRESS" > /dev/null 2>&1
