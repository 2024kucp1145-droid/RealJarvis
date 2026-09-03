# -*- coding: utf-8 -*-
"""
proactive_guardian.py
======================
Phase 1: Proactive Intelligent Code Quality & Error Guardian.

1. Code/Error copied to clipboard:
   - Agar code sahi hai -> Jarvis bilkul chup rehti hai (Zero noise).
   - Agar code mein galti/error hai -> Jarvis AI se theek karke AUTO-CLIPBOARD par daal deti hai
     aur bolti hai: "Aapke code mein ye galti thi, maine theek karke clipboard par daal di hai."
2. Agar user bole "replace karo" / "paste karo" / "yahan daal do":
   - Jarvis seedha cursor position par Ctrl+V se paste kar deti hai!
"""

import re
import time
import threading
import datetime
import pyautogui

try:
    import pyperclip
except ImportError:
    pyperclip = None

# Code & Error signature patterns
ERROR_PATTERNS = [
    (r"Traceback \(most recent call last\):", "Python Traceback"),
    (r"(SyntaxError|NameError|AttributeError|IndexError|KeyError|TypeError|ValueError|ImportError|ModuleNotFoundError|ZeroDivisionError|IndentationError|UnboundLocalError|FileNotFoundError):", "Python Exception"),
    (r"(error|fatal error):\s+.+", "C/C++ Compiler Error"),
    (r"(undefined reference to|Segmentation fault|core dumped)", "C/C++ Runtime Error"),
    (r"Exception in thread \".+\" (java\.lang\.\w+)", "Java Exception"),
    (r"(NullPointerException|ArrayIndexOutOfBoundsException|ClassNotFoundException|NoSuchMethodError)", "Java Runtime Error"),
    (r"(TypeError|ReferenceError|RangeError|URIError): .+", "JavaScript Error"),
    (r"UnhandledPromiseRejection|Unhandled Rejection", "Node.js Unhandled Rejection"),
    (r"(npm ERR!|yarn error|pip error|ERROR: Command errored out)", "Package Manager Error"),
    (r"(fatal: not a git repository|error: failed to push some refs|CONFLICT \(content\))", "Git Error"),
    (r"(Permission denied|No such file or directory|command not found|is not recognized as an internal or external command)", "Terminal Command Error"),
    (r"(404 Not Found|500 Internal Server Error|502 Bad Gateway|503 Service Unavailable|ConnectionRefusedError|ECONNREFUSED)", "Network/HTTP Error"),
]

CODE_KEYWORDS = [
    r"\bdef\s+\w+\(", r"\bclass\s+\w+", r"\bimport\s+\w+", r"\bfrom\s+\w+\s+import",
    r"#include\s*<", r"\bint\s+main\(", r"\bstd::", r"\bconsole\.log\(",
    r"\bfunction\s*\w*\(", r"\bconst\s+\w+\s*=", r"\blet\s+\w+\s*=", r"\bpublic\s+class\b",
    r"\bSystem\.out\.print", r"\bfor\s*\(", r"\bwhile\s*\(", r"\bif\s*\(",
    r"SELECT\s+.+\s+FROM", r"INSERT\s+INTO", r"=>\s*\{"
]


