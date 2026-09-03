# -*- coding: utf-8 -*-
"""
health_focus_coach.py
======================
Phase 3: Health, Ergonomics & Focus Work-Session Coach.

Features:
1. 20-20-20 Eye Strain Guard (every 20 mins of active screen time).
2. 50-Min Deep Work & Hydration Coach (stretch & drink water).
3. Late-Night Overwork Sentry (1:00 AM - 5:00 AM guardian).
4. Genuine Windows OS Idle Detection (pauses timer if user steps away).
5. Focus Time Reporting on demand ("kitni der se kaam kar raha hoon").
"""

import time
import threading
import datetime

try:
    import win32api
except ImportError:
    win32api = None


class HealthFocusCoach:
    def __init__(self, voice=None, ai=None, gui=None, speak_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        self.running = False
        self._thread = None
        self.enabled = True

        # Session tracking state
        self._session_start_time = time.time()
        self._last_active_time = time.time()
        self._active_seconds_today = 0
        self._current_continuous_active_sec = 0

        # Milestone timestamps (in seconds of continuous active work)
        self._last_eye_alert_sec = 0
        self._last_pomodoro_alert_sec = 0
        self._last_late_night_alert_time = 0

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
        self._session_start_time = time.time()
        self._last_active_time = time.time()
        self._thread = threading.Thread(target=self._coach_loop, daemon=True)
        self._thread.start()
        print("[health_focus_coach] Health, Ergonomics & Focus Coach started.")

    def stop(self):
        self.running = False

    def _get_idle_seconds(self) -> float:
        """Returns seconds since last keyboard or mouse input across entire Windows OS."""
        if win32api:
            try:
                millis = win32api.GetTickCount() - win32api.GetLastInputInfo()
                return millis / 1000.0
            except Exception:
                pass
        return 0.0

    def _speak_alert(self, message: str, emotion: str = "calm", priority: str = "low"):
        """Thread-safe proactive gentle speech notification."""
        try:
            import workspace_harmonizer
            if not workspace_harmonizer.harmonizer.can_speak_proactively(priority=priority):
                return
        except Exception:
            pass
        try:
            if self.speak_fn:
                self.speak_fn(message, emotion=emotion)
            elif self.voice:
                self.voice.speak(message, interruptible=True, emotion=emotion)
        except Exception as e:
            print(f"[health_focus_coach alert error: {e}]")

    def _coach_loop(self):
        while self.running:
            try:
                if not self.enabled:
                    time.sleep(5.0)
                    continue

                idle_sec = self._get_idle_seconds()

                with self._lock:
                    if idle_sec < 180:  # User is active (idle < 3 minutes)
                        self._current_continuous_active_sec += 4
                        self._active_seconds_today += 4
                    else:
                        # User stepped away for >= 3 minutes -> Reset continuous counter (took a break)
                        if self._current_continuous_active_sec > 600:
                            self._current_continuous_active_sec = 0
                            self._last_eye_alert_sec = 0
                            self._last_pomodoro_alert_sec = 0

                self._check_health_milestones()

            except Exception as e:
                print(f"[health_focus_coach loop error: {e}]")

            time.sleep(4.0)

    def _check_health_milestones(self):
        with self._lock:
            active_sec = self._current_continuous_active_sec

        # 1. 20-20-20 Eye Strain Guard (every 20 minutes of continuous screen work = 1200 sec)
        if active_sec >= 1200 and (active_sec - self._last_eye_alert_sec) >= 1200:
            self._last_eye_alert_sec = active_sec
            self._speak_alert("Boss, 20 minute se screen dekh rahe hain. 20 second ke liye door dekh lijiye taaki aankhon par strain na pade.", emotion="calm")
            return

        # 2. 50-Minute Deep Work & Hydration Reminder (50 minutes = 3000 sec)
        if active_sec >= 3000 and (active_sec - self._last_pomodoro_alert_sec) >= 3000:
            self._last_pomodoro_alert_sec = active_sec
            mins = active_sec // 60
            self._speak_alert(f"Aap {mins} minute se lagatar kaam kar rahe hain. 2 minute stretch kar lijiye aur thoda paani pee lijiye.", emotion="happy")
            return

        # 3. Late Night Overwork Guard (1:00 AM to 5:00 AM)
        now_hour = datetime.datetime.now().hour
        if (now_hour >= 1 and now_hour <= 4) and active_sec >= 2400:  # 40+ mins active late night
            now_time = time.time()
            if (now_time - self._last_late_night_alert_time) > 1800:  # Every 30 mins
                self._last_late_night_alert_time = now_time
                self._speak_alert(f"Boss, raat ke {datetime.datetime.now().strftime('%I:%M %p')} ho rahe hain aur aap kafi der se kaam kar rahe hain. Health ke liye rest kar lijiye.", emotion="concerned")

    def get_focus_summary(self) -> str:
        """Returns live focus duration for voice command."""
        with self._lock:
            active_sec = self._current_continuous_active_sec
            total_sec = self._active_seconds_today

        active_mins = active_sec // 60
        active_hrs = active_mins // 60
        rem_mins = active_mins % 60

        if active_hrs > 0:
            time_str = f"{active_hrs} ghante {rem_mins} minute"
        else:
            time_str = f"{active_mins} minute"

        return f"Aap pichle {time_str} se lagatar screen par active hain."


coach = HealthFocusCoach()
