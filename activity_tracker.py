# -*- coding: utf-8 -*-
"""
activity_tracker.py
===================
Continuous Workflow & Activity Awareness Engine for Real Jarvis.
Tracks active applications, file edits, clipboard changes, and generates
workflow timelines so Jarvis always knows what the user is working on.
"""

import threading
import time
import datetime
from collections import deque

try:
    import win32gui
    import win32process
    import psutil
except ImportError:
    win32gui = None
    win32process = None
    psutil = None

try:
    import pyperclip
except ImportError:
    pyperclip = None


class ActivityTracker:
    """
    Background daemon that monitors user workflow:
    - Active app transitions
    - Clipboard changes
    - Active working documents
    - Timeline history
    """
    def __init__(self, max_history: int = 50):
        self.running = False
        self._thread = None
        self.history = deque(maxlen=max_history)
        self.clipboard_history = deque(maxlen=20)
        self.current_window = None
        self.current_app = None
        self.current_start_time = None
        self._last_clip_text = ""
        self._lock = threading.Lock()

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print("[activity_tracker] Continuous workflow monitoring started.")

    def stop(self):
        self.running = False

    def _get_active_window_info(self):
        if not win32gui:
            return None, None
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd)
                app_name = None
                if win32process and psutil:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        app_name = psutil.Process(pid).name()
                    except Exception:
                        pass
                return title, app_name
        except Exception:
            pass
        return None, None

    def _monitor_loop(self):
        while self.running:
            try:
                # 1. Track Active Window
                title, app = self._get_active_window_info()
                now = datetime.datetime.now()
                
                with self._lock:
                    if title and title != self.current_window:
                        if self.current_window and self.current_start_time:
                            duration = int((now - self.current_start_time).total_seconds())
                            if duration >= 3:  # Only record if focused for >= 3 seconds
                                self.history.append({
                                    "title": self.current_window,
                                    "app": self.current_app or "App",
                                    "start": self.current_start_time.strftime("%H:%M:%S"),
                                    "duration_sec": duration,
                                })
                        self.current_window = title
                        self.current_app = app
                        self.current_start_time = now

                # 2. Track Clipboard Changes
                if pyperclip:
                    try:
                        clip_text = pyperclip.paste()
                        if clip_text and clip_text.strip() and clip_text != self._last_clip_text:
                            self._last_clip_text = clip_text
                            clean = clip_text.strip()
                            with self._lock:
                                self.clipboard_history.append({
                                    "timestamp": now.strftime("%H:%M:%S"),
                                    "text": clean[:800],
                                    "length": len(clean),
                                    "app_context": self.current_window or "Unknown"
                                })
                    except Exception:
                        pass

            except Exception as e:
                print(f"[activity_tracker loop error: {e}]")

            time.sleep(1.5)

    def get_timeline_summary(self, limit: int = 8) -> str:
        """Returns human-readable timeline of recent user activities."""
        with self._lock:
            if not self.history and not self.current_window:
                return "Abhi koi activity record nahi hui hai."
            
            lines = []
            for item in list(self.history)[-limit:]:
                dur_str = f"{item['duration_sec']}s" if item['duration_sec'] < 60 else f"{item['duration_sec']//60}m"
                lines.append(f"[{item['start']}] {item['app']} - '{item['title']}' ({dur_str})")

            if self.current_window:
                now = datetime.datetime.now()
                dur = int((now - self.current_start_time).total_seconds()) if self.current_start_time else 0
                lines.append(f"[Abhi] Active: {self.current_app or 'App'} - '{self.current_window}' ({dur}s)")

            return "\n".join(lines)

    def get_latest_clipboard(self) -> dict:
        """Returns most recent clipboard entry."""
        with self._lock:
            if self.clipboard_history:
                return self.clipboard_history[-1]
            return {"text": self._last_clip_text, "app_context": self.current_window or "None"}

    def get_current_task_description(self) -> str:
        """Infers current task from active window title and app."""
        with self._lock:
            title = self.current_window or ""
            app = (self.current_app or "").lower()

            if "code" in app or "pycharm" in app or "studio" in app:
                return f"Coding/Editing in {self.current_app} (File/Project: {title})"
            elif "chrome" in app or "msedge" in app or "firefox" in app or "brave" in app:
                return f"Web Browsing / Research (Page: {title})"
            elif "cmd" in app or "powershell" in app or "terminal" in app:
                return f"Terminal / CLI Operations (Window: {title})"
            elif "excel" in app or "calc" in app:
                return f"Working on Spreadsheet/Data (Title: {title})"
            elif "word" in app or "notepad" in app or "writer" in app:
                return f"Writing / Note Taking (Document: {title})"
            elif title:
                return f"Working on {app or 'Desktop'} (Title: {title})"
            return "Active application context not available."


# Global singleton instance
tracker = ActivityTracker()
