# -*- coding: utf-8 -*-
"""
main.py
=======
Real Jarvis - entry point. Isi file ko chalao:

    python main.py

Flow:
  1. App start hote hi Jarvis apna intro deta hai aur SEEDHA password poochta hai
     (wake word ka wait nahi karta pehli baar)
  2. Password sahi -> "Welcome, <naam>!" bolke commands sunna shuru
     Password ki jagah EXIT_PHRASE bola (jaise "jarvis not required") -> khud band ho jaata hai
     Password galat -> access deny
  3. "so jao" bolne se sleep mode me jaata hai - dubara "Jarvis" naam se jagana padega
     (us case me dubara password nahi maangega, session yaad rehta hai)
  4. Lambe AI jawab ke beech me bolna shuru karo toh Jarvis turant ruk jaata hai
     aur tumhari baat sunta hai (barge-in) - best earphones ke saath kaam karta hai
  5. Poora system background me chalta hai - chota floating icon se control hota hai
"""

import sys
import random
import threading
import queue
import re
import time

# Windows ka Command Prompt default me sirf limited characters (cp1252)
# print kar paata hai - special characters aane par crash ho sakta tha.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import config
from voice import Voice
from wake_listener import WakeListener
import auth
from gui import JarvisGUI
from command_data import find_command
from ai_brain import AIBrain
from eye_control import EyeCursorController
from file_intake import FileIntake
from screen_monitor import ScreenMonitor
from chat_gui import JarvisChatGUI
from web_control import execute_web_action, run_autonomous_web_task, extract_screen_info, stop_autonomous_agent
import self_modify
import memory
import reminders
import os_sandbox
import desktop_context
import ui_controller
import activity_tracker
import platform_actions
import proactive_guardian
import hardware_sentry
import health_focus_coach
import download_janitor
import email_sentry
import workspace_harmonizer
import web_workflow_assistant
import project_auto_doctor
import desktop_janitor
import autonomous_evolution
import whatsapp_mobile_bridge
import self_evolution_engine
import morning_briefing_sentry

from commands import system_commands, browser_commands, file_commands, email_commands
from custom import custom_functions
from commands import whatsapp_commands
import subprocess
import os


EXECUTORS = {
    "system": system_commands,
    "browser": browser_commands,
    "file": file_commands,
    "email": email_commands,
    "custom": custom_functions,
    "whatsapp": whatsapp_commands,
    
}

GREETINGS = [
    "Main bilkul achhi hoon! Aap bataiye, aaj main aapki kya madad karoon?",
    "Haanji! Aapka din kaisa jaa raha hai? Bataiye kya hukum hai mere liye.",
    "Main bilkul theek hoon! Aapke saath kaam karke mujhe hamesha bahut achha lagta hai, bataiye kya karna hai.",
]

# Fixed command list me na mile, aur "X kholo"/"X open karo" jaisa pattern
# ho, toh X ko generic app-launcher (Windows 'start' command) se try karte
# hain - isse fixed list se bahar wale apps (Spotify, VS Code, WhatsApp, etc)
# bhi naam bol kar khul sakte hain.
OPEN_APP_PATTERN = re.compile(
    r"^(.*?)\s+(kholo|khol do|khol dijiye|open karo|open kar do|chalu karo|start karo|shuru karo)$",
    re.IGNORECASE,
)

# Koi bhi keyboard key/shortcut bol kar dabane ke liye - "ctrl c dabao",
# "enter dabao", "alt f4 dabao" jaisa kuch bhi. Fixed list wale shortcuts
# (copy/paste/undo) alag se command_data.py me hain, ye unke ALAWA kisi
# bhi combination ko generic tareeke se handle karta hai.
SHORTCUT_PATTERN = re.compile(
    r"^(.*?)\s+(dabao|dabaiye|dabaao|press karo|key dabao|button dabao)$",
    re.IGNORECASE,
)
KEY_ALIASES = {
    "control": "ctrl", "ctrl": "ctrl", "cntrl": "ctrl", "kantrol": "ctrl",
    "shift": "shift",
    "alt": "alt",
    "windows": "win", "win": "win",
    "enter": "enter", "return": "enter", "enter key": "enter",
    "space": "space", "spacebar": "space", "space bar": "space",
    "tab": "tab",
    "escape": "esc", "esc": "esc",
    "delete": "delete", "del": "delete",
    "backspace": "backspace",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "home": "home", "end": "end",
    "pageup": "pgup", "pagedown": "pgdn",
}

# "likhna shuru karo" bolne ke baad jo bhi bolo, wahi type ho jaata hai -
# in phrases mein se koi bhi bolne se dictation mode band ho jaata hai.
DICTATION_STOP_PHRASES = [
    "likhna band karo", "type band karo", "likhna band",
    "typing band karo", "dictation band karo", "bas likhna band",
]


