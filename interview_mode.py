# -*- coding: utf-8 -*-
"""
interview_mode.py  â€”  RealJarvis Secret Interview Cheat Mode
=============================================================

FLOW:
  1. "Jarvis interview mode on" bolo
     â†’ GUI puri tarah gayab (Windows-level hide)
     â†’ Voice mute
     â†’ Jarvis completely invisible

  2. Jab screen par question ho â†’ Ctrl + Shift + S dabaao
     â†’ Silent screenshot (0 flicker, koi popup nahi)
     â†’ Gemini Vision se analyze (MCQ / Fill / Code / Theory detect karo)
     â†’ Answer directly WhatsApp par bhejo
     â†’ Pura background, koi cheez open nahi hogi

  3. "Jarvis interview mode off" bolo
     â†’ GUI wapas
     â†’ Normal mode

IMPORTANT â€” Pehli baar setup:
  pip install keyboard pyautogui pillow pywhatkit
  .env mein WHATSAPP_MASTER_PHONE=+91XXXXXXXXXX set karo
"""

from __future__ import annotations

import os
import sys
import io
import time
import base64
import ctypes
import threading
import subprocess
import urllib.parse
import json

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# OPTIONAL DEPS â€” fail silently
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.0
    _PYAUTOGUI = True
except ImportError:
    pyautogui = None
    _PYAUTOGUI = False

try:
    import keyboard
    _KEYBOARD = True
except ImportError:
    keyboard = None
    _KEYBOARD = False

try:
    from PIL import Image as PilImage
    _PIL = True
except ImportError:
    PilImage = None
    _PIL = False

try:
    from google import genai as _genai_lib
    _GENAI = True
except ImportError:
    _genai_lib = None
    _GENAI = False

try:
    import pywhatkit as _kit
    _PYWHATKIT = True
except ImportError:
    _kit = None
    _PYWHATKIT = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    pyperclip = None
    _PYPERCLIP = False

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONFIG â€” .env se load
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _load_cfg():
    api_key = ""
    wa_num = "+917014093732"
    try:
        import config
        api_key = getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        wa_num = os.environ.get("WHATSAPP_MASTER_PHONE", "").strip() or wa_num
    except Exception:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        wa_num = os.environ.get("WHATSAPP_MASTER_PHONE", wa_num)
    return api_key, wa_num

_GEMINI_KEY, _WA_NUMBER = _load_cfg()

# Hotkey â€” Ctrl+Shift+S (reliable, exam-safe)
# User ne A+S bola tha, lekin Ctrl+Shift+S better hai â€” accidental trigger avoid karta hai
# Agar A+S chahiye toh neeche _HOTKEY = "a+s" kar do
_HOTKEY = "ctrl+shift+s"

# Gemini models — cascade (pehle fast wala try karo, fail ho toh next)
_VISION_MODELS = [
    "gemini-flash-lite-latest",   # fastest, teri key par kaam karta hai
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]

# Screenshot lene se pehle delay (seconds)
_CAPTURE_DELAY = 0.2

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# GEMINI VISION PROMPT
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_PROMPT = """You are a secret exam assistant. Look at this screenshot carefully.

Find every question/problem visible on screen and answer ALL of them.

Reply in EXACTLY this format (no extra text before or after):

---
TYPE: MCQ | FILL | CODE | THEORY
ANSWER:
[your answer]
---

STRICT RULES:
- MCQ â†’ Only the correct option letter + text. E.g. "B) Binary Search"
- FILL â†’ Only the missing word/phrase. E.g. "encapsulation"
- CODE â†’ Full working code. Add language name as first line comment. No truncation.
- THEORY â†’ Max 3-4 crisp lines. No padding.
- If multiple questions: repeat the --- block for each.
- DO NOT say "I cannot help" or anything like that. Just answer.
- Be 100% accurate. Short. Direct.
"""

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# WINDOWS GUI HIDE â€” Force Hide using Win32 API
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_user32 = ctypes.windll.user32

