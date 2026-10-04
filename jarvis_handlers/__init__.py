# -*- coding: utf-8 -*-
"""
jarvis_handlers
===============
`main.py` ke 2162-line monolith ko focused modules me tod diya gaya hai.

Structure:

    optional_deps.py    optional imports ka ek registry (crash-proof loader)
    sentries.py         background sentries ka start/stop registry
    prompts.py          follow-up vocabulary (haan / na / organize / ...)
    followups.py        pending-prompt follow-ups ke declarative rules
    keyword_routes.py   keyword-triggered features ka route table
    text_patterns.py    shared regex patterns aur vocabulary
    lifecycle.py        startup, auth, wake loop, speak/listen, shutdown
    router.py           handle_text() — pura intent pipeline
    command_dispatch.py command_data.py ke matched commands ka executor
    feature_actions.py  memory + email handlers
    info_actions.py     no-argument "info" actions
    ai_actions.py       streaming AI answers + AI function-calling dispatch
    vision_actions.py   screen reading, code writing, file intake
    feature_routes.py   keyword route handlers (games, scouting, travel, ...)
    system_actions.py   app launch + keyboard automation
    chat_actions.py     chat mode
    media_actions.py    video notes / transcript / summary

`core.JarvisCore` in sab mixins ko compose karta hai — `main.py` sirf usko
import karta hai.
"""

from .ai_actions import AiActionsMixin
from .chat_actions import ChatActionsMixin
from .command_dispatch import CommandDispatchMixin
from .feature_actions import FeatureActionsMixin
from .feature_routes import FeatureRoutesMixin
from .info_actions import InfoActionsMixin
from .media_actions import MediaActionsMixin
from .system_actions import SystemActionsMixin
from .vision_actions import VisionActionsMixin

__all__ = [
    "AiActionsMixin",
    "ChatActionsMixin",
    "CommandDispatchMixin",
    "FeatureActionsMixin",
    "FeatureRoutesMixin",
    "InfoActionsMixin",
    "MediaActionsMixin",
    "SystemActionsMixin",
    "VisionActionsMixin",
]