# -*- coding: utf-8 -*-
"""
web_workflow_assistant.py
==========================
Phase 7: Proactive Web & Browser Workflow Assistant.

Features:
1. LeetCode & DSA Problem Hint Master:
   - "hint do" / "approach kya hogi" -> Gives 2-sentence algorithmic intuition without full spoilers.
   - "solution likho" / "code likh do" -> Full optimal code.
2. Webpage & Technical Article Summarizer:
   - "page samjhao" / "summary sunao" -> 3-bullet spoken executive summary of active webpage.
3. Zero-Click YouTube & Media Player Controls:
   - "10 second aage" / "peeche", "speed 1.5x / 2x / normal", "subtitles on", "full screen", "theater mode".
"""

import time
import pyautogui
import threading
import subprocess

pyautogui.FAILSAFE = False


class WebWorkflowAssistant:
    def __init__(self, voice=None, ai=None, gui=None, speak_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        self.running = False
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

        self.running = True
        print("[web_workflow_assistant] Proactive Web & Browser Assistant started.")

    def stop(self):
        self.running = False

    def _speak(self, message: str, emotion: str = "happy"):
        if self.speak_fn:
            self.speak_fn(message, emotion=emotion)
        elif self.voice:
            self.voice.speak(message, interruptible=True, emotion=emotion)

    # =========================================================================
    # 1. LEETCODE & PROBLEM SOLVING HINT MASTER
    # =========================================================================
    def provide_coding_hint(self, capture_fn=None) -> str:
        """Analyzes active screen question and gives intuition/hint without full spoilers."""
        self._speak("Screen par question analyze kar rahi hoon, hint ready kar rahi hoon...", emotion="calm")

        # Capture screen text or screenshot
        import vision
        img = None
        if capture_fn:
            try:
                img = capture_fn(full=True)
            except Exception:
                img = pyautogui.screenshot()
        else:
            img = pyautogui.screenshot()

        prompt = """Look at this coding problem statement on screen.
DO NOT write the full code solution.
Provide a clean, smart algorithmic HINT in 2-3 short sentences in simple conversational Hinglish:
1. What data structure / pattern to use (e.g. Hashmap, Two Pointers, Monotonic Stack, Dynamic Programming).
2. The core intuition / key observation.
3. Time complexity target.

Be sweet and encouraging like a senior mentor."""

        try:
            if not self.ai or not self.ai.available():
                return "AI Brain abhi connected nahi hai, thodi der mein try karein."

            reply, emotion = self.ai.ask_vision(prompt, img)
            self._speak(reply, emotion=emotion or "happy")
            return reply
        except Exception as e:
            err = f"Hint generate karne mein error aa gaya: {e}"
            self._speak("Screen analyze karne mein problem aayi.", emotion="concerned")
            return err

    # =========================================================================
    # 2. WEBPAGE & ARTICLE SUMMARIZER
    # =========================================================================
    def summarize_active_webpage(self, capture_fn=None) -> str:
        """Reads active webpage and generates a 3-bullet spoken executive summary."""
        self._speak("Webpage ka content summarize kar rahi hoon...", emotion="calm")

        img = None
        if capture_fn:
            try:
                img = capture_fn(full=True)
            except Exception:
                img = pyautogui.screenshot()
        else:
            img = pyautogui.screenshot()

        prompt = """Analyze this webpage / article on screen.
Provide an executive spoken summary in 3 short bullet points in conversational Hinglish:
- Main topic kya hai
- Key highlights / important points
- Conclusion

Keep it concise and crystal clear for speech."""

        try:
            if not self.ai or not self.ai.available():
                return "AI Brain connected nahi hai."

            reply, emotion = self.ai.ask_vision(prompt, img)
            self._speak(reply, emotion=emotion or "happy")
            return reply
        except Exception as e:
            self._speak("Webpage summarize karte waqt error aa gaya.", emotion="concerned")
            return str(e)

    # =========================================================================
    # 3. YOUTUBE & MEDIA SMART CONTROLS
    # =========================================================================
    def seek_forward(self, seconds: int = 10):
        """Skips 10 seconds forward on YouTube/media."""
        pyautogui.press('l')
        self._speak("10 second aage kar diya.", emotion="happy")

    def seek_backward(self, seconds: int = 10):
        """Skips 10 seconds backward on YouTube/media."""
        pyautogui.press('j')
        self._speak("10 second peeche kar diya.", emotion="happy")

    def toggle_subtitles(self):
        """Toggles CC captions on YouTube."""
        pyautogui.press('c')
        self._speak("Subtitles toggle kar diye.", emotion="happy")

    def toggle_fullscreen(self):
        """Toggles fullscreen on YouTube/VLC."""
        pyautogui.press('f')
        self._speak("Full screen switch kar diya.", emotion="happy")

    def toggle_theater_mode(self):
        """Toggles theater mode on YouTube."""
        pyautogui.press('t')
        self._speak("Theater mode switch kar diya.", emotion="happy")

    def increase_playback_speed(self):
        """Speeds up video playback (Shift + >)."""
        pyautogui.hotkey('shift', '>')
        self._speak("Speed badha di hai.", emotion="happy")

    def decrease_playback_speed(self):
        """Slows down video playback (Shift + <)."""
        pyautogui.hotkey('shift', '<')
        self._speak("Speed kam kar di hai.", emotion="happy")


assistant = WebWorkflowAssistant()
