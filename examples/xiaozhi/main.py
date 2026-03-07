import argparse
import asyncio
import os
import signal
import sys
import time

from xiaozhi.app import MainApp
from xiaozhi.services.api_server import APIServer
from xiaozhi.utils.logger import logger


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


async def _start_api_server():
    """启动 API Server"""
    global api_server
    api_server = APIServer(host="0.0.0.0", port=9092)
    await api_server.start()


def run_services(xiaozhi_mode: bool = False):
    """统一的服务启动入口

    Args:
        xiaozhi_mode: 是否启动小智 AI 完整服务（包括 VAD/KWS/GUI）
    """
    global main_app_instance, api_server, enable_api_server

    mode_name = "小爱音箱 + 小智 AI" if xiaozhi_mode else "仅小爱音箱"
    logger.info(f"[Main] 启动模式：{mode_name}")

    # 统一使用 MainApp 管理所有服务
    main_app_instance = MainApp.instance(enable_xiaozhi=xiaozhi_mode)
    main_app_instance.run()

    # 在 MainApp 的事件循环中启动 API Server
    if enable_api_server:
        asyncio.run_coroutine_threadsafe(_start_api_server(), main_app_instance.loop)

    # 主线程保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def main():
    global connect_xiaozhi
    run_services(xiaozhi_mode=connect_xiaozhi)
    return 0


def setup_graceful_shutdown():
    def signal_handler(_sig, _frame):
        global api_server, main_app_instance

        # 关闭 API Server
        if api_server and main_app_instance:
            asyncio.run_coroutine_threadsafe(api_server.stop(), main_app_instance.loop)

        # 关闭 MainApp
        if main_app_instance:
            main_app_instance.shutdown()

        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)


if __name__ == "__main__":
    setup_config()
    setup_graceful_shutdown()
    sys.exit(main())
