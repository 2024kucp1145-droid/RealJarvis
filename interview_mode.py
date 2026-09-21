# -*- coding: utf-8 -*-
"""
interview_mode.py
=================
RealJarvis ka Secret Interview Cheat Mode!

HOW IT WORKS:
  1. "Jarvis interview mode on" bolo → GUI gayab, voice chup, Jarvis invisible ho jaata hai
  2. Jab exam mein question aaye → A + S ek saath dabaao
  3. Jarvis silently screenshot lega → Gemini Vision se analyze karega
  4. MCQ → Correct option WhatsApp par
  5. Fill in blank → Answer WhatsApp par
  6. Code question → Pura working code WhatsApp par
  7. Theory → Short accurate answer WhatsApp par
  8. "Jarvis interview mode off" bolo → Normal wapas

INTEGRATION:
  - main.py mein voice trigger detect karke activate()/deactivate() call karo
  - Koi bhi window nahi khulti, koi bhi sound nahi aati — pura silent
"""

import os
import sys
import io
import time
import base64
import threading
import urllib.parse
import subprocess
import ctypes

try:
    import pyautogui
    pyautogui.FAILSAFE = False   # corner mein mouse jane se crash na ho
except ImportError:
    pyautogui = None

try:
    import keyboard
    _KEYBOARD_OK = True
except ImportError:
    _KEYBOARD_OK = False

try:
    from PIL import Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    from google import genai as google_genai
    _GENAI_OK = True
except ImportError:
    _GENAI_OK = False

try:
    import pywhatkit as kit
    _KIT_OK = True
except ImportError:
    _KIT_OK = False

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
# Apna WhatsApp number yahan — interviews ke answers yahan aayenge
# .env se automatically load ho jaata hai (config.py ke through)
try:
    import config
    _WA_NUMBER = os.environ.get("WHATSAPP_MASTER_PHONE", "").strip() or "+917014093732"
    _GEMINI_KEY = getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
except Exception:
    _WA_NUMBER = "+917014093732"
    _GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

# Hotkey — A aur S ek saath dabaao
_HOTKEY = "a+s"

# Gemini model — fast vision model
_VISION_MODEL = "gemini-2.0-flash"

# Kitni der baad screenshot lega (seconds) — A+S dabaane ke baad
_CAPTURE_DELAY = 0.4

# ---------------------------------------------------------------------------
# INTERVIEW BRAIN PROMPT — Gemini ko diya jaata hai
# ---------------------------------------------------------------------------
_ANALYSIS_PROMPT = """You are a SECRET exam assistant. Analyze this screenshot carefully.

Identify what type of question is visible and provide the answer in this EXACT format:

---
TYPE: [MCQ / FILL / CODE / THEORY]
ANSWER:
[Your answer here]
---

RULES:
- MCQ → Give ONLY the correct option letter + its text. Example: "B) Binary Search Tree"
- FILL → Give ONLY the missing word/phrase. Example: "polymorphism"
- CODE → Give COMPLETE working code with brief 1-line explanation at top. Include language name.
- THEORY → Give a concise, accurate answer in 2-4 lines max.
- If multiple questions visible, answer ALL of them one by one.
- Be 100% accurate. Student is depending on you.
- Keep answer SHORT and CRISP — only what is needed.
- Do NOT add unnecessary explanations unless it's a CODE question.
- Language: Mix of Hindi/English is fine (Hinglish), but answers must be technically correct.
"""

# ---------------------------------------------------------------------------
# SILENT WHATSAPP SENDER
# ---------------------------------------------------------------------------