def _force_hide_window(hwnd: int):
    """Win32 SW_HIDE â€” works even from non-main thread."""
    SW_HIDE = 0
    _user32.ShowWindow(hwnd, SW_HIDE)

def _force_show_window(hwnd: int):
    """Win32 SW_SHOW â€” restore window."""
    SW_SHOW = 5
    SW_RESTORE = 9
    _user32.ShowWindow(hwnd, SW_RESTORE)
    _user32.ShowWindow(hwnd, SW_SHOW)
    _user32.SetForegroundWindow(hwnd)

def _get_tk_hwnd(root) -> int | None:
    """Tkinter window ka Win32 HWND nikalo."""
    try:
        return ctypes.windll.user32.FindWindowW(None, root.title())
    except Exception:
        pass
    try:
        # Alternative: winfo_id gives the HWND directly
        return root.winfo_id()
    except Exception:
        return None

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SCREENSHOT
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _take_screenshot() -> bytes | None:
    """
    Full screen screenshot — 6-method fallback chain.
    Method 0: PrintScreen key + Win32 Clipboard (most reliable in real sessions)
    Method 1: PowerShell subprocess
    Method 2: mss (fastest pure-python)
    Method 3: PIL ImageGrab
    Method 4: pyautogui
    Method 5: win32api BitBlt
    Koi bhi flash ya sound nahi.
    """
    import io, os, tempfile, subprocess

    # ?? Method 0: PrintScreen + Clipboard ????????????????????????????????
    # Windows mein PrintScreen key clipboard mein screenshot daalta hai
    # Ye ALWAYS kaam karta hai real user session mein
    try:
        import win32clipboard, win32con
        from PIL import Image as _Img

        # PrintScreen simulate karo
        import ctypes
        _VK_SNAPSHOT = 0x2C
        ctypes.windll.user32.keybd_event(_VK_SNAPSHOT, 0, 0, 0)
        ctypes.windll.user32.keybd_event(_VK_SNAPSHOT, 0, 0x0002, 0)  # KEYEVENTF_KEYUP
        import time as _t; _t.sleep(0.15)  # clipboard fill hone do

        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB):
                data = win32clipboard.GetClipboardData(win32con.CF_DIB)
                win32clipboard.CloseClipboard()
                # DIB data ko PIL Image mein convert karo
                import struct
                # DIB header se width/height nikalo
                hdr_size = struct.unpack_from("<I", data, 0)[0]
                width  = struct.unpack_from("<i", data, 4)[0]
                height = struct.unpack_from("<i", data, 8)[0]
                bits   = struct.unpack_from("<H", data, 14)[0]
                # Pixel data skip header
                px_data = data[hdr_size:]
                mode = "RGB" if bits == 24 else "RGBA"
                img = _Img.frombytes(mode, (width, abs(height)), px_data, "raw", mode, 0, 1 if height < 0 else -1)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                result = buf.getvalue()
                if len(result) > 5000:
                    print(f"[InterviewMode] Screenshot via Clipboard OK ({len(result)//1024} KB)")
                    return result
            else:
                win32clipboard.CloseClipboard()
                raise RuntimeError("CF_DIB not in clipboard")
        except Exception as _inner:
            try: win32clipboard.CloseClipboard()
            except: pass
            raise _inner
    except Exception as _e_clip:
        print(f"[InterviewMode] Clipboard method failed ({_e_clip}), trying PowerShell...")

    # ?? Method 1: PowerShell subprocess ??????????????????????????????????

    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp_path = tmp.name
        tmp.close()

        ps_cmd = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "Add-Type -AssemblyName System.Drawing;"
            "$s=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
            "$b=New-Object System.Drawing.Bitmap($s.Width,$s.Height);"
            "$g=[System.Drawing.Graphics]::FromImage($b);"
            "$g.CopyFromScreen($s.Location,[System.Drawing.Point]::Empty,$s.Size);"
            f"$b.Save('{tmp_path.replace(chr(92), '/')}');"
            "$g.Dispose();$b.Dispose();"
        )
        result = subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=8
        )
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 10000:
            with open(tmp_path, "rb") as f_img:
                data = f_img.read()
            os.unlink(tmp_path)
            print(f"[InterviewMode] Screenshot via PowerShell OK ({len(data)//1024} KB)")
            return data
        else:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise RuntimeError(f"PS screenshot small/empty. stderr={result.stderr[:80]}")
    except Exception as _e0:
        print(f"[InterviewMode] PowerShell method failed ({_e0}), trying mss...")

    # ?? Method 1: mss (fastest, most reliable on Windows) ????????????????
    try:
        import mss, warnings
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="mss")
        with mss.MSS() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            from PIL import Image as _PILImg
            img = _PILImg.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            print("[InterviewMode] Screenshot via mss OK")
            return buf.getvalue()
    except Exception as _e1:
        print(f"[InterviewMode] mss failed ({_e1}), trying PIL...")

    # ?? Method 2: PIL ImageGrab ???????????????????????????????????????????
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=True)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        print("[InterviewMode] Screenshot via PIL.ImageGrab OK")
        return buf.getvalue()
    except Exception as _e2:
        print(f"[InterviewMode] PIL.ImageGrab failed ({_e2}), trying pyautogui...")

    # ?? Method 3: pyautogui ???????????????????????????????????????????????
    try:
        if pyautogui:
            img = pyautogui.screenshot()
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            print("[InterviewMode] Screenshot via pyautogui OK")
            return buf.getvalue()
    except Exception as _e3:
        print(f"[InterviewMode] pyautogui failed ({_e3}), trying win32...")

    # ?? Method 4: win32api BitBlt ?????????????????????????????????????????
    try:
        import win32gui, win32ui, win32con
        hdesktop = win32gui.GetDesktopWindow()
        width  = win32api_GetSystemMetrics(0)
        height = win32api_GetSystemMetrics(1)
        desktop_dc = win32gui.GetWindowDC(hdesktop)
        img_dc  = win32ui.CreateDCFromHandle(desktop_dc)
        mem_dc  = img_dc.CreateCompatibleDC()
        bmp     = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(img_dc, width, height)
        mem_dc.SelectObject(bmp)
        mem_dc.BitBlt((0, 0), (width, height), img_dc, (0, 0), win32con.SRCCOPY)
        bmpinfo  = bmp.GetInfo()
        bmpstr   = bmp.GetBitmapBits(True)
        from PIL import Image as _PILImg2
        img = _PILImg2.frombuffer(
            "RGB", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
            bmpstr, "raw", "BGRX", 0, 1
        )
        mem_dc.DeleteDC()
        win32gui.DeleteObject(bmp.GetHandle())
        win32gui.ReleaseDC(hdesktop, desktop_dc)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        print("[InterviewMode] Screenshot via win32api OK")
        return buf.getvalue()
    except Exception as _e4:
        print(f"[InterviewMode] win32api failed ({_e4})")

    print("[InterviewMode] ALL screenshot methods FAILED!")
    return None


