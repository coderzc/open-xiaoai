import time
from typing import Callable, Optional

from xiaozhi.services.display.base_display import BaseDisplay


class NoDisplay(BaseDisplay):
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
        pass

    def update_status(self, status: str):
        pass

    def update_text(self, text: str):
        pass

    def update_emotion(self, emotion: str):
        pass

    def start_update_threads(self):
        pass

    def on_close(self):
        pass

    def start(self):
        while True:
            time.sleep(1)
