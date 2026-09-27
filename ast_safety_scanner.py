# -*- coding: utf-8 -*-
"""
ast_safety_scanner.py  (Phase 6: AST Static Security & Safety Scanner)
========================================================================
Performs static analysis using Python's Abstract Syntax Tree (AST) to verify
code safety, prevent destructive system commands, and ensure syntactic validity
before code ever touches the sandbox or execution environment.
"""

import ast
import sys
import os
from dataclasses import dataclass, field
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# ALLOWLIST MODEL
# ---------------------------------------------------------------------------
# SECURITY: Pehle yahan ek chhota blocklist tha
#   BLOCKED_FUNCTION_CALLS = {"rmtree", "format", "mkfs", "fork", "kill", "killpg"}
#   BLOCKED_IMPORT_MODULES = {"ctypes.wintypes.FormatDrive", "win32api.InitiateSystemShutdown"}
# Wo approach secure nahi thi: blocklist me sirf exact naam hone chahiye the,
# isliye `subprocess.run(["format", "C:"])`, `os.system(...)`, `os.remove(...)`,
# `shutil.move(...)` — kuch bhi pakda nahi jaata tha. Ab hum ALLOWLIST use karte
# hain: sirf listed safe modules import ho sakte hain, baaki sab reject.
#
# Koi naya safe module chahiye ho toh neeche list me add karo (review karke).

ALLOWED_MODULES = {
    # --- safe stdlib for skills ---
    "os.path", "pathlib", "datetime", "time", "json", "csv", "re", "math",
    "random", "string", "textwrap", "collections", "itertools", "functools",
    "statistics", "uuid", "hashlib", "base64", "urllib.parse", "typing",
    "dataclasses", "enum", "decimal", "fractions", "io", "glob", "zipfile",
    "gzip", "webbrowser", "html", "html.parser", "zoneinfo", "calendar",
    "difflib", "unicodedata", "operator", "numbers", "contextlib", "abc",
    "copy", "struct", "binascii", "secrets", "shlex", "sqlite3", "tempfile",
    "sys",
    # --- pre-installed safe third-party packages ---
    "pyautogui", "requests", "bs4", "PIL", "pandas", "openpyxl", "docx",
    "PyPDF2", "pypdf", "fpdf", "numpy", "cv2", "mss", "psutil", "pyperclip",
    "edge_tts", "pygame", "playsound", "screen_brightness_control",
}

# Ye function/attribute naam kisi bhi module par allowed nahi hain
BLOCKED_CALL_NAMES = {
    "eval", "exec", "compile", "execfile", "__import__", "globals", "locals",
    "vars", "breakpoint", "memoryview", "setattr", "delattr",
}

# In modules ke koi bhi function call allowed nahi (defence in depth).
# NOTE: koi module yahan aur ALLOWED_MODULES dono me nahi hona chahiye -
# allowed list ki entry jeet jaati hai (allowed_len >= blocked_len check).
BLOCKED_MODULE_ROOTS = {
    "subprocess", "ctypes", "socket", "shutil", "pickle", "marshal", "shelve",
    "winreg", "win32api", "win32com", "win32con", "win32file", "win32security",
    "multiprocessing", "signal", "pty", "importlib", "builtins", "__builtin__",
    "os", "platform", "atexit", "code", "codeop", "cmd",
    "telnetlib", "ftplib", "smtplib", "ssl", "asyncio",
}

# Sandbox-escape dunder attributes
BLOCKED_DUNDER_ATTRIBUTES = {
    "__class__", "__globals__", "__subclasses__", "__builtins__", "__mro__",
    "__dict__", "__getattribute__", "__reduce__", "__reduce_ex__", "__code__",
    "__closure__", "__func__", "__self__", "__import__", "__loader__",
}

PROTECTED_SYSTEM_PATHS = [
    r"c:\windows", r"c:\windows\system32", r"c:\program files", r"c:\recovery"
]


@dataclass
class SafetyScanResult:
    is_safe: bool = True
    syntax_valid: bool = True
    has_entrypoint: bool = False
    issues: List[str] = field(default_factory=list)
    imported_modules: List[str] = field(default_factory=list)


