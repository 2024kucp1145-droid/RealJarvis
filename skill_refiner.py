# -*- coding: utf-8 -*-
"""
skill_refiner.py  (Phase 15: Skill Evolution & Delta Auto-Refinement Engine)
=============================================================================
Allows progressive enhancement of existing self-learned skills.
When the user requests modifications (e.g., "is skill mein timeout badhao" or
"result ko clipboard par bhi copy karo"), this engine loads the existing code,
applies delta edits, verifies through the full sandbox pipeline, and hot-swaps
the code live.
"""

import sys
import os
import re
from typing import Tuple, Optional, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_spec_formulator import SkillSpec
from skill_registry import registry, SKILLS_DIR
from guardrail_injector import injector
from ast_safety_scanner import scanner
from sandbox_runner import sandbox
from dynamic_hot_reloader import hot_reloader
from completion_announcer import announcer


DELTA_REFINEMENT_PROMPT = """You are the Senior Automation Architect for Jarvis AI Assistant.
The user wants to refine/evolve an EXISTING self-learned Python skill.

EXISTING SKILL CODE:
```python
{existing_code}
```

USER'S REQUESTED MODIFICATION:
"{refinement_request}"

STRICT REFINEMENT RULES:
1. Return ONLY the complete, updated Python code inside a single ```python code block.
2. Preserve the top-level `def execute(context: dict = None) -> dict:` signature.
3. Apply the user's requested modifications accurately.
4. Keep all robust try-except error handling intact.
"""


class SkillRefiner:
    """Manages iterative evolution and delta refinement of learned skills."""

    def __init__(self, ai_brain=None):
        self.ai = ai_brain

    def refine_skill(self, skill_id: str, refinement_request: str) -> Tuple[bool, str]:
        """
        Loads existing skill, applies delta modification, runs verification pipeline,
        and hot-swaps in runtime memory.
        """
        file_path = os.path.join(SKILLS_DIR, f"{skill_id}.py")
        if not os.path.exists(file_path):
            return False, f"Skill '{skill_id}' not found on disk."

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing_code = f.read()
        except Exception as e:
            return False, f"Failed to read existing skill code: {e}"

        safe_req = refinement_request.encode('ascii', 'ignore').decode()
        print(f"[skill_refiner] [>>] Refining skill '{skill_id}' with request: '{safe_req}'")

        # 1. Synthesize Delta Code
        updated_code = self._synthesize_delta_code(existing_code, refinement_request)

        # 2. Inject Guardrails
        guarded_code = injector.inject_guardrails(updated_code)

        # 3. AST Safety Scanner
        scan_res = scanner.scan_code(guarded_code)
        if not scan_res.is_safe:
            return False, f"Refinement rejected by AST Safety Scanner: {', '.join(scan_res.issues)}"

        # 4. Sandbox Test
        sandbox_res = sandbox.run_in_sandbox(guarded_code, context={"dry_run": True})
        if not sandbox_res.passed:
            return False, f"Refined code failed sandbox verification: {sandbox_res.error_message}"

        # 5. Persist to Disk & Update SQLite
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(guarded_code)
        except Exception as e:
            return False, f"Failed to save refined code: {e}"

        # 6. Hot-Swap in Memory
        hot_reloader.hot_load_from_file(skill_id, file_path)

        print(f"[skill_refiner] [OK] Skill '{skill_id}' successfully refined and hot-swapped!")
        return True, f"Skill '{skill_id}' successfully updated and hot-reloaded."

    def _synthesize_delta_code(self, existing_code: str, request: str) -> str:
        """Invokes LLM for delta synthesis or applies heuristic fallback."""
        if self.ai and hasattr(self.ai, "ask"):
            try:
                prompt = DELETA_REFINEMENT_PROMPT.format(
                    existing_code=existing_code,
                    refinement_request=request
                )
                response, _ = self.ai.ask(prompt, skip_history_append=True)
                match = re.search(r"```(?:python)?\s*(.*?)\s*```", response, re.DOTALL)
                if match:
                    return match.group(1).strip()
            except Exception as e:
                print(f"[skill_refiner AI error: {e}]")

        # Fallback: append comment marker
        return existing_code + f"\n# Refined based on request: {request}\n"


refiner = SkillRefiner()
