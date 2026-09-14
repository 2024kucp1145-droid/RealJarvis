# -*- coding: utf-8 -*-
"""
platform_compat.py
==================
Cross-Platform Compatibility Layer for RealJarvis.

Detects OS at runtime and routes all platform-specific calls through
a unified API. Windows code is completely untouched — Linux gets a
parallel implementation via subprocess / xdotool / espeak-ng.

Usage (in any file):
    from platform_compat import compat
    compat.beep()
    compat.get_idle_ms()
    compat.lock_screen()
"""

import os
import sys
import time
import subprocess
import platform

_OS = platform.system()   # "Windows" | "Linux" | "Darwin"
IS_WINDOWS = _OS == "Windows"
IS_LINUX   = _OS == "Linux"
IS_MAC     = _OS == "Darwin"

# ─────────────────────────────────────────────
#  Windows-only imports (guarded)
# ─────────────────────────────────────────────
if IS_WINDOWS:
    import ctypes
    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    try:
        import winsound as _winsound
        _WINSOUND_OK = True
    except ImportError:
        _WINSOUND_OK = False


def _run(cmd: list, silent: bool = True) -> str:
    """Helper: run a subprocess command, return stdout."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL if silent else None,
            timeout=5
        )
        return result.stdout.decode(errors="ignore").strip()
    except Exception:
        return ""


# ─────────────────────────────────────────────
#  1. IDLE TIME (keyboard/mouse last input)
# ─────────────────────────────────────────────
def get_idle_ms() -> float:
    """
    Returns milliseconds since last keyboard/mouse activity.
    Windows: GetLastInputInfo  |  Linux: xprintidle or Xlib
    """
    if IS_WINDOWS:
        try:
            info = _LASTINPUTINFO()
            info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
            elapsed = ctypes.windll.kernel32.GetTickCount() - info.dwTime
            return max(0.0, float(elapsed))
        except Exception:
            return 999_000.0

    if IS_LINUX:
        # Try xprintidle first (most accurate)
        out = _run(["xprintidle"])
        if out.isdigit():
            return float(out)
        # Fallback: xdotool
        out = _run(["xdotool", "getactivewindow"])
        # xdotool can't measure idle — return large value so typing gate stays open
        return 999_000.0

    return 999_000.0


def get_idle_seconds() -> float:
    return get_idle_ms() / 1000.0


# ─────────────────────────────────────────────
#  2. BEEP / CHIME
# ─────────────────────────────────────────────
def beep(freq_hz: int = 880, duration_ms: int = 100):
    """
    Play a system beep.
    Windows: winsound.Beep  |  Linux: paplay / beep command
    """
    if IS_WINDOWS and _WINSOUND_OK:
        try:
            _winsound.Beep(freq_hz, duration_ms)
        except Exception:
            pass
        return

    if IS_LINUX:
        # Try 'beep' command (needs: sudo apt install beep)
        _run(["beep", "-f", str(freq_hz), "-l", str(duration_ms)])


def wake_chime():
    """Two-tone ascending chime used on wake-word detection."""
    beep(880, 70)
    beep(1320, 90)


# ─────────────────────────────────────────────
#  3. OFFLINE TTS (espeak-ng on Linux)
# ─────────────────────────────────────────────
def offline_speak(text: str, rate: int = 175):
    """
    Speak text using offline TTS.
    Windows: pyttsx3 (caller handles it)  |  Linux: espeak-ng
    Returns True if handled, False if caller should fallback.
    """
    if IS_LINUX:
        try:
            subprocess.Popen(
                ["espeak-ng", "-s", str(rate), text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except FileNotFoundError:
            # espeak-ng not installed
            print("[TTS] espeak-ng not found. Install: sudo apt install espeak-ng")
            return False
        except Exception:
            return False
    return False   # Windows: caller uses pyttsx3


# ─────────────────────────────────────────────
#  4. POWER / SESSION COMMANDS
# ─────────────────────────────────────────────
def lock_screen():
    if IS_WINDOWS:
        ctypes.windll.user32.LockWorkStation()
    elif IS_LINUX:
        # Try multiple lock methods in order
        for cmd in [
            ["loginctl", "lock-session"],
            ["gnome-screensaver-command", "--lock"],
            ["xdg-screensaver", "lock"],
            ["i3lock"],
        ]:
            if _run(["which", cmd[0]]):
                _run(cmd)
                return


def sleep_system():
    if IS_WINDOWS:
        subprocess.run(["powercfg", "/hibernate", "off"], shell=True)
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
    elif IS_LINUX:
        _run(["systemctl", "suspend"])


def shutdown_system():
    if IS_WINDOWS:
        subprocess.run(["shutdown", "/s", "/t", "5"])
    elif IS_LINUX:
        _run(["shutdown", "-h", "now"])


def restart_system():
    if IS_WINDOWS:
        subprocess.run(["shutdown", "/r", "/t", "5"])
    elif IS_LINUX:
        _run(["reboot"])


# ─────────────────────────────────────────────
#  5. FOREGROUND WINDOW TITLE
# ─────────────────────────────────────────────
def get_active_window_title() -> str:
    """
    Returns the title of the currently focused window.
    Windows: win32gui  |  Linux: xdotool
    """
    if IS_WINDOWS:
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(hwnd) or ""
        except Exception:
            return ""

    if IS_LINUX:
        wid = _run(["xdotool", "getactivewindow"])
        if wid:
            return _run(["xdotool", "getwindowname", wid])
        return ""

    return ""


def focus_window_by_title(title: str) -> bool:
    """
    Brings window matching title to foreground.
    Windows: win32gui  |  Linux: wmctrl / xdotool
    """
    if IS_WINDOWS:
        try:
            import win32gui, win32con
            found = []
            def _cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd) and title.lower() in win32gui.GetWindowText(hwnd).lower():
                    found.append(hwnd)
            win32gui.EnumWindows(_cb, None)
            if found:
                win32gui.ShowWindow(found[0], win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(found[0])
                return True
        except Exception:
            pass
        return False

    if IS_LINUX:
        # wmctrl approach
        out = _run(["wmctrl", "-l"])
        for line in out.splitlines():
            if title.lower() in line.lower():
                parts = line.split(None, 3)
                if parts:
                    _run(["wmctrl", "-ia", parts[0]])
                    return True
        # xdotool fallback
        wid = _run(["xdotool", "search", "--name", title])
        if wid:
            _run(["xdotool", "windowactivate", "--sync", wid.splitlines()[0]])
            return True
        return False

    return False


# ─────────────────────────────────────────────
#  6. FONT PATHS
# ─────────────────────────────────────────────
def get_font_paths() -> list:
    """Returns list of font paths to try, in order of preference."""
    if IS_WINDOWS:
        return [
            "C:/Windows/Fonts/nirmala.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]
    if IS_LINUX:
        return [
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        ]
    return []


# ─────────────────────────────────────────────
#  7. APP LAUNCHER MAPPING
# ─────────────────────────────────────────────
_APP_MAP_LINUX = {
    "notepad":        ["gedit"],
    "calc":           ["gnome-calculator", "kcalc", "galculator"],
    "paint":          ["gimp", "kolourpaint"],
    "explorer":       ["nautilus", "thunar", "nemo"],
    "cmd":            ["bash"],
    "powershell":     ["bash"],
    "taskmgr":        ["gnome-system-monitor", "ksysguard", "htop"],
    "control":        ["gnome-control-center"],
    "regedit":        [],   # no Linux equivalent
    "devmgmt.msc":    [],
    "diskmgmt.msc":   ["gnome-disks"],
}

def get_app_cmd(windows_cmd: str) -> list:
    """
    Given a Windows app name, returns a list[str] suitable for subprocess.
    Windows: [windows_cmd]  |  Linux: mapped equivalent or []
    """
    if IS_WINDOWS:
        return [windows_cmd]
    if IS_LINUX:
        candidates = _APP_MAP_LINUX.get(windows_cmd.lower(), [windows_cmd])
        # Return first candidate that exists on PATH
        for c in candidates:
            if _run(["which", c]):
                return [c]
        return []
    return []


print(f"[platform_compat] OS: {_OS} | Windows={IS_WINDOWS} | Linux={IS_LINUX}")
