# -*- coding: utf-8 -*-
"""
sentries.py
===========
Background sentries (proactive monitors) ka ek declarative registry.

Pehle `main.py` me 14 `X.start(voice=..., ai=..., gui=..., speak_fn=...)`
lines aur phir shutdown me 13 `X.stop()` lines likhi thi — aur har call
unguarded thi, yaani optional module import fail hua toh startup pe hi
`AttributeError: 'NoneType' object has no attribute 'start'` crash.

Ab: ek table. Missing module skip ho jaata hai, exception ek line me log hoti
hai, aur start/stop order code me dikhta hai.
"""

import importlib
from dataclasses import dataclass
from typing import Tuple

from .optional_deps import deps


@dataclass(frozen=True)
class SentrySpec:
    """Ek background sentry ka contract."""

    name: str
    module: str                      # module ka naam
    attr: str                        # us module pe exposed singleton
    start_kwargs: Tuple[str, ...] = ("voice", "ai", "gui", "speak_fn")
    hard: bool = False               # True -> hard dependency (optional-deps registry se nahi)

    def resolve(self):
        if self.hard:
            try:
                return getattr(importlib.import_module(self.module), self.attr)
            except Exception:  # noqa: BLE001
                return None
        return deps.singleton(self.module, self.attr)


# START ORDER — pehle wala pehle chalta hai. Ye order matter karta hai:
# guardian/hardware sabse pehle (turant protection), bridges aur briefing sabse
# baad me (taaki login hone ke baad hi chalein).
SENTRIES: Tuple[SentrySpec, ...] = (
    SentrySpec("activity_tracker", "activity_tracker", "tracker",
               start_kwargs=(), hard=True),
    SentrySpec("proactive_guardian", "proactive_guardian", "guardian"),
    SentrySpec("hardware_sentry", "hardware_sentry", "sentry"),
    SentrySpec("health_focus_coach", "health_focus_coach", "coach"),
    SentrySpec("download_janitor", "download_janitor", "janitor"),
    SentrySpec("email_sentry", "email_sentry", "sentry"),
    SentrySpec("workspace_harmonizer", "workspace_harmonizer", "harmonizer"),
    SentrySpec("web_workflow_assistant", "web_workflow_assistant", "assistant"),
    SentrySpec("project_auto_doctor", "project_auto_doctor", "doctor"),
    SentrySpec("desktop_janitor", "desktop_janitor", "janitor"),
    SentrySpec("autonomous_evolution", "autonomous_evolution", "evolution",
               start_kwargs=("voice", "ai", "gui", "speak_fn", "dispatcher_fn")),
    SentrySpec("whatsapp_mobile_bridge", "whatsapp_mobile_bridge", "bridge",
               start_kwargs=("voice", "ai", "gui", "speak_fn", "dispatcher_fn")),
    SentrySpec("self_evolution_engine", "self_evolution_engine", "evolution_engine"),
    SentrySpec("morning_briefing_sentry", "morning_briefing_sentry", "briefing_sentry",
               start_kwargs=("voice", "ai", "gui")),
)

# STOP ORDER — shutdown me kis order me band karna hai.
# self_evolution_engine ke paas stop() nahi hai, wo hasattr check se skip ho jata hai.
STOP_ORDER: Tuple[str, ...] = (
    "hardware_sentry",
    "proactive_guardian",
    "health_focus_coach",
    "download_janitor",
    "email_sentry",
    "workspace_harmonizer",
    "web_workflow_assistant",
    "project_auto_doctor",
    "desktop_janitor",
    "autonomous_evolution",
    "whatsapp_mobile_bridge",
    "morning_briefing_sentry",
    "activity_tracker",
)

_BY_NAME = {spec.name: spec for spec in SENTRIES}


def start_all(voice=None, ai=None, gui=None, speak_fn=None, dispatcher_fn=None):
    """
    Login ke baad saari proactive sentries start karta hai.
    Missing optional module skip ho jaata hai (crash nahi hota).
    """
    available = {"voice": voice, "ai": ai, "gui": gui,
                 "speak_fn": speak_fn, "dispatcher_fn": dispatcher_fn}

    for spec in SENTRIES:
        instance = spec.resolve()
        if instance is None:
            print(f"[sentry] skip '{spec.name}' - module unavailable")
            continue
        if not hasattr(instance, "start"):
            continue
        kwargs = {key: available[key] for key in spec.start_kwargs}
        try:
            instance.start(**kwargs)
        except Exception as exc:  # noqa: BLE001 - ek sentry fail baakiyon ko mat rokega
            print(f"[sentry] '{spec.name}' start failed: {exc}")


def stop_all():
    """Shutdown pe saari sentries band karta hai (best-effort, order me)."""
    for name in STOP_ORDER:
        spec = _BY_NAME.get(name)
        if spec is None:
            continue
        try:
            instance = spec.resolve()
        except Exception:  # noqa: BLE001
            continue
        if instance is None or not hasattr(instance, "stop"):
            continue
        try:
            instance.stop()
        except Exception as exc:  # noqa: BLE001
            print(f"[sentry] '{name}' stop failed: {exc}")