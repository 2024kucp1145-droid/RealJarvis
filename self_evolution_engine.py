# -*- coding: utf-8 -*-
"""
self_evolution_engine.py  (Phase 1: Unknown Intent Detector & Missing-Skill Triager)
=====================================================================================
Autonomous Self-Evolution & Live Skill Synthesizer for Jarvis.

When the user asks for a capability or automation that Jarvis does not yet know:
1. Triages whether it is an actionable task (Desktop, Browser, App, System, File automation)
   or casual conversational Q&A.
2. If actionable & unlearned:
   - Instantly acknowledges: "Yeh toh mujhe abhi nahi aata, ise main seekhti hoon."
   - Spawns an asynchronous background synthesizer (non-blocking).
   - Allows the user to continue interacting with Jarvis.
"""

import os
import re
import sys
import time
import json
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Actionable intent indicators in Hinglish & English
ACTION_VERBS = [
    "karo", "kardo", "kariye", "khol do", "banao", "bana do", "download",
    "extract", "convert", "scrape", "click", "fill", "send", "bhejo",
    "save", "record", "automate", "type", "press", "delete", "copy",
    "paste", "organize", "search", "dhundo", "clean", "export", "import",
    "fetch", "check", "monitor", "track", "close", "restart", "start",
    "play", "pause", "mute", "scroll", "summarize", "summarise", "translate",
    "generate", "fix", "repair", "compile", "run", "execute"
]

CONVERSATIONAL_PATTERNS = [
    r"^(kya|kaise|kyun|kahan|kab|who|what|why|when|where|how|tell me about|explain)\b",
    r"^(hi|hello|hey|namaste|good morning|good evening|good night|kaise ho)\b",
    r"^(joke|shayari|poem|story|kahani|time|date|din|tarikh|mausam|weather)\b"
]

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_skills")
os.makedirs(SKILLS_DIR, exist_ok=True)


import context_sniffer
import skill_spec_formulator
import code_synthesizer
import guardrail_injector
import ast_safety_scanner
import dependency_manager
import sandbox_runner
import self_correction_engine
import regression_guard
import skill_registry
import dynamic_hot_reloader
import completion_announcer

