import argparse
import asyncio
import threading
import time

import numpy as np
import open_xiaoai_server

from config import APP_CONFIG
from xiaozhi.event import EventManager
from xiaozhi.ref import get_speaker, set_xiaoai
from xiaozhi.services.audio.stream import GlobalStream
from xiaozhi.services.speaker import SpeakerManager
from xiaozhi.utils.base import json_decode
from xiaozhi.utils.logger import logger

ASCII_BANNER = """
▄▖      ▖▖▘    ▄▖▄▖
▌▌▛▌█▌▛▌▚▘▌▀▌▛▌▌▌▐ 
▙▌▙▌▙▖▌▌▌▌▌█▌▙▌▛▌▟▖
  ▌                
                                                                                                                
v1.0.0  by: https://del.wang
"""


class XiaoAI:
    mode = "xiaoai"
    speaker = SpeakerManager()
    async_loop: asyncio.AbstractEventLoop = None

    config = APP_CONFIG.get("xiaoai", {})

    continuous_conversation_mode = config.get("continuous_conversation_mode", True)
    max_listening_retries = config.get("max_listening_retries", 2)  # 最多连续重新唤醒次数
    exit_command_keywords = config.get("exit_command_keywords", ["停止", "退下", "退出", "下去吧"])
    exit_prompt = config.get("exit_prompt", "再见，主人")
    listen_notify_voice_url = config.get("listen_notify_voice_url", "")

    conversing = False # 是否在连续对话中
    current_retries = 0  # 当前重新唤醒次数

    @classmethod
    def setup_mode(cls):
        set_xiaoai(cls)
        parser = argparse.ArgumentParser(
            description="小爱音箱接入小智 AI | by: https://del.wang"
        )
        parser.add_argument(
            "--mode",
            type=str,
            choices=["xiaoai", "xiaozhi"],
            default="xiaoai",
            help="运行模式：【xiaoai】使用小爱音箱的输入输出音频（默认）、【xiaozhi】使用本地电脑的输入输出音频",
        )
        args = parser.parse_args()
        if args.mode == "xiaozhi":
            cls.mode = "xiaozhi"

    @classmethod
    def on_input_data(cls, data: bytes):
        audio_array = np.frombuffer(data, dtype=np.uint16)
        GlobalStream.input(audio_array.tobytes())

    @classmethod
    def on_output_data(cls, data: bytes):
        async def on_output_data_async(data: bytes):
            return await open_xiaoai_server.on_output_data(data)

        asyncio.run_coroutine_threadsafe(
            on_output_data_async(data),
            cls.async_loop,
        )

    @classmethod
    async def run_shell(cls, script: str, timeout: float = 10 * 1000):
        return await open_xiaoai_server.run_shell(script, timeout)

    @classmethod
    async def on_event(cls, event: str):
        event_json = json_decode(event) or {}
        event_data = event_json.get("data", {})
        event_type = event_json.get("event")

        if not event_json.get("event"):
            return

        # 记录所有事件用于调试监听退出
        logger.debug(f"[XiaoAI] 📡 收到事件: {event_type} | 数据: {event_data}")

        if event_type == "instruction" and event_data.get("NewLine"):
            line = json_decode(event_data.get("NewLine"))
            if (
                line
                and line.get("header", {}).get("namespace") == "SpeechRecognizer"
            ):
                header_name = line.get("header", {}).get("name")
                
                if header_name == "RecognizeResult":
                    text = line.get("payload", {}).get("results")[0].get("text")
                    is_final = line.get("payload", {}).get("is_final")
                    is_vad_begin = line.get("payload", {}).get("is_vad_begin")
                    
                    # 只有明确的 is_vad_begin=False 且没有文本时才触发唤醒
                    # 避免重复触发
                    if not text and is_vad_begin is False:
                        logger.wakeup("小爱同学")
                        cls.conversing = True
                        # 开始新的对话，重置重试计数
                        cls.current_retries = 0
                        EventManager.on_interrupt()
                    elif text and is_final:
                        logger.info(f"[XiaoAI] 🔥 收到指令: {text}")
                        if any(cmd in text for cmd in cls.exit_command_keywords):
                            logger.info("[XiaoAI] 👋 收到退出指令，立即退出对话模式")
                            cls.stop_conversation()
                            speaker = get_speaker()
                            await speaker.play(text=cls.exit_prompt)
                        # 收到语音输入，重置重试计数
                        cls.current_retries = 0
                        await EventManager.wakeup(text, "xiaoai")
                    elif is_final and not text:
                        # 小爱监听超时退出：is_final=true and text=""
                        logger.debug("[XiaoAI] 🛑 小爱监听超时自动退出")
                        
                        if cls.continuous_conversation_mode and cls.conversing and cls.current_retries > 0:
                            # 检查是否还能重新唤醒
                            speaker = get_speaker()
                            if cls.current_retries < cls.max_listening_retries:
                                cls.current_retries += 1
                                logger.info(f"[XiaoAI] 🔄 重新唤醒小爱继续监听 ({cls.current_retries}/{cls.max_listening_retries})")
                                await speaker.wake_up(awake=True, silent=True)
                                # 播放短提示音表示继续监听
                                # await speaker.play(url=cls.listen_notify_voice_url)
                            else:
                                # 达到重试上限，退出对话模式
                                logger.info(f"[XiaoAI] 💤 达到重试上限({cls.max_listening_retries}次)，退出连续对话模式")
                                cls.conversing = False
                                cls.current_retries = 0
                                await speaker.play(text=cls.exit_prompt)
            elif  (line
                and line.get("header", {}).get("namespace") == "AudioPlayer"):
                logger.info("[XiaoAI] 收到播放音频事件，立即退出对话模式")
                cls.stop_conversation()
        elif event_type == "playing":
            playing_status = event_data.lower()
            
            get_speaker().status = playing_status
            
            # 连续对话：TTS播放完毕后重新唤醒小爱
            if cls.continuous_conversation_mode and playing_status == "idle" and cls.conversing:
                speaker = get_speaker()
                await speaker.wake_up(awake=True, silent=True)
                cls.current_retries += 1
                logger.info("[XiaoAI] 🎯 TTS播放完毕，重新唤醒小爱等待下一句...")
                # 播放短提示音表示继续监听
                await speaker.play(url=cls.listen_notify_voice_url)
        
        else:
            # 记录未处理的事件类型，可能包含监听退出信息
            logger.debug(f"[XiaoAI] ❓ 未处理的事件类型: {event_type} | 完整数据: {event_json}")

    @classmethod
    def __init_background_event_loop(cls):
        def run_event_loop():
            cls.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls.async_loop)
            cls.async_loop.run_forever()

        thread = threading.Thread(target=run_event_loop, daemon=True)
        thread.start()

    @classmethod
    def __on_event(cls, event: str):
        asyncio.run_coroutine_threadsafe(
            cls.on_event(event),
            cls.async_loop,
        )

    @classmethod
    async def init_xiaoai(cls):
        GlobalStream.on_output_data = cls.on_output_data
        open_xiaoai_server.register_fn("on_input_data", cls.on_input_data)
        open_xiaoai_server.register_fn("on_event", cls.__on_event)
        cls.__init_background_event_loop()
        print("[XiaoAI] 启动小爱音箱服务...")
        print(ASCII_BANNER)
        await open_xiaoai_server.start_server()

    @classmethod
    def stop_conversation(cls):
        '''
         停止连续对话
        '''
        logger.info("[XiaoAI] 停止连续对话")
        cls.conversing = False
        cls.current_retries = 0
