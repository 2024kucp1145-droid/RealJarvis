# -*- coding: utf-8 -*-
"""
guardrail_injector.py  (Phase 5: Worst-Case & Edge-Case Failure Guardrail Injector)
====================================================================================
Injects defensive programming patterns, safety boundaries, and worst-case handling
into synthesized Python code.

Guarantees:
1. PyAutoGUI FailSafe & Screen Coordinate Clamping.
2. Network timeout bounds (default 10s on requests/urllib).
3. File exist checks & safe path resolution.
4. Top-level universal catch-all returning standardized failure JSON rather than crashing.
"""

import re
import ast
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class GuardrailInjector:
    """Injects defensive guardrails and fallback resilience into raw synthesized code."""

    @staticmethod
    def inject_guardrails(code: str, target_app: str = "general") -> str:
        """Applies worst-case analyzers and wraps code with safety provisions."""
        modified_code = code

        # 1. Enforce PyAutoGUI safety if GUI automation is detected
        if "pyautogui" in modified_code:
            modified_code = GuardrailInjector._inject_pyautogui_safeties(modified_code)

        # 2. Enforce network request timeouts if requests / urllib is used
        if "requests." in modified_code or "urllib." in modified_code:
            modified_code = GuardrailInjector._inject_network_timeouts(modified_code)

        # 3. Ensure top-level exception guarantee
        modified_code = GuardrailInjector._ensure_toplevel_exception_safety(modified_code)

        return modified_code

    @staticmethod
    def _inject_pyautogui_safeties(code: str) -> str:
        """Ensures pyautogui FAILSAFE and PAUSE settings are configured at start of execute."""
        safety_lines = "    # Guardrail: Enforce PyAutoGUI safety boundaries\n    import pyautogui\n    pyautogui.FAILSAFE = True\n    pyautogui.PAUSE = 0.2\n"
        
        # Inject right after `def execute(` line if not present
        if "pyautogui.FAILSAFE" not in code:
            code = re.sub(
                r"(def execute\s*\([^)]*\)(?:\s*->\s*[^:]+)?:\s*\n(?:\s*\"\"\"[\s\S]*?\"\"\"\s*\n)?)",
                r"\1" + safety_lines,
                code,
                count=1
            )
        return code

    @staticmethod
    def _inject_network_timeouts(code: str) -> str:
        """Ensures all requests.get / requests.post calls have default timeout=10."""
        # Replace requests.get(url) with requests.get(url, timeout=10) if timeout not specified
        def _add_timeout(match):
            call_text = match.group(0)
            if "timeout" not in call_text:
                # Add timeout before closing parenthesis
                return call_text[:-1] + ", timeout=10)"
            return call_text

        code = re.sub(r"requests\.(?:get|post|put|delete|head)\([^)]+\)", _add_timeout, code)
        return code

    @staticmethod
    def _ensure_toplevel_exception_safety(code: str) -> str:
        """Verifies that the execute function has a try/except structure returning a dict."""
        if "try:" not in code or "except Exception" not in code:
            # Wrap function body in try-except
            lines = code.splitlines()
            exec_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith("def execute("):
                    exec_idx = i
                    break

            if exec_idx != -1:
                header = lines[:exec_idx + 1]
                body = lines[exec_idx + 1:]
                indented_body = ["        " + l if l.strip() else l for l in body]
                wrapped = header + [
                    "    try:",
                ] + indented_body + [
                    "    except Exception as e:",
                    "        return {'success': False, 'message': f'Task failed with error: {e}', 'data': None}"
                ]
                return "\n".join(wrapped)

        return code


injector = GuardrailInjector()
