#! /bin/sh

set -e

DOWNLOAD_BASE_URL="https://gitee.com/idootop/artifacts/releases/download"

WORK_DIR="/data/open-xiaoai/scripts"

if [ ! -d "$WORK_DIR" ]; then
    mkdir -p "$WORK_DIR"
fi

if [ ! -f "$WORK_DIR/client.sh" ]; then
    curl -L -# -o "$WORK_DIR/client.sh" "$DOWNLOAD_BASE_URL/open-xiaoai-client/init.sh"
fi

if [ ! -f "$WORK_DIR/kws.sh" ]; then
    curl -L -# -o "$WORK_DIR/kws.sh" "$DOWNLOAD_BASE_URL/open-xiaoai-kws/init.sh"
fi

kill -9 `ps|grep "open-xiaoai/kws/monitor"|grep -v grep|awk '{print $1}'` > /dev/null 2>&1 || true

sh "$WORK_DIR/kws.sh" --no-monitor > /dev/null 2>&1 &

sh "$WORK_DIR/client.sh"
