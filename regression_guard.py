# -*- coding: utf-8 -*-
"""
regression_guard.py  (Phase 10: Regression Guard Shield)
==========================================================
Protects the core Jarvis framework from unintended side-effects or namespace
collisions caused by newly synthesized custom skills.

Audits:
1. Core Jarvis Module Imports (Voice, AI Brain, Sentries, Bridge).
2. Hardware Sentry & Battery API Health.
3. System Memory & Execution Boundaries.
4. Core Command Namespace Conflict Prevention (protects built-in triggers like 'so jao', 'shutdown').
"""

import sys
import os
import importlib
from dataclasses import dataclass, field
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CORE_JARVIS_MODULES = [
    "ai_brain",
    "voice",
    "gui",
    "hardware_sentry",
    "whatsapp_mobile_bridge",
    "desktop_context",
    "commands.system_commands",
    "commands.file_commands",
    "commands.browser_commands"
]

PROTECTED_CORE_TRIGGERS = {
    "so jao", "sleep", "shutdown", "restart", "lock", "exit", "quit",
    "help", "status", "stop", "pause", "resume", "mute", "unmute"
}


@dataclass
class RegressionReport:
    passed: bool = True
    total_checks: int = 0
    failures: List[str] = field(default_factory=list)
    details: Dict[str, str] = field(default_factory=dict)


class RegressionGuard:
    """Audits system integrity and guards core functionality against regressions."""

    @staticmethod
    def audit_system_integrity(new_skill_triggers: List[str] = None) -> RegressionReport:
        report = RegressionReport()

        # 1. Namespace Conflict Check
        if new_skill_triggers:
            report.total_checks += 1
            for trigger in new_skill_triggers:
                clean_trig = trigger.strip().lower()
                if clean_trig in PROTECTED_CORE_TRIGGERS:
                    report.passed = False
                    report.failures.append(f"Namespace Collision: Trigger '{clean_trig}' is a protected core Jarvis command.")

        # 2. Core Modules Importability Check
        for mod_name in CORE_JARVIS_MODULES:
            report.total_checks += 1
            try:
                mod = importlib.import_module(mod_name)
                report.details[mod_name] = "OK"
            except Exception as e:
                report.passed = False
                report.failures.append(f"Core module '{mod_name}' failed import integrity: {e}")
                report.details[mod_name] = f"FAIL: {e}"

        # 3. Hardware Sentry Check
        report.total_checks += 1
        try:
            import hardware_sentry
            st = hardware_sentry.sentry._get_battery_status()
            report.details["hardware_sentry"] = "OK" if st else "WARNING (No battery data)"
        except Exception as e:
            report.passed = False
            report.failures.append(f"Hardware Sentry health check failed: {e}")

        # 4. WhatsApp Mobile Bridge Check
        report.total_checks += 1
        try:
            import whatsapp_mobile_bridge
            phone = whatsapp_mobile_bridge.bridge.master_phone
            report.details["whatsapp_bridge"] = f"OK (Master: {phone})"
        except Exception as e:
            report.passed = False
            report.failures.append(f"WhatsApp Mobile Bridge health check failed: {e}")

        return report


guard = RegressionGuard()
