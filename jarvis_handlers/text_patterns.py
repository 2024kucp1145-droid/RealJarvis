# -*- coding: utf-8 -*-
"""
text_patterns.py
================
Voice-command parsing ke shared patterns aur vocabulary.

Ye sab pehle main.py ke module level par the — router, keyboard handlers aur
command dispatch sab inhe import karte the. Ab ek jagah hain taaki patterns
badalne se router aur keyboard handler dono ek hi truth se chalein.
"""

import re

GREETINGS = (
    "Main bilkul achhi hoon! Aap bataiye, aaj main aapki kya madad karoon?",
    "Haanji! Aapka din kaisa jaa raha hai? Bataiye kya hukum hai mere liye.",
    "Main bilkul theek hoon! Aapke saath kaam karke mujhe hamesha bahut achha lagta hai, bataiye kya karna hai.",
)

# Fixed command list me na mile, aur "X kholo"/"X open karo" jaisa pattern
# ho, toh X ko generic app-launcher se try karte hain - isse fixed list se
# bahar wale apps (Spotify, VS Code, WhatsApp, etc) bhi naam bol kar khul
# sakte hain.
OPEN_APP_PATTERN = re.compile(
    r"^(.*?)\s+(kholo|khol do|khol dijiye|open karo|open kar do|chalu karo|start karo|shuru karo)$",
    re.IGNORECASE,
)

# "ctrl c dabao" / "enter dabao" / "alt f4 dabao" - koi bhi key combination.
SHORTCUT_PATTERN = re.compile(
    r"^(.*?)\s+(dabao|dabaiye|dabaao|press karo|key dabao|button dabao)$",
    re.IGNORECASE,
)

KEY_ALIASES = {
    "control": "ctrl", "ctrl": "ctrl", "cntrl": "ctrl", "kantrol": "ctrl",
    "shift": "shift",
    "alt": "alt",
    "windows": "win", "win": "win",
    "enter": "enter", "return": "enter", "enter key": "enter",
    "space": "space", "spacebar": "space", "space bar": "space",
    "tab": "tab",
    "escape": "esc", "esc": "esc",
    "delete": "delete", "del": "delete",
    "backspace": "backspace",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "home": "home", "end": "end",
    "pageup": "pgup", "pagedown": "pgdn",
}

# "likhna shuru karo" ke baad jo bhi bolo wahi type hota hai - in phrases me
# se koi bhi bolne se dictation mode band ho jaata hai.
DICTATION_STOP_PHRASES = (
    "likhna band karo", "type band karo", "likhna band",
    "typing band karo", "dictation band karo", "bas likhna band",
)

# "so jao" / "bye jarvis" - inhe sunke bhi command_loop turant nahi toot-ta,
# pehle command handle hota hai (kuch commands me bhi "so jao" hota hai).
SLEEP_PHRASES = (
    "so jao", "sleep jarvis", "go to sleep", "bye jarvis",
    "alvida jarvis", "exit jarvis",
)

# Explicit screen-vision commands (on-demand screen monitor start karte hain)
EXPLICIT_VISUAL_KEYWORDS = (
    "screen par kya hai", "screen dekho", "meri screen dekho",
    "screen padho", "display par kya hai", "screen samjhao",
    "screen pe kya khula hai", "what is on my screen", "look at my screen",
)

# Jo "X kholo" match ho par woh app na ho — inhe app na samjhein
APP_NAME_STOPWORDS = (
    "game", "banao", "banakar", "create", "generate", "code", "runner", "surfer", "for",
)
APP_NAME_MAX_WORDS = 3

# File intake mode se bahar aane ke phrases
FILE_RELEASE_PHRASES = (
    "complete", "ho gaya", "done", "file band karo", "bahar nikaalo", "bas karo",
)