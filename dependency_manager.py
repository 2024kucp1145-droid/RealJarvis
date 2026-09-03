# -*- coding: utf-8 -*-
"""
dependency_manager.py  (Phase 7: Dynamic Background Dependency & Pip Installer)
================================================================================
Detects required external third-party libraries from AST imported modules,
checks if already present in venv, and installs missing packages in background.
"""

import sys
import os
import subprocess
import importlib.util
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mapping from import names to PyPI package names
IMPORT_TO_PYPI = {
    "bs4": "beautifulsoup4",
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "docx": "python-docx",
    "yaml": "pyyaml",
    "win32gui": "pywin32",
    "win32process": "pywin32",
    "win32api": "pywin32",
    "fitz": "pymupdf",
    "playwright": "playwright",
    "sklearn": "scikit-learn"
}

# Standard built-in Python modules (no pip needed)
BUILTIN_MODULES = {
    "os", "sys", "time", "json", "re", "math", "random", "datetime",
    "glob", "shutil", "urllib", "ctypes", "threading", "subprocess",
    "tempfile", "hashlib", "sqlite3", "queue", "pathlib", "collections",
    "itertools", "functools", "dataclasses", "typing", "ast", "xml",
    "io", "string", "copy", "socket", "http", "email", "logging"
}


class DependencyManager:
    """Manages dynamic background installation of third-party dependencies."""

    @staticmethod
    def ensure_dependencies(imported_modules: List[str]) -> Dict[str, any]:
        """
        Inspects imported modules, installs missing packages, and returns status.
        """
        missing_pkgs = []
        installed = []
        failed = []

        for mod in imported_modules:
            base_mod = mod.split(".")[0].strip()
            if not base_mod or base_mod in BUILTIN_MODULES:
                continue

            # Check if importable
            if not DependencyManager._is_module_installed(base_mod):
                pypi_name = IMPORT_TO_PYPI.get(base_mod, base_mod)
                missing_pkgs.append(pypi_name)

        # Deduplicate
        missing_pkgs = list(dict.fromkeys(missing_pkgs))

        # Install missing packages
        for pkg in missing_pkgs:
            print(f"[dependency_manager] Installing missing dependency: '{pkg}'...")
            success = DependencyManager._install_package(pkg)
            if success:
                installed.append(pkg)
                print(f"[dependency_manager] Successfully installed '{pkg}'.")
            else:
                failed.append(pkg)
                print(f"[dependency_manager] Failed to install '{pkg}'.")

        return {
            "all_ready": len(failed) == 0,
            "installed": installed,
            "failed": failed
        }

    @staticmethod
    def _is_module_installed(mod_name: str) -> bool:
        """Checks if a module exists in the current Python environment."""
        try:
            spec = importlib.util.find_spec(mod_name)
            return spec is not None
        except Exception:
            return False

    @staticmethod
    def _install_package(pkg_name: str) -> bool:
        """Runs pip install in the current virtualenv."""
        try:
            cmd = [sys.executable, "-m", "pip", "install", pkg_name, "-q"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return res.returncode == 0
        except Exception as e:
            print(f"[dependency_manager install error: {e}]")
            return False


dep_manager = DependencyManager()
