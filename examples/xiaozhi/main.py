import argparse
import asyncio
import os
import signal
import sys
import time

from xiaozhi.xiaoai import XiaoAI
from xiaozhi.app import MainApp
from xiaozhi.services.api_server import APIServer
from xiaozhi.utils.logger import logger
from xiaozhi.ref import set_xiaoai


api_server = None
main_app_instance = None

# 启动配置（从环境变量读取）
connect_xiaozhi = False  # 是否连接小智 AI
enable_api_server = False  # 是否开启 API Server


def setup_config():
    """解析命令行参数和环境变量"""
    global connect_xiaozhi, enable_api_server

    parser = argparse.ArgumentParser(description="小爱音箱接入 Open XiaoAI")
    parser.parse_args()

    # 从环境变量读取配置
    connect_xiaozhi = os.environ.get("XIAOZHI_ENABLE", "").lower() in ("1", "true", "yes")
    enable_api_server = os.environ.get("API_SERVER_ENABLE", "").lower() in ("1", "true", "yes")

    logger.info(f"[Main] Config: XIAOZHI_ENABLE={os.environ.get('XIAOZHI_ENABLE', 'not set')}, API_SERVER_ENABLE={os.environ.get('API_SERVER_ENABLE', 'not set')}")
    logger.info(f"[Main] Parsed: connect_xiaozhi={connect_xiaozhi}, enable_api_server={enable_api_server}")


async def _run_xiaoai():
    """启动小爱音箱服务（会阻塞直到服务器停止）"""
    set_xiaoai(XiaoAI)
    await XiaoAI.init_xiaoai()


def run_without_xiaozhi():
    """不连接小智 AI，只启动小爱音箱服务 + API Server"""
    global api_server, enable_api_server

    logger.info("[Main] 启动模式：仅小爱音箱（不连接小智 AI）")

    # 创建独立的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def main():
        global api_server
        # 先启动 API Server（如果不启用 XiaoAI 单独启动）
        if enable_api_server:
            api_server = APIServer(host="0.0.0.0", port=9092)
            await api_server.start()

        # 启动小爱音箱服务（这会阻塞，所以用 gather 同时运行）
        await _run_xiaoai()

    # 保持运行
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        if api_server:
            loop.run_until_complete(api_server.stop())
        loop.close()


def run_with_xiaozhi():
    """连接小智 AI，启动完整服务"""
    global main_app_instance, api_server, enable_api_server

    logger.info("[Main] 启动模式：小爱音箱 + 小智 AI")

    # 启动 MainApp（包含小爱音箱服务、VAD、KWS、小智连接等）
    main_app_instance = MainApp.instance()
    main_app_instance.run()

    # 按需启动 API Server（在 MainApp 的事件循环中）
    if enable_api_server:
        api_server = APIServer(host="0.0.0.0", port=9092)
        asyncio.run_coroutine_threadsafe(api_server.start(), main_app_instance.loop)

    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def main():
    global connect_xiaozhi
    if connect_xiaozhi:
        run_with_xiaozhi()
    else:
        run_without_xiaozhi()
    return 0


def setup_graceful_shutdown():
    def signal_handler(_sig, _frame):
        global api_server, main_app_instance

        # 关闭 API Server
        if api_server:
            if main_app_instance and main_app_instance.loop:
                asyncio.run_coroutine_threadsafe(api_server.stop(), main_app_instance.loop)
            else:
                asyncio.get_event_loop().run_until_complete(api_server.stop())

        # 关闭 MainApp（如果已创建）
        if main_app_instance:
            main_app_instance.shutdown()

        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    setup_config()
    setup_graceful_shutdown()
    sys.exit(main())
