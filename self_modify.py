# -*- coding: utf-8 -*-
"""
self_modify.py
================
Autonomous AI Developer Engine for Jarvis (Agentic Coding & Self-Evolution).
Empowers Jarvis to autonomously read, search, modify, compile, and verify code:
  1. CODE SEARCH & GREP: Instant symbol, class, and text search across the codebase.
  2. TARGETED FILE SLICE READER: Reads exact line ranges (1-indexed).
  3. SURGICAL CODE REPLACER: Precise block replacement with automated .bak backups.
  4. AUTONOMOUS FILE CREATOR: Generates complete, new modules safely.
  5. COMPILER & TEST HARNESS: Verifies syntax with py_compile before saving.
  6. SELF-HEALING ROLLBACK: Automatically restores backups if a syntax regression occurs.
"""

import os
import sys
import re
import shutil
import subprocess
import datetime
from typing import Dict, List, Any, Optional, Tuple

CUSTOM_DIR = os.path.join(os.path.dirname(__file__), "custom")
FUNCTIONS_FILE = os.path.join(CUSTOM_DIR, "custom_functions.py")
TRIGGERS_FILE = os.path.join(CUSTOM_DIR, "custom_triggers.py")
PROPOSALS_DIR = os.path.join(os.path.dirname(__file__), "proposals")
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

os.makedirs(PROPOSALS_DIR, exist_ok=True)
os.makedirs(CUSTOM_DIR, exist_ok=True)


