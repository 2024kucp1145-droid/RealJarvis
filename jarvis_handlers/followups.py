# -*- coding: utf-8 -*-
"""
followups.py
============
"Pending prompt" follow-ups — ek hi pattern, 9 jagah repeat hua tha.

Pattern: koi background sentry/user ne Jarvis se kuch pucha, Jarvis ne permission
maangi, aur user ke agle sentence ("haan" / "nahi" / "organize kar do") ko
sentry apne pending action se jod diya.

Pehle `handle_text()` me 9 nearly-identical try/except blocks the — har ek apna
`if any(w in text.lower() for w in (...))` list, apna method call, apna
`speak(...)`. Ab wo ek declarative table hai (`RULES`), aur matching/mapping
ka kaam `prompts.py` karta hai.

Ek rule = ek pending owner + uske ordered branches. Pehla matching branch
chalta hai; koi branch match na ho toh agla rule check hota hai. Order
`RULES` me hai aur jaan-boojh kar rakha gaya hai (jo pehle chalta tha, wahi).
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from . import prompts
from .optional_deps import deps


@dataclass
class Branch:
    """Ek specific user-sentence -> ek specific action."""

    words: Tuple[str, ...]
    method: str
    args: Tuple = ()
    kwargs_factory: Optional[Callable[[object], dict]] = None
    speak_result: bool = False     # action ka return value bolna hai?
    speech: Optional[str] = None   # ya ye fixed text bolna hai
    emotion: str = "happy"


@dataclass
class Rule:
    """Ek sentry ka pending state + uske possible replies."""

    name: str
    owner: str          # optional module name
    attr: str           # us module ka singleton
    pending: str        # "kya pending hai?" wala method
    branches: List[Branch] = field(default_factory=list)


def _speak_result(jarvis, result, emotion):
    """Har sentry apna reply string return karta hai — use bolte hain."""
    if isinstance(result, str) and result:
        jarvis.speak(result, emotion=emotion)


RULES_BEFORE_CLIPBOARD: Tuple[Rule, ...] = (
    # --- clipboard-error hook se PEHLE wale follow-ups -----------------
    # 1. Self-evolution: "naya skill seekh lo?" -> haan = skill banao, na = cancel
    Rule(
        "self_evolution_permission",
        "self_evolution_engine", "evolution_engine", "has_pending_permission",
        branches=[
            Branch(prompts.YES_LEARNING, "confirm_learning_permission", args=(True,)),
            Branch(prompts.NO_LEARNING, "confirm_learning_permission", args=(False,)),
        ],
    ),
    # 2. Predictive copilot: "agla step ye hai?" -> haan = chalao, na = cancel
    Rule(
        "predictive_copilot",
        "universal_predictive_copilot", "predictive_copilot", "has_pending_prediction",
        branches=[
            Branch(
                prompts.YES_ACTION, "execute_pending_prediction",
                kwargs_factory=lambda j: {"voice": j.voice, "gui": j.gui},
            ),
            Branch(
                prompts.NO_ACTION, "clear_pending",
                speech="Theek hai boss, step cancel kar diya.",
            ),
        ],
    ),
    # 3. Proactive guardian: "error fix karoon?" -> "haan/batao/fix"
    Rule(
        "proactive_guardian",
        "proactive_guardian", "guardian", "has_pending_solution",
        branches=[
            Branch(prompts.GUARDIAN_FIX_WORDS, "apply_or_explain_fix", speak_result=True),
        ],
    ),
    # 4. Hardware sentry: RAM choke, process band karoon?
    Rule(
        "hardware_sentry",
        "hardware_sentry", "sentry", "has_pending_kill_action",
        branches=[
            Branch(prompts.HARDWARE_KILL_WORDS, "kill_culprit_process", speak_result=True),
        ],
    ),
)

# Clipboard-error hook (router beech me chalta hai) ke baad wale follow-ups.
RULES_AFTER_CLIPBOARD: Tuple[Rule, ...] = (
    # 5. Download janitor: nayi file download hui -> organize / extract / open
    Rule(
        "download_janitor",
        "download_janitor", "janitor", "has_pending_file_action",
        branches=[
            Branch(prompts.DOWNLOAD_ORGANIZE_WORDS, "organize_pending_file", speak_result=True),
            Branch(prompts.DOWNLOAD_EXTRACT_WORDS, "extract_pending_archive", speak_result=True),
            Branch(prompts.DOWNLOAD_OPEN_WORDS, "open_pending_file", speak_result=True),
        ],
    ),
    # 6. Email sentry: urgent email aaya -> inbox kholo / summary sunao
    Rule(
        "email_sentry",
        "email_sentry", "sentry", "has_pending_email",
        branches=[
            Branch(prompts.EMAIL_OPEN_WORDS, "open_gmail_inbox", speak_result=True),
            Branch(prompts.EMAIL_READ_WORDS, "read_pending_summary", speak_result=True),
        ],
    ),
    # 7. Auto-doctor: missing library install karoon?
    Rule(
        "project_auto_doctor_install",
        "project_auto_doctor", "doctor", "has_pending_install",
        branches=[
            Branch(prompts.DOCTOR_INSTALL_WORDS, "install_pending_package", speak_result=True),
        ],
    ),
    # 8. Auto-doctor: port blocked hai -> free karoon?
    Rule(
        "project_auto_doctor_port",
        "project_auto_doctor", "doctor", "has_pending_port_kill",
        branches=[
            Branch(prompts.DOCTOR_PORT_WORDS, "free_port", speak_result=True),
        ],
    ),
    # 9. Desktop janitor: purane downloads / duplicate files -> trash karoon?
    Rule(
        "desktop_janitor_old",
        "desktop_janitor", "janitor", "has_pending_old_files",
        branches=[
            Branch(prompts.DESKTOP_OLD_WORDS, "trash_old_downloads", speak_result=True),
        ],
    ),
    Rule(
        "desktop_janitor_duplicates",
        "desktop_janitor", "janitor", "has_pending_duplicates",
        branches=[
            Branch(prompts.DESKTOP_DUPLICATES_WORDS, "trash_duplicates", speak_result=True),
        ],
    ),
)

# Poori list (tests / introspection ke liye)
RULES: Tuple[Rule, ...] = RULES_BEFORE_CLIPBOARD + RULES_AFTER_CLIPBOARD


def _invoke(jarvis, instance, rule: Rule, branch: Branch) -> bool:
    """Branch ka action chalao. False return = exception aaya (aage badho)."""
    try:
        kwargs = branch.kwargs_factory(jarvis) if branch.kwargs_factory else {}
        result = getattr(instance, branch.method)(*branch.args, **kwargs)
        if branch.speak_result:
            _speak_result(jarvis, result, branch.emotion)
        elif branch.speech:
            jarvis.speak(branch.speech, emotion=branch.emotion)
        return True
    except Exception as exc:  # noqa: BLE001 - ek follow-up fail ho toh agla try ho
        print(f"[{rule.name}] follow-up failed: {exc}")
        return False


def run(jarvis, text: str, rules: Tuple[Rule, ...] = RULES) -> bool:
    """
    Pending follow-ups check karta hai (order = `rules` order).
    True  -> is sentence ne koi pending action trigger kiya (consume)
    False -> kuch pending nahi tha ya koi trigger nahi hua
    """
    text_lower = prompts.normalize(text)

    for rule in rules:
        instance = deps.singleton(rule.owner, rule.attr)
        if instance is None:
            continue
        checker = getattr(instance, rule.pending, None)
        if not callable(checker):
            continue
        try:
            if not checker():
                continue
        except Exception as exc:  # noqa: BLE001
            print(f"[{rule.name}] pending check failed: {exc}")
            continue

        for branch in rule.branches:
            if prompts.matches(text_lower, branch.words):
                return _invoke(jarvis, instance, rule, branch)

    return False


# ---------------------------------------------------------------------------
# Clipboard error hook — ye pending-prompt nahi hai: user ne terminal ka error
# copy kiya hai toh auto-doctor turant diagnose karta hai. Pehle ye bhi
# handle_text() me inline tha.
# ---------------------------------------------------------------------------
_CLIPBOARD_ERROR_MARKERS = (
    "ModuleNotFoundError",
    "ImportError",
    "EADDRINUSE",
    "address already in use",
    "Cannot find module",
)


def inspect_clipboard_error(jarvis, text: str) -> bool:
    """Clipboard me terminal error hai toh project_auto_doctor se diagnose karo."""
    try:
        import pyperclip
        clip = pyperclip.paste() or ""
        if not clip or not any(marker in clip for marker in _CLIPBOARD_ERROR_MARKERS):
            return False
        doctor = deps.singleton("project_auto_doctor", "doctor")
        if doctor is None:
            return False
        return bool(doctor.inspect_terminal_error(clip))
    except Exception:  # noqa: BLE001 - pyperclip optional hai, clipboard optional hai
        return False