def win32api_GetSystemMetrics(n):
    """Helper for win32 screen size."""
    import ctypes as _ct
    return _ct.windll.user32.GetSystemMetrics(n)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# GEMINI VISION ANALYSIS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _analyze(img_bytes: bytes) -> str:
    """Screenshot ko Gemini Vision se analyze karo — model cascade with fallback."""
    if not _GENAI:
        return "ERROR: google-generativeai not installed."
    if not _GEMINI_KEY:
        return "ERROR: GEMINI_API_KEY missing in .env file!"

    client = _genai_lib.Client(api_key=_GEMINI_KEY)
    img_b64 = base64.b64encode(img_bytes).decode()

    last_err = ""
    for model in _VISION_MODELS:
        try:
            print(f"[InterviewMode]    Trying model: {model}")
            response = client.models.generate_content(
                model=model,
                contents=[{
                    "role": "user",
                    "parts": [
                        {"inline_data": {"mime_type": "image/png", "data": img_b64}},
                        {"text": _PROMPT},
                    ],
                }],
            )
            answer = (response.text or "").strip()
            if answer:
                print(f"[InterviewMode]    Model {model} answered OK")
                return answer
        except Exception as e:
            last_err = str(e)
            err_short = last_err[:80]
            if "429" in last_err:
                print(f"[InterviewMode]    {model}: quota full, trying next...")
            elif "404" in last_err:
                print(f"[InterviewMode]    {model}: not available, trying next...")
            else:
                print(f"[InterviewMode]    {model}: {err_short}")

    if "429" in last_err:
        return "Quota full hai. 1 minute baad Ctrl+Shift+S dobara dabaao."
    return f"Koi bhi Gemini model kaam nahi kiya. Error: {last_err[:100]}"

