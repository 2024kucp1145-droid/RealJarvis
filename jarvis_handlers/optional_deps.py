# -*- coding: utf-8 -*-
"""
optional_deps.py
================
Saare optional dependencies ek hi jagah load hoti hain.

Pehle main.py me har optional import ka apna try/except block tha (10+ blocks),
aur phir un modules ka use *unguarded* tha. Matlab agar `hardware_sentry`
import fail hota toh startup pe hi `None.start()` jaisa AttributeError aa
kar poora Jarvis gir jaata tha.

Ab: ek registry + ek loader.
  - load fail hua  -> module `None` ho jaata hai
  - call-site par `deps.module(...)` / `deps.attr(...)` None-safe hain
  - sentries registry (sentries.py) missing module ko chhod deta hai

Result: graceful degradation — Jarvis missing optional feature ke saath bhi
chalti hai, aur har missing dependency console pe ek line me report hoti hai.
"""

import importlib

# module name -> wo attributes jo us module se chahiye hain
_OPTIONAL_ATTRS = {
    # UI / input
    "eye_control": ("EyeCursorController",),
    "screen_monitor": ("ScreenMonitor",),
    "chat_gui": ("JarvisChatGUI",),
    "web_control": (
        "execute_web_action",
        "run_autonomous_web_task",
        "extract_screen_info",
        "stop_autonomous_agent",
    ),
    # background sentries (module-level singletons)
    "proactive_guardian": (),
    "hardware_sentry": (),
    "health_focus_coach": (),
    "download_janitor": (),
    "email_sentry": (),
    "workspace_harmonizer": (),
    "web_workflow_assistant": (),
    "project_auto_doctor": (),
    "desktop_janitor": (),
    "autonomous_evolution": (),
    "whatsapp_mobile_bridge": (),
    "self_evolution_engine": (),
    "morning_briefing_sentry": (),
}


class OptionalDeps:
    """
    Optional modules ka ek namespace. Attribute access se load hota hai:

        deps.eye_control          -> module (ya None)
        deps.ScreenMonitor        -> class    (ya None)
        deps.call("web_control", "execute_web_action", args=(v, ai, text))

    `report()` sab loaded modules ka ek-line status deta hai (debug ke liye).
    """

    def __init__(self):
        self._modules = {}
        self._attrs = {}
        self._failed = []
        self._load_all()

    # ------------------------------------------------------------------ load
    def _load_all(self):
        for name, attrs in _OPTIONAL_ATTRS.items():
            module = self._import(name)
            self._modules[name] = module
            if module is None:
                self._failed.append(name)
                self._attrs[name] = {}
                continue
            resolved = {}
            for attr in attrs:
                value = getattr(module, attr, None)
                if value is None:
                    self._failed.append(f"{name}.{attr}")
                resolved[attr] = value
            self._attrs[name] = resolved

    def _import(self, name):
        try:
            return importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 - koi bhi optional dep fail ho sakti hai
            print(f"[WARN] optional module '{name}' load nahi hua: {exc}")
            return None

    # --------------------------------------------------------------- access
    def module(self, name):
        """Loaded module, ya None agar load fail hua tha."""
        if name not in self._modules:
            self._modules[name] = self._import(name)
            if self._modules[name] is None:
                self._failed.append(name)
        return self._modules[name]

    def attr(self, module_name, attr_name, default=None):
        """Module ka attribute, ya default agar module/attribute missing hai."""
        module = self.module(module_name)
        if module is None:
            return default
        return getattr(module, attr_name, default)

    def singleton(self, module_name, attr_name):
        """
        Sentries jaise modules apna instance module pe expose karte hain
    (jaise hardware_sentry.sentry). Missing ho to None.
        """
        module = self.module(module_name)
        return getattr(module, attr_name, None) if module is not None else None

    def missing(self, module_name) -> bool:
        return self.module(module_name) is None

    # ---------------------------------------------------------------- misc
    def report(self) -> str:
        ok = len(_OPTIONAL_ATTRS) - len(self._failed)
        return f"optional deps: {ok}/{len(_OPTIONAL_ATTRS)} loaded" + (
            f", missing: {sorted(set(self._failed))}" if self._failed else ""
        )


deps = OptionalDeps()