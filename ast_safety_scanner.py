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

BLOCKED_FUNCTION_CALLS = {
    "rmtree", "format", "mkfs", "fork", "kill", "killpg"
}

BLOCKED_IMPORT_MODULES = {
    "ctypes.wintypes.FormatDrive", "win32api.InitiateSystemShutdown"
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
    """Deep AST Node Visitor for security analysis."""

    def __init__(self):
        self.result = SafetyScanResult()

    def scan_code(self, code_str: str) -> SafetyScanResult:
        self.result = SafetyScanResult()

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

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name == "execute":
            self.result.has_entrypoint = True
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.result.imported_modules.append(alias.name)
            if alias.name in BLOCKED_IMPORT_MODULES:
                self.result.issues.append(f"Security Alert: Blocked dangerous module import '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.result.imported_modules.append(node.module)
            for alias in node.names:
                full_name = f"{node.module}.{alias.name}"
                if full_name in BLOCKED_IMPORT_MODULES:
                    self.result.issues.append(f"Security Alert: Blocked dangerous import '{full_name}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Detect function calls
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in BLOCKED_FUNCTION_CALLS:
            self.result.issues.append(f"Security Alert: Dangerous function call '{func_name}' detected.")

        # Detect dangerous eval/exec
        if func_name in ("eval", "exec") and not getattr(self, "_in_safe_context", False):
            # Only flag if arbitrary dynamic code execution inside user skill
            self.result.issues.append(f"Security Alert: Dynamic evaluation via '{func_name}' is restricted.")

        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        # Check for dangerous string literals (e.g. system paths being modified)
        if isinstance(node.value, str):
            val_lower = node.value.lower()
            for sys_path in PROTECTED_SYSTEM_PATHS:
                if val_lower == sys_path or val_lower.startswith(sys_path + "\\"):
                    self.result.issues.append(f"Security Alert: Direct reference to protected Windows system path '{node.value}'")
        self.generic_visit(node)


scanner = ASTSafetyScanner()
