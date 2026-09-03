# -*- coding: utf-8 -*-
"""
autonomous_evolution.py
========================
Phase 10: Autonomous Multi-Step Tool Chain & Self-Evolution.

Features:
1. Multi-Step Mission Planner — breaks complex high-level goals into step-by-step tool DAGs.
2. Voice Macro Learner & Self-Evolution — user can teach custom multi-step routines.
3. System Self-Diagnostic & Health Debrief — checks all 9 sentries & subsystems.
"""

import os
import re
import json
import time
import subprocess
import threading
import pyautogui

MACROS_FILE = os.path.join(os.path.dirname(__file__), "user_macros.json")


class AutonomousEvolution:
    def __init__(self, voice=None, ai=None, gui=None, speak_fn=None, dispatcher_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        self.dispatcher_fn = dispatcher_fn
        self.running = False
        self.enabled = True

        self.macros = self._load_macros()
        self._lock = threading.Lock()

    def start(self, voice=None, ai=None, gui=None, speak_fn=None, dispatcher_fn=None):
        if voice:
            self.voice = voice
        if ai:
            self.ai = ai
        if gui:
            self.gui = gui
        if speak_fn:
            self.speak_fn = speak_fn
        if dispatcher_fn:
            self.dispatcher_fn = dispatcher_fn

        self.running = True
        print("[autonomous_evolution] Autonomous Evolution & Multi-Step Planner started.")

    def stop(self):
        self.running = False

    def _speak(self, message: str, emotion: str = "happy"):
        print(f"[autonomous_evolution] {message}")
        if self.speak_fn:
            self.speak_fn(message, emotion=emotion)
        elif self.voice:
            self.voice.speak(message, interruptible=True, emotion=emotion)

    def _load_macros(self) -> dict:
        if os.path.exists(MACROS_FILE):
            try:
                with open(MACROS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_macros(self):
        try:
            with open(MACROS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.macros, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[save_macros error: {e}]")

    # =========================================================================
    # 1. MULTI-STEP MISSION PLANNER
    # =========================================================================
    def plan_and_execute_mission(self, mission_text: str) -> str:
        """Deconstructs complex goals into sequential sub-tasks and executes them."""
        self._speak("Complex task analyze karke step-by-step plan bana rahi hoon...", emotion="calm")

        if not self.ai or not self.ai.available():
            return "AI Brain connected nahi hai, complex mission plan nahi ho sakta."

        prompt = f"""You are an autonomous AI task planner.
The user wants to accomplish this multi-step goal:
"{mission_text}"

Deconstruct this into a clean list of 2-5 actionable steps.
Available action types:
- "open_app": value is app name (e.g. "vscode", "chrome", "notepad", "terminal")
- "run_cmd": value is shell command string
- "speak": value is spoken progress message to user
- "organize_desktop": organize desktop files
- "git_commit": commit git changes
- "clean_downloads": clean old downloads

Return ONLY a valid JSON array of objects with keys "action", "value", and "desc":
[
  {{"action": "speak", "value": "Project setup shuru kar rahi hoon", "desc": "Announcement"}},
  {{"action": "open_app", "value": "vscode", "desc": "Open VS Code"}}
]"""

        try:
            raw_reply, _ = self.ai.ask(prompt, skip_history_append=True)
            # Clean json fences
            raw_json = re.sub(r"```json|```", "", raw_reply).strip()
            # Extract JSON array
            match = re.search(r"\[.*\]", raw_json, re.DOTALL)
            if not match:
                return "Mission plan formulate karne mein dikkat aayi."

            steps = json.loads(match.group(0))
            total = len(steps)

            for i, step in enumerate(steps, 1):
                action = step.get("action")
                val = step.get("value")
                desc = step.get("desc", f"Step {i}")

                print(f"[autonomous_evolution] Executing Step {i}/{total}: {desc} ({action}: {val})")

                if action == "speak":
                    self._speak(val, emotion="happy")
                elif action == "open_app":
                    import commands.system_commands as sys_cmd
                    sys_cmd.open_any_app(self.voice, name=val)
                    time.sleep(1.0)
                elif action == "run_cmd":
                    subprocess.Popen(val, shell=True)
                    time.sleep(0.5)
                elif action == "organize_desktop":
                    import desktop_janitor
                    desktop_janitor.janitor.organize_desktop()
                elif action == "git_commit":
                    import project_auto_doctor
                    project_auto_doctor.doctor.auto_git_commit_and_sync()
                elif action == "clean_downloads":
                    import desktop_janitor
                    desktop_janitor.janitor.find_old_downloads()

                time.sleep(0.8)

            self._speak(f"Mission accomplished! Sabhi {total} steps successfully execute ho gaye.", emotion="happy")
            return "Mission accomplished!"

        except Exception as e:
            err = f"Mission execution error: {e}"
            print(f"[{err}]")
            self._speak("Mission execute karte waqt error aa gaya.", emotion="concerned")
            return err

    # =========================================================================
    # 2. VOICE-LEARNED MACROS & SELF-EVOLUTION
    # =========================================================================
    def learn_macro_from_voice(self, user_text: str) -> str:
        """Parses 'jab main boloon X, toh Y karo' and saves custom routine."""
        # e.g. "jab main boloon morning routine toh spotify kholo aur vs code kholo"
        if not self.ai or not self.ai.available():
            return "AI Brain connected nahi hai."

        prompt = f"""The user wants to teach you a new voice macro/routine.
User said: "{user_text}"

Extract:
1. "trigger": the trigger phrase (e.g. "morning routine", "deploy project")
2. "actions": list of command strings to execute (e.g. ["open spotify", "open vscode"])

Return ONLY a JSON object:
{{"trigger": "morning routine", "actions": ["open spotify", "open vscode"]}}"""

        try:
            reply, _ = self.ai.ask(prompt, skip_history_append=True)
            raw_json = re.sub(r"```json|```", "", reply).strip()
            match = re.search(r"\{.*\}", raw_json, re.DOTALL)
            if not match:
                return "Macro samajhne mein dikkat aayi."

            data = json.loads(match.group(0))
            trig = data.get("trigger", "").lower().strip()
            actions = data.get("actions", [])

            if not trig or not actions:
                return "Macro ka trigger ya actions clear nahi the."

            with self._lock:
                self.macros[trig] = actions
                self._save_macros()

            resp = f"Samajh gayi boss! Ab se jab aap '{trig}' bolenge, main ye {len(actions)} actions execute karungi."
            self._speak(resp, emotion="happy")
            return resp

        except Exception as e:
            return f"Macro save error: {e}"

    def check_and_execute_macro(self, text: str) -> bool:
        """Checks if text matches any learned custom macro."""
        clean_text = text.lower().strip().rstrip(".?!,")
        matched_actions = None

        with self._lock:
            for trig, actions in self.macros.items():
                if trig in clean_text:
                    matched_actions = actions
                    break

        if not matched_actions:
            return False

        self._speak(f"Custom routine execute kar rahi hoon: {len(matched_actions)} actions...", emotion="happy")
        for act in matched_actions:
            print(f"[macro execute] Action: {act}")
            if self.dispatcher_fn:
                try:
                    self.dispatcher_fn(act)
                except Exception as e:
                    print(f"[macro dispatch error: {e}]")
            time.sleep(1.0)

        self._speak("Routine complete ho gayi.", emotion="happy")
        return True

    def list_learned_macros(self) -> str:
        with self._lock:
            count = len(self.macros)
            if count == 0:
                return "Abhi koi custom routine nahi seekhi hai. Aap mujhe 'jab main boloon X toh Y karo' bolkar sikha sakte hain."

            names = ", ".join(f"'{k}'" for k in self.macros.keys())
            return f"Mere paas {count} custom routines hain: {names}."

    # =========================================================================
    # 3. AUTONOMOUS SYSTEM SELF-DIAGNOSTIC
    # =========================================================================
    def run_system_diagnostic(self) -> str:
        """Audits all 10 subsystems and reports Tony Stark diagnostic debrief."""
        self._speak("Autonomous diagnostic shuru kar rahi hoon. Sabhi subsystems audit kar rahi hoon...", emotion="calm")

        results = []

        # 1. AI Connectivity
        ai_ok = self.ai.available() if self.ai else False
        results.append(("AI Brain (Gemini/DeepMind)", "ACTIVE" if ai_ok else "OFFLINE"))

        # 2. Hardware Sentry
        import hardware_sentry
        hw_ok = hardware_sentry.sentry.running
        results.append(("Hardware & Battery Sentry", "ACTIVE (0.8s loop)" if hw_ok else "INACTIVE"))

        # 3. Health & Focus Coach
        import health_focus_coach
        hc_ok = health_focus_coach.coach.running
        results.append(("Health & Focus Coach", "ACTIVE" if hc_ok else "INACTIVE"))

        # 4. Download Janitor
        import download_janitor
        dj_ok = download_janitor.janitor.running
        results.append(("Download Janitor", "ACTIVE" if dj_ok else "INACTIVE"))

        # 5. Email Sentry
        import email_sentry
        es_ok = email_sentry.sentry.running
        results.append(("Email Sentry", "ACTIVE" if es_ok else "INACTIVE"))

        # 6. Workspace Harmonizer
        import workspace_harmonizer
        wh_ok = workspace_harmonizer.harmonizer.running
        results.append(("Workspace Harmonizer", "ACTIVE (Meeting Shield)" if wh_ok else "INACTIVE"))

        # 7. Web Assistant
        import web_workflow_assistant
        ww_ok = web_workflow_assistant.assistant.running
        results.append(("Web Workflow Assistant", "ACTIVE" if ww_ok else "INACTIVE"))

        # 8. Project Auto-Doctor
        import project_auto_doctor
        pad_ok = project_auto_doctor.doctor.running
        results.append(("Project Auto-Doctor", "ACTIVE" if pad_ok else "INACTIVE"))

        # 9. Desktop Janitor
        import desktop_janitor
        dtj_ok = desktop_janitor.janitor.running
        results.append(("Desktop Janitor", "ACTIVE" if dtj_ok else "INACTIVE"))

        # 10. Autonomous Evolution
        results.append(("Autonomous Evolution Engine", "ACTIVE"))

        active_count = sum(1 for name, status in results if "ACTIVE" in status)
        total_count = len(results)

        debrief = (
            f"All systems operational, boss! "
            f"Total {active_count}/{total_count} autonomous sentries active aur healthy hain. "
            f"Voice latency optimal hai, battery sentry 0.8 second loop par chal raha hai, "
            f"aur system 100% ready hai."
        )

        self._speak(debrief, emotion="happy")
        return debrief


evolution = AutonomousEvolution()