def _send_whatsapp_silent(message: str, phone: str = _WA_NUMBER) -> bool:
    """
    Bina koi window khole / bina awaz ke WhatsApp message bhejta hai.
    Method 1: pywhatkit (preferred — works if WhatsApp Web session saved)
    Method 2: wa.me link via subprocess (headless browser)
    Method 3: WhatsApp URI scheme (desktop app must be open)
    """
    if not message or not phone:
        return False

    # Clean phone number
    phone_clean = phone.replace(" ", "").replace("-", "")
    if not phone_clean.startswith("+"):
        phone_clean = "+" + phone_clean

    # Prefix message with tag
    tagged_msg = f"[JARVIS INTERVIEW]\n{message}"

    # METHOD 1: pywhatkit — instant send (WhatsApp Web session must exist)
    if _KIT_OK:
        try:
            kit.sendwhatmsg_instantly(
                phone_no=phone_clean,
                message=tagged_msg,
                wait_time=12,
                tab_close=True,
                close_time=3,
            )
            print("[InterviewMode] WhatsApp sent via pywhatkit")
            return True
        except Exception as e:
            print(f"[InterviewMode] pywhatkit failed: {e}, trying URI...")

    # METHOD 2: WhatsApp Desktop URI (opens WhatsApp app, goes to chat)
    try:
        encoded = urllib.parse.quote(tagged_msg)
        # Strip + for URI
        num_for_uri = phone_clean.lstrip("+")
        uri = f"whatsapp://send?phone={num_for_uri}&text={encoded}"
        os.startfile(uri)
        time.sleep(3.0)

        # Auto-press Enter to send
        if pyautogui:
            pyautogui.hotkey("ctrl", "End")
            time.sleep(0.3)
            pyautogui.press("enter")

        print("[InterviewMode] WhatsApp sent via URI scheme")
        return True
    except Exception as e:
        print(f"[InterviewMode] URI scheme failed: {e}")

    # METHOD 3: wa.me via default browser (last resort)
    try:
        import webbrowser
        encoded = urllib.parse.quote(tagged_msg)
        num_for_web = phone_clean.lstrip("+")
        url = f"https://api.whatsapp.com/send?phone={num_for_web}&text={encoded}"
        webbrowser.open(url)
        time.sleep(4.0)
        if pyautogui:
            pyautogui.press("enter")
        print("[InterviewMode] WhatsApp sent via web URL")
        return True
    except Exception as e:
        print(f"[InterviewMode] All WhatsApp methods failed: {e}")
        return False


# ---------------------------------------------------------------------------
# SCREENSHOT CAPTURE
# ---------------------------------------------------------------------------

def _capture_screen() -> bytes | None:
    """Full screen ka silent screenshot leta hai aur PNG bytes return karta hai."""
    if pyautogui is None:
        print("[InterviewMode] pyautogui not available!")
        return None
    try:
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"[InterviewMode] Screenshot failed: {e}")
        return None


# ---------------------------------------------------------------------------
# GEMINI VISION ANALYSIS
# ---------------------------------------------------------------------------

def _analyze_screenshot(img_bytes: bytes) -> str:
    """Screenshot ko Gemini Vision se analyze karta hai aur answer return karta hai."""
    if not img_bytes:
        return "Screenshot lene mein dikkat aayi."

    if not _GENAI_KEY_VALID():
        return "Gemini API key missing. .env file mein GEMINI_API_KEY daalo."

    try:
        client = google_genai.Client(api_key=_GEMINI_KEY)
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        response = client.models.generate_content(
            model=_VISION_MODEL,
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": img_b64,
                            }
                        },
                        {"text": _ANALYSIS_PROMPT},
                    ],
                }
            ],
        )
        return response.text.strip()

    except Exception as e:
        err = str(e)
        print(f"[InterviewMode] Gemini error: {err}")
        if "429" in err or "quota" in err.lower():
            return "Gemini busy hai (429). Thodi der baad A+S try karo."
        return f"Analysis error: {err[:100]}"


def _GEMINI_KEY_VALID() -> bool:
    return bool(_GEMINI_KEY and len(_GEMINI_KEY) > 10)


# ---------------------------------------------------------------------------
# MAIN INTERVIEW MODE CLASS
# ---------------------------------------------------------------------------

