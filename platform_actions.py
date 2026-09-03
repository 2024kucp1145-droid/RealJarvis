# -*- coding: utf-8 -*-
"""
platform_actions.py
====================
Platform-Aware Smart Automation Engine.

Jo bhi platform ya website user ke saamne hai, us par ADAPT karke kaam karta hai.
YouTube => scroll, play, skip, search
Instagram => like, scroll feed, send reel
WhatsApp Web => send message, open chat, scroll
Twitter/X => like, retweet, scroll
Any site => scroll, click, type, read
"""

import re
import time
import pyautogui
import win32gui

try:
    import pyperclip
except ImportError:
    pyperclip = None

pyautogui.PAUSE = 0.15
pyautogui.FAILSAFE = True

def _get_active_window_title() -> str:
    try:
        hwnd = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(hwnd).lower()
    except Exception:
        return ""

def detect_platform() -> str:
    title = _get_active_window_title()
    if "youtube" in title:
        return "youtube"
    if "instagram" in title:
        return "instagram"
    if "whatsapp" in title:
        return "whatsapp"
    if "twitter" in title or "x.com" in title:
        return "twitter"
    if "facebook" in title or "fb.com" in title:
        return "facebook"
    if "reddit" in title:
        return "reddit"
    if "netflix" in title:
        return "netflix"
    if "spotify" in title:
        return "spotify"
    if any(b in title for b in ["chrome", "firefox", "edge", "opera", "brave", "browser"]):
        return "browser"
    return "unknown"

def get_platform_name_hindi(platform: str) -> str:
    names = {
        "youtube": "YouTube", "instagram": "Instagram", "whatsapp": "WhatsApp",
        "twitter": "Twitter", "facebook": "Facebook", "reddit": "Reddit",
        "netflix": "Netflix", "spotify": "Spotify", "browser": "Browser", "unknown": "current window",
    }
    return names.get(platform, platform)

def _type_text(text: str):
    if not text:
        return
    if pyperclip:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.1)
    else:
        pyautogui.write(text, interval=0.03)