class Jarvis:
    def __init__(self, gui: JarvisGUI):
        self.gui = gui
        self.voice = Voice()
        self.wake_listener = WakeListener(self.voice, gui=self.gui)
        self.ai = AIBrain()
        self.eye_cursor = EyeCursorController()
        self.session_authenticated = False
        self.running = True
        self.dictation_mode = False
        self.awaiting_modification = False
        self.gui.set_quit_callback(self.shutdown)
        self.active_file = None
        self.gui.set_file_drop_callback(self.on_file_dropped)
        self.chat_gui = JarvisChatGUI(
            self.gui.root,
            on_send=self.handle_chat_message,
            on_voice=self.handle_chat_voice,
            on_file_drop=self.on_file_dropped,
            on_close=self.toggle_chat_mode_off,
        )
        self.chat_mode = False
        self.reminder_queue = queue.Queue()
        self.screen_monitor = ScreenMonitor()
        self.video_mode = False
        self.video_path = None
        self._sentries_started = False

    def start_background_sentries(self):
        """Starts all proactive background sentries ONLY after successful password/face login."""
        if self._sentries_started:
            return
        self._sentries_started = True

        # Start continuous workflow and clipboard tracker
        activity_tracker.tracker.start()
        # Phase 1: Start proactive clipboard & error guardian
        proactive_guardian.guardian.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak)
        # Phase 2: Start proactive hardware & battery sentry
        hardware_sentry.sentry.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak)
        # Phase 3: Start health & focus work-session coach
        health_focus_coach.coach.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak)
        # Phase 4: Start proactive download & file janitor
        download_janitor.janitor.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak)
        # Phase 5: Start urgent email & alert sentry
        email_sentry.sentry.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak)
        # Phase 6: Start contextual workspace harmonizer
        workspace_harmonizer.harmonizer.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak)
        # Phase 7: Start web & browser workflow assistant
        web_workflow_assistant.assistant.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak)
        # Phase 8: Start project & git auto-doctor
        project_auto_doctor.doctor.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak)
        # Phase 9: Start desktop janitor
        desktop_janitor.janitor.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak)
        # Phase 10: Start autonomous evolution & multi-step mission planner
        autonomous_evolution.evolution.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak, dispatcher_fn=self.handle_text)
        # Mobile Bridge: Start WhatsApp daemon (notifications-based, no Chrome)
        whatsapp_mobile_bridge.bridge.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak, dispatcher_fn=self.handle_text)
        # Self-Evolution: Start autonomous skill synthesizer engine
        self_evolution_engine.evolution_engine.start(voice=self.voice, ai=self.ai, gui=self.gui, speak_fn=self.speak)
        # Morning Stark Briefing: Start daily morning intelligence sentry
        morning_briefing_sentry.briefing_sentry.start(voice=self.voice, ai=self.ai, gui=self.gui)


    def speak(self, text: str, interruptible: bool = False, emotion: str = "calm",
              is_first_chunk: bool = True) -> bool:
        """Bolta hai. Chat mode mein bubble bhi dikhata hai."""
        try:
            self.gui.set_emotion(emotion)
            self.gui.set_state("speaking")
            self.gui.show_message(text)
        except Exception:
            pass

        # Chat mode: message bubble add karo
        try:
            if self.chat_mode and self.chat_gui:
                self.chat_gui.add_jarvis_message(text, emotion)
        except Exception:
            pass

        interrupted = self.voice.speak(text, interruptible=interruptible, emotion=emotion,
                                        is_first_chunk=is_first_chunk)
        try:
            self.gui.set_state("idle")
            self.gui.set_emotion("calm")
        except Exception:
            pass
        return interrupted

    def listen(self, timeout=7, phrase_time_limit=10) -> str:
        self.gui.set_state("listening")
        text = self.voice.listen(timeout=timeout, phrase_time_limit=phrase_time_limit)
        self.gui.set_state("thinking" if text else "idle")
        return text

    def _capture_clean_screenshot(self, full: bool = True):
        """
        Jarvis ki apni window HIDE karke screenshot lo — taaki problem/screen
        pe Jarvis ka floating icon na dikhe aur AI galat jawab na de.
        full=True → poori screen, full=False → cursor region
        """
        import vision
        try:
            self.gui.root.withdraw()
            time.sleep(0.35)   # Window fully disappear hone do
        except Exception:
            pass

        try:
            img = vision.capture_full_screen() if full else vision.capture_cursor_region()
        except Exception:
            img = None
        finally:
            try:
                self.gui.root.deiconify()
            except Exception:
                pass
        return img

    # ------------------------------------------------------------- lifecycle
    def run_forever(self):
        """Background thread me chalta hai - GUI ke mainloop se alag."""
        memory.init_db()
        self._start_reminder_checker()
        self.screen_monitor.start()  # Background screen monitoring shuru
        self.wake_listener.start()

        # App start hote hi seedha login/password flow shuru karo - wake
        # word ka wait nahi karna pehli baar.
        try:
            self.on_wake()
        except Exception as e:
            print(f"[startup error: {e}]")

        while self.running:
            self.wake_listener.wait_for_wake()
            if not self.running:
                break
            try:
                self.on_wake()
            except Exception as e:
                # Koi bhi anexpected error aaye, poora Jarvis band nahi hoga -
                # bas is baar ka kaam skip karke wapas sunna shuru kar dega.
                print(f"[unexpected error, ignoring aur wapas sun rahi hoon: {e}]")
                self.gui.set_state("idle")

    def shutdown(self):
        self.running = False
        self.screen_monitor.stop()
        try:
            hardware_sentry.sentry.stop()
        except Exception:
            pass
        try:
            proactive_guardian.guardian.stop()
        except Exception:
            pass
        try:
            health_focus_coach.coach.stop()
        except Exception:
            pass
        try:
            download_janitor.janitor.stop()
        except Exception:
            pass
        try:
            email_sentry.sentry.stop()
        except Exception:
            pass
        try:
            workspace_harmonizer.harmonizer.stop()
        except Exception:
            pass
        try:
            web_workflow_assistant.assistant.stop()
        except Exception:
            pass
        try:
            project_auto_doctor.doctor.stop()
        except Exception:
            pass
        try:
            desktop_janitor.janitor.stop()
        except Exception:
            pass
        try:
            autonomous_evolution.evolution.stop()
        except Exception:
            pass
        try:
            whatsapp_mobile_bridge.bridge.stop()
        except Exception:
            pass
        try:
            morning_briefing_sentry.briefing_sentry.stop()
        except Exception:
            pass

        try:
            self.wake_listener.stop()
        except Exception as e:
            print(f"[shutdown: wake_listener.stop error: {e}]")
        try:
            # start_eye_cursor/stop_eye_cursor dono self.voice ke saath
            # call hote hain (lines above) - yaha bhi wahi signature.
            self.eye_cursor.stop(self.voice)
        except Exception as e:
            print(f"[shutdown: eye_cursor.stop error: {e}]")
        try:
            self.gui.root.destroy()
        except Exception:
            pass

    # ----------------------------------------------------------------- wake
    def on_wake(self):
        # Wake ho gaya - ab background wale wake-listeners ko pause karte hain
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

    # ------------------------------------------------------------- commands
    def command_loop(self):
        """Wake ke baad HAMESHA active rehta hai - jab tak user khud 'so
        jao' ya 'bye jarvis' na bole, kabhi khud se sona nahi jaata."""
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
                self_modify.perform_modification(self.voice, self.ai, text)
                continue

            should_continue = self.handle_text(text)
            if not should_continue:
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
        except Exception as e:
            print(f"[dictation type error: {e}]")

    def handle_text(self, text: str) -> bool:
        """Return False agar conversation/session yahi khatam karni ho."""
        
        # ---- HUMAN PARALINGUISTIC BIO-EVENT HANDLER (Yawn, Laugh, Hum, Cry) ----
        try:
            from acoustic_filter_engine import acoustic_filter
            bio_event = acoustic_filter.detect_paralinguistic_event(b"", text=text)
            if bio_event.get("event") != "none" and bio_event.get("message"):
                self.speak(bio_event["message"], emotion=bio_event.get("emotion", "calm"))
                return True
        except Exception as e:
            print(f"[paralinguistic bio-event error: {e}]")

        # ---- VIDEO MODE ----
        if getattr(self, 'video_mode', False):
            return self._handle_video_commands(text)

        # ---- AUTONOMOUS GAME & WEBGL SYNTHESIZER PRIORITY TRIGGER ----
        try:
            clean_lower = text.strip().lower()
            if any(w in clean_lower for w in ("game bana", "game chalu", "game generate", "subway surfer", "subway surfers", "3d runner", "snake game", "space shooter", "shooter game", "racing game", "flappy bird", "puzzle game", "play game", "arcade game")):
                import game_synthesizer
                game_synthesizer.synthesizer.synthesize_custom_game(text)
                self.speak("Boss, maine game synthesize karke aapke browser mein launch kar diya hai. Enjoy kijiye!", emotion="excited")
                return True
        except Exception as e:
            print(f"[game_synthesizer priority error: {e}]")
        
        cmd_id, data, matched_trigger = find_command(text)
        # ... baaki same code ...
         # ---- FIXED COMMAND: AI history mein log karo taaki context rahe ----
        if cmd_id:
            try:
                self.ai.history.append({"role": "user", "parts": [{"text": text}]})
                self.ai.history.append({"role": "model", "parts": [{"text": f"[Command executed: {cmd_id}]"}]})
            except Exception:
                pass
        # ---- PHASE 10: MACRO LEARNING & EXECUTION ----
        text_lower = text.lower()
        if "jab main boloon" in text_lower or "jab bhi main bolu" in text_lower or "jab main kahu" in text_lower:
            autonomous_evolution.evolution.learn_macro_from_voice(text)
            return True

        if not cmd_id and autonomous_evolution.evolution.check_and_execute_macro(text):
            return True

        # ---- FILE INTAKE MODE ----
        if self.active_file:
            # "complete" / "ho gaya" → file bahar nikaalo
            if any(phrase in text.lower() for phrase in ("complete", "ho gaya", "done", "file band karo", "bahar nikaalo", "bas karo")):
                self.clear_active_file()
                return True

            # Agar koi specific command match nahi hui, toh file Q&A samjho
            if not cmd_id:
                return self.handle_file_question(text)
            # Agar command match hui (jaise "volume badhao"), toh wo chalegi

        # ---- SELF-EVOLUTION LEARNING PERMISSION FOLLOW-UP ----
        try:
            if self_evolution_engine.evolution_engine.has_pending_permission():
                text_lower = text.lower()
                affirmative = (
                    "haan", "ha", "yes", "yep", "yeah", "seekh lo", "seekho",
                    "banao", "banaa do", "bana do", "banado", "bana doon", "bana de", "banaa",
                    "kar do", "kardo", "karo", "theek hai", "thik hai", "thik h", "theek h",
                    "sure", "ok", "okay", "bilkul", "start", "approve", "allow", "proceed", "go ahead", "chalo", "sahi hai"
                )
                negative = (
                    "nahi", "cancel", "mat karo", "rehne do", "no", "stop", "chhod do", "mat banao", "dont", "don't", "reject"
                )
                if any(w in text_lower for w in affirmative):
                    self_evolution_engine.evolution_engine.confirm_learning_permission(True)
                    return True
                elif any(w in text_lower for w in negative):
                    self_evolution_engine.evolution_engine.confirm_learning_permission(False)
                    return True
        except Exception as e:
            print(f"[self_evolution permission hook error: {e}]")

        # ---- UNIVERSAL PREDICTIVE COPILOT PERMISSION FOLLOW-UP ----
        try:
            import universal_predictive_copilot
            if universal_predictive_copilot.predictive_copilot.has_pending_prediction():
                text_lower = text.lower()
                affirmative = (
                    "haan", "ha", "yes", "yep", "yeah", "kar do", "kardo", "karo", "likh do",
                    "theek hai", "thik hai", "sure", "ok", "okay", "bilkul", "execute karo",
                    "banao", "bana do", "banado", "banaa do", "chalo"
                )
                negative = ("nahi", "cancel", "mat karo", "rehne do", "no", "stop", "chhod do")
                if any(w in text_lower for w in affirmative):
                    universal_predictive_copilot.predictive_copilot.execute_pending_prediction(voice=self.voice, gui=self.gui)
                    return True
                elif any(w in text_lower for w in negative):
                    universal_predictive_copilot.predictive_copilot.clear_pending()
                    self.speak("Theek hai boss, step cancel kar diya.")
                    return True
        except Exception as e:
            print(f"[predictive_copilot follow-up error: {e}]")

        # ---- PROACTIVE GUARDIAN FOLLOW-UP ----
        # Agar user ne Jarvis ke proactive error alert ka response diya
        # jaise "haan batao", "fix kya hai", "solution copy karo", "theek karo"
        try:
            if hasattr(proactive_guardian.guardian, 'has_pending_solution') and proactive_guardian.guardian.has_pending_solution():
                confirm_words = ("haan", "batao", "fix", "solution", "theek", "copy", "kar do", "yes", "solve", "bataiye", "bata do")
                if any(w in text.lower() for w in confirm_words):
                    fix_reply = proactive_guardian.guardian.apply_or_explain_fix()
                    self.speak(fix_reply, emotion="happy")
                    return True
        except Exception as e:
            print(f"[proactive_guardian hook error: {e}]")

        # ---- HARDWARE SENTRY PROCESS KILL FOLLOW-UP ----
        # Agar RAM choke hone par user ne process close karne ko bola
        try:
            if hasattr(hardware_sentry.sentry, 'has_pending_kill_action') and hardware_sentry.sentry.has_pending_kill_action():
                kill_words = ("haan", "close", "band", "kill", "hatao", "kar do", "yes", "theek hai")
                if any(w in text.lower() for w in kill_words):
                    kill_reply = hardware_sentry.sentry.kill_culprit_process()
                    self.speak(kill_reply, emotion="happy")
                    return True
        except Exception as e:
            print(f"[hardware_sentry hook error: {e}]")

        # ---- PROJECT AUTO-DOCTOR: CLIPBOARD ERROR INSPECTION ----
        # Agar user ne terminal error copy karke kuch bola toh auto-detect karo
        try:
            import pyperclip
            clip = pyperclip.paste() or ""
            if clip and ("ModuleNotFoundError" in clip or "ImportError" in clip or
                         "EADDRINUSE" in clip or "address already in use" in clip or
                         "Cannot find module" in clip):
                triggered = project_auto_doctor.doctor.inspect_terminal_error(clip)
                if triggered:
                    return True
        except Exception:
            pass


        # ---- DOWNLOAD JANITOR FOLLOW-UP ----
        # Agar nayi file download hone par user ne open/organize/extract karne ko bola
        try:
            if hasattr(download_janitor.janitor, 'has_pending_file_action') and download_janitor.janitor.has_pending_file_action():
                text_lower = text.lower()
                if any(w in text_lower for w in ("organize", "move", "folder mein", "categorize", "shift")):
                    reply = download_janitor.janitor.organize_pending_file()
                    self.speak(reply, emotion="happy")
                    return True
                elif any(w in text_lower for w in ("extract", "unzip", "khol do archive")):
                    reply = download_janitor.janitor.extract_pending_archive()
                    self.speak(reply, emotion="happy")
                    return True
                elif any(w in text_lower for w in ("open", "kholo", "haan", "khol do", "chalao", "dikhao", "yes")):
                    reply = download_janitor.janitor.open_pending_file()
                    self.speak(reply, emotion="happy")
                    return True
        except Exception as e:
            print(f"[download_janitor hook error: {e}]")

        # ---- EMAIL SENTRY FOLLOW-UP ----
        # Agar nayi urgent email aane par user ne summary sunne ya inbox kholne ko bola
        try:
            if hasattr(email_sentry.sentry, 'has_pending_email') and email_sentry.sentry.has_pending_email():
                text_lower = text.lower()
                if any(w in text_lower for w in ("inbox", "gmail", "kholo email", "open karo email", "browser")):
                    reply = email_sentry.sentry.open_gmail_inbox()
                    self.speak(reply, emotion="happy")
                    return True
                elif any(w in text_lower for w in ("haan", "sunao", "padho", "summary", "batao", "kya likha hai", "yes", "bataiye")):
                    reply = email_sentry.sentry.read_pending_summary()
                    self.speak(reply, emotion="happy")
                    return True
        except Exception as e:
            print(f"[email_sentry hook error: {e}]")

        # ---- PROJECT AUTO-DOCTOR FOLLOW-UP ----
        # Agar missing library install ya blocked port free karne ko bola
        try:
            if hasattr(project_auto_doctor.doctor, 'has_pending_install') and project_auto_doctor.doctor.has_pending_install():
                if any(w in text.lower() for w in ("haan", "install", "kar do", "yes", "theek hai", "kardo")):
                    reply = project_auto_doctor.doctor.install_pending_package()
                    self.speak(reply, emotion="happy")
                    return True
            if hasattr(project_auto_doctor.doctor, 'has_pending_port_kill') and project_auto_doctor.doctor.has_pending_port_kill():
                if any(w in text.lower() for w in ("haan", "port", "free", "kill", "clean", "kar do", "yes", "theek hai")):
                    reply = project_auto_doctor.doctor.free_port()
                    self.speak(reply, emotion="happy")
                    return True
        except Exception as e:
            print(f"[project_auto_doctor hook error: {e}]")

        # ---- DESKTOP JANITOR FOLLOW-UP ----
        try:
            if desktop_janitor.janitor.has_pending_old_files():
                if any(w in text.lower() for w in ("haan", "daal do", "yes", "trash", "hatao", "theek hai", "kar do")):
                    reply = desktop_janitor.janitor.trash_old_downloads()
                    self.speak(reply, emotion="happy")
                    return True
            if desktop_janitor.janitor.has_pending_duplicates():
                if any(w in text.lower() for w in ("haan", "duplicates hatao", "delete karo", "yes", "hatao", "theek hai", "kar do")):
                    reply = desktop_janitor.janitor.trash_duplicates()
                    self.speak(reply, emotion="happy")
                    return True
        except Exception as e:
            print(f"[desktop_janitor hook error: {e}]")




        # ---- UNIVERSAL PREDICTIVE COPILOT (ASTRA-STYLE WORKFLOW PREDICTION) ----
        clean_lower = text.strip().lower()
        if any(w in clean_lower for w in ("next step", "agla step", "aage kya", "suggest step", "predict workflow", "mera kaam dekho", "workflow suggest", "aage ka step")):
            import universal_predictive_copilot
            pred = universal_predictive_copilot.predictive_copilot.analyze_and_predict(text)
            if pred:
                self.speak(pred.speech_summary, emotion="excited")
                return True

        # ---- AVENGERS ASSEMBLE PROTOCOL (FULL SYSTEM DIAGNOSTICS) ----
        if any(w in clean_lower for w in ("avengers assemble", "avenger assemble", "avengers ready", "assemble avengers", "system diagnostics", "all systems check", "system health check")):
            import avengers_protocol
            avengers_protocol.protocol.execute_assemble_protocol(voice=self.voice, ai=self.ai, gui=self.gui)
            return True

        # ---- EXPLICIT SELF-EVOLUTION LEARNING TRIGGER ----
        if any(w in clean_lower for w in ("naya skill seekho", "naya feature seekho", "ye kaam seekh lo", "ye automate karo", "naya skill banao", "seekh lo")):
            self_evolution_engine.evolution_engine.triage_missing_skill(text)
            return True

        # ---- LEARNED SKILLS USER MANUAL OPENER ----
        if any(w in clean_lower for w in ("skills manual", "skill manual", "manual kholo", "manual khol do", "manual dikhao", "skills guide", "custom skills manual", "skills document")):
            import skills_manual_manager
            opened = skills_manual_manager.manual_manager.open_manual()
            if opened:
                self.speak("Boss, maine learned skills ka complete manual screen par open kar diya hai. Aap wahan se sabhi voice commands aur unka use padh sakte hain.", emotion="happy")
                return True

        # ---- SKILL SCOUT DISCOVERY POPUP TRIGGER ----
        if any(w in clean_lower for w in ("naye skills dhundo", "naye skills propose", "skills propose", "propose skills", "skills scout karo", "scout skills")):
            import skill_scout_engine
            skill_scout_engine.scout_engine.present_proposals_vocally(voice=self.voice, gui=self.gui)
            return True

        # ---- SKILL DASHBOARD & INTROSPECTION ----
        if any(w in clean_lower for w in ("kya kya seekha", "kya seekha", "learned skills", "skills batao", "apne skills", "skills dashboard", "show skills")):
            import skill_dashboard
            summary_speech = skill_dashboard.dashboard.get_summary_speech()
            self.speak(summary_speech, emotion="happy")
            try:
                if self.gui and hasattr(self.gui, 'root'):
                    self.gui.root.after(0, lambda: skill_dashboard.dashboard.open_dashboard_gui(self.gui.root))
            except Exception:
                pass
            return True

        # ---- DYNAMIC SELF-EVOLVED CUSTOM SKILLS ----
        try:
            import dynamic_hot_reloader
            custom_res = dynamic_hot_reloader.hot_reloader.match_and_execute(text, context={"gui": self.gui})
            if custom_res:
                msg = custom_res.get("message", "Task successfully execute ho gaya hai.")
                self.speak(msg, emotion="happy")
                return True
        except Exception as e:
            print(f"[custom_skill execution error: {e}]")

        # ---- STARK MORNING BRIEFING ----
        try:
            clean_text_lower = text.strip().lower()
            if any(w in clean_text_lower for w in ("good morning", "morning briefing", "daily briefing", "aaj ka update", "morning update", "stark briefing", "aaj ka schedule", "morning report")):
                import morning_briefing_sentry
                morning_briefing_sentry.briefing_sentry.voice = self.voice
                morning_briefing_sentry.briefing_sentry.ai = self.ai
                morning_briefing_sentry.briefing_sentry.gui = self.gui
                morning_briefing_sentry.briefing_sentry.deliver_briefing(is_auto=False)
                return True
        except Exception as e:
            print(f"[morning_briefing voice command error: {e}]")

        # ---- UNIVERSAL AUTONOMOUS WEB OPERATOR ----
        try:
            clean_text_lower = text.strip().lower()
            if any(w in clean_text_lower for w in ("compare price", "price check", "flipkart", "amazon", "leetcode problem", "search on google", "web operator")):
                import universal_web_operator
                universal_web_operator.web_operator.voice = self.voice
                universal_web_operator.web_operator.ai = self.ai
                universal_web_operator.web_operator.gui = self.gui
                res = universal_web_operator.web_operator.execute_web_goal(text)
                if res and res.get("success"):
                    return True
        except Exception as e:
            print(f"[universal_web_operator error: {e}]")

        # ---- GOOGLE MAPS & TRAVEL INTELLIGENCE HUB ----
        try:
            clean_text_lower = text.strip().lower()
            if any(w in clean_text_lower for w in ("google map", "route dikhao", "kitna time lagta", "se jaipur", "to jaipur", "train dikhao", "bus dikhao", "flight dikhao", "travel time", "kaise jaye", "kaise jaana", "rasta dikhao", "maps", "distance batao")):
                import google_maps_travel_hub
                google_maps_travel_hub.travel_hub.voice = self.voice
                google_maps_travel_hub.travel_hub.ai = self.ai
                google_maps_travel_hub.travel_hub.gui = self.gui
                res = google_maps_travel_hub.travel_hub.answer_travel_query(text)
                if res:
                    return True
        except Exception as e:
            print(f"[google_maps_travel_hub error: {e}]")

        # ---- AUTONOMOUS GAME & WEBGL SYNTHESIZER ----
        try:
            clean_lower = text.strip().lower()
            if any(w in clean_lower for w in ("subway surfer", "subway surfers", "3d game", "runner game", "game bana", "game chalu karo", "game generate", "snake game", "space game", "shooter game", "play game", "arcade game")):
                import game_synthesizer
                game_synthesizer.synthesizer.synthesize_custom_game(text)
                self.speak("Boss, maine game synthesize karke browser mein launch kar diya hai. Enjoy kijiye!", emotion="excited")
                return True
        except Exception as e:
            print(f"[game_synthesizer error: {e}]")

        if not cmd_id:
            # STT kabhi-kabhi trailing punctuation (., ?) add kar deta hai -
            # usse hata ke match karte hain, warna pattern silently fail ho
            # jaata tha.
            
            clean_text = text.strip().rstrip(".?!,")
            app_match = OPEN_APP_PATTERN.match(clean_text)
            if app_match and app_match.group(1).strip():
                app_name = app_match.group(1).strip()
                # Guard: Do not treat long complex prompts or game synthesis requests as OS apps
                if len(app_name.split()) <= 3 and not any(v in app_name.lower() for v in ("game", "banao", "banakar", "create", "generate", "code", "runner", "surfer", "for")):
                    print(f"[generic app-open matched: '{app_name}']")
                    system_commands.open_any_app(self.voice, name=app_name)
                    return True

            shortcut_match = SHORTCUT_PATTERN.match(clean_text)
            if shortcut_match and shortcut_match.group(1).strip():
                if self._press_shortcut(shortcut_match.group(1).strip()):
                    return True

            # ---- PLATFORM-AWARE LIVE AUTOMATION ----
            # Jo bhi platform khula ho (YouTube/Instagram/WhatsApp/etc.)
            # us par seedha adapt karke action karo — AI ko call karne ki zaroorat nahi
            if platform_actions.route_platform_action(text, self.voice, self.ai):
                return True

            # ---- ALWAYS-ON VISION: Sirf tab trigger hoga jab user EXPLICITLY screen/display ke baare mein pooche ----
            if self.screen_monitor.is_running() and self.screen_monitor.get_latest():
                explicit_visual_keywords = [
                    "screen par kya hai", "screen dekho", "meri screen dekho",
                    "screen padho", "display par kya hai", "screen samjhao",
                    "screen pe kya khula hai", "what is on my screen", "look at my screen"
                ]
                if any(kw in text.lower() for kw in explicit_visual_keywords):
                    return self.handle_monitor_vision(text)

            if self.ai.available():
                # Build live associative memory + desktop workflow context
                mem_ctx = memory.build_memory_context(current_query=text, limit=4)
                desktop_ctx = desktop_context.build_context_summary()
                full_ctx = f"{mem_ctx}\n\n{desktop_ctx}"

                # ---- AGENTIC CHAIN-OF-THOUGHT (CoT) REASONING LOOP ----
                import agentic_cot_brain
                step = agentic_cot_brain.cot_brain.reason_and_plan(text, context=full_ctx)

                if step.action_name:
                    if step.response_text:
                        self.speak(step.response_text, emotion=step.emotion)
                    agentic_cot_brain.cot_brain.execute_step_action(step, jarvis_instance=self)
                    return True
                else:
                    if step.response_text:
                        interrupted = self.speak(step.response_text, interruptible=True, emotion=step.emotion)
                        if interrupted:
                            follow_up = self.listen(timeout=6, phrase_time_limit=10)
                            if follow_up:
                                self.gui.show_message(f"Aapne kaha: {follow_up}")
                                return self.handle_text(follow_up)
                        return True
                    else:
                        interrupted = self.speak_ai_stream(text)
                        if interrupted:
                            follow_up = self.listen(timeout=6, phrase_time_limit=10)
                            if follow_up:
                                self.gui.show_message(f"Aapne kaha: {follow_up}")
                                return self.handle_text(follow_up)
                        return True

                # Check if unhandled intent is an actionable missing skill
                if self_evolution_engine.evolution_engine.triage_missing_skill(text, context=full_ctx):
                    return True

                # Fallback (function-calling wala tareeka fail ho gaya kisi
                # wajah se) - purana streaming chat try karo.
                interrupted = self.speak_ai_stream(text)
                if interrupted:
                    follow_up = self.listen(timeout=6, phrase_time_limit=10)
                    if follow_up:
                        self.gui.show_message(f"Aapne kaha: {follow_up}")
                        return self.handle_text(follow_up)
            else:
                if self_evolution_engine.evolution_engine.triage_missing_skill(text):
                    return True
                self.speak("Samajh nahi paayi, dobara boliye ya thoda alag tarike se kahiye.")
            return True

        ctype = data["type"]
        action = data["action"]

        if ctype == "info":
            return self.handle_info(action)

        if ctype == "vision":
            if action == "read_full_screen":
                self.handle_read_screen(text)
            elif action == "write_code_for_screen":
                self.handle_write_code(text)
            elif action == "provide_coding_hint":
                web_workflow_assistant.assistant.provide_coding_hint(capture_fn=self._capture_clean_screenshot)
            elif action == "summarize_active_webpage":
                web_workflow_assistant.assistant.summarize_active_webpage(capture_fn=self._capture_clean_screenshot)
            elif action == "what_am_i_doing":
                self.handle_monitor_vision(text)
            else:
                self.handle_vision(text)
            return True
        
        # ---- WEB / APP VISUAL & AUTONOMOUS CONTROL ----
        if ctype == "web":
            execute_web_action(self.voice, self.ai, text)
            return True

        if ctype == "web_agent":
            run_autonomous_web_task(self.voice, self.ai, text)
            return True

        if ctype == "web_extract":
            extract_screen_info(self.voice, self.ai, text)
            return True

        if ctype == "email_ai":
            filter_who = None
            param_name = data.get("param")
            if param_name:
                filter_who = self._extract_param(text, matched_trigger)
            self.handle_email_query(text, filter_who=filter_who)
            return True

        if ctype == "memory":
            param_name = data.get("param")
            note_or_keyword = self._extract_param(text, matched_trigger) if param_name else ""
            self.handle_memory(action, note_or_keyword)
            return True

        if ctype == "email_ui":
            self.handle_open_email_window()
            return True

        if ctype == "run":
            self.run_program(action)
            return True

        if ctype == "keyboard":
            self.send_shortcut(action)
            return True

        if ctype == "guardian":
            if action == "replace_at_cursor":
                reply = proactive_guardian.guardian.replace_at_cursor()
                self.speak(reply, emotion="happy")
                return True

        executor_module = EXECUTORS.get(ctype)
        if executor_module and hasattr(executor_module, action):
            # Item #2 - Security/Permission Manager: destructive commands
            # (file delete, shutdown, restart) pehle confirm karwate hain.
            if data.get("confirm"):
                self.speak("Pakka? Haan boliye confirm karne ke liye, warna cancel kar deti hoon.")
                confirmation = self.listen(timeout=6, phrase_time_limit=5)
                if not confirmation or not any(
                    w in confirmation.lower() for w in ("haan", "yes", "confirm", "pakka", "kar do")
                ):
                    self.speak("Theek hai, cancel kar diya.")
                    return True

            kwargs = {}
            param_name = data.get("param")
            if param_name:
                remainder = self._extract_param(text, matched_trigger)
                if remainder:
                    kwargs[param_name] = remainder
            try:
                getattr(executor_module, action)(self.voice, **kwargs)
            except Exception as e:
                self.speak("Sorry, ye karte waqt error aa gaya.")
                print(f"[executor error: {e}]")
            return True

        self.speak("Ye feature abhi maine implement nahi kiya, jaldi add karungi.")
        return True

    @staticmethod
    def _extract_param(text: str, matched_trigger: str) -> str:
        """
        Bole gaye text me se trigger phrase hata kar jo bacha hai wahi
        actual naam/query hai. Jaise "gaana chalao kesariya" me se
        "gaana chalao" hata ke "kesariya" bachta hai.
        """
        if not matched_trigger:
            return ""
        lower = text.lower()
        idx = lower.find(matched_trigger)
        if idx == -1:
            return ""
        remainder = text[:idx] + text[idx + len(matched_trigger):]
        remainder = remainder.strip(" ,.-:")
        # chhote filler words hata do shuru/end se
        for filler in ("ka", "ke", "ki", "naam", "se", "ko"):
            words = remainder.split()
            if words and words[0] == filler:
                words = words[1:]
            if words and words[-1] == filler:
                words = words[:-1]
            remainder = " ".join(words)
        return remainder.strip()

    def speak_ai_stream(self, user_text: str) -> bool:
        """
        AI se streaming jawab leke turant-turant bolta hai - poore jawab
        generate hone ka wait nahi karta, jaise hi ek sentence ready hota
        hai bol deta hai. Isse response bahut fast lagta hai.
        Return True agar beech me interrupt hua.

        Item #1 (Memory) - ab ye pichli baaton ka context AI ko deta hai,
        aur har naya exchange automatically yaad rakh leta hai - kuch
        bolne ki zaroorat nahi.
        """
        memory_context = memory.build_memory_context(limit=6)
        workflow_ctx = activity_tracker.tracker.get_current_task_description()
        desktop_ctx = desktop_context.build_context_summary()
        combined_context = f"{memory_context}\n\n[Live Workflow]: {workflow_ctx}\n{desktop_ctx}"

        is_first = True
        full_reply = ""
        for sentence, emotion in self.ai.ask_stream(user_text, extra_context=combined_context):
            full_reply += sentence + " "
            interrupted = self.speak(sentence, interruptible=True, emotion=emotion,
                                      is_first_chunk=is_first)
            is_first = False
            if interrupted:
                memory.log_conversation(user_text, full_reply.strip() + " (beech me roka gaya)")
                if memory.looks_like_fact(user_text):
                    memory.save_note(f"{user_text} -> {full_reply.strip()}")
                return True

        memory.log_conversation(user_text, full_reply.strip())
        if memory.looks_like_fact(user_text):
            # Fact jaisi lagti baat hai (birthday, naam, pasand, etc) - isse
            # PERMANENT notes me bhi save karte hain taaki kabhi na bhoole,
            # sirf "recent conversations" tak limited na rahe.
            memory.save_note(f"{user_text} -> {full_reply.strip()}")
        return False

    def handle_open_email_window(self):
        """Email inbox ko ek proper window me kholta hai - scroll/click karke padh sakte ho."""
        from commands import email_commands

        if not config.EMAIL_ENABLED or not config.EMAIL_APP_PASSWORD:
            self.speak("Email abhi set up nahi hai. config.py me EMAIL_ADDRESS aur "
                       "EMAIL_APP_PASSWORD bhariye pehle.")
            return

        self.speak("Email khol rahi hoon...")
        emails = email_commands.get_recent_emails(limit=20)

        if not emails:
            self.speak("Koi email nahi mili ya connect karne me dikkat aa rahi hai.")
            return

        self.gui.open_email_inbox(emails)
        self.speak(f"{len(emails)} emails khol di hain, dekh lijiye.")

    def handle_memory(self, action: str, param: str):
        """Item #1 - Memory System. Naya, self-contained handler - kisi
        purani cheez ko chhuta nahi."""
        if action == "save_note":
            if not param:
                self.speak("Kya yaad rakhu? Kuch bataiye.")
                return
            ok = memory.save_note(param)
            self.speak("Yaad rakh liya." if ok else "Yaad rakhne me dikkat aa gayi.")

        elif action == "recall_notes":
            notes = memory.get_recent_notes(limit=5)
            if not notes:
                self.speak("Abhi tak kuch yaad rakhne ko nahi mila.")
                return
            summary = "; ".join(content for _, content in notes)
            self.speak(f"Ye yaad hai: {summary}")

        elif action == "search_notes":
            if not param:
                self.speak("Kis baare mein yaad dilau?")
                return
            notes = memory.search_notes(param, limit=3)
            if not notes:
                self.speak(f"{param} ke baare mein kuch yaad nahi hai.")
                return
            summary = "; ".join(content for _, content in notes)
            self.speak(f"Ye mila: {summary}")

        elif action == "set_reminder":
            msg = reminders.parse_and_set_reminder(param)
            self.speak(msg)

    def _start_reminder_checker(self):
        """Item #4 - har 20 second mein check karta hai koi reminder due
        toh nahi hai. Queue use karta hai taaki main thread se safely bole."""
        def _loop():
            import time as _time
            while self.running:
                try:
                    for reminder_id, message in memory.get_due_reminders():
                        self.reminder_queue.put((reminder_id, message))
                except Exception as e:
                    print(f"[reminder checker error: {e}]")
                _time.sleep(20)
        threading.Thread(target=_loop, daemon=True).start()

    def handle_email_query(self, user_text: str, filter_who: str = None):
        """
        Email ke baare me natural sawaal.
        - filter_who diya gaya hai (jaise "Rahul ka email dikhao") -> usi
          naam/subject se match karke emails dhoondta hai.
        - filter_who nahi diya (generic sawaal jaise "email me kya hai") ->
          seedha SABSE NAYI email dikhata hai.
        """
        from commands import email_commands

        if not config.EMAIL_ENABLED or not config.EMAIL_APP_PASSWORD:
            self.speak("Email abhi set up nahi hai. config.py me EMAIL_ADDRESS aur "
                       "EMAIL_APP_PASSWORD bhariye pehle (Gmail App Password chahiye hoga).")
            return
        if not self.ai.available():
            self.speak("AI setup nahi hai, isliye email samajh kar bata nahi paungi.")
            return

        self.gui.set_state("thinking")
        self.gui.show_message("Email check kar rahi hoon...")

        if filter_who:
            emails = email_commands.search_emails_content(filter_who, limit=5)
        else:
            emails = email_commands.get_recent_emails(limit=1)  # generic sawaal -> sirf latest

        if not emails:
            if filter_who:
                self.speak(f"{filter_who} se related koi email nahi mili.")
            else:
                self.speak("Koi email nahi mili, ya connect karne me dikkat aa rahi hai.")
            return

        email_summary = "\n\n".join(
            f"From: {e['from']}\nSubject: {e['subject']}\nDate: {e['date']}\nBody: {e['body']}"
            for e in emails
        )
        full_question = (
            f"User ka sawaal: {user_text}\n\n"
            f"Ye user ki asli email(s) hai (sirf yahi data sach hai):\n{email_summary}\n\n"
            f"IMPORTANT: Sirf UPAR diye gaye asli email data ka use karke jawab do. "
            f"Kabhi bhi khud se sender ka naam, email address, ya content mat banao/imagine "
            f"mat karo. Agar upar diye gaye data me sawaal ka jawab nahi hai, saaf keh do "
            f"'mujhe ye jaankari nahi mili' - guess mat karo."
        )
        reply, emotion = self.ai.ask(full_question)
        self.speak(reply, interruptible=True, emotion=emotion)

    def handle_write_code(self, user_text: str):
        """
        Smart code writing:
        1. Full problem screen se padhta hai (scroll karke agar poora na dikhe)
        2. Cursor region mein existing code detect karta hai
        3. Agar code hai → verify + fix with comments
        4. Agar nahi hai → scratch se likhta hai
        5. Cursor pe type karta hai (cursor busy/rotating rahega)
        """
        import vision
        if not vision.available():
            self.speak("Screen dekhne wali library install nahi hai.")
            return
        if not self.ai.available():
            self.speak("AI setup nahi hai.")
            return

        self.gui.set_state("thinking")
        self.speak("Screen dekh rahi hoon...")

        # ---- STEP 1: Clean screenshot — Jarvis ki apni window bina ----
        first_img = self._capture_clean_screenshot(full=True)
        if first_img is None:
            self.speak("Screenshot lene me dikkat aa gayi.")
            return

        status, language = self.ai.is_problem_complete_from_image(first_img)
        print(f"[problem check] status={status}, language={language}")

        all_images = [first_img]

        # Agar partial hai ya unknown hai, tabhi scroll karo — warna mat karo
        if status in ("partial", "unknown"):
            self.speak("Problem neeche bhi hai, scroll kar ke dekh rahi hoon...")
            self.gui.show_message("Neeche scroll kar rahi hoon...")
            try:
                self.gui.root.withdraw()
                time.sleep(0.3)
            except Exception:
                pass
            scroll_images = vision.scroll_and_capture_full_page(max_scrolls=3)
            try:
                self.gui.root.deiconify()
            except Exception:
                pass
            # Pehla hata do (duplicate hai), baaki add karo
            for img in scroll_images[1:]:
                if img:
                    all_images.append(img)


        # ---- STEP 2: Har image se problem text nikaalo ----
        self.gui.show_message("Problem padh rahi hoon...")
        problem_parts = []

        for i, img in enumerate(all_images):
            self.gui.show_message(f"Page {i+1} analyze kar rahi hoon...")
            part_text = self.ai.extract_problem_from_image(img)
            if part_text and part_text not in "\n\n".join(problem_parts):
                problem_parts.append(part_text)
                print(f"[page {i}] extracted {len(part_text)} chars")

        full_problem = "\n\n".join(problem_parts)
        if not full_problem or len(full_problem) < 20:
            self.speak("Problem padhne me dikkat aa gayi, dobara try kijiye.")
            return

        print(f"[full problem length: {len(full_problem)} chars]")

        # ---- STEP 3: Cursor pe existing code detect karo ----
        self.gui.show_message("Editor check kar rahi hoon...")
        time.sleep(0.5)
        editor_img = vision.get_cursor_region(width=700, height=450)
        existing_code = None

        if editor_img:
            existing_code = self.ai.extract_existing_code(editor_img)
            if existing_code:
                self.gui.show_message("Existing code verify kar rahi hoon...")
                print(f"[existing code detected, length: {len(existing_code)}]")
                
                # === GARBAGE DETECTION ===
                # Agar existing code bahut chhota hai ya sab ek line mein hai ya 
                # bahut zyada syntax errors dikh rahe hain, toh ignore karo
                lines = existing_code.split('\n')
                if len(existing_code) < 30 or len(lines) == 1 and len(existing_code) > 80:
                    # Either too short, or everything crammed in one line = garbage
                    print(f"[garbage code detected, ignoring. Lines: {len(lines)}, Length: {len(existing_code)}]")
                    existing_code = None
                
        # ---- STEP 4: Code generate karo ----
        self.gui.show_message("Code likh rahi hoon...")
        code = self.ai.generate_smart_code(full_problem, existing_code, language)

        if not code:
            self.speak("Code generate karne me dikkat aa gayi, dobara try kijiye.")
            return

        # === FORCE FORMATTING & CLEANING ===
        import re

        # Markdown fences hatao
        code = code.replace("```python", "").replace("```cpp", "").replace("```java", "")
        code = code.replace("```javascript", "").replace("```", "").strip()

        # Sab comments hatao
        code = re.sub(r'^\s*//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'^\s*#.*$', '', code, flags=re.MULTILINE)

        # GARBAGE DETECTION
        garbage_keywords = ['std::make_heap', 'uint16_t', 'wchar_t', 'register', 'intint', 'retureturn', 'endelse', 'ncase']
        lower_code = code.lower().replace(' ', '')
        if any(g.replace(' ', '') in lower_code for g in garbage_keywords):
            self.speak("Code generate karte waqt kuch galat ho gaya. Dobara try kijiye.")
            print(f"[GARBAGE DETECTED]")
            return

        # Force newlines around braces and semicolons
        code = re.sub(r';\s+', ';\n', code)
        code = re.sub(r'\{\s*', '{\n', code)
        code = re.sub(r'\}\s*', '}\n', code)

        # Clean lines
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Multiple statements in one line? Split by semicolon
            if ';' in line and line.count(';') > 1 and not line.startswith('#'):
                parts = [p.strip() + ';' for p in line.split(';') if p.strip()]
                cleaned_lines.extend(parts)
            else:
                cleaned_lines.append(line)

        # Normalize indentation (left align properly)
        indents = [len(l) - len(l.lstrip()) for l in cleaned_lines if l.lstrip()]
        if indents:
            min_indent = min(i for i in indents if i > 0) if any(i > 0 for i in indents) else 4
            final_lines = []
            for line in cleaned_lines:
                stripped = line.lstrip()
                current = len(line) - len(stripped)
                if current > 0 and min_indent > 0:
                    level = max(0, current // min_indent)
                    final_lines.append('    ' * level + stripped)
                else:
                    final_lines.append(stripped)
            cleaned_lines = final_lines

        code = '\n'.join(cleaned_lines)

        if len(cleaned_lines) <= 2 and len(code) > 50:
            self.speak("Code formatting theek nahi hui. Dobara try kijiye.")
            return

        print(f"[final code: {len(cleaned_lines)} lines]")

        # ---- STEP 5: Cursor pe click karke type karo ----
        try:
            import pyautogui
            import time as _time
            import threading

            x, y = pyautogui.position()
            pyautogui.click(x, y)
            _time.sleep(0.3)

            if existing_code:
                pyautogui.keyDown('ctrl')
                pyautogui.keyDown('a')
                pyautogui.keyUp('a')
                pyautogui.keyUp('ctrl')
                _time.sleep(0.2)

            # === CURSOR BUSY ===
            _stop_cursor = threading.Event()
            _normal_cursor = None

            def _rotate_cursor():
                try:
                    import win32gui
                    import win32con
                    busy = win32gui.LoadCursor(0, win32con.IDC_APPSTARTING)
                    normal = win32gui.LoadCursor(0, win32con.IDC_ARROW)
                    nonlocal _normal_cursor
                    _normal_cursor = normal
                    while not _stop_cursor.is_set():
                        win32gui.SetCursor(busy)
                        _stop_cursor.wait(0.15)
                except Exception:
                    pass

            cursor_thread = threading.Thread(target=_rotate_cursor, daemon=True)
            cursor_thread.start()

            try:
                # Line by line type karo taaki left alignment sahi rahe
                for line in code.split('\n'):
                    pyautogui.write(line, interval=0.01)
                    pyautogui.keyDown('return')
                    pyautogui.keyUp('return')
                    _time.sleep(0.03)
            finally:
                _stop_cursor.set()
                _time.sleep(0.2)
                try:
                    import win32gui
                    import win32con
                    if _normal_cursor:
                        win32gui.SetCursor(_normal_cursor)
                except Exception:
                    pass

            if existing_code:
                self.speak("Code likh diya.", interruptible=True)
            else:
                self.speak("Code likh diya.", interruptible=True)

        except Exception as e:
            self.speak("Code type karte waqt error aa gaya.")
            print(f"[handle_write_code type error: {e}]")
            
        # ------------------------------------------------------------- file intake
    def on_file_dropped(self, filepath: str):
        """User ne file drag karke Jarvis icon pe drop ki."""
        print(f"[main] File dropped: {filepath}")
        self.gui.set_state("file_intake")
        self.speak("File aa gayi, andar le rahi hoon...")

        # Purana video mode clear karo agar nayi file aayi hai
        if self.video_mode:
            self.video_mode = False
            self.video_path = None

        self.active_file = FileIntake(filepath)
        print(f"[main] Type check: image={self.active_file.is_image}, video={self.active_file.is_video}, folder={self.active_file.is_folder}, valid={self.active_file.is_valid()}")

        if not self.active_file.is_valid():
            self.speak(f"Sorry, {self.active_file.filename} read nahi kar payi.")
            self.active_file = None
            return

        if self.active_file.is_video:
            self.video_path = filepath
            self.video_mode = True
            self.active_file = None
            filename = os.path.basename(filepath)
            self.speak(f"{filename} video aa gayi. Kya karna hai? 'notes banao', 'summary do', ya 'transcribe karo'?")
            return

        if self.active_file.is_folder:
            item_count = self.active_file.content.count('\n')
            self.speak(f"{self.active_file.filename} folder aa gaya. Isme approximately {item_count} items hain. Ab kuch bhi pooch sakte ho. 'complete' bolke bahar nikaal do.")
            return

        if self.active_file.is_image:
            self.speak(f"{self.active_file.filename} image aa gayi. Ab kuch bhi pooch sakte ho. 'complete' bolke bahar nikaal do.")
        else:
            lines = self.active_file.content.count('\n') + 1
            chars = len(self.active_file.content)
            self.speak(f"{self.active_file.filename} andar aa gayi. {lines} lines, {chars} characters. Ab kuch bhi pooch sakte ho. 'complete' bolke bahar nikaal do.")
    
    def handle_file_question(self, text: str) -> bool:
        """Active file ke context mein sawaal ka jawab."""
        if not self.active_file:
            return False

        self.gui.set_state("thinking")
        self.gui.show_message("File padh rahi hoon...")

        try:
            # Image file → vision use karo
            if self.active_file.is_image:
                from PIL import Image
                image = Image.open(self.active_file.filepath)
                reply, emotion = self.ai.ask_about_image(text, image)
                self.speak(reply, interruptible=True, emotion=emotion)
                return True

            # Text file → AI ko prompt bhejo
            prompt = self.active_file.build_prompt(text)
            reply, emotion = self.ai.ask(prompt, skip_history_append=True)
            self.speak(reply, interruptible=True, emotion=emotion)
            return True

        except Exception as e:
            self.speak("File padhne mein dikkat aa gayi.")
            print(f"[handle_file_question error: {e}]")
            return True

    def clear_active_file(self):
        """File intake mode band karo."""
        if self.active_file:
            name = self.active_file.filename
            self.active_file = None
            self.speak(f"{name} bahar nikaal di. Ab normal baat-cheet.")
        else:
            self.speak("Koi file andar nahi hai.")

    def handle_read_screen(self, user_text: str):
        """Poori screen ka content padh kar sunata hai - jaise LeetCode
        problem, article, ya kisi bhi page ka poora text."""
        import vision
        if not vision.available():
            self.speak("Screen dekhne wali library install nahi hai.")
            return
        if not self.ai.available():
            self.speak("AI setup nahi hai.")
            return

        self.gui.set_state("thinking")
        self.gui.show_message("Poora page padh rahi hoon...")
        image = self._capture_clean_screenshot(full=True)
        if image is None:
            self.speak("Screenshot lene me dikkat aa gayi.")
            return

        reply, emotion = self.ai.ask_about_image(user_text, image)
        self.speak(reply, interruptible=True, emotion=emotion)

    def handle_vision(self, user_text: str):
        """Screen/cursor ke baare me sawaal - ek snapshot + window info leke AI se poochta hai."""
        import vision
        import desktop_context

        if not vision.available():
            self.speak("Screen dekhne wali library install nahi hai - pyautogui chahiye.")
            return
        if not self.ai.available():
            self.speak("AI setup nahi hai, isliye screen samajh nahi paungi.")
            return

        self.gui.set_state("thinking")
        image = self._capture_clean_screenshot(full=False)
        if image is None:
            self.speak("Screenshot lene me dikkat aa gayi.")
            return

        context_info = desktop_context.build_context_summary()
        full_question = f"{user_text}\n\n(Extra context: {context_info})"

        reply, emotion = self.ai.ask_about_image(full_question, image)
        self.speak(reply, interruptible=True, emotion=emotion)
    
    def handle_monitor_vision(self, user_text: str):
        """Screen monitor se latest image leke AI se jawab mangta hai."""
        import desktop_context
        
        if not self.ai.available():
            self.speak("AI setup nahi hai, isliye screen samajh nahi paungi.")
            return True

        image = self.screen_monitor.get_latest()
        if image is None:
            self.speak("Screen capture abhi available nahi hai, dobara try kijiye.")
            return True

        self.gui.set_state("thinking")
        self.gui.show_message("Screen dekh kar jawab de rahi hoon...")

        context_info = desktop_context.build_context_summary()
        full_question = (
            f"{user_text}\n\n"
            f"(Extra context: {context_info})\n\n"
            f"NOTE: Ye user ke screen ka latest snapshot hai. Jo bhi screen pe dikh raha hai "
            f"uska analysis do aur user ki madad karo."
        )

        reply, emotion = self.ai.ask_about_image(full_question, image)
        self.speak(reply, interruptible=True, emotion=emotion)
        return True

    def _press_shortcut(self, phrase: str) -> bool:
        """
        "ctrl c" jaisa bola gaya phrase ko actual keyboard combo me badal
        kar dabata hai. Return False agar koi valid key na mile (jisse
        AI conversation try ho sake), True agar dabaya (successfully ya
        error ke saath dono).
        """
        words = phrase.lower().replace("+", " ").split()
        keys = []
        for w in words:
            if w in KEY_ALIASES:
                keys.append(KEY_ALIASES[w])
            elif len(w) == 1 and (w.isalnum()):
                keys.append(w)  # single letter/number jaisa "c", "4"
            elif w.isdigit():
                keys.append(w)
            else:
                # pehchana nahi gaya word - shayad ye shortcut hai hi nahi,
                # kisi aur cheez ka sawaal hai ("mujhe kal ka plan batao" jaisa)
                return False

        if not keys:
            return False

        combo = "+".join(keys)
        try:
            import pyautogui
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)
            self.speak(f"{combo} dabaya.")
        except Exception as e:
            self.speak("Ye shortcut nahi dabaa payi.")
            print(f"[shortcut error: {e}]")
        return True

    def _dispatch_ai_action(self, function_name: str, args: dict):
        """AI ne jo function-call decide kiya, use actual code se execute karta hai."""
        try:
            if function_name == "open_app":
                system_commands.open_any_app(self.voice, name=args.get("app_name", ""))
            elif function_name == "open_website":
                browser_commands.open_website(self.voice, site=args.get("site_name", ""))
            elif function_name == "adjust_volume":
                direction = args.get("direction", "")
                {"up": system_commands.volume_up, "down": system_commands.volume_down,
                 "mute": system_commands.volume_mute, "unmute": system_commands.volume_unmute,
                 }.get(direction, lambda v: None)(self.voice)
            elif function_name == "adjust_brightness":
                direction = args.get("direction", "")
                {"up": system_commands.brightness_up,
                 "down": system_commands.brightness_down,
                 }.get(direction, lambda v: None)(self.voice)
            elif function_name == "play_youtube_song":
                browser_commands.play_youtube(self.voice, song=args.get("song", ""))
            elif function_name == "search_google":
                browser_commands.search_google(self.voice, query=args.get("query", ""))
            elif function_name == "execute_web_action":
                execute_web_action(self.voice, self.ai, args.get("description", ""))
            elif function_name == "run_autonomous_web_task":
                run_autonomous_web_task(self.voice, self.ai, args.get("goal", ""))
            elif function_name == "execute_python_script":
                code = args.get("code", "")
                self.speak("Script execute kar rahi hoon...", emotion="calm")
                res = os_sandbox.execute_python_code(code)
                if res["success"]:
                    out = res["output"][:300] if res["output"] else "Code execute ho gaya."
                    self.speak(out, emotion="happy")
                else:
                    err = res["error"][:200]
                    self.speak(f"Code execute karne me error aaya: {err}", emotion="concerned")
            elif function_name == "execute_powershell_command":
                cmd = args.get("command", "")
                self.speak("Command run kar rahi hoon...", emotion="calm")
                res = os_sandbox.execute_powershell(cmd)
                if res["success"]:
                    out = res["output"][:300] if res["output"] else "Command execute ho gaya."
                    self.speak(out, emotion="happy")
                else:
                    self.speak(f"Error: {res['error'][:200]}", emotion="concerned")
            elif function_name == "search_computer_files":
                q = args.get("query", "")
                self.speak(f"{q} dhoondh rahi hoon...")
                matches = os_sandbox.search_computer_files(q)
                if matches:
                    summary = ", ".join(f"{m['name']} ({m['size']})" for m in matches[:4])
                    self.speak(f"{len(matches)} files mili: {summary}", emotion="happy")
                else:
                    self.speak(f"Computer me {q} se related koi file nahi mili.")
            elif function_name == "get_system_vitals":
                vitals = os_sandbox.get_system_vitals()
                if "error" not in vitals:
                    self.speak(f"CPU usage hai {vitals['cpu_percent']} percent, RAM used hai {vitals['ram_percent']} percent, aur {vitals['ram_free_gb']} GB RAM khali hai.", emotion="happy")
                else:
                    self.speak("System stats read nahi kar payi.")
            elif function_name == "recall_memory":
                q = args.get("query", "")
                recalled = memory.search_semantic_memory(q, limit=4)
                if recalled:
                    summary = "; ".join(recalled[:3])
                    self.speak(f"Mujhe ye yaad hai: {summary}", emotion="happy")
                else:
                    self.speak("Is baare me koi purani baat yaad nahi mili.")
            elif function_name == "click_native_element":
                el = args.get("element_name", "")
                c_type = args.get("control_type", None)
                self.speak(f"{el} button pe click kar rahi hoon...", emotion="calm")
                res = ui_controller.click_native_element(el, control_type=c_type)
                if res["success"]:
                    self.speak(res["message"], emotion="happy")
                else:
                    self.speak(res["message"], emotion="concerned")
            elif function_name == "type_native_element":
                val = args.get("value", "")
                el = args.get("element_name", "")
                p_enter = args.get("press_enter", False)
                res = ui_controller.set_native_edit_text(el, val, press_enter=p_enter)
                self.speak(res["message"], emotion="happy" if res["success"] else "concerned")
            elif function_name == "list_clickable_elements":
                elems = ui_controller.list_clickable_elements(limit=8)
                if elems:
                    summary = ", ".join(elems[:5])
                    self.speak(f"Screen pe ye elements mile: {summary}", emotion="calm")
                else:
                    self.speak("Active window me koi native control detect nahi hua.")
            elif function_name == "arrange_window":
                act = args.get("action", "")
                res = ui_controller.arrange_window(act)
                self.speak(res["message"], emotion="happy" if res["success"] else "concerned")
            elif function_name == "get_workflow_timeline":
                timeline = activity_tracker.tracker.get_timeline_summary(limit=6)
                self.speak(f"Aapka recent activity summary:\n{timeline}", emotion="calm")
            elif function_name == "get_clipboard_analysis":
                clip_data = activity_tracker.tracker.get_latest_clipboard()
                clip_text = clip_data.get("text", "")
                if clip_text:
                    self.speak("Clipboard content analyze kar rahi hoon...", emotion="calm")
                    prompt = f"User ne ye text/code clipboard me copy kiya hai:\n\n{clip_text}\n\nIska seedha concise explanation ya solution do."
                    reply, emotion = self.ai.ask(prompt)
                    self.speak(reply, emotion=emotion)
                else:
                    self.speak("Clipboard par abhi koi text ya code copy nahi mila.")
            elif function_name == "explain_current_work":
                task = activity_tracker.tracker.get_current_task_description()
                self.speak(f"Aap abhi is par kaam kar rahe hain: {task}", emotion="happy")
            else:
                self.speak("Ye action abhi maine implement nahi kiya.")
        except Exception as e:
            self.speak("Ye karte waqt error aa gaya.")
            print(f"[_dispatch_ai_action error: {e}]")

    def handle_info(self, action: str) -> bool:
        if action == "greet":
            self.speak(random.choice(GREETINGS))
        elif action == "who_are_you":
            self.speak("Main aapka apna Jarvis hoon, poori tarah aapke laptop ke liye bana.")
        elif action == "focus_time_check":
            summary = health_focus_coach.coach.get_focus_summary()
            self.speak(summary, emotion="happy")
        elif action == "coding_mode_on":
            msg = workspace_harmonizer.harmonizer.launch_coding_workspace()
            self.speak(msg, emotion="happy")
        elif action == "study_mode_on":
            msg = workspace_harmonizer.harmonizer.launch_study_workspace()
            self.speak(msg, emotion="happy")
        elif action == "meeting_mode_on":
            msg = workspace_harmonizer.harmonizer.toggle_meeting_shield(on=True)
            self.speak(msg, emotion="calm")
        elif action == "meeting_mode_off":
            msg = workspace_harmonizer.harmonizer.toggle_meeting_shield(on=False)
            self.speak(msg, emotion="happy")
        elif action == "sleep_assistant":
            self.speak(f"Theek hai, main sone ja rahi hoon. '{config.ASSISTANT_NAME}' bolke jagana.")
            self.gui.set_state("sleeping")  # ← AANKHEIN BAND
            return False
        elif action == "exit_assistant":
            self.shutdown()
            return False
        elif action == "start_dictation":
            self.dictation_mode = True
            self.speak("Theek hai, ab jo boliye wahi type hoga. Rukne ke liye 'likhna band karo' boliye.")
        elif action == "start_eye_cursor":
            self.eye_cursor.start(self.voice)
        elif action == "stop_eye_cursor":
            self.eye_cursor.stop(self.voice)
        elif action == "stop_web_agent":
            stop_autonomous_agent()
            self.speak("Browser automation rok diya gaya hai.")
        elif action == "modify_self":
            self.awaiting_modification = True
            self.speak("Kya karna hai boss? Debugging karu, ya naya feature add karu?")
        elif action == "chat_mode_on":
            self.toggle_chat_mode_on()
            return True
        elif action == "chat_mode_off":
            self.toggle_chat_mode_off()
            return True
        elif action == "my_email_address":
            if config.EMAIL_ENABLED and config.EMAIL_ADDRESS:
                self.speak(f"Aapka email hai {config.EMAIL_ADDRESS}")
            else:
                self.speak("Email abhi config me set nahi kiya gaya hai.")

        elif action == "screen_monitor_start":
            self.screen_monitor.start(self.voice)
            self.speak("Screen monitoring chalu kar di. Ab main hamesha dekh rahi hoon aap kya kar rahe ho.")

        elif action == "screen_monitor_stop":
            self.screen_monitor.stop(self.voice)
            self.speak("Screen monitoring band kar di.")

        # ---------------- PHASE 8: PROJECT & GIT AUTO-DOCTOR ----------------
        elif action == "git_auto_commit":
            self.speak("Git status check kar rahi hoon...", emotion="calm")
            reply = project_auto_doctor.doctor.auto_git_commit_and_sync()
            self.speak(reply, emotion="happy")
        elif action == "git_status_check":
            reply = project_auto_doctor.doctor.get_git_status_summary()
            self.speak(reply, emotion="happy")
        elif action == "free_port_3000":
            self.speak("Port 3000 free kar rahi hoon...", emotion="calm")
            reply = project_auto_doctor.doctor.free_port("3000")
            self.speak(reply, emotion="happy")
        elif action == "free_port_8000":
            self.speak("Port 8000 free kar rahi hoon...", emotion="calm")
            reply = project_auto_doctor.doctor.free_port("8000")
            self.speak(reply, emotion="happy")
        elif action == "free_port_5000":
            self.speak("Port 5000 free kar rahi hoon...", emotion="calm")
            reply = project_auto_doctor.doctor.free_port("5000")
            self.speak(reply, emotion="happy")

        # ---------------- PHASE 9: DESKTOP JANITOR ----------------
        elif action == "organize_desktop":
            self.speak("Desktop organize kar rahi hoon, please ek second...", emotion="calm")
            reply = desktop_janitor.janitor.organize_desktop()
            self.speak(reply, emotion="happy")
        elif action == "clean_old_downloads":
            self.speak("Downloads folder scan kar rahi hoon...", emotion="calm")
            reply = desktop_janitor.janitor.find_old_downloads()
            self.speak(reply, emotion="concerned")
        elif action == "find_duplicate_files":
            self.speak("Duplicate files dhundh rahi hoon...", emotion="calm")
            reply = desktop_janitor.janitor.find_duplicates()
            self.speak(reply, emotion="concerned")
        elif action == "disk_space_report":
            reply = desktop_janitor.janitor.report_disk_space()
            self.speak(reply, emotion="happy")

        # ---------------- PHASE 10: AUTONOMOUS EVOLUTION & DIAGNOSTIC ----------------
        elif action == "system_diagnostic":
            autonomous_evolution.evolution.run_system_diagnostic()
        elif action == "list_macros":
            reply = autonomous_evolution.evolution.list_learned_macros()
            self.speak(reply, emotion="happy")

        # ---------------- WHATSAPP MOBILE BRIDGE (PHASES 1, 2 & 3) ----------------
        elif action == "send_laptop_telemetry_whatsapp":
            if not whatsapp_mobile_bridge.bridge.master_phone:
                self.speak("Aapka master WhatsApp number configure nahi hai. Pehle WhatsApp bridge mein number set kijiye.", emotion="concerned")
            else:
                self.speak("Laptop telemetry status WhatsApp par bhej rahi hoon...", emotion="calm")
                telemetry = whatsapp_mobile_bridge.bridge.get_telemetry_status()
                whatsapp_mobile_bridge.bridge.send_whatsapp_message(telemetry)
        elif action == "send_screenshot_whatsapp":
            self.speak("Live screenshot capture karke WhatsApp par bhej rahi hoon...", emotion="calm")
            reply = whatsapp_mobile_bridge.bridge.dispatch_screenshot_to_whatsapp()
            self.speak(reply, emotion="happy")
        elif action == "show_wol_instructions":
            info = remote_boot_wol.get_wol_configuration_info()
            self.speak("Remote boot aur Wake-on-LAN ki settings WhatsApp par bhej di hain.", emotion="happy")
            whatsapp_mobile_bridge.bridge.send_whatsapp_message(info)

        return True   # ← YE SABSE END MEIN HONA CHAHIYE




    # -------------------------------------------------------- run / keyboard
    def run_program(self, program: str):
        try:
            safe_program = program.strip().replace('"', '').replace('&', '').replace('|', '').replace('>', '').replace('<', '')
            if safe_program.startswith("ms-settings"):
                subprocess.run(["powershell", "-Command", f"Start-Process {safe_program}"])
            else:
                subprocess.Popen([safe_program], shell=False)
            self.speak("Khol diya.")
        except Exception as e:
            self.speak("Ye open nahi ho paaya.")
            print(f"[run_program error: {e}]")

    def send_shortcut(self, combo: str):
        try:
            import pyautogui
            # Click hata diya — keyboard shortcut ke liye zaroorat nahi
            import time as _time
            _time.sleep(0.05)

            parts = combo.lower().split("+")
            if len(parts) == 1:
                pyautogui.press(parts[0])
            else:
                pyautogui.hotkey(*parts)
            self.speak("Kar diya.")
        except Exception as e:
            self.speak("Shortcut bhejne me dikkat aa gayi.")
            print(f"[send_shortcut error: {e}]")
        # ---- VIDEO HANDLING METHODS (moved inside class) ----
        
        # ------------------------------------------------------------- chat mode
    def toggle_chat_mode_on(self):
        """Floating widget band, chat window kholo."""
        self.chat_mode = True
        self.gui.hide()
        self.chat_gui.show()
        self.speak("Chat Mode chalu ho gaya. Yahan type karke, voice se, ya file drop karke baat kar sakte ho.", "happy")

    def toggle_chat_mode_off(self):
        """Chat window band, floating widget wapas."""
        self.chat_mode = False
        self.chat_gui.hide()
        self.gui.show()
        self.speak("Floating Mode mein wapas aa gayi. Ab robot widget pe kaam karungi.", "calm")

    def handle_chat_message(self, text: str):
        """Chat se typed message aaya — same voice command ki tarah process karo."""
        if not text:
            return
        self.chat_gui.set_typing(True)
        try:
            should_continue = self.handle_text(text)
            if not should_continue:
                pass  # command ne khatam kiya, ignore
        except Exception as e:
            print(f"[chat message error: {e}]")
            self.speak("Kuch error aa gayi chat mein.", "concerned")
        finally:
            self.chat_gui.set_typing(False)

    def handle_chat_voice(self):
        """Chat mode mein voice button dabaya."""
        if not self.chat_mode:
            return
        self.chat_gui.set_typing(True)
        self.chat_gui.add_jarvis_message("Sun rahi hoon...", "calm")

        def _listen_thread():
            text = self.voice.listen(timeout=7, phrase_time_limit=10)
            if text:
                self.chat_gui.add_user_message(text)
                self.handle_chat_message(text)
            else:
                self.chat_gui.add_jarvis_message("Kuch sunayi nahi diya, dobara boliye.", "concerned")
                self.chat_gui.set_typing(False)

        threading.Thread(target=_listen_thread, daemon=True).start()
        
    def _handle_video_commands(self, text: str) -> bool:
        """Video drop hone ke baad user ka command handle karta hai."""
        t = text.lower()
        if any(w in t for w in ("notes", "note", "banao", "bana do")):
            self.video_mode = False
            self._make_video_notes(self.video_path)
            self.video_path = None
        elif any(w in t for w in ("transcribe", "transcription", "likh do", "text")):
            self.video_mode = False
            self._transcribe_video(self.video_path)
            self.video_path = None
        elif any(w in t for w in ("summary", "samajh", "batao", "short")):
            self.video_mode = False
            self._summarize_video(self.video_path)
            self.video_path = None
        elif any(w in t for w in ("cancel", "band", "nahi", "exit", "chhodo")):
            self.video_mode = False
            self.video_path = None
            self.speak("Video mode band kar diya.")
        else:
            self.speak("Kya karna hai? 'notes banao', 'summary do', ya 'transcribe karo'?")
        return True

    def _make_video_notes(self, video_path: str):
        """Full flow: video → audio → transcript → notes → PDF."""
        from video_notes import VideoNotes
        import datetime

        vn = VideoNotes(video_path, self.ai, self.voice)
        self.gui.set_state("thinking")

        self.speak("Video se audio nikaal rahi hoon...")
        if not vn.extract_audio():
            self.speak("Audio extract karne mein dikkat aa gayi. Shayad video corrupt hai ya ffmpeg missing hai.")
            return

        if not vn.transcribe():
            self.speak("Transcribe karne mein dikkat aa gayi.")
            vn.cleanup()
            return

        self.gui.show_message("Smart notes bana rahi hoon...")
        if not vn.generate_notes():
            self.speak("Notes generate karne mein dikkat aa gayi.")
            vn.cleanup()
            return

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pdf_name = f"Jarvis_Notes_{timestamp}.pdf"
        pdf_path = os.path.join(desktop, pdf_name)

        self.speak("PDF bana rahi hoon...")
        if vn.create_pdf(pdf_path):
            self.speak(f"Notes ban gayi hain! Desktop pe save ho gayi: {pdf_name}")
            try:
                os.startfile(pdf_path)
            except Exception:
                pass
        else:
            txt_path = pdf_path.replace(".pdf", ".txt")
            try:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(vn.notes)
                self.speak("PDF banane mein dikkat aa gayi, lekin notes text file mein save ho gayi.")
                os.startfile(txt_path)
            except Exception:
                self.speak("Notes save karne mein dikkat aa gayi.")

        vn.cleanup()

    def _transcribe_video(self, video_path: str):
        """Sirf transcript generate karo aur bol do."""
        from video_notes import VideoNotes
        vn = VideoNotes(video_path, self.ai, self.voice)
        if not vn.extract_audio() or not vn.transcribe():
            self.speak("Transcribe nahi ho paya.")
            vn.cleanup()
            return
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        import datetime
        t = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = os.path.join(desktop, f"Jarvis_Transcript_{t}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(vn.transcript)
        self.speak(f"Transcript ban gayi. Desktop pe save ho gayi. {len(vn.transcript)} characters.")
        os.startfile(path)
        vn.cleanup()

    def _summarize_video(self, video_path: str):
        """Video ka short summary banao."""
        from video_notes import VideoNotes
        vn = VideoNotes(video_path, self.ai, self.voice)
        if not vn.extract_audio() or not vn.transcribe():
            self.speak("Summary nahi bana payi.")
            vn.cleanup()
            return
        prompt = f"Video ka transcript:\n{vn.transcript[:8000]}\n\nIska ek chhota aur precise summary do — 5-6 sentences mein. Hinglish mein."
        summary, emotion = self.ai.ask(prompt, skip_history_append=True)
        self.speak(summary, interruptible=True, emotion=emotion)
        vn.cleanup()


if __name__ == "__main__":
    gui = JarvisGUI()
    jarvis = Jarvis(gui)

    # Jarvis ki poori logic (mic sunna, wake, commands) background thread me
    # chalti hai. pywebview GUI hamesha MAIN thread pe chalni chahiye, isliye
    # yaha split kiya gaya hai.
    worker = threading.Thread(target=jarvis.run_forever, daemon=True)
    worker.start()

    gui.run_mainloop()  # yehi window band hone tak block karega (main thread)
    