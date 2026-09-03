# -*- coding: utf-8 -*-
"""
desktop_context.py
===================
Jarvis ko computer ke "context" ki jaankari deta hai - kaunsa app/window
abhi active hai, kitni windows khuli hain, wagera. Ye bhi ON-DEMAND hai
(jab pucho tabhi check karta hai), hamesha background me track nahi karta.

NOTE: Browser ke andar "kitne TABS khule hain" ye batana possible nahi hai
isse - Windows ko sirf itna pata hota hai ki "Chrome" ki ek window khuli
hai, uske andar kitne tabs hain ye sirf browser khud jaanta hai (extension
ke bina access nahi milta). Isliye ye sirf window-level info deta hai.
"""

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


def available() -> bool:
    return win32gui is not None


def get_active_window():
    """Return (window_title, app_process_name) - dono None agar na mile."""
    if not win32gui:
        return None, None
    try:
        hwnd = win32gui.GetForegroundWindow()
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
        return None, None


def list_open_windows(limit: int = 20):
    """Saari visible windows ke titles ki list (khaali titles skip)."""
    if not win32gui:
        return []
    windows = []

    def _enum(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                windows.append(title)

    try:
        win32gui.EnumWindows(_enum, None)
    except Exception:
        pass
    return windows[:limit]


def cursor_position():
    if not pyautogui:
        return None
    return pyautogui.position()


def get_clipboard_content(max_chars: int = 1000) -> str:
    """Returns current text on Windows clipboard."""
    try:
        import pyperclip
        text = pyperclip.paste()
        if text and text.strip():
            clean = text.strip()
            if len(clean) > max_chars:
                return clean[:max_chars] + "... (truncated)"
            return clean
    except Exception:
        pass
    return ""


def get_current_workflow_state() -> dict:
    """Returns rich snapshot of what the user is currently working on."""
    active_title, active_app = get_active_window()
    clip = get_clipboard_content(max_chars=400)
    windows = list_open_windows(limit=8)
    
    return {
        "active_title": active_title or "None",
        "active_app": active_app or "None",
        "clipboard": clip,
        "open_windows": windows,
    }


import time
_last_ctx_time = 0.0
_cached_ctx_summary = ""

def build_context_summary() -> str:
    """
    Ek comprehensive workflow summary banata hai jo AI ko bheja jaata hai
    taaki use pata ho user computer pe kya kar raha hai (cached for 1.5s).
    """
    global _last_ctx_time, _cached_ctx_summary
    now = time.time()
    if now - _last_ctx_time < 1.5 and _cached_ctx_summary:
        return _cached_ctx_summary

    state = get_current_workflow_state()
    lines = []
    
    if state["active_title"] != "None":
        lines.append(f"Currently Active App/Window: \"{state['active_title']}\" (Process: {state['active_app']})")
    if state["clipboard"]:
        lines.append(f"User Recent Clipboard Text: \"{state['clipboard']}\"")
    if state["open_windows"]:
        lines.append(f"Other Open Windows: {', '.join(state['open_windows'])}")
        
    _cached_ctx_summary = "\n".join(lines) if lines else "Active desktop context unavailable."
    _last_ctx_time = now
    return _cached_ctx_summary