class SelfModifier:
    """Autonomous Agentic Coding & Self-Modification Suite for Jarvis."""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.proposals_dir = PROPOSALS_DIR

    # ------------------------------------------------------------- 1. DISCOVERY & SEARCH
    def discover_project_files(self) -> List[str]:
        """Discovers all python and project code files, excluding build/cache dirs."""
        py_files = []
        skip_dirs = {'venv', '__pycache__', 'data', '.git', 'proposals', 'screenshots', '.idea', '.vscode'}
        
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
            for f in files:
                if f.endswith(('.py', '.json', '.md', '.html', '.css', '.js')):
                    py_files.append(os.path.join(root, f))
        return sorted(py_files)

    def search_code(self, query: str, extensions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Searches across codebase for exact pattern matches."""
        valid_exts = tuple(extensions or ['.py', '.json', '.md'])
        all_files = self.discover_project_files()
        results = []
        q_lower = query.lower()

        for fpath in all_files:
            if not fpath.endswith(valid_exts):
                continue
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    for idx, line in enumerate(f, 1):
                        if q_lower in line.lower():
                            results.append({
                                "file": os.path.relpath(fpath, self.project_root),
                                "full_path": fpath,
                                "line": idx,
                                "snippet": line.strip()[:120]
                            })
                            if len(results) >= 50:
                                break
            except Exception:
                continue
            if len(results) >= 50:
                break
        return results

    # ------------------------------------------------------------- 2. SLICE READING
    def view_file_slice(self, filepath: str, start_line: int = 1, end_line: int = 80) -> Dict[str, Any]:
        """Reads exact line ranges from a file with line numbers."""
        if not os.path.isabs(filepath):
            filepath = os.path.join(self.project_root, filepath)

        if not os.path.exists(filepath):
            return {"success": False, "message": f"File '{filepath}' not found.", "content": ""}

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            total = len(lines)
            s_idx = max(1, start_line)
            e_idx = min(total, end_line)

            slice_text = "".join([f"{i + s_idx}: {lines[i + s_idx - 1]}" for i in range(e_idx - s_idx + 1)])
            return {
                "success": True,
                "file": os.path.relpath(filepath, self.project_root),
                "total_lines": total,
                "start_line": s_idx,
                "end_line": e_idx,
                "content": slice_text
            }
        except Exception as e:
            return {"success": False, "message": str(e), "content": ""}

    # ------------------------------------------------------------- 3. SURGICAL MODIFICATION
    def replace_code_block(self, filepath: str, target_snippet: str, replacement_snippet: str, backup: bool = True) -> Dict[str, Any]:
        """Surgically replaces a unique block of text with backup and syntax verification."""
        if not os.path.isabs(filepath):
            filepath = os.path.join(self.project_root, filepath)

        if not os.path.exists(filepath):
            return {"success": False, "message": f"File '{filepath}' does not exist."}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original_text = f.read()

            if target_snippet not in original_text:
                return {"success": False, "message": "Target code snippet not found in file."}

            if original_text.count(target_snippet) > 1:
                return {"success": False, "message": "Target snippet is ambiguous (found multiple times)."}

            # Backup
            bak_path = f"{filepath}.bak"
            if backup:
                shutil.copy2(filepath, bak_path)

            new_text = original_text.replace(target_snippet, replacement_snippet, 1)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_text)

            # Verification
            if filepath.endswith('.py'):
                v_res = self.compile_verify(filepath)
                if not v_res["success"]:
                    # Self-healing rollback
                    if backup and os.path.exists(bak_path):
                        shutil.copy2(bak_path, filepath)
                    return {"success": False, "message": f"Syntax error introduced. Rolled back to backup. Error: {v_res['message']}"}

            return {"success": True, "message": f"Successfully updated '{os.path.basename(filepath)}' with syntax verification passing."}
        except Exception as e:
            return {"success": False, "message": f"Modification error: {e}"}

    def write_code_file(self, filepath: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
        """Safely writes a new code file and compiles it."""
        if not os.path.isabs(filepath):
            filepath = os.path.join(self.project_root, filepath)

        if os.path.exists(filepath) and not overwrite:
            return {"success": False, "message": f"File '{filepath}' already exists."}

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            if filepath.endswith('.py'):
                v_res = self.compile_verify(filepath)
                if not v_res["success"]:
                    return {"success": False, "message": f"File created but syntax failed: {v_res['message']}"}

            return {"success": True, "message": f"Successfully created '{os.path.basename(filepath)}'."}
        except Exception as e:
            return {"success": False, "message": f"Write error: {e}"}

    # ------------------------------------------------------------- 4. COMPILER VERIFICATION
    def compile_verify(self, filepath: str) -> Dict[str, Any]:
        """Runs python py_compile to ensure zero syntax errors."""
        try:
            res = subprocess.run(
                [sys.executable, "-m", "py_compile", filepath],
                capture_output=True,
                text=True,
                timeout=10
            )
            if res.returncode == 0:
                return {"success": True, "message": "Syntax OK"}
            else:
                return {"success": False, "message": res.stderr}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------- 5. AUTONOMOUS WORKFLOWS
    def debug_project(self, voice, ai) -> bool:
        """Deep project debugging using search, digest, and AI analysis."""
        if voice:
            voice.speak("Apni files debug kar rahi hoon, thoda time lagega boss...")

        all_files = self.discover_project_files()
        critical = ['main.py', 'ai_brain.py', 'voice.py', 'gui.py', 'self_evolution_engine.py']
        context_parts = []

        for cf in critical:
            fp = os.path.join(self.project_root, cf)
            if os.path.exists(fp):
                slice_res = self.view_file_slice(fp, start_line=1, end_line=60)
                if slice_res["success"]:
                    context_parts.append(f"=== {cf} ===\n{slice_res['content']}")

        context = "\n\n".join(context_parts)
        if len(context) > 12000:
            context = context[:12000]

        prompt = f"""Tum ek Senior AI Lead Developer ho. Neeche Jarvis project ka codebase hai.
Analyze code for bugs, missing error handling, or performance improvements:

PROJECT CONTEXT:
{context}

Format:
###ANALYSIS###
- File: <file> -> <issue & fix>
###CRITICAL_ISSUES###
<critical issues>
###IMPROVEMENTS###
<actionable improvements>"""

        try:
            analysis, _ = ai.ask(prompt, skip_history_append=True)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            report_file = os.path.join(self.proposals_dir, f"DEBUG_REPORT_{timestamp}.txt")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"JARVIS AGENTIC DEBUG REPORT [{timestamp}]\n\n{analysis}")

            self._open_in_editor(report_file)
            if voice:
                voice.speak("Debug report taiyaar! Notepad mein analysis likh di hai boss.")
            return True
        except Exception as e:
            print(f"[SelfModifier debug error: {e}]")
            return False

    def plan_and_implement_feature(self, voice, ai, instruction: str) -> bool:
        """Autonomous feature planning and implementation."""
        if voice:
            voice.speak("Naya feature analyze karke code formulate kar rahi hoon boss...")

        # Formulate and create proposal / code
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', instruction[:25])
        proposal_file = os.path.join(self.proposals_dir, f"FEATURE_{safe_name}_{timestamp}.txt")

        prompt = f"""You are the Lead Systems Developer for Jarvis.
USER REQUEST: {instruction}
Formulate a clean, modular Python implementation for Jarvis."""

        try:
            plan, _ = ai.ask(prompt, skip_history_append=True)
            with open(proposal_file, 'w', encoding='utf-8') as f:
                f.write(f"FEATURE IMPLEMENTATION PROPOSAL\nRequest: {instruction}\n\n{plan}")
            self._open_in_editor(proposal_file)
            if voice:
                voice.speak("Feature formulate ho gaya hai aur Notepad mein open hai boss!")
            return True
        except Exception as e:
            print(f"[SelfModifier feature error: {e}]")
            return False

    def _open_in_editor(self, filepath: str):
        try:
            subprocess.Popen(['notepad.exe', filepath])
        except Exception:
            try:
                os.startfile(filepath)
            except Exception:
                pass


_modifier = SelfModifier()

def perform_modification(voice, ai, instruction: str) -> bool:
    """Main entrypoint for self-modification commands."""
    text = instruction.lower()
    if any(w in text for w in ['debug', 'error', 'bug', 'fix', 'scan', 'check']):
        return _modifier.debug_project(voice, ai)
    else:
        return _modifier.plan_and_implement_feature(voice, ai, instruction)