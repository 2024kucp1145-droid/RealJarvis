# -*- coding: utf-8 -*-
"""
prompts.py
==========
Follow-up (pending prompt) vocabulary.

Ye sab `handle_text()` me 9 jagah inline copy-paste hota tha. Ab vocabulary
ek jagah hai aur matching ka ek helper hai.

Do alag "haan" lists kyun?
--------------------------------
`YES_LEARNING` (self-evolution) me "seekh lo", "approve", "go ahead" jaise
words hain — wo skill-learning trigger hain.
`YES_ACTION` (copilot / pending step) me "likh do", "execute karo" jaise words
hain — wo koi bhi pending step chalayein.

Inhe merge karne se behaviour badalega: "likh do" pe self-evolution engine
skill seekhne lagta, ya "approve" pe copilot ka step chal jaata. Isliye jaan
boojh kar alag rakhe hain. Common hissa (haan/yes/thik hai/...) dono me hai.
"""

from typing import Iterable

# --- self-evolution learning permission -------------------------------
YES_LEARNING = (
    "haan", "ha", "yes", "yep", "yeah", "seekh lo", "seekho",
    "banao", "banaa do", "bana do", "banado", "bana doon", "bana de", "banaa",
    "kar do", "kardo", "karo", "theek hai", "thik hai", "thik h", "theek h",
    "sure", "ok", "okay", "bilkul", "start", "approve", "allow", "proceed",
    "go ahead", "chalo", "sahi hai",
)

NO_LEARNING = (
    "nahi", "cancel", "mat karo", "rehne do", "no", "stop", "chhod do",
    "mat banao", "dont", "don't", "reject",
)

# --- generic pending-step confirmation (predictive copilot) -----------
YES_ACTION = (
    "haan", "ha", "yes", "yep", "yeah", "kar do", "kardo", "karo", "likh do",
    "theek hai", "thik hai", "sure", "ok", "okay", "bilkul", "execute karo",
    "banao", "bana do", "banado", "banaa do", "chalo",
)

NO_ACTION = (
    "nahi", "cancel", "mat karo", "rehne do", "no", "stop", "chhod do",
)

# --- per-sentry confirmation words (unchanged from the original code) --
GUARDIAN_FIX_WORDS = (
    "haan", "batao", "fix", "solution", "theek", "copy", "kar do", "yes",
    "solve", "bataiye", "bata do",
)

HARDWARE_KILL_WORDS = ("haan", "close", "band", "kill", "hatao", "kar do", "yes", "theek hai")

DOWNLOAD_ORGANIZE_WORDS = ("organize", "move", "folder mein", "categorize", "shift")
DOWNLOAD_EXTRACT_WORDS = ("extract", "unzip", "khol do archive")
DOWNLOAD_OPEN_WORDS = ("open", "kholo", "haan", "khol do", "chalao", "dikhao", "yes")

EMAIL_OPEN_WORDS = ("inbox", "gmail", "kholo email", "open karo email", "browser")
EMAIL_READ_WORDS = ("haan", "sunao", "padho", "summary", "batao", "kya likha hai", "yes", "bataiye")

DOCTOR_INSTALL_WORDS = ("haan", "install", "kar do", "yes", "theek hai", "kardo")
DOCTOR_PORT_WORDS = ("haan", "port", "free", "kill", "clean", "kar do", "yes", "theek hai")

DESKTOP_OLD_WORDS = ("haan", "daal do", "yes", "trash", "hatao", "theek hai", "kar do")
DESKTOP_DUPLICATES_WORDS = ("haan", "duplicates hatao", "delete karo", "yes", "hatao", "theek hai", "kar do")

# --- destructive command confirmation (file delete / shutdown / restart)
EXECUTE_CONFIRM_WORDS = ("haan", "yes", "confirm", "pakka", "kar do")


def normalize(text: str) -> str:
    """Poora comparison lower-case par hota hai (pehle bhi yahi hota tha)."""
    return (text or "").lower()


def matches(text_lower: str, words: Iterable[str]) -> bool:
    """Substring match — 'haan' jaise word kahin bhi text me ho toh match."""
    return any(word in text_lower for word in words)


def contains_any(text: str, words: Iterable[str]) -> bool:
    """`matches()` ka `normalize()` + `matches()` convenience version."""
    return matches(normalize(text), words)