class InterviewMode:
    """
    Main Interview Mode controller.

    Usage in main.py:
        from interview_mode import interview_mode
        interview_mode.activate(gui=self.gui)    # "interview mode on"
        interview_mode.deactivate(gui=self.gui)  # "interview mode off"
    """

    def __init__(self):
        self.active = False
        self._hotkey_registered = False
        self._processing = False   # ek time pe ek hi capture ho
        self._gui = None
        self._voice = None
        self._capture_count = 0    # kitni baar capture hua is session mein

    # ------------------------------------------------------------------ PUBLIC

    def activate(self, gui=None, voice=None):
        """
        Interview Mode ON:
          - GUI hide karo
          - Voice mute karo (instance store)
          - A+S hotkey register karo
        """
        if self.active:
            print("[InterviewMode] Already active.")
            return

        self._gui = gui
        self._voice = voice
        self.active = True
        self._capture_count = 0

        # GUI completely hide karo
        if gui:
            try:
                gui.root.after(0, gui.root.withdraw)
            except Exception as e:
                print(f"[InterviewMode] GUI hide error: {e}")

        # Hotkey register karo
        if _KEYBOARD_OK:
            try:
                keyboard.add_hotkey(_HOTKEY, self._on_hotkey_pressed, suppress=False)
                self._hotkey_registered = True
                print(f"[InterviewMode] Hotkey '{_HOTKEY}' registered.")
            except Exception as e:
                print(f"[InterviewMode] Hotkey registration failed: {e}")
        else:
            print("[InterviewMode] WARNING: 'keyboard' library not installed. pip install keyboard")

        print("[InterviewMode] *** INTERVIEW MODE ACTIVATED *** A+S = capture & answer")

    def deactivate(self, gui=None, voice=None):
        """
        Interview Mode OFF:
          - GUI wapas dikhao
          - Voice restore karo
          - Hotkey hata do
        """
        if not self.active:
            return

        self.active = False
        _gui = gui or self._gui

        # Hotkey hata do
        if _KEYBOARD_OK and self._hotkey_registered:
            try:
                keyboard.remove_hotkey(_HOTKEY)
            except Exception:
                pass
            self._hotkey_registered = False

        # GUI wapas dikhao
        if _gui:
            try:
                _gui.root.after(0, _gui.root.deiconify)
                _gui.root.after(0, _gui.root.lift)
                _gui.root.after(0, lambda: _gui.root.attributes("-topmost", True))
            except Exception as e:
                print(f"[InterviewMode] GUI show error: {e}")

        print(f"[InterviewMode] *** INTERVIEW MODE OFF *** (Total captures this session: {self._capture_count})")

    @property
    def is_active(self) -> bool:
        return self.active

    # ------------------------------------------------------------------ INTERNAL

    def _on_hotkey_pressed(self):
        """A+S dabaane par call hota hai — background thread mein kaam karta hai."""
        if not self.active:
            return
        if self._processing:
            print("[InterviewMode] Still processing last capture... please wait.")
            return
        # Background mein chalao — UI block na ho
        threading.Thread(
            target=self._capture_and_answer_pipeline,
            daemon=True,
            name="interview-capture"
        ).start()

    def _capture_and_answer_pipeline(self):
        """
        Complete pipeline:
        1. Thoda ruko (user ne key dabaayi, cursor move karega)
        2. Screenshot lo
        3. Gemini se analyze karo
        4. WhatsApp par bhejo
        """
        self._processing = True
        self._capture_count += 1
        capture_num = self._capture_count

        try:
            print(f"\n[InterviewMode] === Capture #{capture_num} STARTED ===")

            # Step 1: Delay — key dabaayi, ab stable hone do screen ko
            time.sleep(_CAPTURE_DELAY)

            # Step 2: Screenshot
            print("[InterviewMode] Taking screenshot...")
            img_bytes = _capture_screen()
            if not img_bytes:
                print("[InterviewMode] Screenshot failed, aborting.")
                return

            print(f"[InterviewMode] Screenshot taken ({len(img_bytes) // 1024} KB)")

            # Step 3: Gemini Vision Analysis
            print("[InterviewMode] Analyzing with Gemini Vision...")
            answer = _analyze_screenshot(img_bytes)
            print(f"[InterviewMode] Analysis complete:\n{answer[:200]}...")

            # Step 4: WhatsApp par bhejo
            print(f"[InterviewMode] Sending to WhatsApp {_WA_NUMBER}...")
            success = _send_whatsapp_silent(answer, phone=_WA_NUMBER)

            if success:
                print(f"[InterviewMode] === Capture #{capture_num} DONE — Answer sent! ===")
            else:
                print(f"[InterviewMode] === Capture #{capture_num} — WhatsApp send failed ===")

        except Exception as e:
            print(f"[InterviewMode] Pipeline error: {e}")
        finally:
            self._processing = False


