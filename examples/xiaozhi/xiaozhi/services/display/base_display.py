from abc import ABC, abstractmethod
from typing import Callable, Optional


class BaseDisplay(ABC):
    """显示接口的抽象基类"""

    def __init__(self):
        self.current_volume = 70  # 默认音量

    @abstractmethod
    def set_callbacks(
        self,
        press_callback: Optional[Callable] = None,
        release_callback: Optional[Callable] = None,
        status_callback: Optional[Callable] = None,
        text_callback: Optional[Callable] = None,
        emotion_callback: Optional[Callable] = None,
        mode_callback: Optional[Callable] = None,
        auto_callback: Optional[Callable] = None,
        abort_callback: Optional[Callable] = None,
    ):
        """设置回调函数"""
        pass

    @abstractmethod
    def update_status(self, status: str):
        """更新状态文本"""
        pass

    @abstractmethod
    def update_text(self, text: str):
        """更新TTS文本"""
        pass

    @abstractmethod
    def update_emotion(self, emotion: str):
        """更新表情"""
        pass

    @abstractmethod
    def start(self):
        """启动显示"""
        pass

    @abstractmethod
    def on_close(self):
        """关闭显示"""
        pass
