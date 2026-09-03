# -*- coding: utf-8 -*-
"""
browser_commands.py
====================
Browser, Google search, aur YouTube gaana play karna - sab bina touch ke.
Ye sab actions ONLINE hai, isliye pehle internet check hota hai.
"""
from urllib.parse import quote
import webbrowser
from voice import has_internet


def _need_internet(voice) -> bool:
    if not has_internet():
        voice.speak("Network nahi hai. Internet connect kijiye phir try karti hoon.")
        return False
    return True


def open_browser(voice, **kw):
    if not _need_internet(voice):
        return
    webbrowser.open("https://www.google.com")
    voice.speak("Browser khol diya.")


def open_website(voice, site="", **kw):
    if not _need_internet(voice):
        return
    if not site:
        voice.speak("Konsi website kholu, batayein?")
        return
    url = site if site.startswith("http") else f"https://{site}"
    webbrowser.open(url)
    voice.speak(f"{site} khol rahi hoon.")


def search_google(voice, query="", **kw):
    if not _need_internet(voice):
        return
    if not query:
        voice.speak("Kya search karu?")
        return
    webbrowser.open(f"https://www.google.com/search?q={quote(query)}")
    voice.speak(f"{query} search kar rahi hoon.")


def play_youtube(voice, song="", **kw):
    """
    pywhatkit.playonyt seedha YouTube pe search karke top result
    autoplay kar deta hai - bilkul jaisa maanga tha: "bina chuye gaana khud play ho jaye"
    """
    if not _need_internet(voice):
        return
    if not song:
        voice.speak("Konsa gaana chalau?")
        return
    try:
        import pywhatkit
        voice.speak(f"{song} chala rahi hoon.")
        pywhatkit.playonyt(song)
    except Exception:
        # fallback: seedha YouTube search results khol do
        webbrowser.open(f"https://www.youtube.com/results?search_query={quote(song)}")
        voice.speak(f"{song} YouTube pe search kar diya.")


def leetcode_search(voice, query="", **kw):
    if not _need_internet(voice):
        return
    if not query:
        voice.speak("Konsi problem dhoondu?")
        return

    webbrowser.open(f"https://leetcode.com/problemset/?search={quote(query)}")
    voice.speak(f"LeetCode pe {query} dhoond rahi hoon.")


def run_web_agent(voice, ai=None, goal="", **kw):
    """Multi-step hands-free browser automation agent."""
    if not _need_internet(voice):
        return
    import web_control
    if not goal:
        voice.speak("Browser pe kya kaam karna hai, batayein?")
        return
    web_control.run_autonomous_web_task(voice, ai, goal)


def extract_info(voice, ai=None, query="", **kw):
    """Extract specific details like dates, contacts from current webpage."""
    if not _need_internet(voice):
        return
    import web_control
    web_control.extract_screen_info(voice, ai, query)


def stop_agent(voice, **kw):
    """Emergency stop browser automation."""
    import web_control
    web_control.stop_autonomous_agent()
    voice.speak("Browser automation rok diya gaya hai.")