# -------------------------------------------------
# WHATSAPP SEND -- COMPLETELY INVISIBLE
# No browser opens, no window switches, no focus steal
# -------------------------------------------------

# Headless Chrome session folder
_WA_SESSION_DIR = r"C:\RealJarvis_v2\wa_headless_session"


def _send_whatsapp(message: str, phone: str = "") -> bool:
    phone = (phone or _WA_NUMBER).strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    phone_digits = phone.lstrip("+")
    full_msg = "[JARVIS]\n" + message

    # Method 1: Headless Chrome (completely invisible)
    if _send_headless_chrome(full_msg, phone_digits):
        return True

    # Headless se nahi gaya toh log karo
    print("[InterviewMode] Headless Chrome FAILED.")
    print("[InterviewMode] Pehle setup karo: venv\Scripts\python.exe interview_mode.py setup")
    return False


def _send_headless_chrome(message: str, phone_digits: str) -> bool:
    import os, time, urllib.parse
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        print("[InterviewMode] selenium missing: pip install selenium")
        return False

    if not os.path.isdir(_WA_SESSION_DIR):
        print("[InterviewMode] WA session not found!")
        print("[InterviewMode] Ek baar ye run karo: venv\\Scripts\\python.exe interview_mode.py setup")
        return False

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument(f"--user-data-dir={_WA_SESSION_DIR}")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--window-size=1366,768")
    opts.add_argument("--log-level=3")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = None
    try:
        from selenium.webdriver.chrome.service import Service
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            svc = Service(ChromeDriverManager().install(), log_path=os.devnull)
        except Exception:
            svc = Service(log_path=os.devnull)

        driver = webdriver.Chrome(service=svc, options=opts)
        driver.set_page_load_timeout(30)

        encoded = urllib.parse.quote(message)
        url = (
            f"https://web.whatsapp.com/send"
            f"?phone={phone_digits}&text={encoded}"
            f"&type=phone_number&app_absent=0"
        )
        print("[InterviewMode] Headless Chrome: WhatsApp Web load kar raha hoon...")
        driver.get(url)

        wait = WebDriverWait(driver, 25)
        send_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@aria-label=\'Send\']")
            )
        )
        time.sleep(0.5)
        send_btn.click()
        time.sleep(2)
        print("[InterviewMode] Headless send: ANSWER BHEJA -- phone check karo!")
        return True

    except Exception as e:
        err = str(e)
        if "session" in err.lower():
            print("[InterviewMode] Session expired. Setup dobara karo.")
        else:
            print(f"[InterviewMode] Headless error: {err[:100]}")
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def _send_via_desktop_app(message: str, phone: str) -> bool:
    import time, urllib.parse, ctypes
    try:
        import win32gui, win32api
    except ImportError:
        print("[InterviewMode] pywin32 missing: pip install pywin32")
        return False

    wa_hwnd = None
    def _cb(hwnd, _):
        nonlocal wa_hwnd
        if "WhatsApp" in win32gui.GetWindowText(hwnd) and win32gui.IsWindow(hwnd):
            wa_hwnd = hwnd
    win32gui.EnumWindows(_cb, None)

    if not wa_hwnd:
        print("[InterviewMode] WhatsApp Desktop not open. App kholo taskbar mein.")
        return False

    try:
        phone_digits = phone.lstrip("+")
        encoded = urllib.parse.quote(message)
        uri = f"whatsapp://send?phone={phone_digits}&text={encoded}"

        # Minimize state mein kholo -- focus nahi lega screen par
        SW_SHOWMINNOACTIVE = 7
        ctypes.windll.shell32.ShellExecuteW(
            None, "open", uri, None, None, SW_SHOWMINNOACTIVE
        )
        time.sleep(3.0)

        # Enter key -- bina window ko foreground kiye
        WM_KEYDOWN = 0x0100
        WM_KEYUP   = 0x0101
        VK_RETURN  = 0x0D
        win32api.PostMessage(wa_hwnd, WM_KEYDOWN, VK_RETURN, 0)
        time.sleep(0.1)
        win32api.PostMessage(wa_hwnd, WM_KEYUP,   VK_RETURN, 0)
        time.sleep(0.5)
        print("[InterviewMode] Desktop app: bheja background mein -- phone check karo!")
        return True
    except Exception as e:
        print(f"[InterviewMode] Desktop app error: {e}")
        return False


