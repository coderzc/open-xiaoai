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

MIN_SPACE_MB=32
DOWNLOAD_BASE_URL="https://gitee.com/idootop/artifacts/releases/download/open-xiaoai-kws"


check_disk_space() {
    local space_kb=$(df -k "$1" | awk 'NR==2 {print $4}')
    if [ $((space_kb / 1024)) -lt "$MIN_SPACE_MB" ]; then
        echo 1
    else
        echo 0
    fi
}


BASE_DIR="/data"
if [ $(check_disk_space "$BASE_DIR") -eq 1 ]; then
    BASE_DIR="/tmp"
    if [ $(check_disk_space "$BASE_DIR") -eq 1 ]; then
        echo "❌ 磁盘空间不足，请先清理磁盘空间（至少需要 $MIN_SPACE_MB MB 空间）"
        exit 1
    fi
fi


WORK_DIR="$BASE_DIR/open-xiaoai/kws"
KWS_BIN="$WORK_DIR/kws"

if [ ! -d "$WORK_DIR" ]; then
    mkdir -p "$WORK_DIR"
fi

if [ ! -f "$WORK_DIR/models/encoder.onnx" ]; then
    echo "🔥 正在下载模型文件..."
    curl -L -# -o "$WORK_DIR/kws.tar.gz" "$DOWNLOAD_BASE_URL/kws.tar.gz"
    tar -xzvf "$WORK_DIR/kws.tar.gz" -C "$WORK_DIR"
    chmod +x "$KWS_BIN"
    rm "$WORK_DIR/kws.tar.gz"
    echo "✅ 模型文件下载完毕"
fi


CONFIG_DIR="/data/open-xiaoai/kws"

if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
fi

if [ ! -f "$CONFIG_DIR/keywords.txt" ]; then
    echo "n ǐ h ǎo x iǎo zh ì @你好小智" >> "$CONFIG_DIR/keywords.txt"
    echo "d òu b āo d òu b āo @豆包豆包" >> "$CONFIG_DIR/keywords.txt"
    echo "t iān m āo j īng l íng @天猫精灵" >> "$CONFIG_DIR/keywords.txt"
    echo "x iǎo d ù x iǎo d ù @小度小度" >> "$CONFIG_DIR/keywords.txt"
    echo "✅ 默认唤醒词已创建"
fi

if [ "$1" != "--no-monitor" ]; then
    # 如果没有设置 --no-monitor 参数，则启动 monitor 进程
    MONITOR_BIN="$CONFIG_DIR/monitor"
    if [ ! -f "$MONITOR_BIN" ]; then
        curl -L -# -o "$MONITOR_BIN" "$DOWNLOAD_BASE_URL/monitor"
        chmod +x "$MONITOR_BIN"
    fi
    kill -9 `ps|grep "open-xiaoai/kws/monitor"|grep -v grep|awk '{print $1}'` > /dev/null 2>&1 || true
    "$MONITOR_BIN" > /dev/null 2>&1 &
fi

echo "🔥 正在启动唤醒词识别服务，请耐心等待..."
echo "🐢 模型加载较慢，请在语音提示初始化成功后，再使用自定义唤醒词"

kill -9 `ps|grep "open-xiaoai/kws/kws"|grep -v grep|awk '{print $1}'` > /dev/null 2>&1 || true
"$KWS_BIN" \
    --model-type=zipformer2 \
    --tokens="$WORK_DIR/models/tokens.txt" \
    --encoder="$WORK_DIR/models/encoder.onnx" \
    --decoder="$WORK_DIR/models/decoder.onnx" \
    --joiner="$WORK_DIR/models/joiner.onnx" \
    --keywords-file="/data/open-xiaoai/kws/keywords.txt" \
    --provider=cpu \
    --num-threads=1 \
    --chunk-size=1024 \
    noop
