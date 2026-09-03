# -*- coding: utf-8 -*-
"""
context_sniffer.py  (Phase 2: Live Desktop, Native App & Browser Context Sniffer)
===================================================================================
Captures real-time deep environmental context when an unlearned command is spoken:
1. Foreground window handle, title, process name, and screen coordinates.
2. Browser context sniffer (domain, tab topic, page title, address bar).
3. System state (active resolution, cursor location, open apps list, clipboard).
4. Formats everything into a structured JSON / Prompt block for the Code Synthesizer.
"""

import os
import sys
import re
import json
import time
import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field, asdict

try:
    import win32gui
    import win32process
    import psutil
except ImportError:
    win32gui = None
    win32process = None
    psutil = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None


KNOWN_BROWSERS = {
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "brave.exe": "Brave Browser",
    "firefox.exe": "Mozilla Firefox",
    "opera.exe": "Opera Browser",
    "arc.exe": "Arc Browser"
}

KNOWN_DEV_APPS = {
    "code.exe": "Visual Studio Code",
    "pycharm64.exe": "PyCharm IDE",
    "windowsterminal.exe": "Windows Terminal",
    "cmd.exe": "Command Prompt",
    "powershell.exe": "PowerShell",
    "postman.exe": "Postman API Client"
}


@dataclass
class DesktopContextSnapshot:
    timestamp: float = field(default_factory=time.time)
    active_hwnd: int = 0
    active_process: str = "Unknown"
    active_app_label: str = "Unknown"
    active_title: str = "Unknown"
    is_browser: bool = False
    browser_domain: str = ""
    is_ide: bool = False
    window_rect: dict = field(default_factory=lambda: {"left": 0, "top": 0, "right": 0, "bottom": 0, "width": 0, "height": 0})
    screen_resolution: dict = field(default_factory=lambda: {"width": 1920, "height": 1080})
    cursor_position: dict = field(default_factory=lambda: {"x": 0, "y": 0})
    clipboard_snippet: str = ""
    open_windows: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_markdown_summary(self) -> str:
        """Formats snapshot into clean Markdown for LLM code synthesis."""
        lines = [
            "### Live Desktop & Environmental Context:",
            f"- **Active Application:** {self.active_app_label} (`{self.active_process}`)",
            f"- **Active Window Title:** {self.active_title}",
            f"- **Is Browser:** {self.is_browser}" + (f" (Domain/Topic: {self.browser_domain})" if self.browser_domain else ""),
            f"- **Is Development Tool / IDE:** {self.is_ide}",
            f"- **Window Bounds:** {self.window_rect['width']}x{self.window_rect['height']} at ({self.window_rect['left']}, {self.window_rect['top']})",
            f"- **Screen Resolution:** {self.screen_resolution['width']}x{self.screen_resolution['height']}",
            f"- **Cursor Position:** ({self.cursor_position['x']}, {self.cursor_position['y']})",
            f"- **Open Background Windows:** {', '.join(self.open_windows[:5]) if self.open_windows else 'None'}"
        ]
        if self.clipboard_snippet:
            lines.append(f"- **Clipboard Content Preview:**\n```\n{self.clipboard_snippet[:300]}\n```")
        return "\n".join(lines)


class ContextSniffer:
    """Sniffs full environmental context without disturbing active user workflows."""

    @staticmethod
    def capture_snapshot() -> DesktopContextSnapshot:
        snapshot = DesktopContextSnapshot()

        # 1. Screen Resolution & Cursor
        if pyautogui:
            try:
                w, h = pyautogui.size()
                snapshot.screen_resolution = {"width": w, "height": h}
                cx, cy = pyautogui.position()
                snapshot.cursor_position = {"x": cx, "y": cy}
            except Exception:
                pass

        # 2. Clipboard Snippet
        if pyperclip:
            try:
                clip = pyperclip.paste()
                if clip and clip.strip():
                    snapshot.clipboard_snippet = clip.strip()[:400]
            except Exception:
                pass

        # 3. Active Window & Process Detection
        if win32gui:
            try:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    snapshot.active_hwnd = hwnd
                    title = win32gui.GetWindowText(hwnd)
                    snapshot.active_title = title if title.strip() else "Untitled Window"

                    # Get Process Name
                    if win32process and psutil:
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            pid = abs(pid)
                            if pid > 0 and psutil.pid_exists(pid):
                                p = psutil.Process(pid)
                                pname = p.name().lower()
                                snapshot.active_process = pname
                                
                                # Check Browser & IDE Categories
                                if pname in KNOWN_BROWSERS:
                                    snapshot.is_browser = True
                                    snapshot.active_app_label = KNOWN_BROWSERS[pname]
                                    snapshot.browser_domain = ContextSniffer._infer_browser_domain(title)
                                elif pname in KNOWN_DEV_APPS:
                                    snapshot.is_ide = True
                                    snapshot.active_app_label = KNOWN_DEV_APPS[pname]
                                else:
                                    snapshot.active_app_label = p.name()
                        except Exception:
                            pass

                    # Get Window Rect
                    try:
                        rect = wintypes.RECT()
                        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        w = max(0, rect.right - rect.left)
                        h = max(0, rect.bottom - rect.top)
                        snapshot.window_rect = {
                            "left": rect.left,
                            "top": rect.top,
                            "right": rect.right,
                            "bottom": rect.bottom,
                            "width": w,
                            "height": h
                        }
                    except Exception:
                        pass
            except Exception as e:
                print(f"[context_sniffer active window error: {e}]")

        # 4. Open Background Windows
        if win32gui:
            open_wins = []
            def _enum_cb(h, _):
                try:
                    if win32gui.IsWindowVisible(h):
                        t = win32gui.GetWindowText(h)
                        if t and t.strip() and t != snapshot.active_title:
                            open_wins.append(t.strip())
                except Exception:
                    pass
                return True

            try:
                win32gui.EnumWindows(_enum_cb, None)
                snapshot.open_windows = open_wins[:8]
            except Exception:
                pass

        return snapshot

    @staticmethod
    def _infer_browser_domain(title: str) -> str:
        """Infers website domain or topic from browser window title."""
        if not title:
            return ""
        
        # Common patterns: "Page Title - Domain / Service - Browser"
        clean = title.strip()
        for b_name in ["Google Chrome", "Microsoft Edge", "Brave", "Firefox", "Opera"]:
            clean = re.sub(rf"\s*-\s*{b_name}\s*$", "", clean, flags=re.IGNORECASE)

        # Domain clues
        if "youtube" in clean.lower():
            return "youtube.com"
        elif "github" in clean.lower():
            return "github.com"
        elif "leetcode" in clean.lower():
            return "leetcode.com"
        elif "flipkart" in clean.lower():
            return "flipkart.com"
        elif "amazon" in clean.lower():
            return "amazon.in"
        elif "linkedin" in clean.lower():
            return "linkedin.com"
        elif "chatgpt" in clean.lower() or "openai" in clean.lower():
            return "chatgpt.com"
        elif "mail" in clean.lower() or "gmail" in clean.lower():
            return "mail.google.com"

        return clean


sniffer = ContextSniffer()