# ---------------------------------------------------------------------------
# SINGLETON INSTANCE — main.py yahi use karega
# ---------------------------------------------------------------------------
interview_mode = InterviewMode()


# ---------------------------------------------------------------------------
# VOICE TRIGGER DETECTION HELPER — main.py mein import karke use karo
# ---------------------------------------------------------------------------

def check_interview_trigger(text: str, gui=None, voice=None) -> bool:
    """
    main.py ke handle_text() mein sabse pehle yeh call karo.
    Returns True agar interview mode trigger hua (baaki processing skip karo).

    Usage in main.py handle_text():
        from interview_mode import check_interview_trigger
        if check_interview_trigger(text, gui=self.gui, voice=self.voice):
            return True
    """
    lower = text.lower().strip()

    # Interview Mode ON triggers
    on_triggers = [
        "interview mode on", "interview mode chalu", "interview mode start",
        "interview mode shuru", "interview on", "cheat mode on",
        "exam mode on", "exam mode chalu", "hide ho jao",
    ]
    # Interview Mode OFF triggers
    off_triggers = [
        "interview mode off", "interview mode band", "interview mode stop",
        "interview off", "cheat mode off", "exam mode off",
        "wapas aao jarvis", "normal mode on",
    ]

    for trigger in on_triggers:
        if trigger in lower:
            interview_mode.activate(gui=gui, voice=voice)
            # Voice se confirm mat karo (silent mode!) — sirf print
            print("[InterviewMode] Activated via voice trigger.")
            return True

    for trigger in off_triggers:
        if trigger in lower:
            interview_mode.deactivate(gui=gui, voice=voice)
            if voice:
                try:
                    voice.speak("Wapas aa gaya hoon boss!", emotion="happy")
                except Exception:
                    pass
            return True

    return False


# ---------------------------------------------------------------------------
# STANDALONE TEST — python interview_mode.py test se run karo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  RealJarvis Interview Mode — Standalone Test")
    print("=" * 60)

    if not _KEYBOARD_OK:
        print("ERROR: 'keyboard' library missing. Run: pip install keyboard")
        sys.exit(1)
    if not pyautogui:
        print("ERROR: 'pyautogui' missing. Run: pip install pyautogui")
        sys.exit(1)
    if not _GEMINI_KEY_VALID():
        print("ERROR: GEMINI_API_KEY not set. Check .env file.")
        sys.exit(1)

    print(f"WhatsApp target: {_WA_NUMBER}")
    print(f"Gemini model: {_VISION_MODEL}")
    print(f"Hotkey: {_HOTKEY}")
    print()
    print("Press A+S to capture & analyze screen (Ctrl+C to quit)...")
    print()

    interview_mode.activate()

    try:
        keyboard.wait()   # jab tak Ctrl+C na dabaao, wait karo
    except KeyboardInterrupt:
        print("\nQuitting test mode.")
        interview_mode.deactivate()