class InterviewMode:
    def __init__(self):
        self.active = False
        self._hwnd: int | None = None
        self._gui = None
        self._voice = None
        self._processing = False
        self._capture_count = 0
        self._hotkey_added = False
        self._last_right_time = 0.0

    # ── PUBLIC ──────────────────────────────────────────────────────────

    def activate(self, gui=None, voice=None):
        """Interview Mode ON — GUI hide + hotkey register."""
        if self.active:
            return

        self._gui = gui
        self._voice = voice
        self.active = True
        self._capture_count = 0
        self._last_right_time = 0.0

        # ── 1. GUI ko puri tarah hide karo ──────────────────────────────
        if gui:
            try:
                # Try Win32 force-hide first (works from any thread)
                hwnd = _get_tk_hwnd(gui.root)
                if hwnd:
                    self._hwnd = hwnd
                    _force_hide_window(hwnd)
                    print(f"[InterviewMode] GUI hidden via Win32 (hwnd={hwnd})")
                else:
                    # Fallback: Tkinter withdraw via main thread queue
                    gui.root.after(0, self._tk_hide)
                    print("[InterviewMode] GUI withdraw queued via Tkinter.after()")
            except Exception as e:
                print(f"[InterviewMode] GUI hide error: {e}")
                try:
                    gui.root.withdraw()
                except Exception:
                    pass

        # ── 2. Voice silence (store reference, will check is_active) ────
        # voice.speak() calls will be skipped when interview mode is on
        # because handle_text returns early

        # ── 3. Hotkey & Double Right-Arrow register ─────────────────────
        if _KEYBOARD:
            try:
                if self._hotkey_added:
                    try:
                        keyboard.remove_hotkey(_HOTKEY)
                    except Exception:
                        pass
                    try:
                        keyboard.unhook_key("right")
                    except Exception:
                        pass

                # Secret Trigger: 2x Right Arrow within 1.0 second
                keyboard.on_press_key("right", self._on_right_arrow, suppress=False)
                # Backup Trigger: Ctrl+Shift+S
                keyboard.add_hotkey(_HOTKEY, self._on_hotkey, suppress=False)
                self._hotkey_added = True
                print(f"[InterviewMode] Trigger active: Double-tap Right Arrow within 1s (or {_HOTKEY})")
            except Exception as e:
                print(f"[InterviewMode] Hotkey ERROR: {e}")
                print("  -> Try running Jarvis as Administrator!")
        else:
            print("[InterviewMode] keyboard library missing! Run: pip install keyboard")

        print(f"[InterviewMode] *** ACTIVATED *** Double-tap Right Arrow (or {_HOTKEY}) to capture & answer")

    def deactivate(self, gui=None, voice=None):
        """Interview Mode OFF — GUI restore + hotkey remove."""
        if not self.active:
            return

        self.active = False
        _gui = gui or self._gui

        # Remove hotkey & right arrow hook
        if _KEYBOARD and self._hotkey_added:
            try:
                keyboard.remove_hotkey(_HOTKEY)
            except Exception:
                pass
            try:
                keyboard.unhook_key("right")
            except Exception:
                pass
            self._hotkey_added = False

        # Restore GUI
        if _gui:
            try:
                if self._hwnd:
                    _force_show_window(self._hwnd)
                    print("[InterviewMode] GUI restored via Win32")
                else:
                    _gui.root.after(0, _gui.root.deiconify)
                    _gui.root.after(0, _gui.root.lift)
                    _gui.root.after(0, lambda: _gui.root.attributes("-topmost", True))
            except Exception as e:
                print(f"[InterviewMode] GUI restore error: {e}")

        print(f"[InterviewMode] *** OFF *** Captures this session: {self._capture_count}")

    def _tk_hide(self):
        """Tkinter main thread mein withdraw call."""
        try:
            self._gui.root.withdraw()
        except Exception:
            pass

    @property
    def is_active(self) -> bool:
        return self.active

    # ── HOTKEY & KEY TRIGGER HANDLERS ───────────────────────────────────

    def _on_right_arrow(self, event=None):
        """Secret trigger: 2x Right Arrow key press within 1.0 second."""
        if not self.active:
            return
        now = time.time()
        diff = now - self._last_right_time
        # Min 0.10s to avoid key-repeat, Max 1.0s between 2 distinct taps
        if 0.10 <= diff <= 1.0:
            print(f"[InterviewMode] >> Secret Double Right-Arrow Triggered ({diff:.2f}s)! <<")
            self._last_right_time = 0.0
            self._on_hotkey()
        else:
            self._last_right_time = now

    def _on_hotkey(self):
        """Triggered — background thread mein pipeline chalao."""
        if not self.active:
            return
        if self._processing:
            print("[InterviewMode] Still processing previous capture... wait!")
            return
        threading.Thread(
            target=self._pipeline,
            daemon=True,
            name="im-pipeline"
        ).start()

    # â”€â”€ MAIN PIPELINE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _pipeline(self):
        """Screenshot â†’ Gemini â†’ WhatsApp â€” poora silent background flow."""
        self._processing = True
        self._capture_count += 1
        n = self._capture_count

        try:
            print(f"\n[InterviewMode] â”€â”€ CAPTURE #{n} â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")

            # Small delay so key-press animation clears from screen
            time.sleep(_CAPTURE_DELAY)

            # STEP 1: Screenshot
            print("[InterviewMode] 1. Taking screenshot...")
            img = _take_screenshot()
            if not img:
                print("[InterviewMode] Screenshot failed!")
                return
            print(f"[InterviewMode]    Screenshot OK ({len(img)//1024} KB)")

            # STEP 2: Gemini Vision
            print("[InterviewMode] 2. Analyzing with Gemini Vision...")
            answer = _analyze(img)
            print("[InterviewMode]    Answer: " + answer[:120].encode("ascii","replace").decode())

            # STEP 3: WhatsApp
            print(f"[InterviewMode] 3. Sending to WhatsApp {_WA_NUMBER}...")
            ok = _send_whatsapp(answer)
            status = "âœ“ SENT" if ok else "âœ— FAILED"
            print(f"[InterviewMode] â”€â”€ CAPTURE #{n} {status} â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")

        except Exception as e:
            print(f"[InterviewMode] Pipeline crash: {e}")
            import traceback; traceback.print_exc()
        finally:
            self._processing = False


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SINGLETON
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
interview_mode = InterviewMode()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# VOICE TRIGGER HELPER â€” main.py mein call karo
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_ON_PHRASES = [
    "interview mode on", "interview mode chalu", "interview mode start",
    "interview shuru", "interview on", "cheat mode on", "exam mode on",
    "exam mode chalu", "hide ho jao", "gayab ho jao",
]

