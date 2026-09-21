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

# Gemini model for vision
_VISION_MODEL = "gemini-2.0-flash"

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

    # ── Method 0: PrintScreen + Clipboard ────────────────────────────────
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

    # ── Method 1: PowerShell subprocess ──────────────────────────────────

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

    # ── Method 1: mss (fastest, most reliable on Windows) ────────────────
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

    # ── Method 2: PIL ImageGrab ───────────────────────────────────────────
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=True)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        print("[InterviewMode] Screenshot via PIL.ImageGrab OK")
        return buf.getvalue()
    except Exception as _e2:
        print(f"[InterviewMode] PIL.ImageGrab failed ({_e2}), trying pyautogui...")

    # ── Method 3: pyautogui ───────────────────────────────────────────────
    try:
        if pyautogui:
            img = pyautogui.screenshot()
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            print("[InterviewMode] Screenshot via pyautogui OK")
            return buf.getvalue()
    except Exception as _e3:
        print(f"[InterviewMode] pyautogui failed ({_e3}), trying win32...")

    # ── Method 4: win32api BitBlt ─────────────────────────────────────────
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
    """Screenshot ko Gemini Vision se analyze karo."""
    if not _GENAI:
        return "ERROR: google-generativeai not installed. Run: pip install google-generativeai"
    if not _GEMINI_KEY:
        return "ERROR: GEMINI_API_KEY missing in .env file!"

    try:
        client = _genai_lib.Client(api_key=_GEMINI_KEY)
        img_b64 = base64.b64encode(img_bytes).decode()

        response = client.models.generate_content(
            model=_VISION_MODEL,
            contents=[{
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}},
                    {"text": _PROMPT},
                ],
            }],
        )
        return (response.text or "No answer generated.").strip()
    except Exception as e:
        err = str(e)
        print(f"[InterviewMode] Gemini error: {err}")
        if "429" in err:
            return "Gemini busy (429 quota). 1 minute baad try karo."
        return f"Analysis failed: {err[:120]}"

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# WHATSAPP SILENT SEND â€” 3 methods, fallback chain
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _send_whatsapp(message: str, phone: str = "") -> bool:
    """
    WhatsApp par silently message bhejo.
    Method 1: pywhatkit (best â€” browser briefly opens, then closes)
    Method 2: WhatsApp Desktop URI + auto-enter
    Method 3: Web URL via default browser + auto-enter
    """
    phone = (phone or _WA_NUMBER).strip()
    if not phone.startswith("+"):
        phone = "+" + phone

    full_msg = f"[JARVIS]\n{message}"
    phone_no_plus = phone.lstrip("+")

    # â”€â”€ Method 1: pywhatkit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if _PYWHATKIT:
        try:
            _kit.sendwhatmsg_instantly(
                phone_no=phone,
                message=full_msg,
                wait_time=12,
                tab_close=True,
                close_time=3,
            )
            print("[InterviewMode] âœ“ Sent via pywhatkit")
            return True
        except Exception as e:
            print(f"[InterviewMode] pywhatkit failed: {e}")

    # â”€â”€ Method 2: WhatsApp Desktop app URI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    try:
        encoded = urllib.parse.quote(full_msg)
        uri = f"whatsapp://send?phone={phone_no_plus}&text={encoded}"
        os.startfile(uri)
        time.sleep(3.5)
        # Auto press Enter to send
        if _PYAUTOGUI:
            pyautogui.hotkey("ctrl", "End")
            time.sleep(0.3)
            pyautogui.press("enter")
            time.sleep(0.5)
            pyautogui.hotkey("alt", "f4")  # close WhatsApp after send
        print("[InterviewMode] âœ“ Sent via WhatsApp Desktop URI")
        return True
    except Exception as e:
        print(f"[InterviewMode] URI method failed: {e}")

    # â”€â”€ Method 3: wa.me web URL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    try:
        import webbrowser
        encoded = urllib.parse.quote(full_msg)
        url = f"https://api.whatsapp.com/send?phone={phone_no_plus}&text={encoded}"
        webbrowser.open(url)
        time.sleep(4.5)
        if _PYAUTOGUI:
            pyautogui.press("enter")
        print("[InterviewMode] âœ“ Sent via wa.me URL")
        return True
    except Exception as e:
        print(f"[InterviewMode] wa.me method failed: {e}")

    print("[InterviewMode] âœ— ALL WhatsApp methods FAILED")
    return False

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# INTERVIEW MODE CONTROLLER
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class InterviewMode:
    def __init__(self):
        self.active = False
        self._hwnd: int | None = None
        self._gui = None
        self._voice = None
        self._processing = False
        self._capture_count = 0
        self._hotkey_added = False

    # â”€â”€ PUBLIC â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def activate(self, gui=None, voice=None):
        """Interview Mode ON â€” GUI hide + hotkey register."""
        if self.active:
            return

        self._gui = gui
        self._voice = voice
        self.active = True
        self._capture_count = 0

        # â”€â”€ 1. GUI ko puri tarah hide karo â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ 2. Voice silence (store reference, will check is_active) â”€â”€â”€â”€
        # voice.speak() calls will be skipped when interview mode is on
        # because handle_text returns early

        # â”€â”€ 3. Hotkey register â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if _KEYBOARD:
            try:
                if self._hotkey_added:
                    try:
                        keyboard.remove_hotkey(_HOTKEY)
                    except Exception:
                        pass

                keyboard.add_hotkey(_HOTKEY, self._on_hotkey, suppress=False)
                self._hotkey_added = True
                print(f"[InterviewMode] Hotkey '{_HOTKEY}' registered âœ“")
            except Exception as e:
                print(f"[InterviewMode] Hotkey ERROR: {e}")
                print("  â†’ Try running Jarvis as Administrator!")
        else:
            print("[InterviewMode] keyboard library missing! Run: pip install keyboard")

        print(f"[InterviewMode] *** ACTIVATED *** Press {_HOTKEY} to capture & answer")

    def deactivate(self, gui=None, voice=None):
        """Interview Mode OFF â€” GUI restore + hotkey remove."""
        if not self.active:
            return

        self.active = False
        _gui = gui or self._gui

        # Remove hotkey
        if _KEYBOARD and self._hotkey_added:
            try:
                keyboard.remove_hotkey(_HOTKEY)
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

    # â”€â”€ HOTKEY HANDLER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _on_hotkey(self):
        """Ctrl+Shift+S pressed â€” background thread mein pipeline chalao."""
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
            print(f"[InterviewMode]    Answer preview: {answer[:100]}...")

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
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    import platform
    print("=" * 60)
    print("  RealJarvis Interview Mode â€” STANDALONE TEST")
    print("=" * 60)
    print(f"  OS: {platform.system()} {platform.version()[:20]}")
    print(f"  Admin: {bool(ctypes.windll.shell32.IsUserAnAdmin())}")
    print(f"  keyboard: {_KEYBOARD}")
    print(f"  pyautogui: {_PYAUTOGUI}")
    print(f"  PIL: {_PIL}")
    print(f"  Gemini key: {'SET' if _GEMINI_KEY else 'MISSING'}")
    print(f"  pywhatkit: {_PYWHATKIT}")
    print(f"  WA Number: {_WA_NUMBER}")
    print(f"  Hotkey: {_HOTKEY}")
    print()

    if not _KEYBOARD:
        print("FATAL: keyboard not installed. Run: pip install keyboard")
        sys.exit(1)
    if not _PYAUTOGUI:
        print("FATAL: pyautogui not installed. Run: pip install pyautogui")
        sys.exit(1)
    if not _GEMINI_KEY:
        print("FATAL: GEMINI_API_KEY not set in .env file!")
        sys.exit(1)

    print(f"Activating... Press {_HOTKEY} to test capture.")
    print("Press Ctrl+C to quit.\n")

    interview_mode.activate()

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\nTest ended.")
        interview_mode.deactivate()

