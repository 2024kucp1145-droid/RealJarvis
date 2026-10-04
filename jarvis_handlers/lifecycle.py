# -*- coding: utf-8 -*-
"""
lifecycle.py
============
Jarvis ka startup / shutdown / wake / speak / listen — yaani "zinda hai" wali
saari logic. Ye woh hissa hai jo poori app ke dauran chalta rehta hai.

Baaki sab feature modules (router, vision, media, ...) sirf `self.speak()`,
`self.voice`, `self.gui` par depend karte hain — lifecycle inhe deta hai.
"""

import queue
import threading
import time

import auth
import config
import memory

from ai_brain import AIBrain
from voice import Voice
from wake_listener import WakeListener

from . import sentries
from .optional_deps import deps
from .text_patterns import DICTATION_STOP_PHRASES, SLEEP_PHRASES


class LifecycleMixin:
    """Construction, authentication, wake loop, speech, aur clean shutdown."""

    # ------------------------------------------------------------- creation
    def __init__(self, gui):
        self.gui = gui
        self.voice = Voice()
        self.wake_listener = WakeListener(self.voice, gui=self.gui)
        self.ai = AIBrain()

        # Optional components — load fail hue to None, aur None-safe handlers use karte hain
        screen_monitor_cls = deps.attr("screen_monitor", "ScreenMonitor")
        self.screen_monitor = screen_monitor_cls() if screen_monitor_cls else None
        eye_cursor_cls = deps.attr("eye_control", "EyeCursorController")
        self.eye_cursor = eye_cursor_cls() if eye_cursor_cls else None
        chat_gui_cls = deps.attr("chat_gui", "JarvisChatGUI")
        self.chat_gui = (
            chat_gui_cls(
                self.gui.root,
                on_send=self.handle_chat_message,
                on_voice=self.handle_chat_voice,
                on_file_drop=self.on_file_dropped,
                on_close=self.toggle_chat_mode_off,
            )
            if chat_gui_cls else None
        )

        self.session_authenticated = False
        self.running = True
        self.dictation_mode = False
        self.awaiting_modification = False
        self.gui.set_quit_callback(self.shutdown)
        self.gui.set_file_drop_callback(self.on_file_dropped)
        self.active_file = None
        self.chat_mode = False
        self.reminder_queue = queue.Queue()
        self.video_mode = False
        self.video_path = None
        self._sentries_started = False

        # Sequential Message Scheduler (FIFO multi-query processing & collision prevention)
        import message_scheduler
        self.scheduler = message_scheduler.MessageScheduler(
            dispatch_fn=self._execute_scheduled_query, gui=self.gui
        )
        self.scheduler.start()

    # ------------------------------------------------------------ scheduler
    def _execute_scheduled_query(self, text: str) -> bool:
        """Ek scheduled query execute karo (scheduler ke worker thread se)."""
        try:
            return self.handle_text(text)
        except Exception as e:  # noqa: BLE001
            print(f"[scheduled query execution error: {e}]")
            self.speak("Query execute karne me dikkat aa gayi.", emotion="concerned")
            return True

    def enqueue_query(self, text: str, source: str = "general", wait: bool = False) -> list:
        """Query ko FIFO queue me daalo (compound queries ek-ek karke answer hote hain)."""
        return self.scheduler.enqueue(text, source=source, wait=wait)

    # ------------------------------------------------------------- sentries
    def start_background_sentries(self):
        """
        Saari proactive sentries start karo — SIRF successful login ke baad.
        Missing optional module skip ho jaata hai (sentries registry khud handle karta hai).
        """
        if self._sentries_started:
            return
        self._sentries_started = True
        sentries.start_all(
            voice=self.voice,
            ai=self.ai,
            gui=self.gui,
            speak_fn=self.speak,
            dispatcher_fn=self.enqueue_query,
        )

    # ----------------------------------------------------------- speak/listen
    def speak(self, text: str, interruptible: bool = True, emotion: str = "calm",
              is_first_chunk: bool = True) -> bool:
        """
        Bolta hai. Chat mode mein bubble bhi dikhata hai. Instant barge-in supported.
        True return = user beech me bol kar interrupt kar chuka hai.
        """
        try:
            from interview_mode import interview_mode as _imode
            if _imode.is_active:
                return False
        except Exception:  # noqa: BLE001
            pass

        try:
            self.gui.set_emotion(emotion)
            self.gui.set_state("speaking")
            self.gui.show_message(text)
        except Exception:  # noqa: BLE001
            pass

        try:
            if self.chat_mode and self.chat_gui:
                self.chat_gui.add_jarvis_message(text, emotion)
        except Exception:  # noqa: BLE001
            pass

        interrupted = self.voice.speak(text, interruptible=interruptible, emotion=emotion,
                                        is_first_chunk=is_first_chunk)
        if interrupted:
            print("[main] User barged in during speech! Reacting instinctively...")
            try:
                self.gui.set_state("listening")
                self.gui.show_message("Ji boliye...")
            except Exception:  # noqa: BLE001
                pass
            cut_in = self.voice.listen(timeout=4, phrase_time_limit=10, wait_for_thought=True)
            if cut_in:
                print(f"[main] Interruption query captured: '{cut_in}', "
                      f"answering instantly within seconds!")
                self.enqueue_query(cut_in, source="barge_in", wait=False)
            return True

        try:
            self.gui.set_state("idle")
            self.gui.set_emotion("calm")
        except Exception:  # noqa: BLE001
            pass
        return False

    def listen(self, timeout=7, phrase_time_limit=10) -> str:
        self.gui.set_state("listening")
        text = self.voice.listen(timeout=timeout, phrase_time_limit=phrase_time_limit)
        self.gui.set_state("thinking" if text else "idle")
        return text

    def _capture_clean_screenshot(self, full: bool = True):
        """
        Jarvis ki apni window HIDE karke screenshot lo — taaki problem/screen
        pe Jarvis ka floating icon na dikhe aur AI galat jawab na de.
        full=True -> poori screen, full=False -> cursor region
        """
        import vision
        try:
            self.gui.root.withdraw()
            time.sleep(0.35)   # Window fully disappear hone do
        except Exception:  # noqa: BLE001
            pass

        try:
            img = vision.capture_full_screen() if full else vision.capture_cursor_region()
        except Exception:  # noqa: BLE001
            img = None
        finally:
            try:
                self.gui.root.deiconify()
            except Exception:  # noqa: BLE001
                pass
        return img

    # ------------------------------------------------------------- main loop
    def run_forever(self):
        """Background thread me chalta hai - GUI ke mainloop se alag."""
        memory.init_db()
        self._start_reminder_checker()
        # Screen monitor ON-DEMAND — sirf tab start hogi jab user screen command use kare
        self.wake_listener.start()

        # Pehli baar seedha login flow — wake word ka wait nahi karna.
        try:
            self.on_wake()
        except Exception as e:  # noqa: BLE001
            print(f"[startup error: {e}]")

        while self.running:
            self.wake_listener.wait_for_wake()
            if not self.running:
                break
            try:
                self.on_wake()
            except Exception as e:  # noqa: BLE001
                # Koi bhi unexpected error aaye toh poora Jarvis band nahi hoga -
                # bas is baar ka kaam skip karke wapas sunna shuru kar dega.
                print(f"[unexpected error, ignoring aur wapas sun rahi hoon: {e}]")
                self.gui.set_state("idle")

    def shutdown(self):
        self.running = False
        if self.screen_monitor is not None:
            try:
                self.screen_monitor.stop()
            except Exception as e:  # noqa: BLE001
                print(f"[shutdown: screen_monitor.stop error: {e}]")
        sentries.stop_all()

        for label, stop in (("scheduler", self.scheduler.stop),
                            ("wake_listener", self.wake_listener.stop)):
            try:
                stop()
            except Exception as e:  # noqa: BLE001
                print(f"[shutdown: {label}.stop error: {e}]")

        # start_eye_cursor/stop_eye_cursor dono self.voice ke saath call hote hain
        if self.eye_cursor is not None:
            try:
                self.eye_cursor.stop(self.voice)
            except Exception as e:  # noqa: BLE001
                print(f"[shutdown: eye_cursor.stop error: {e}]")

        try:
            self.gui.root.destroy()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ wake
    def on_wake(self):
        # Wake ho gaya - ab background wale wake-listeners pause karte hain
        # taaki mic device sirf command-listening use kare, koi conflict na ho.
        self.wake_listener.pause()
        try:
            self._handle_wake_session()
        finally:
            self.wake_listener.resume()

    def _handle_wake_session(self):
        if not self.session_authenticated:
            self.gui.set_state("thinking")
            self.gui.show_message("Verify kar rahi hoon...")
            ok = auth.authenticate(self.voice, gui=self.gui)

            if not ok:
                self.speak("Verification fail ho gaya. Sorry, main help nahi kar sakti.")
                return

            self.session_authenticated = True
            self.start_background_sentries()
            self.speak(f"Welcome, {config.USER_NAME}!")
        else:
            self.speak("Ji boliye?")

        self.command_loop()

    def command_loop(self):
        """
        Wake ke baad HAMESHA active rehta hai - jab tak user khud 'so jao' ya
        'bye jarvis' na bole, kabhi khud se sona nahi jaata.
        """
        while True:
            text = self.listen(timeout=15, phrase_time_limit=10)
            if not text:
                continue  # kuch nahi suna, bas dobara suno - so mat jao

            self.gui.show_message(f"Aapne kaha: {text}")

            if self.dictation_mode:
                if any(p in text.lower() for p in DICTATION_STOP_PHRASES):
                    self.dictation_mode = False
                    self.speak("Likhna band kar diya.")
                else:
                    self._type_text(text)
                continue

            if self.awaiting_modification:
                self.awaiting_modification = False
                import self_modify
                self_modify.perform_modification(self.voice, self.ai, text)
                continue

            clean_lower = text.strip().lower()
            if any(w in clean_lower for w in SLEEP_PHRASES):
                should_continue = self.handle_text(text)
                if not should_continue:
                    break
                continue

            # Route through Sequential FIFO Scheduler
            # Splits compound queries ("aur", "and also", "?") and answers sequentially
            self.enqueue_query(text, source="voice", wait=True)
            if not self.running or getattr(self.gui, "state", "") == "sleeping":
                break

    def _type_text(self, text: str):
        """
        Dictation mode me jo bhi bola gaya, wahi literally type kar deta hai.
        Pehle jaha mouse cursor abhi POINT kar raha hai wahi click karta hai
        (taaki text-caret wahi aa jaaye), phir type karta hai - isse jaha
        bhi mouse le jao, wahi likh jaata hai.
        """
        try:
            import pyautogui
            import time as _time
            x, y = pyautogui.position()
            pyautogui.click(x, y)
            _time.sleep(0.2)  # browser jaise apps ko focus register karne ka time do
            pyautogui.write(text + " ", interval=0.02)
        except Exception as e:  # noqa: BLE001
            print(f"[dictation type error: {e}]")

    # -------------------------------------------------------------- reminders
    def _start_reminder_checker(self):
        """Har 20 second me check karta hai koi reminder due toh nahi hai.
        Queue use karta hai taaki main thread se safely bole."""
        def _loop():
            import time as _time
            while self.running:
                try:
                    for reminder_id, message in memory.get_due_reminders():
                        self.reminder_queue.put((reminder_id, message))
                except Exception as e:  # noqa: BLE001
                    print(f"[reminder checker error: {e}]")
                _time.sleep(20)

        threading.Thread(target=_loop, daemon=True).start()