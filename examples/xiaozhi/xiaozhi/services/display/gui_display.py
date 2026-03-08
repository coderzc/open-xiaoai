import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from xiaozhi.services.display.base_display import BaseDisplay


class GuiDisplay(BaseDisplay):
    def __init__(self):
        super().__init__()  # 调用父类初始化
        """创建 GUI 界面"""
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("小爱音箱接入小智 AI 演示")
        self.root.geometry("520x360")

        # 在窗口底部添加作者信息
        self.author_label = ttk.Label(self.root, text="作者: https://del.wang")
        self.author_label.pack(side=tk.BOTTOM, pady=5)

        # 让窗口居中显示
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")

        # 状态显示
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(pady=20)
        self.status_label = ttk.Label(self.status_frame, text="状态: 未连接")
        self.status_label.pack(side=tk.LEFT)

        # 表情显示
        self.emotion_label = tk.Label(self.root, text="😊", font=("Segoe UI Emoji", 32))
        self.emotion_label.pack(padx=20, pady=20)

        # TTS文本显示
        self.tts_text_label = ttk.Label(
            self.root, text="很高兴认识你！", wraplength=250
        )
        self.tts_text_label.pack(padx=20, pady=10)

        # 控制按钮
        self.btn_frame = ttk.Frame(self.root)
        self.btn_frame.pack(pady=20)

        # 手动模式按钮
        self.manual_btn = ttk.Button(self.btn_frame, text="按住说话")
        self.manual_btn.bind("<ButtonPress-1>", self._on_manual_button_press)
        self.manual_btn.bind("<ButtonRelease-1>", self._on_manual_button_release)
        self.manual_btn.pack(side=tk.LEFT, padx=10)

        # 打断按钮
        self.abort_btn = ttk.Button(
            self.btn_frame, text="停止播放", command=self._on_abort_button_click
        )
        self.abort_btn.pack(side=tk.LEFT, padx=10)

        # 对话模式标志
        self.auto_mode = False

        # 回调函数
        self.button_press_callback = None
        self.button_release_callback = None
        self.status_update_callback = None
        self.text_update_callback = None
        self.emotion_update_callback = None
        self.mode_callback = None
        self.auto_callback = None
        self.abort_callback = None

        # 更新队列
        self.update_queue = queue.Queue()

        # 运行标志
        self._running = True

        # 设置窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 启动更新处理
        self.root.after(100, self._process_updates)

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
        self.button_press_callback = press_callback
        self.button_release_callback = release_callback
        self.status_update_callback = status_callback
        self.text_update_callback = text_callback
        self.emotion_update_callback = emotion_callback
        self.mode_callback = mode_callback
        self.auto_callback = auto_callback
        self.abort_callback = abort_callback

    def _process_updates(self):
        """处理更新队列"""
        try:
            while True:
                try:
                    # 非阻塞方式获取更新
                    update_func = self.update_queue.get_nowait()
                    update_func()
                    self.update_queue.task_done()
                except queue.Empty:
                    break
        finally:
            if self._running:
                self.root.after(100, self._process_updates)

    def _on_manual_button_press(self, event):
        """手动模式按钮按下事件处理"""
        try:
            # 更新按钮文本为"松开以停止"
            self.manual_btn.config(text="松开以停止")

            # 调用回调函数
            if self.button_press_callback:
                self.button_press_callback()
        except Exception:
            pass

    def _on_manual_button_release(self, event):
        """手动模式按钮释放事件处理"""
        try:
            # 更新按钮文本为"按住说话"
            self.manual_btn.config(text="按住说话")

            # 调用回调函数
            if self.button_release_callback:
                self.button_release_callback()
        except Exception:
            pass

    def _on_abort_button_click(self):
        """打断按钮点击事件处理"""
        try:
            if self.abort_callback:
                self.abort_callback()
        except Exception:
            pass

    def update_status(self, status: str):
        """更新状态文本"""
        self.update_queue.put(lambda: self.status_label.config(text=f"状态: {status}"))

    def update_text(self, text: str):
        """更新TTS文本"""
        self.update_queue.put(lambda: self.tts_text_label.config(text=text))

    def update_emotion(self, emotion: str):
        """更新表情"""
        self.update_queue.put(lambda: self.emotion_label.config(text=emotion))

    def start_update_threads(self):
        """启动更新线程"""

        def update_loop():
            while self._running:
                try:
                    # 更新状态
                    if self.status_update_callback:
                        status = self.status_update_callback()
                        if status:
                            self.update_status(status)

                    # 更新文本
                    if self.text_update_callback:
                        text = self.text_update_callback()
                        if text:
                            self.update_text(text)

                    # 更新表情
                    if self.emotion_update_callback:
                        emotion = self.emotion_update_callback()
                        if emotion:
                            self.update_emotion(emotion)

                except Exception:
                    pass
                time.sleep(0.1)

        threading.Thread(target=update_loop, daemon=True).start()

    def on_close(self):
        """关闭窗口处理"""
        self._running = False
        self.root.destroy()

    def start(self):
        """启动GUI"""
        try:
            # 启动更新线程
            self.start_update_threads()
            # 在主线程中运行主循环
            self.root.mainloop()
        except Exception:
            pass
