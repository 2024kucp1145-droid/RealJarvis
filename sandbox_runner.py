# -*- coding: utf-8 -*-
"""
sandbox_runner.py  (Phase 8: Isolated Subprocess Sandbox Verification Harness)
================================================================================
Executes synthesized Python skills inside an isolated subprocess with strict
execution timeouts, memory encapsulation, and output contract validation.

Guarantees:
1. Complete process isolation (if skill crashes/hangs, main Jarvis process is 100% unaffected).
2. Strict timeout enforcement (default 10s).
3. Captures stdout, stderr, exit codes, and structured JSON output.
"""

import sys
import os
import json
import tempfile
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@dataclass
class SandboxResult:
    passed: bool = False
    exit_code: int = -1
    output_data: Optional[Dict[str, Any]] = None
    stdout: str = ""
    stderr: str = ""
    execution_time: float = 0.0
    error_message: str = ""


SANDBOX_HARNESS_WRAPPER = '''# -*- coding: utf-8 -*-
import sys
import json
import base64
import traceback

{skill_code}

if __name__ == "__main__":
    context = json.loads(base64.b64decode("{context_b64}").decode("utf-8"))
    try:
        if "execute" not in globals():
            raise AttributeError("Entrypoint 'def execute(context=None)' not found in module.")
        res = execute(context)
        if not isinstance(res, dict):
            raise TypeError(f"execute() must return a dict, got {{type(res).__name__}}")
        if "success" not in res or "message" not in res:
            raise KeyError("execute() return dict must contain 'success' (bool) and 'message' (str) keys.")
        print("__SANDBOX_START__")
        print(json.dumps(res, ensure_ascii=False))
        print("__SANDBOX_END__")
        sys.exit(0)
    except Exception as e:
        err_payload = {{"success": False, "message": f"Sandbox runtime error: {{e}}", "traceback": traceback.format_exc()}}
        print("__SANDBOX_START__")
        print(json.dumps(err_payload, ensure_ascii=False))
        print("__SANDBOX_END__")
        sys.exit(1)
'''


class SandboxRunner:
    """Executes and validates skills in an isolated subshell."""

    @staticmethod
    def run_in_sandbox(code_str: str, context: Dict[str, Any] = None, timeout_sec: int = 10) -> SandboxResult:
        import base64
        result = SandboxResult()
        ctx = context or {"dry_run": True, "query_text": "Sandbox verification run"}
        ctx_b64 = base64.b64encode(json.dumps(ctx).encode('utf-8')).decode('ascii')

        # Wrap code into standalone executable script
        harness_code = SANDBOX_HARNESS_WRAPPER.format(
            skill_code=code_str,
            context_b64=ctx_b64
        )

        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as f:
                f.write(harness_code)
                tmp_file = f.name

            import time
            start_t = time.time()
            # Execute in isolated subprocess using virtualenv python
            cmd = [sys.executable, tmp_file]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                encoding="utf-8",
                errors="replace"
            )
            end_t = time.time()

            result.exit_code = proc.returncode
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.execution_time = round(end_t - start_t, 3)

            # Parse sandbox output
            if "__SANDBOX_START__" in proc.stdout and "__SANDBOX_END__" in proc.stdout:
                payload_str = proc.stdout.split("__SANDBOX_START__")[1].split("__SANDBOX_END__")[0].strip()
                try:
                    payload = json.loads(payload_str)
                    result.output_data = payload
                    if proc.returncode == 0 and payload.get("success") is True:
                        result.passed = True
                    else:
                        result.passed = False
                        result.error_message = payload.get("message", "Task returned success=False in sandbox.")
                except json.JSONDecodeError:
                    result.passed = False
                    result.error_message = f"Failed to parse JSON payload from sandbox: {payload_str[:200]}"
            else:
                result.passed = False
                result.error_message = proc.stderr or proc.stdout or "No valid sandbox markers detected in output."

        except subprocess.TimeoutExpired:
            result.passed = False
            result.exit_code = -99
            result.error_message = f"Sandbox execution timed out (> {timeout_sec}s). Possible infinite loop or blocking I/O."
        except Exception as e:
            result.passed = False
            result.error_message = f"Sandbox invocation exception: {e}"
        finally:
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.unlink(tmp_file)
                except Exception:
                    pass

        return result


runner = SandboxRunner()


sandbox = SandboxRunner()
