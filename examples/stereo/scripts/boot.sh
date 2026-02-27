#!/bin/sh

exec > /dev/null 2>&1

WORK_DIR="/data/open-xiaoai"
APP_BINARY="$WORK_DIR/stereo"
CONFIG_FILE="$WORK_DIR/stereo.conf"
DOWNLOAD_URL="https://gitee.com/idootop/artifacts/releases/download/open-xiaoai-stereo/stereo"

cat << 'EOF'

▄▖      ▖▖▘    ▄▖▄▖
▌▌▛▌█▌▛▌▚▘▌▀▌▛▌▌▌▐ 
▙▌▙▌▙▖▌▌▌▌▌█▌▙▌▛▌▟▖
  ▌ - Stereo（立体声）          

v1.0.0  by: https://del.wang

EOF

# 等待能够正常访问 baidu.com
while ! ping -c 1 baidu.com > /dev/null 2>&1; do
    echo "🤫 等待网络连接中..."
    sleep 1
done

sleep 3

echo "✅ 网络连接成功"

main() {
    # 1. 确保目录存在
    [ -d "$WORK_DIR" ] || mkdir -p "$WORK_DIR"

    # 2. 检查并下载程序
    if [ ! -f "$APP_BINARY" ]; then
        echo "🚀 正在下载 Stereo 立体声程序..."
        if ! curl -L -# -f -o "$APP_BINARY" "$DOWNLOAD_URL"; then
            echo "❌ 下载失败，请检查网络连接。"
            exit 1
        fi
        chmod +x "$APP_BINARY"
        echo "✅ 程序下载完毕"
    fi

    # 3. 如果运行脚本时带了参数，则覆盖更新配置文件
    if [ $# -gt 0 ]; then
        echo "$*" > "$CONFIG_FILE"
    fi

    # 4. 读取配置
    local ARGS=""
    if [ -f "$CONFIG_FILE" ]; then
        ARGS=$(cat "$CONFIG_FILE")
    fi

    # 5. 停止旧进程
    PID=$(pgrep -f "$APP_BINARY" || true)
    if [ -n "$PID" ]; then
        kill -9 $PID > /dev/null 2>&1 || true
    fi

    # 6. 启动程序
    echo "🔥 Stereo 立体声程序启动中..."
    "$APP_BINARY" $ARGS
}

main "$@"