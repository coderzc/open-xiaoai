import asyncio
import socket
import requests
import sys
import time
import subprocess

async def before_wakeup(speaker, text, source, xiaozhi, xiaoai, app):
    """
    处理收到的用户消息，并决定是否唤醒小智 AI

    - source: 唤醒来源
        - 'kws': 关键字唤醒
        - 'xiaoai': 小爱同学收到用户指令
    """
    if source == "kws":
        # 播放唤醒提示语
        await speaker.play(url="http://192.168.3.6:8080/hello.wav")

        # 给小智发送打招呼消息
        # await xiaozhi.send_text("小智在吗")
        # # 等待小智服务器回复（延长到 5 秒）
        # time.sleep(5)

        return True

    if source == "xiaoai":
        # 打断原来的小爱同学
        await speaker.abort_xiaoai()
        if text == "召唤小智":
            # 停止连续对话
            xiaoai.stop_conversation()
            # 等待 2 秒，让小爱 TTS 恢复可用
            time.sleep(2)
            # 播放唤醒提示语（如果你不使用自带的小爱 TTS，可以去掉上面的延时）
            await speaker.play(url="http://192.168.3.6:8080/hello.wav")
            # 唤醒小智 AI
            return True
        if text.startswith("让龙虾"):
            await app.send_to_openclaw(text.replace("让龙虾", ""))
            return False
            

async def after_wakeup(speaker):
    """
    退出唤醒状态
    """
    await speaker.play(url="http://192.168.3.6:8080/bye.wav")


def _ensure_dependencies(requirements: list[str]):
    """检查并安装缺失的 Python 依赖包。"""
    import importlib.util
    missing_packages = [
        pkg for pkg in requirements if not importlib.util.find_spec(pkg)
    ]

    if not missing_packages:
        return

    print(f"检测到缺失的依赖: {missing_packages}，正在尝试安装...")
    # 假设脚本在一个虚拟环境目录的父目录中运行
    script_dir = os.path.dirname(os.path.abspath(__file__))
    python_executable = os.path.join(script_dir, '.venv', "bin", 'python')
    if not os.path.exists(python_executable):
        # 如果找不到虚拟环境的 python，就使用系统默认的 python
        import sys
        python_executable = sys.executable
        print(f"未找到虚拟环境，使用系统 Python: {python_executable}")

    subprocess.run([python_executable, "-m", "ensurepip"], check=False)
    subprocess.run(
        [python_executable, "-m", "pip", "install", *missing_packages],
        check=True)
    print("依赖安装完成。")

APP_CONFIG = {
    "wakeup": {
        # 自定义唤醒词列表（英文字母要全小写）
        "keywords": [
            "你好小智",
            "小智小智",
            "贾维斯"
            "hi 贾维斯"
            "嘿 贾维斯"
            "你好贾维斯"
        ],
        # 静音多久后自动退出唤醒（秒）
        "timeout": 20,
        # 语音识别结果回调
        "before_wakeup": before_wakeup,
        # 退出唤醒时的提示语（设置为空可关闭）
        "after_wakeup": after_wakeup,
    },
    "vad": {
        # 语音检测阈值（0-1，越小越灵敏）
        "threshold": 0.10,
        # 最小语音时长（ms）
        "min_speech_duration": 250,
        # 最小静默时长（ms）
        "min_silence_duration": 500,
    },
    "xiaozhi": {
        "OTA_URL": "http://192.168.3.6:8003/xiaozhi/ota/",
        "WEBSOCKET_URL": "ws://192.168.3.6:8000/xiaozhi/v1/",
        "WEBSOCKET_ACCESS_TOKEN": "", #（可选）一般用不到这个值
        "DEVICE_ID": "6c:1f:f7:8d:61:b0", #（可选）默认自动生成
        "VERIFICATION_CODE": "", # 首次登陆时，验证码会在这里更新
    },
    "xiaoai": {
        "continuous_conversation_mode": True,
        "exit_command_keywords": ["停止", "退下", "退出", "下去吧"],
        "max_listening_retries": 2,  # 最多连续重新唤醒次数
        "exit_prompt": "再见，主人",
        "continuous_conversation_keywords": ["开启连续对话", "启动连续对话", "我想跟你聊天"]
    },
    # TTS (Text-to-Speech) Configuration
    "tts": {
        "doubao": {
            # 豆包语音合成 API 配置
            # 文档地址: https://www.volcengine.com/docs/6561/1598757?lang=zh
            # 产品地址: https://www.volcengine.com/docs/6561/1871062
            "app_id": "xxxxx",           # 你的 App ID
            "access_key": "xxxxxx",       # 你的 Access Key
            "default_speaker": "zh_female_xiaohe_uranus_bigtts",  # 音色 https://www.volcengine.com/docs/6561/1257544?lang=zh
        }
    },
    # OpenClaw Configuration
    "openclaw": {
        "url": "ws://localhost:18789",  # OpenClaw WebSocket 地址
        "token": "",  # OpenClaw 认证令牌
        "session_key": "main",  # 会话标识
    },
}