class PlatformActions:
    @staticmethod
    def youtube_scroll_down():
        pyautogui.scroll(-600); return "YouTube pe neeche scroll kar diya."
    @staticmethod
    def youtube_scroll_up():
        pyautogui.scroll(600); return "YouTube pe upar scroll kar diya."
    @staticmethod
    def youtube_play_pause():
        pyautogui.press("k"); return "YouTube video play/pause kar diya."
    @staticmethod
    def youtube_next_video():
        pyautogui.hotkey("shift", "n"); return "Agla YouTube video chalu kar diya."
    @staticmethod
    def youtube_fullscreen():
        pyautogui.press("f"); return "Fullscreen toggle kar diya."
    @staticmethod
    def youtube_mute():
        pyautogui.press("m"); return "YouTube mute/unmute kar diya."
    @staticmethod
    def youtube_skip_forward():
        pyautogui.press("l"); return "YouTube video 10 second aage skip kar diya."
    @staticmethod
    def youtube_skip_backward():
        pyautogui.press("j"); return "YouTube video 10 second peeche gaya."
    @staticmethod
    def youtube_search(query: str):
        pyautogui.hotkey("ctrl", "l"); time.sleep(0.3)
        _type_text(f"youtube.com/results?search_query={query.replace(' ','+')}"); pyautogui.press("enter")
        return f"YouTube pe search kar diya."

    @staticmethod
    def instagram_scroll_down():
        pyautogui.scroll(-500); return "Instagram feed neeche scroll kar diya."
    @staticmethod
    def instagram_scroll_up():
        pyautogui.scroll(500); return "Instagram feed upar scroll kar diya."
    @staticmethod
    def instagram_like():
        screen_w, screen_h = pyautogui.size()
        pyautogui.doubleClick(screen_w // 2, screen_h // 2); return "Instagram post/reel like karne ki koshish ki."
    @staticmethod
    def instagram_next_reel():
        pyautogui.scroll(-800); time.sleep(0.3); return "Agla Instagram reel dikhaya."
    @staticmethod
    def instagram_open_dms():
        pyautogui.hotkey("ctrl", "l"); time.sleep(0.3)
        _type_text("instagram.com/direct/inbox/"); pyautogui.press("enter")
        return "Instagram DMs khol diya."

    @staticmethod
    def whatsapp_scroll_down():
        pyautogui.scroll(-400); return "WhatsApp neeche scroll kar diya."
    @staticmethod
    def whatsapp_scroll_up():
        pyautogui.scroll(400); return "WhatsApp upar scroll kar diya."
    @staticmethod
    def whatsapp_open_search():
        pyautogui.hotkey("ctrl", "f"); time.sleep(0.3); return "WhatsApp search khol diya."

    @staticmethod
    def twitter_scroll_down():
        pyautogui.scroll(-600); return "Twitter feed neeche scroll kar diya."
    @staticmethod
    def twitter_next_tweet():
        pyautogui.press("j"); return "Agla tweet."
    @staticmethod
    def twitter_like():
        pyautogui.press("l"); return "Tweet like kar diya."
    @staticmethod
    def twitter_new_tweet():
        pyautogui.press("n"); return "Naya tweet compose karne ke liye box khul gaya."

    @staticmethod
    def generic_scroll_down():
        pyautogui.scroll(-600); return "Neeche scroll kar diya."
    @staticmethod
    def generic_scroll_up():
        pyautogui.scroll(600); return "Upar scroll kar diya."
    @staticmethod
    def generic_page_top():
        pyautogui.hotkey("ctrl", "Home"); return "Page ke top pe aa gaye."
    @staticmethod
    def generic_page_bottom():
        pyautogui.hotkey("ctrl", "End"); return "Page ke end pe aa gaye."
    @staticmethod
    def generic_refresh():
        pyautogui.press("f5"); return "Page refresh kar diya."
    @staticmethod
    def generic_go_back():
        pyautogui.hotkey("alt", "left"); return "Wapas gaye."
    @staticmethod
    def generic_go_forward():
        pyautogui.hotkey("alt", "right"); return "Aage gaye."
    @staticmethod
    def generic_fullscreen():
        pyautogui.press("f11"); return "Fullscreen toggle kar diya."
    @staticmethod
    def generic_play_pause():
        pyautogui.press("space"); return "Play/pause kar diya."


INTENT_MAP = {
    "scroll_down": {
        "keywords": ["neeche scroll", "scroll down", "niche karo", "aage badho", "age badho",
                     "next karo", "neeche jao", "scroll karo", "next reel", "agla reel", "agla video"],
        "youtube": PlatformActions.youtube_scroll_down,
        "instagram": PlatformActions.instagram_scroll_down,
        "whatsapp": PlatformActions.whatsapp_scroll_down,
        "twitter": PlatformActions.twitter_scroll_down,
        "default": PlatformActions.generic_scroll_down,
    },
    "scroll_up": {
        "keywords": ["upar scroll", "scroll up", "upar jao", "peeche jao pichle", "upar karo"],
        "youtube": PlatformActions.youtube_scroll_up,
        "instagram": PlatformActions.instagram_scroll_up,
        "whatsapp": PlatformActions.whatsapp_scroll_up,
        "default": PlatformActions.generic_scroll_up,
    },
    "play_pause": {
        "keywords": ["play karo", "pause karo", "roko", "chalao", "resume karo"],
        "youtube": PlatformActions.youtube_play_pause,
        "netflix": PlatformActions.generic_play_pause,
        "spotify": PlatformActions.generic_play_pause,
        "default": PlatformActions.generic_play_pause,
    },
    "next": {
        "keywords": ["agla", "next video", "next song", "skip karo", "aage karo", "next"],
        "youtube": PlatformActions.youtube_next_video,
        "instagram": PlatformActions.instagram_next_reel,
        "twitter": PlatformActions.twitter_next_tweet,
        "default": PlatformActions.generic_scroll_down,
    },
    "like": {
        "keywords": ["like karo", "like kar do", "pasand karo", "heart dabao", "like this", "like"],
        "instagram": PlatformActions.instagram_like,
        "twitter": PlatformActions.twitter_like,
        "default": None,
    },
    "fullscreen": {
        "keywords": ["fullscreen karo", "bada karo", "poori screen", "full screen", "fullscreen"],
        "youtube": PlatformActions.youtube_fullscreen,
        "netflix": PlatformActions.youtube_fullscreen,
        "default": PlatformActions.generic_fullscreen,
    },
    "mute": {
        "keywords": ["mute karo", "awaaz band", "chup karo awaaz", "video mute"],
        "youtube": PlatformActions.youtube_mute,
        "default": None,
    },
    "skip_forward": {
        "keywords": ["aage skip", "skip forward", "10 second aage", "skip"],
        "youtube": PlatformActions.youtube_skip_forward,
        "default": PlatformActions.generic_go_forward,
    },
    "go_back": {
        "keywords": ["wapas jao", "back jao", "peeche jao", "back karo"],
        "default": PlatformActions.generic_go_back,
    },
    "refresh": {
        "keywords": ["refresh karo", "reload karo", "dobara kholo"],
        "default": PlatformActions.generic_refresh,
    },
    "page_top": {
        "keywords": ["top pe jao", "page ke upar", "shuruaat pe jao"],
        "default": PlatformActions.generic_page_top,
    },
    "page_bottom": {
        "keywords": ["end pe jao", "sabse neeche", "page ke neeche"],
        "default": PlatformActions.generic_page_bottom,
    },
    "open_dms": {
        "keywords": ["dm kholo", "direct message kholo", "inbox kholo", "messages kholo"],
        "instagram": PlatformActions.instagram_open_dms,
        "whatsapp": PlatformActions.whatsapp_open_search,
        "default": None,
    },
    "new_post": {
        "keywords": ["naya tweet", "naya post karo", "tweet karo"],
        "twitter": PlatformActions.twitter_new_tweet,
        "default": None,
    },
}


def route_platform_action(user_text: str, voice, ai=None) -> bool:
    """
    User ke bole hue command ko platform detect karke sahi action chalao.
    Returns True agar koi action execute hua.
    """
    text = user_text.lower().strip()
    platform = detect_platform()
    platform_name = get_platform_name_hindi(platform)

    matched_intent = None
    for intent, data in INTENT_MAP.items():
        if any(kw in text for kw in data["keywords"]):
            matched_intent = intent
            break

    if not matched_intent:
        return False

    data = INTENT_MAP[matched_intent]
    action_fn = data.get(platform) or data.get("default")

    if action_fn is None:
        if ai:
            voice.speak(f"{platform_name} pe ye kaam AI se kar rahi hoon...", emotion="calm")
            from web_control import execute_web_action
            execute_web_action(voice, ai, user_text)
            return True
        voice.speak(f"{platform_name} pe ye action directly nahi ho sakta.")
        return True

    try:
        result_msg = action_fn()
        voice.speak(result_msg, emotion="happy")
        return True
    except Exception as e:
        print(f"[platform_actions error: {e}]")
        if ai:
            voice.speak("Direct nahi hua, AI se try kar rahi hoon...", emotion="calm")
            from web_control import execute_web_action
            execute_web_action(voice, ai, user_text)
            return True
        return False


def get_current_platform_info() -> dict:
    platform = detect_platform()
    title = _get_active_window_title()
    return {"platform": platform, "window_title": title, "platform_name": get_platform_name_hindi(platform)}
