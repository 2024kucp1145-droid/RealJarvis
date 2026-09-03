# -*- coding: utf-8 -*-
"""
os_sandbox.py
=============
Deep Windows Execution Sandbox and OS Automation Engine for Real Jarvis.
Allows Jarvis to write and run Python/PowerShell scripts on-the-fly,
search files across all drives in milliseconds, and control native Windows UI.
"""

import sys
import os
import subprocess
import tempfile
import time
import re

try:
    import psutil
except ImportError:
    psutil = None

# Dangerous commands blocklist for safety
DANGEROUS_PATTERNS = [
    r"format\s+[a-z]:",
    r"rmdir\s+/s\s+/q\s+c:\\",
    r"del\s+/f\s+/s\s+/q\s+c:\\windows",
    r"drop\s+database",
    r"diskpart",
]


def _is_safe_command(cmd: str) -> bool:
    cmd_lower = cmd.lower()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_lower):
            return False
    return True


def execute_python_code(code: str, timeout: int = 20) -> dict:
    """
    Executes Python automation code on-the-fly in a subprocess.
    Returns {"success": bool, "output": str, "error": str}.
    """
    if not code or not code.strip():
        return {"success": False, "output": "", "error": "Empty code provided"}

    clean_code = code.strip()
    if clean_code.startswith("```python"):
        clean_code = clean_code[9:]
    elif clean_code.startswith("```"):
        clean_code = clean_code[3:]
    if clean_code.endswith("```"):
        clean_code = clean_code[:-3]
    clean_code = clean_code.strip()

    if not _is_safe_command(clean_code):
        return {"success": False, "output": "", "error": "Security Alert: Dangerous command blocked."}

    temp_file = os.path.join(tempfile.gettempdir(), f"jarvis_task_{int(time.time()*1000)}.py")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("# -*- coding: utf-8 -*-\n")
            f.write(clean_code)

        proc = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

        output = proc.stdout.strip()
        error = proc.stderr.strip()
        success = (proc.returncode == 0)

        return {
            "success": success,
            "output": output if output else ("Success (No output)" if success else ""),
            "error": error
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": f"Execution timed out after {timeout} seconds."}
    except Exception as e:
        return {"success": False, "output": "", "error": f"Execution failed: {str(e)}"}
    finally:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception:
            pass


def execute_powershell(command: str, timeout: int = 15) -> dict:
    """
    Executes PowerShell command directly on Windows.
    Returns {"success": bool, "output": str, "error": str}.
    """
    if not command or not command.strip():
        return {"success": False, "output": "", "error": "Empty command"}

    clean_cmd = command.strip()
    if clean_cmd.startswith("```powershell") or clean_cmd.startswith("```bash"):
        clean_cmd = clean_cmd.split("\n", 1)[1]
    if clean_cmd.endswith("```"):
        clean_cmd = clean_cmd.rsplit("```", 1)[0]
    clean_cmd = clean_cmd.strip()

    if not _is_safe_command(clean_cmd):
        return {"success": False, "output": "", "error": "Security Alert: Dangerous PowerShell command blocked."}

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", clean_cmd],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "success": proc.returncode == 0,
            "output": proc.stdout.strip(),
            "error": proc.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": f"PowerShell timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "output": "", "error": f"PowerShell failed: {str(e)}"}


def search_computer_files(query: str, search_path: str = None, max_results: int = 10) -> list:
    """
    Fast multi-directory file search across Windows file system.
    """
    if not query:
        return []

    q_lower = query.lower()
    matches = []
    
    user_home = os.path.expanduser("~")
    search_dirs = [
        os.path.join(user_home, "Desktop"),
        os.path.join(user_home, "Downloads"),
        os.path.join(user_home, "Documents"),
        r"C:\RealJarvis_v2",
        user_home,
    ]
    if search_path and os.path.exists(search_path):
        search_dirs.insert(0, search_path)

    skip_folders = {"node_modules", ".git", "venv", "__pycache__", "appdata", "windows", "program files"}

    for root_dir in search_dirs:
        if not os.path.exists(root_dir):
            continue
        try:
            for root, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if d.lower() not in skip_folders and not d.startswith(".")]
                for f in files:
                    if q_lower in f.lower():
                        full_path = os.path.join(root, f)
                        size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
                        size_str = f"{size//1024} KB" if size < 1024*1024 else f"{size//(1024*1024)} MB"
                        matches.append({"name": f, "path": full_path, "size": size_str})
                        if len(matches) >= max_results:
                            return matches
        except Exception:
            continue

    return matches


def get_system_vitals() -> dict:
    """Returns detailed real-time system performance data."""
    if not psutil:
        return {
            "cpu_percent": "N/A",
            "ram_percent": "N/A",
            "ram_free_gb": "N/A",
            "disks": {},
            "top_processes": []
        }
    try:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disks = {}
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disks[part.device] = {
                    "total_gb": round(usage.total / (1024**3), 1),
                    "free_gb": round(usage.free / (1024**3), 1),
                    "percent": usage.percent
                }
            except Exception:
                pass
                
        procs = []
        for p in psutil.process_iter(['name', 'memory_percent', 'cpu_percent']):
            try:
                procs.append(p.info)
            except Exception:
                pass
        procs.sort(key=lambda x: x.get('memory_percent') or 0, reverse=True)
        top_procs = [f"{p['name']} ({round(p['memory_percent'] or 0, 1)}% RAM)" for p in procs[:4]]

        return {
            "cpu_percent": cpu_pct,
            "ram_percent": mem.percent,
            "ram_free_gb": round(mem.available / (1024**3), 1),
            "disks": disks,
            "top_processes": top_procs
        }
    except Exception as e:
        return {"error": str(e)}