_OFF_PHRASES = [
    "interview mode off", "interview mode band", "interview mode stop",
    "interview off", "cheat mode off", "exam mode off",
    "wapas aao jarvis", "normal mode", "normal wapas",
]


def check_interview_trigger(text: str, gui=None, voice=None) -> bool:
    """
    main.py ke handle_text() mein sabse PEHLE call karo.
    Returns True agar interview trigger hua (baaki processing skip karo).
    """
    lower = text.lower().strip()

    for phrase in _ON_PHRASES:
        if phrase in lower:
            interview_mode.activate(gui=gui, voice=voice)
            return True

    for phrase in _OFF_PHRASES:
        if phrase in lower:
            interview_mode.deactivate(gui=gui, voice=voice)
            # Voice se confirm karo (ab normal mode hai)
            if voice:
                try:
                    voice.speak("Wapas aa gaya hoon boss!", emotion="happy")
                except Exception:
                    pass
            return True

    return False


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# STANDALONE TEST â€” python interview_mode.py
# -------------------------------------------------
# STANDALONE -- python interview_mode.py [setup]
# -------------------------------------------------
if __name__ == "__main__":
    import platform, os, sys

    # ── SETUP MODE: pehli baar QR scan ──────────────────────────────────
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        print("=" * 60)
        print("  WHATSAPP WEB SESSION SETUP (ek baar hi chahiye)")
        print("=" * 60)
        print()
        print("Chrome browser khulega.")
        print("Apne phone se WhatsApp QR code scan karo.")
        print("Scan ke baad yahan Enter dabaao.")
        print()

        os.makedirs(_WA_SESSION_DIR, exist_ok=True)
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            opts = Options()
            opts.add_argument(f"--user-data-dir={_WA_SESSION_DIR}")
            opts.add_argument("--profile-directory=Default")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--window-size=1200,800")
            opts.add_experimental_option("excludeSwitches", ["enable-logging"])

            try:
                from webdriver_manager.chrome import ChromeDriverManager
                svc = Service(ChromeDriverManager().install(), log_path=os.devnull)
            except Exception:
                svc = Service(log_path=os.devnull)

            print("Chrome open ho raha hai...")
            driver = webdriver.Chrome(service=svc, options=opts)
            driver.get("https://web.whatsapp.com")

            print()
            print("======================================")
            print("  >> QR code scan karo phone se <<  ")
            print("  >> Scan ke baad ENTER dabaao   <<  ")
            print("======================================")
            input()

            driver.quit()
            print()
            print("SESSION SAVE HO GAYA!")
            print("Location:", _WA_SESSION_DIR)
            print()
            print("Ab interview mode mein Ctrl+Shift+S dabaao.")
            print("Message completely invisible background mein bhejega!")

        except ImportError:
            print("ERROR: selenium not installed!")
            print("Run: pip install selenium webdriver-manager")
        except Exception as e:
            print(f"Setup error: {e}")
        sys.exit(0)

    # ── NORMAL TEST MODE ─────────────────────────────────────────────────
    print("=" * 60)
    print("  RealJarvis Interview Mode -- STANDALONE TEST")
    print("=" * 60)
    print(f"  OS: {platform.system()} {platform.version()[:20]}")
    print(f"  Admin: {bool(ctypes.windll.shell32.IsUserAnAdmin())}")
    print(f"  keyboard: {_KEYBOARD}")
    print(f"  Gemini key: {'SET' if _GEMINI_KEY else 'MISSING'}")
    print(f"  WA Number: {_WA_NUMBER}")
    print(f"  WA Session: {'FOUND' if os.path.isdir(_WA_SESSION_DIR) else 'NOT FOUND -- run setup!'}")
    print(f"  Hotkey: {_HOTKEY}")
    print()

    if not os.path.isdir(_WA_SESSION_DIR):
        print("WARNING: WhatsApp session setup nahi hua!")
        print("Pehle ye run karo:")
        print(f"  venv\\Scripts\\python.exe interview_mode.py setup")
        print()

    if not _KEYBOARD:
        print("FATAL: keyboard not installed. Run: pip install keyboard")
        sys.exit(1)
    if not _GEMINI_KEY:
        print("FATAL: GEMINI_API_KEY not set in .env file!")
        sys.exit(1)

    print(f"Activating... Double-tap Right Arrow within 1s (or press {_HOTKEY}) to test capture & send.")
    print("Press Ctrl+C to quit.")
    print()

    interview_mode.activate()
    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\nTest ended.")
        interview_mode.deactivate()