class ProactiveGuardian:
    def __init__(self, voice=None, ai=None, gui=None, speak_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        self.running = False
        self._thread = None
        self._last_clip_text = ""
        self._last_alert_time = 0
        self._alert_cooldown_seconds = 20
        self._last_fixed_code = None
        self._last_bug_summary = None
        self._seen_hashes = set()
        self._lock = threading.Lock()
        self.enabled = True

    def start(self, voice=None, ai=None, gui=None, speak_fn=None):
        if voice:
            self.voice = voice
        if ai:
            self.ai = ai
        if gui:
            self.gui = gui
        if speak_fn:
            self.speak_fn = speak_fn

        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._guardian_loop, daemon=True)
        self._thread.start()
        print("[proactive_guardian] Proactive Code & Error Guardian started.")

    def stop(self):
        self.running = False

    def is_code_or_error(self, text: str) -> tuple:
        """Checks if text looks like code snippet or error traceback."""
        if not text or len(text.strip()) < 12:
            return False, None

        # Check errors first
        for pattern, label in ERROR_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True, "error"

        # Check code patterns
        for kw in CODE_KEYWORDS:
            if re.search(kw, text):
                return True, "code"

        # Check indentation / braces heuristic
        lines = [l for l in text.strip().splitlines() if l.strip()]
        if len(lines) >= 2 and any("{" in l or ":" in l or "=" in l for l in lines):
            if any(l.startswith("    ") or l.startswith("\t") for l in lines[1:]):
                return True, "code"

        return False, None

    def _guardian_loop(self):
        while self.running:
            try:
                if not self.enabled or not pyperclip:
                    time.sleep(2.0)
                    continue

                clip_text = pyperclip.paste()
                if clip_text and clip_text.strip() and clip_text != self._last_clip_text:
                    self._last_clip_text = clip_text
                    clean_text = clip_text.strip()

                    # Don't re-analyze code that Jarvis herself just placed on clipboard
                    if self._last_fixed_code and clean_text == self._last_fixed_code.strip():
                        time.sleep(1.5)
                        continue

                    is_relevant, kind = self.is_code_or_error(clean_text)
                    if is_relevant:
                        self._analyze_code_or_error(clean_text, kind)

            except Exception as e:
                print(f"[proactive_guardian loop error: {e}]")

            time.sleep(1.8)

    def _analyze_code_or_error(self, text_content: str, kind: str):
        now = time.time()
        text_hash = hash(text_content[:350])
        with self._lock:
            if (now - self._last_alert_time) < self._alert_cooldown_seconds:
                return
            if text_hash in self._seen_hashes:
                return
            self._seen_hashes.add(text_hash)
            self._last_alert_time = now

        try:
            import workspace_harmonizer
            if not workspace_harmonizer.harmonizer.can_speak_proactively():
                return
        except Exception:
            pass

        if not self.ai or not self.ai.available():
            return

        prompt = f"""Tum ek expert software developer aur code reviewer ho.
User ne clipboard pe ye text copy kiya hai:

```{kind}
{text_content[:1500]}
```

Tumhara kaam:
1. Agar ye code 100% correct hai (syntax, logic sab theek hai, koi bug/error nahi hai) -> STATUS: OK
2. Agar isme koi bug, syntax error, exception, missing import, ya logic error hai -> STATUS: HAS_BUG
   - BUG_EXPLANATION: 1 short sweet sentence in Hinglish (jo user ko batayi ja sake)
   - FIXED_CODE: Sirf aur sirf theek kiya hua complete correct code snippet (bina extra explanation ya markdown ke).

FORMAT EXACTLY LIKE THIS:
STATUS: OK ya HAS_BUG
BUG_EXPLANATION: [agar bug hai toh 1 line explanation, warna NA]
FIXED_CODE:
[corrected code yahan]"""

        try:
            raw_result, _ = self.ai.ask(prompt, skip_history_append=True)
            
            if "STATUS: OK" in raw_result and "HAS_BUG" not in raw_result:
                # Code is perfectly fine -> Jarvis remains completely silent!
                print("[proactive_guardian] Copied code is 100% valid. Staying silent.")
                return

            # Code has errors!
            bug_msg = "Aapke code mein kuch syntax ya logic ki galti thi."
            fixed_code_parts = []
            capturing_code = False

            for line in raw_result.splitlines():
                if line.startswith("BUG_EXPLANATION:"):
                    bug_msg = line.replace("BUG_EXPLANATION:", "").strip()
                elif line.startswith("FIXED_CODE:"):
                    capturing_code = True
                elif capturing_code:
                    fixed_code_parts.append(line)

            fixed_code = "\n".join(fixed_code_parts).strip()
            # Clean markdown code fences if model output any
            fixed_code = re.sub(r"^```[a-zA-Z]*\n", "", fixed_code)
            fixed_code = re.sub(r"\n```$", "", fixed_code).strip()

            if fixed_code and fixed_code != "NA":
                with self._lock:
                    self._last_fixed_code = fixed_code
                    self._last_bug_summary = bug_msg
                    self._last_clip_text = fixed_code  # Update to avoid self-trigger

                # 1. AUTO-PASTE ONTO USER'S CLIPBOARD
                if pyperclip:
                    pyperclip.copy(fixed_code)

                # 2. PROACTIVE SWEET SPOKEN NOTIFICATION
                notification = f"Aapke code mein {bug_msg}. Maine ise theek karke aapke clipboard par daal diya hai."
                
                try:
                    if self.speak_fn:
                        self.speak_fn(notification, emotion="happy")
                    elif self.voice:
                        self.voice.speak(notification, interruptible=True, emotion="happy")
                except Exception as e:
                    print(f"[proactive_guardian alert error: {e}]")

                print(f"[proactive_guardian] Auto-fixed and placed on clipboard: {bug_msg}")

        except Exception as e:
            print(f"[proactive_guardian analysis error: {e}]")
            if self.gui:
                try:
                    self.gui.set_state("idle")
                except Exception:
                    pass

    def has_fixed_code_ready(self) -> bool:
        """Returns True if Jarvis recently auto-fixed code ready to be pasted."""
        with self._lock:
            return bool(self._last_fixed_code)

    def replace_at_cursor(self) -> str:
        """
        User ne bola 'replace karo' / 'paste karo' / 'yahan daal do':
        Cursor position par directly code paste kar deta hai.
        """
        with self._lock:
            code_to_paste = self._last_fixed_code

        if not code_to_paste:
            # Fallback to whatever is in clipboard
            try:
                pyautogui.hotkey('ctrl', 'v')
                return "Clipboard ka content cursor par paste kar diya hai."
            except Exception:
                return "Paste karne mein dikkat aayi."

        try:
            # Re-ensure it is in clipboard
            if pyperclip:
                pyperclip.copy(code_to_paste)
            time.sleep(0.15)
            # Execute physical paste at current cursor position
            prev_failsafe = pyautogui.FAILSAFE
            pyautogui.FAILSAFE = False
            try:
                pyautogui.hotkey('ctrl', 'v')
            finally:
                pyautogui.FAILSAFE = prev_failsafe
            return "Theek kiya hua code maine cursor par paste kar diya hai."
        except Exception as e:
            print(f"[replace_at_cursor error: {e}]")
            return "Cursor par paste karne mein error aa gaya."

    def has_pending_solution(self) -> bool:
        """Alias for has_fixed_code_ready."""
        return self.has_fixed_code_ready()

    def apply_or_explain_fix(self) -> str:
        """Alias for replace_at_cursor."""
        return self.replace_at_cursor()


guardian = ProactiveGuardian()