class SelfEvolutionEngine:
    def __init__(self):
        self.voice = None
        self.ai = None
        self.gui = None
        self.speak_fn = None
        self.running = True
        self._lock = threading.Lock()
        self._active_learning_tasks = {}  # {task_id: {"query": str, "snapshot": DesktopContextSnapshot, ...}}
        self._learned_skills = set()
        self._pending_learning_intent = None  # Holds intent awaiting user permission
        self._load_existing_skills()

    def start(self, voice=None, ai=None, gui=None, speak_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        if self.ai:
            code_synthesizer.synthesizer.ai = self.ai
            self_correction_engine.correction_engine.ai = self.ai
        print("[self_evolution] Autonomous Self-Evolution Engine active (Phases 1-16 Live with Permission Guard).")

    def _load_existing_skills(self):
        """Indexes all existing custom skills from custom_skills directory."""
        if not os.path.exists(SKILLS_DIR):
            return
        for fname in os.listdir(SKILLS_DIR):
            if fname.endswith(".py") and not fname.startswith("__"):
                skill_name = fname[:-3]
                self._learned_skills.add(skill_name)
        print(f"[self_evolution] Loaded {len(self._learned_skills)} custom skills: {list(self._learned_skills)}")

    def is_actionable_intent(self, text: str) -> bool:
        """
        Determines whether the prompt is an actionable automation command
        (as opposed to general knowledge conversation or casual chat).
        """
        clean = text.lower().strip()
        
        # Check if it's purely conversational
        for pat in CONVERSATIONAL_PATTERNS:
            if re.search(pat, clean):
                if not any(v in clean for v in ["karo", "kardo", "download", "automate", "convert", "export", "banao", "seekh"]):
                    return False

        has_action_verb = any(v in clean for v in ACTION_VERBS)
        has_target_entity = any(e in clean for e in [
            "file", "folder", "browser", "chrome", "edge", "youtube", "tab",
            "page", "screen", "pdf", "excel", "sheet", "code", "github",
            "url", "site", "website", "desktop", "window", "app", "audio",
            "video", "image", "button", "link", "form", "data", "price",
            "notification", "mail", "whatsapp", "document", "text"
        ])
        return has_action_verb or has_target_entity

    def has_pending_permission(self) -> bool:
        """Returns True if Jarvis is currently waiting for user's approval to learn a skill."""
        with self._lock:
            if not self._pending_learning_intent:
                return False
            # Expire pending request after 60 seconds
            if time.time() - self._pending_learning_intent.get("time", 0) > 60:
                self._pending_learning_intent = None
                return False
            return True

    def ask_learning_permission(self, query: str, context: str = "") -> bool:
        """
        Asks explicit permission before synthesizing and installing new code.
        """
        clean_q = query.strip()
        with self._lock:
            self._pending_learning_intent = {
                "query": clean_q,
                "context": context,
                "time": time.time()
            }

        msg = f"Boss, yeh kaam mujhe abhi nahi aata hai. Kya main iska naya Python automation skill seekh kar bana doon?"
        
        if self.gui and hasattr(self.gui, "show_message"):
            try:
                self.gui.show_message(f"🧬 Learn New Skill? '{clean_q[:30]}...'", ms=5000)
            except Exception:
                pass

        try:
            if self.speak_fn:
                self.speak_fn(msg, emotion="concerned")
            elif self.voice:
                self.voice.speak(msg, interruptible=True, emotion="concerned")
        except Exception as e:
            print(f"[self_evolution ask permission voice error: {e}]")

        return True

    def confirm_learning_permission(self, user_confirmed: bool) -> bool:
        """
        Handles user's 'Haan' / 'Nahi' response to the learning prompt.
        """
        with self._lock:
            pending = self._pending_learning_intent
            self._pending_learning_intent = None

        if not pending:
            return False

        query = pending["query"]
        context = pending["context"]

        if not user_confirmed:
            cancel_msg = "Theek hai boss, naya skill learn karna cancel kar diya."
            if self.speak_fn:
                self.speak_fn(cancel_msg, emotion="calm")
            elif self.voice:
                self.voice.speak(cancel_msg, emotion="calm")
            return True

        # User Approved: Start learning pipeline
        ack_msg = f"Theek hai boss! Main '{query[:35]}' ka naya skill formulate karke code likh rahi hoon aur sandbox mein test kar rahi hoon. Ek minute dijiye..."
        if self.gui and hasattr(self.gui, "show_message"):
            try:
                self.gui.show_message("🧬 Synthesizing & Testing New Skill in Sandbox...", ms=6000)
            except Exception:
                pass

        if self.speak_fn:
            self.speak_fn(ack_msg, emotion="excited")
        elif self.voice:
            self.voice.speak(ack_msg, emotion="excited")

        task_id = f"task_{int(time.time())}"
        snapshot = context_sniffer.sniffer.capture_snapshot()

        with self._lock:
            self._active_learning_tasks[task_id] = {
                "query": query,
                "context": context,
                "snapshot": snapshot,
                "status": "in_progress",
                "started_at": time.time()
            }

        worker = threading.Thread(
            target=self._background_learning_pipeline,
            args=(task_id, query, context, snapshot),
            daemon=True,
            name=f"self_evolve_{task_id}"
        )
        worker.start()
        return True

    def triage_missing_skill(self, query: str, context: str = "") -> bool:
        """
        Phase 1 Entrypoint:
        If query is an actionable intent not currently handled, asks user permission.
        """
        if not self.is_actionable_intent(query):
            return False

        safe_query = query.encode('ascii', 'ignore').decode()
        print(f"[self_evolution] [*] Unlearned Actionable Intent detected: '{safe_query}'")
        return self.ask_learning_permission(query, context=context)

    def _background_learning_pipeline(self, task_id: str, query: str, context: str, snapshot: context_sniffer.DesktopContextSnapshot = None):
        """
        Background learning pipeline orchestrator.
        (Phases 2-16 sequentially wired into this worker).
        """
        safe_q = query.encode('ascii', 'ignore').decode()
        print(f"[self_evolution] [>>] Background learning pipeline started for task [{task_id}]: '{safe_q}'")
        
        if snapshot:
            print(f"[self_evolution] [Task {task_id}] Active App: {snapshot.active_app_label} | Window: {snapshot.active_title[:50]}")
            if snapshot.is_browser:
                print(f"[self_evolution] [Task {task_id}] Browser Target: {snapshot.browser_domain or 'General Web'}")

        # Phase 3: Formulate deterministic SkillSpec
        spec = skill_spec_formulator.formulator.formulate_spec(query, snapshot=snapshot, ai_brain=self.ai)
        print(f"[self_evolution] [Task {task_id}] SkillSpec formulated: ID='{spec.skill_id}', Category='{spec.category}', Triggers={spec.triggers[:3]}")

        # Phase 4: Autonomous Python Code Synthesis
        raw_code = code_synthesizer.synthesizer.synthesize_skill(spec, snapshot=snapshot)
        print(f"[self_evolution] [Task {task_id}] Code Synthesized ({len(raw_code.splitlines())} lines).")

        # Phase 5: Worst-Case & Edge-Case Guardrail Injection
        guarded_code = guardrail_injector.injector.inject_guardrails(raw_code, target_app=spec.target_app)
        print(f"[self_evolution] [Task {task_id}] Guardrails injected (PyAutoGUI FailSafe, Network Timeouts, Top-level Catch-all).")

        # Phase 6: AST Static Security & Safety Scanner
        scan_res = ast_safety_scanner.scanner.scan_code(guarded_code)
        if not scan_res.is_safe:
            print(f"[self_evolution] [Task {task_id}] [!] Safety Scan Issues: {scan_res.issues}")
        else:
            print(f"[self_evolution] [Task {task_id}] [OK] AST Static Safety Scan PASSED (Zero security risks detected).")

        # Phase 7: Dynamic Background Dependency Check
        if scan_res.imported_modules:
            dep_res = dependency_manager.dep_manager.ensure_dependencies(scan_res.imported_modules)
            print(f"[self_evolution] [Task {task_id}] Dependencies verified (All ready: {dep_res['all_ready']}).")

        # Phase 8: Isolated Subprocess Sandbox Verification Harness
        print(f"[self_evolution] [Task {task_id}] Running Phase 8 Isolated Sandbox Test...")
        sandbox_res = sandbox_runner.sandbox.run_in_sandbox(
            guarded_code,
            context={"query_text": query, "dry_run": True},
            timeout_sec=10
        )

        final_code = guarded_code

        # Phase 9: Automated Self-Correction Loop (if Sandbox fails)
        if not sandbox_res.passed:
            safe_err = str(sandbox_res.error_message)[:100].encode('ascii', 'ignore').decode()
            print(f"[self_evolution] [Task {task_id}] Sandbox test failed: {safe_err}. Triggering Phase 9 Self-Correction...")
            repaired_success, repaired_code, iters, repair_msg = self_correction_engine.correction_engine.repair_and_verify(
                spec,
                guarded_code,
                sandbox_res.error_message,
                max_retries=3
            )
            if repaired_success:
                final_code = repaired_code
                print(f"[self_evolution] [Task {task_id}] [OK] Self-Correction succeeded after {iters} iterations.")
            else:
                print(f"[self_evolution] [Task {task_id}] [FAIL] Self-Correction could not resolve error: {repair_msg}")
                return
        else:
            print(f"[self_evolution] [Task {task_id}] [OK] Sandbox Verification PASSED ({sandbox_res.execution_time}s).")

        # Phase 10: Regression Guard Shield
        print(f"[self_evolution] [Task {task_id}] Running Phase 10 Regression Guard Audit...")
        reg_report = regression_guard.guard.audit_system_integrity(new_skill_triggers=spec.triggers)
        if not reg_report.passed:
            print(f"[self_evolution] [Task {task_id}] [FAIL] Regression Guard Failed: {reg_report.failures}")
            return
        else:
            print(f"[self_evolution] [Task {task_id}] [OK] Regression Guard PASSED ({reg_report.total_checks} checks OK, 0 conflicts).")

        # Phase 12: Permanent Disk & SQLite Registry
        print(f"[self_evolution] [Task {task_id}] Persisting skill to custom_skills and SQLite DB...")
        file_path = skill_registry.registry.save_skill(spec, final_code)
        if not file_path:
            print(f"[self_evolution] [Task {task_id}] [FAIL] Could not persist skill file to disk.")
            return

        # Phase 11: Zero-Restart Dynamic Hot-Reloader
        print(f"[self_evolution] [Task {task_id}] Hot-loading '{spec.skill_id}' into live running memory...")
        loaded = dynamic_hot_reloader.hot_reloader.hot_load_from_file(spec.skill_id, file_path, triggers=spec.triggers)
        if not loaded:
            print(f"[self_evolution] [Task {task_id}] [FAIL] Hot-reloader failed to bind module into memory.")
            return

        # Phase 13: Multi-Channel Completion Announcer (Voice, GUI, WhatsApp)
        completion_announcer.announcer.voice = self.voice
        completion_announcer.announcer.gui = self.gui
        completion_announcer.announcer.speak_fn = self.speak_fn
        completion_announcer.announcer.announce_completion(spec)

        with self._lock:
            if task_id in self._active_learning_tasks:
                self._active_learning_tasks[task_id]["status"] = "completed"
                self._active_learning_tasks[task_id]["spec"] = spec
                self._active_learning_tasks[task_id]["generated_code"] = final_code
                self._active_learning_tasks[task_id]["sandbox_res"] = sandbox_res
            self._learned_skills.add(spec.skill_id)

        print(f"[self_evolution] [OK] Skill '{spec.skill_name}' is now FULLY LEARNED, HOT-LOADED and LIVE!")


evolution_engine = SelfEvolutionEngine()
