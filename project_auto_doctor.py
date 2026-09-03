# -*- coding: utf-8 -*-
"""
project_auto_doctor.py
=======================
Phase 8: Proactive Git, Terminal & Project Auto-Doctor.

Features:
1. Missing Module Auto-Doctor (ModuleNotFoundError -> 1-word pip/npm install).
2. Port Conflict Cleaner (Port 3000/8000 EADDRINUSE -> free port).
3. AI-Powered Smart Git Auto-Commit & Sync with auto-generated commit message.
4. Git Uncommitted work status check.
"""

import os
import re
import time
import subprocess
import threading

MODULE_ERROR_PATTERN = re.compile(
    r"(?:ModuleNotFoundError:\s*No module named ['\"]([^'\"]+)['\"]|"
    r"ImportError:\s*No module named ['\"]([^'\"]+)['\"]|"
    r"Cannot find module ['\"]([^'\"]+)['\"])",
    re.IGNORECASE
)

PORT_ERROR_PATTERN = re.compile(
    r"(?:address already in use|port (\d+) is already in use|EADDRINUSE.*?(\d+)|bind.*?failed.*?(\d+))",
    re.IGNORECASE
)


class ProjectAutoDoctor:
    def __init__(self, voice=None, ai=None, gui=None, speak_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        self.running = False
        self.enabled = True

        self._pending_install_cmd = None  # { 'pkg': str, 'cmd': str, 'type': 'pip'|'npm' }
        self._pending_blocked_port = None
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

        self.running = True
        print("[project_auto_doctor] Project Auto-Doctor started.")

    def stop(self):
        self.running = False

    def _speak(self, message: str, emotion: str = "happy"):
        if self.speak_fn:
            self.speak_fn(message, emotion=emotion)
        elif self.voice:
            self.voice.speak(message, interruptible=True, emotion=emotion)

    # =========================================================================
    # 1. MISSING PACKAGE AUTO-DOCTOR
    # =========================================================================
    def inspect_terminal_error(self, text: str) -> bool:
        """Inspects terminal text or clipboard for missing module or port conflict."""
        if not text:
            return False

        # 1. Check Missing Module
        mod_match = MODULE_ERROR_PATTERN.search(text)
        if mod_match:
            pkg = mod_match.group(1) or mod_match.group(2) or mod_match.group(3)
            if pkg and not pkg.startswith("."):
                with self._lock:
                    self._pending_install_cmd = {
                        "pkg": pkg,
                        "cmd": f"pip install {pkg}",
                        "type": "pip"
                    }
                self._speak(f"Boss, '{pkg}' library missing hai. Kya main ise install kar doon?", emotion="concerned")
                return True

        # 2. Check Port Conflict
        port_match = PORT_ERROR_PATTERN.search(text)
        if port_match:
            port = port_match.group(1) or port_match.group(2) or port_match.group(3) or "3000"
            with self._lock:
                self._pending_blocked_port = port
            self._speak(f"Port {port} par purana process chal raha hai. Kya main ise free kar doon?", emotion="concerned")
            return True

        return False

    def has_pending_install(self) -> bool:
        with self._lock:
            return bool(self._pending_install_cmd)

    def has_pending_port_kill(self) -> bool:
        with self._lock:
            return bool(self._pending_blocked_port)

    def install_pending_package(self) -> str:
        with self._lock:
            p = self._pending_install_cmd
            self._pending_install_cmd = None

        if not p:
            return "Koi pending library installation nahi hai."

        pkg = p["pkg"]
        self._speak(f"{pkg} install kar rahi hoon, please wait...", emotion="calm")

        try:
            res = subprocess.run(["pip", "install", pkg], capture_output=True, text=True, timeout=60)
            if res.returncode == 0:
                return f"{pkg} successfully install ho gaya hai."
            else:
                return f"{pkg} install karne mein error aaya."
        except Exception as e:
            return f"Installation error: {e}"

    # =========================================================================
    # 2. PORT CONFLICT CLEANER
    # =========================================================================
    def free_port(self, port: str = None) -> str:
        if not port:
            with self._lock:
                port = self._pending_blocked_port or "3000"
                self._pending_blocked_port = None

        port = str(port).strip()
        try:
            # Find PID using netstat
            cmd = f'netstat -ano | findstr :{port}'
            out = subprocess.check_output(cmd, shell=True, text=True, errors="ignore")
            pids = set()
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = parts[-1]
                    if pid.isdigit() and pid != "0":
                        pids.add(pid)

            if not pids:
                # Try any matching state
                for line in out.splitlines():
                    parts = line.strip().split()
                    if parts and parts[-1].isdigit() and parts[-1] != "0":
                        pids.add(parts[-1])

            if pids:
                for pid in pids:
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                return f"Port {port} ko clear kar diya gaya hai (PID {', '.join(pids)} terminated)."
            else:
                return f"Port {port} par koi active process nahi mila."

        except subprocess.CalledProcessError:
            return f"Port {port} pehle se hi free hai."
        except Exception as e:
            return f"Port free karte waqt error: {e}"

    # =========================================================================
    # 3. AI-POWERED SMART GIT AUTO-COMMIT & SYNC
    # =========================================================================
    def auto_git_commit_and_sync(self, repo_dir: str = None) -> str:
        if not repo_dir:
            repo_dir = r"C:\RealJarvis_v2\RealJarvis"

        try:
            # Check git status
            status_res = subprocess.run(["git", "status", "--porcelain"], cwd=repo_dir, capture_output=True, text=True)
            changes = status_res.stdout.strip()

            if not changes:
                return "Git repo clean hai, koi uncommitted changes nahi hain."

            # Get diff summary
            diff_res = subprocess.run(["git", "diff", "--stat"], cwd=repo_dir, capture_output=True, text=True)
            diff_stat = diff_res.stdout.strip() or changes

            # Generate AI commit message
            commit_msg = "feat: update project codebase"
            if self.ai and self.ai.available():
                prompt = f"""Generate a concise 1-line conventional git commit message (e.g. 'feat: implement auto doctor', 'fix: resolve bug') for these git changes:
{diff_stat[:600]}

Reply ONLY with the commit message string, nothing else."""
                try:
                    ai_msg, _ = self.ai.ask(prompt, skip_history_append=True)
                    commit_msg = ai_msg.strip().strip('"').strip("'")
                except Exception:
                    pass

            # Stage, commit
            subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
            c_res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_dir, capture_output=True, text=True)

            if c_res.returncode == 0:
                return f"Changes commit ho gaye hain: '{commit_msg}'"
            else:
                return "Git commit execute karne mein error aaya."

        except Exception as e:
            return f"Git automation error: {e}"

    def get_git_status_summary(self, repo_dir: str = None) -> str:
        if not repo_dir:
            repo_dir = r"C:\RealJarvis_v2\RealJarvis"

        try:
            res = subprocess.run(["git", "status", "-s"], cwd=repo_dir, capture_output=True, text=True)
            out = res.stdout.strip()
            if not out:
                return "Git working tree bilkul clean hai."
            lines = out.splitlines()
            return f"Git repo mein {len(lines)} modified files hain."
        except Exception:
            return "Git status check nahi ho paya."


doctor = ProjectAutoDoctor()
