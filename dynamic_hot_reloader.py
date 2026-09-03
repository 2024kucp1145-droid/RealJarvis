# -*- coding: utf-8 -*-
"""
dynamic_hot_reloader.py  (Phase 11: Zero-Restart Dynamic Hot-Reloader)
========================================================================
Dynamically imports, instantiates, and registers verified custom skills directly
into running memory without requiring Jarvis to restart.
Also auto-loads existing skills on startup.
"""

import sys
import os
import re
import importlib.util
import types
from typing import Dict, List, Optional, Any, Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_spec_formulator import SkillSpec
from skill_registry import registry, SKILLS_DIR


class DynamicHotReloader:
    """Hot-loads modules into Python runtime and handles live command dispatch."""

    def __init__(self):
        self._loaded_modules: Dict[str, types.ModuleType] = {}   # {skill_id: module}
        self._trigger_to_skill: Dict[str, str] = {}              # {trigger: skill_id}
        self._skill_specs: Dict[str, SkillSpec] = {}             # {skill_id: SkillSpec}
        self.load_all_persisted_skills()

    def load_all_persisted_skills(self):
        """Loads all existing skills from SQLite / custom_skills on startup."""
        skills_meta = registry.get_all_skills()
        for s in skills_meta:
            skill_id = s["skill_id"]
            file_path = s["file_path"]
            triggers = s.get("triggers", [])
            if os.path.exists(file_path):
                self.hot_load_from_file(skill_id, file_path, triggers=triggers)
        print(f"[hot_reloader] Active live skills in memory: {len(self._loaded_modules)}")

    def hot_load_from_file(self, skill_id: str, file_path: str, triggers: List[str] = None) -> bool:
        """
        Dynamically loads a .py file into sys.modules and registers its execute entrypoint.
        """
        try:
            mod_name = f"custom_skills.{skill_id}"
            spec = importlib.util.spec_from_file_location(mod_name, file_path)
            if not spec or not spec.loader:
                print(f"[hot_reloader] Failed to create module spec for: {file_path}")
                return False

            module = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = module
            spec.loader.exec_module(module)

            if not hasattr(module, "execute") or not callable(module.execute):
                print(f"[hot_reloader] Error: Module '{skill_id}' does not have a callable 'execute' function.")
                return False

            self._loaded_modules[skill_id] = module

            # Register Triggers
            if triggers:
                for trig in triggers:
                    clean_trig = trig.strip().lower()
                    self._trigger_to_skill[clean_trig] = skill_id

            print(f"[hot_reloader] Successfully hot-loaded skill '{skill_id}' with {len(triggers or [])} triggers.")
            return True
        except Exception as e:
            print(f"[hot_reloader error loading '{skill_id}': {e}]")
            return False

    def match_and_execute(self, query_text: str, context: dict = None) -> Optional[dict]:
        """
        Checks if query_text matches any registered custom skill trigger.
        If matched, executes the skill in-memory, updates statistics, and returns outcome.
        """
        clean = query_text.strip().lower().rstrip(".?!,")

        # 1. Exact or Substring Trigger Match
        target_skill_id = None
        matched_trigger = None

        # Check exact trigger match first
        if clean in self._trigger_to_skill:
            target_skill_id = self._trigger_to_skill[clean]
            matched_trigger = clean
        else:
            # Check if any trigger is contained in clean query
            for trig, s_id in self._trigger_to_skill.items():
                if trig in clean or clean in trig:
                    target_skill_id = s_id
                    matched_trigger = trig
                    break

        if not target_skill_id or target_skill_id not in self._loaded_modules:
            return None

        # 2. Execute the hot-loaded skill
        module = self._loaded_modules[target_skill_id]
        safe_q = query_text.encode('ascii', 'ignore').decode()
        print(f"[hot_reloader] [>>] Executing hot-loaded skill '{target_skill_id}' for query: '{safe_q}'")

        exec_ctx = context or {}
        exec_ctx["query_text"] = query_text
        exec_ctx["matched_trigger"] = matched_trigger

        try:
            res = module.execute(exec_ctx)
            success = isinstance(res, dict) and res.get("success", True)
            registry.record_execution(target_skill_id, success=success)
            return res
        except Exception as e:
            print(f"[hot_reloader execution error for '{target_skill_id}': {e}]")
            registry.record_execution(target_skill_id, success=False)
            return {
                "success": False,
                "message": f"Skill '{target_skill_id}' execute karte waqt error aayi: {e}",
                "data": None
            }


hot_reloader = DynamicHotReloader()
