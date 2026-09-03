# -*- coding: utf-8 -*-
"""
self_correction_engine.py  (Phase 9: Automated Self-Correction Loop / Reflection & Repair)
==========================================================================================
If AST scanning or Sandbox verification fails, this engine analyzes the failing code,
traceback, and error logs, then reflects and synthesizes corrected code.
Supports up to 3 iterative repair cycles.
"""

import sys
import os
import re
from typing import Tuple, Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_spec_formulator import SkillSpec
from sandbox_runner import sandbox, SandboxResult
from guardrail_injector import injector
from ast_safety_scanner import scanner


REPAIR_SYSTEM_PROMPT = """You are the Lead Self-Healing Debugger for Jarvis AI Assistant.
A synthesized Python automation module failed during isolated sandbox testing.

Your task is to fix the code so it executes cleanly and passes all checks.

STRICT REPAIR GUIDELINES:
1. Return ONLY the fixed Python code inside a single ```python code block.
2. The module MUST define: def execute(context: dict = None) -> dict:
3. Fix the exact root cause identified in the Error Traceback.
4. Ensure all necessary standard/popular library imports are present.
5. Wrap logic in try...except so it never raises uncaught exceptions.
"""


class SelfCorrectionEngine:
    """Manages the reflection and iterative repair loop for synthesized skills."""

    def __init__(self, ai_brain=None):
        self.ai = ai_brain

    def repair_and_verify(self, spec: SkillSpec, initial_code: str, initial_error: str, max_retries: int = 3) -> Tuple[bool, str, int, str]:
        """
        Executes up to `max_retries` repair cycles.
        Returns:
            (success: bool, final_code: str, total_iterations: int, status_message: str)
        """
        current_code = initial_code
        last_error = initial_error

        for iteration in range(1, max_retries + 1):
            print(f"[self_correction] [*] Repair iteration {iteration}/{max_retries} for skill '{spec.skill_id}'...")
            
            # 1. Synthesize repaired code
            repaired_code = self._synthesize_repair(spec, current_code, last_error)
            
            # 2. Inject Guardrails
            guarded_code = injector.inject_guardrails(repaired_code, target_app=spec.target_app)
            
            # 3. AST Safety Scan
            scan_res = scanner.scan_code(guarded_code)
            if not scan_res.is_safe:
                last_error = f"AST Safety scan failed: {', '.join(scan_res.issues)}"
                current_code = guarded_code
                continue

            # 4. Sandbox Test
            sandbox_res = sandbox.run_in_sandbox(guarded_code, context={"query_text": spec.description, "dry_run": True})
            if sandbox_res.passed:
                print(f"[self_correction] [OK] Repair SUCCEEDED on iteration {iteration}!")
                return True, guarded_code, iteration, f"Self-correction succeeded on iteration {iteration}."
            else:
                last_error = sandbox_res.error_message or sandbox_res.stderr or "Sandbox verification failed."
                current_code = guarded_code
                safe_err = str(last_error)[:120].encode('ascii', 'ignore').decode()
                print(f"[self_correction] [!] Iteration {iteration} failed: {safe_err}")

        return False, current_code, max_retries, f"Self-correction failed after {max_retries} attempts. Last error: {last_error}"

    def _synthesize_repair(self, spec: SkillSpec, code: str, error: str) -> str:
        """Invokes LLM repair or applies algorithmic heuristic fixes."""
        if self.ai and hasattr(self.ai, "ask"):
            try:
                prompt = (
                    f"SKILL: {spec.skill_name} ({spec.skill_id})\n"
                    f"DESCRIPTION: {spec.description}\n\n"
                    f"FAILING CODE:\n```python\n{code}\n```\n\n"
                    f"ERROR TRACEBACK / FAILURE REASON:\n{error}\n\n"
                    f"Please provide the corrected, complete Python module."
                )
                response, _ = self.ai.ask(f"{REPAIR_SYSTEM_PROMPT}\n\n{prompt}", skip_history_append=True)
                match = re.search(r"```(?:python)?\s*(.*?)\s*```", response, re.DOTALL)
                if match:
                    return match.group(1).strip()
            except Exception as e:
                print(f"[self_correction AI error: {e}] Falling back to heuristic repair.")

        # Algorithmic Heuristic Repair Fallback
        return self._heuristic_repair(code, error)

    def _heuristic_repair(self, code: str, error: str) -> str:
        """Applies rule-based heuristic fixes for common failure modes."""
        fixed = code

        # Fix missing imports
        if ("'re'" in error or "name 're' is not defined" in error) and "import re" not in fixed:
            fixed = "import re\n" + fixed
        if ("'json'" in error or "name 'json' is not defined" in error) and "import json" not in fixed:
            fixed = "import json\n" + fixed
        if ("'time'" in error or "name 'time' is not defined" in error) and "import time" not in fixed:
            fixed = "import time\n" + fixed

        # Fix non-dictionary return format
        if "must return a dict" in error or "execute() must return a dict" in error or "return {" not in fixed:
            # Replace simple returns like `return q` with dict return
            def _replace_return(m):
                val = m.group(1).strip()
                if val.startswith("{") and val.endswith("}"):
                    return m.group(0)
                return f"return {{'success': True, 'message': f'Result: {{{val}}}', 'data': {val}}}"

            fixed = re.sub(r"return\s+([^{\n\r;]+)", _replace_return, fixed)

        return fixed


correction_engine = SelfCorrectionEngine()
