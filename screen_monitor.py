# -*- coding: utf-8 -*-
"""
screen_monitor.py
=================
Background mein har X seconds mein screen capture karta hai.
Jab user kuch poochta hai, latest screenshot AI ko context ke roop mein di jaati hai.
"""

import threading
import time

try:
    import pyautogui
except ImportError:
    pyautogui = None


class ScreenMonitor:
    def __init__(self, interval: float = 2.5):
        self.interval = interval
        self._running = False
        self._thread = None
        self._latest_image = None
        self._lock = threading.Lock()

    def available(self) -> bool:
        return pyautogui is not None

    def start(self, voice=None):
        if not self.available():
            if voice:
                voice.speak("Screen monitor ke liye pyautogui install nahi hai.")
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[screen_monitor] started")

    def stop(self, voice=None):
        self._running = False
        if voice:
            voice.speak("Screen monitoring band kar di.")

    def is_running(self) -> bool:
        return self._running

    def get_latest(self):
        """Return a COPY of latest PIL Image, or None."""
        with self._lock:
            if self._latest_image is None:
                return None
            return self._latest_image.copy()

    def _run(self):
        while self._running:
            try:
                img = pyautogui.screenshot()
                with self._lock:
                    self._latest_image = img
            except Exception as e:
                print(f"[screen_monitor capture error: {e}]")
            time.sleep(self.interval)