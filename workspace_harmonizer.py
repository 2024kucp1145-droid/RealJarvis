# -*- coding: utf-8 -*-
"""
workspace_harmonizer.py
========================
Phase 6: Contextual Workspace & App-Switch Auto Setup.

Features:
1. Auto-detects user workspace transitions (Coding, Meeting/Class, Entertainment, Study).
2. "Meeting & Class Shield": Silences proactive voice alerts during Zoom/Google Meet/Teams.
3. "Dev & Coding Environment": Auto-adapts when VS Code/PyCharm/Terminal is focused.
4. "Entertainment / Cinema Mode": Suppresses chatter during full-screen videos/movies.
5. Manual 1-word workspace setups ("coding mode on", "study mode on", "meeting mode on").
"""

import os
import time
import subprocess
import threading
import webbrowser
import datetime

try:
    import win32gui
    import win32process
    import psutil
except ImportError:
    win32gui = None
    win32process = None
    psutil = None


class WorkspaceHarmonizer:
    def __init__(self, voice=None, ai=None, gui=None, speak_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        self.running = False
        self._thread = None
        self.enabled = True

        # Mode states
        self.current_mode = "general"       # "coding", "meeting", "entertainment", "study", "general"
        self.meeting_shield_active = False  # If True, suppresses all proactive speech
        self.manual_override_mode = None

        # Tracking state
        self._last_window_title = ""
        self._mode_transition_time = time.time()
        self._lock = threading.Lock()

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
        self._thread = threading.Thread(target=self._harmonizer_loop, daemon=True)
        self._thread.start()
        print("[workspace_harmonizer] Contextual Workspace Harmonizer started.")

    def stop(self):
        self.running = False

    def can_speak_proactively(self, priority: str = "normal") -> bool:
        """
        Global gatekeeper for all proactive modules.
        If in meeting/class shield -> Returns False (Except emergency hardware alerts).
        """
        with self._lock:
            if self.meeting_shield_active and priority != "emergency":
                return False
            if self.current_mode == "entertainment" and priority == "low":
                return False
            return True

    def _get_active_window(self) -> tuple:
        if not win32gui:
            return "", ""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd)
                app_name = ""
                if win32process and psutil:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        app_name = psutil.Process(pid).name().lower()
                    except Exception:
                        pass
                return title, app_name
        except Exception:
            pass
        return "", ""

    def _detect_workspace_mode(self, title: str, app_name: str) -> str:
        comb = (title + " " + app_name).lower()

        # 1. Meeting & Online Class Mode
        meeting_triggers = ["zoom", "teams", "meet.google.com", "google meet", "webex", "gotomeeting"]
        if any(m in comb for m in meeting_triggers):
            return "meeting"

        # 2. Coding & Dev Mode
        coding_triggers = ["visual studio code", "code.exe", "pycharm", "intellij", "clion", "sublime_text", "powershell", "cmd.exe", "wt.exe", "antigravity"]
        if any(c in comb for c in coding_triggers):
            return "coding"

        # 3. Entertainment & Media Mode
        media_triggers = ["youtube", "netflix", "spotify", "vlc", "prime video", "hotstar", "disney+"]
        if any(m in comb for m in media_triggers):
            return "entertainment"

        # 4. Study & Competitive Programming Mode
        study_triggers = ["leetcode", "codechef", "geeksforgeeks", "hackerrank", "overleaf", "arxiv", ".pdf"]
        if any(s in comb for s in study_triggers):
            return "study"

        return "general"

    def _speak_alert(self, message: str, emotion: str = "happy"):
        """Thread-safe speech alert."""
        try:
            if self.speak_fn:
                self.speak_fn(message, emotion=emotion)
            elif self.voice:
                self.voice.speak(message, interruptible=True, emotion=emotion)
        except Exception as e:
            print(f"[workspace_harmonizer alert error: {e}]")

    def _harmonizer_loop(self):
        while self.running:
            try:
                if not self.enabled:
                    time.sleep(3.0)
                    continue

                title, app_name = self._get_active_window()
                if title and title != self._last_window_title:
                    self._last_window_title = title
                    detected_mode = self._detect_workspace_mode(title, app_name)

                    with self._lock:
                        prev_mode = self.current_mode
                        if detected_mode != prev_mode:
                            self.current_mode = detected_mode
                            self.meeting_shield_active = (detected_mode == "meeting")
                            self._mode_transition_time = time.time()

                            # Transition actions
                            if detected_mode == "meeting":
                                print("[workspace_harmonizer] Meeting / Online Class detected -> Proactive alerts MUTED.")
                            elif detected_mode == "coding" and prev_mode != "coding":
                                print("[workspace_harmonizer] Coding workspace active.")
                            elif detected_mode == "entertainment":
                                print("[workspace_harmonizer] Media & Entertainment mode active.")

            except Exception as e:
                print(f"[workspace_harmonizer loop error: {e}]")

            time.sleep(2.5)

    # --- MANUAL VOICE ACTIONS ---
    def launch_coding_workspace(self) -> str:
        """Opens VS Code and Terminal for coding."""
        try:
            subprocess.Popen("code", shell=True)
            subprocess.Popen("wt", shell=True)
            with self._lock:
                self.current_mode = "coding"
            return "Coding workspace activate kar diya hai. VS Code aur Terminal open ho gaye hain."
        except Exception:
            return "Coding workspace open karne mein dikkat aayi."

    def launch_study_workspace(self) -> str:
        """Opens LeetCode and Study Documents folder."""
        try:
            webbrowser.open("https://leetcode.com/problemset/all/")
            docs_dir = os.path.join(os.path.expanduser("~"), "Documents")
            if os.path.exists(docs_dir):
                subprocess.Popen(f'explorer "{docs_dir}"', shell=True)
            with self._lock:
                self.current_mode = "study"
            return "Study workspace activate kar diya hai. LeetCode aur Documents folder open kar diye hain."
        except Exception:
            return "Study workspace open karne mein error aa gaya."

    def toggle_meeting_shield(self, on: bool = True) -> str:
        with self._lock:
            self.meeting_shield_active = on
            self.current_mode = "meeting" if on else "general"
        if on:
            return "Meeting Shield ON kar diya hai. Main poori call ke dauran bilkul silent rahungi."
        else:
            return "Meeting Shield OFF kar diya hai. Normal proactive assistance wapas chalu ho gaya hai."


harmonizer = WorkspaceHarmonizer()