class ASTSafetyScanner(ast.NodeVisitor):
    """Deep AST Node Visitor for security analysis (allowlist enforced)."""

    def __init__(self):
        self.result = SafetyScanResult()
        self._import_aliases: Dict[str, str] = {}

    def scan_code(self, code_str: str) -> SafetyScanResult:
        self.result = SafetyScanResult()
        self._import_aliases = {}

        # 1. Syntax Validation
        try:
            tree = ast.parse(code_str)
            self.result.syntax_valid = True
        except SyntaxError as e:
            self.result.syntax_valid = False
            self.result.is_safe = False
            self.result.issues.append(f"SyntaxError at line {e.lineno}: {e.msg}")
            return self.result

        # 2. Traverse AST Nodes
        self.visit(tree)

        if not self.result.has_entrypoint:
            self.result.is_safe = False
            self.result.issues.append("Missing required 'def execute(context=None)' entrypoint function.")

        if self.result.issues:
            self.result.is_safe = False

        return self.result

    # --------------------------- helpers ---------------------------

    @staticmethod
    def _classify_module(dotted_name: str) -> str:
        """Dotted naam ko 'allowed' / 'blocked' / 'unknown' me classify karo.

        Sabse lamba matching prefix jeetta hai, isliye `os.path.join` allowed
        hai (allowed prefix 'os.path' > blocked prefix 'os') jabki `os.system`
        blocked hai (blocked prefix 'os', koi allowed prefix nahi).
        """
        segments = [seg for seg in dotted_name.split(".") if seg]
        allowed_len = 0
        blocked_len = 0
        for index in range(1, len(segments) + 1):
            prefix = ".".join(segments[:index])
            if prefix in ALLOWED_MODULES:
                allowed_len = index
            if prefix in BLOCKED_MODULE_ROOTS:
                blocked_len = index

        if blocked_len and blocked_len >= allowed_len:
            return "blocked"
        if allowed_len:
            return "allowed"
        return "unknown"

    @classmethod
    def _is_allowed_module(cls, module_name: str) -> bool:
        return cls._classify_module(module_name) == "allowed"

    def _record_import(self, module_name: str, local_name: str, resolves_to: str = None):
        self.result.imported_modules.append(module_name)
        self._import_aliases[local_name] = resolves_to or module_name

    def _resolve_attribute_chain(self, node: ast.AST) -> str:
        """`os.path.join` ya aliased `p.join` jaisa poora dotted naam nikalo."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            root = self._import_aliases.get(current.id, current.id)
            parts.append(root)
            return ".".join(reversed(parts))
        return ""

    # --------------------------- visitors ---------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name == "execute":
            self.result.has_entrypoint = True
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            module_name = alias.name
            if alias.asname:
                local_name = alias.asname
                resolves_to = module_name
            else:
                # `import os.path` likhne par code `os.path.join` use karta hai,
                # isliye root token ko khud se map karo (os -> os).
                local_name = module_name.split(".")[0]
                resolves_to = local_name
            self._record_import(module_name, local_name, resolves_to)
            if not self._is_allowed_module(module_name):
                self.result.issues.append(
                    f"Security Alert: Import '{module_name}' allowlist me nahi hai (line {node.lineno})."
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module_name = node.module or ""
        if node.level and node.level > 0:
            self.result.issues.append(
                f"Security Alert: Relative import allowed nahi hai (line {node.lineno})."
            )
            self.generic_visit(node)
            return

        for alias in node.names:
            if alias.name == "*":
                self.result.issues.append(
                    f"Security Alert: Wildcard import ('from {module_name} import *') allowed nahi hai "
                    f"(line {node.lineno})."
                )
                continue

            full_name = f"{module_name}.{alias.name}" if module_name else alias.name
            local_name = alias.asname or alias.name
            self.result.imported_modules.append(full_name)
            self._import_aliases[local_name] = full_name

            if not self._is_allowed_module(full_name):
                self.result.issues.append(
                    f"Security Alert: Import '{full_name}' allowlist me nahi hai (line {node.lineno})."
                )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in BLOCKED_DUNDER_ATTRIBUTES:
            self.result.issues.append(
                f"Security Alert: Sandbox-escape attribute '{node.attr}' blocked (line {node.lineno})."
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        resolved_name = self._resolve_attribute_chain(node.func)

        # a) Bare dangerous functions: eval / exec / __import__ ...
        bare_name = resolved_name.split(".")[-1] if resolved_name else ""
        if bare_name in BLOCKED_CALL_NAMES:
            self.result.issues.append(
                f"Security Alert: Dynamic/dangerous call '{bare_name}' restricted (line {node.lineno})."
            )

        # b) Called module blocked root pe hai? (subprocess.run, os.system, ...)
        if resolved_name:
            if self._classify_module(resolved_name) == "blocked":
                self.result.issues.append(
                    f"Security Alert: Call to blocked module '{resolved_name}' (line {node.lineno})."
                )

        # c) open() sirf read-only mode me allowed
        if bare_name == "open":
            mode = ""
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = str(node.args[1].value or "")
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = str(kw.value.value or "")
            if any(flag in mode for flag in ("w", "a", "x", "+")):
                self.result.issues.append(
                    f"Security Alert: File write via open(mode='{mode}') blocked "
                    f"(line {node.lineno}) - read-only allowed hai."
                )

        # d) getattr(obj, "__globals__") jaisa string-based escape
        if bare_name == "getattr":
            for arg in node.args[1:2]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value in BLOCKED_DUNDER_ATTRIBUTES:
                        self.result.issues.append(
                            f"Security Alert: getattr() se '{arg.value}' access blocked "
                            f"(line {node.lineno})."
                        )

        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        # Check for dangerous string literals (e.g. system paths being modified)
        if isinstance(node.value, str):
            val_lower = node.value.lower()
            for sys_path in PROTECTED_SYSTEM_PATHS:
                if val_lower == sys_path or val_lower.startswith(sys_path + "\\"):
                    self.result.issues.append(
                        f"Security Alert: Direct reference to protected Windows system path "
                        f"'{node.value}' (line {node.lineno})."
                    )
        self.generic_visit(node)


scanner = ASTSafetyScanner()
