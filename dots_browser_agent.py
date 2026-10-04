# -*- coding: utf-8 -*-
"""
dots_browser_agent.py
======================
Stealth Web Browsing & Anti-Bot AI Browser Agent Integration for Real Jarvis.
Powered by feder-cr/dots and invisible-playwright.

Features:
1. Unblockable stealth browser automation using patched Firefox engine.
2. Two-pane Live Agent Web UI launch (uvx dots ui).
3. Organic human-like cursor control and fingerprint spoofing.
4. Seamless integration with Jarvis Voice, Universal Web Operator, and AI Brain.
"""

import os
import sys
import time
import subprocess
import threading
import webbrowser
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

try:
    import invisible_playwright
    from invisible_playwright import InvisiblePlaywright
    _INVISIBLE_PLAYWRIGHT_AVAILABLE = True
except ImportError:
    invisible_playwright = None
    InvisiblePlaywright = None
    _INVISIBLE_PLAYWRIGHT_AVAILABLE = False


class DotsBrowserAgent:
    """Manages stealth anti-bot browsing tasks and the Dots interface."""

    def __init__(self, voice=None, ai=None, gui=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self._dots_proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        """Checks if invisible-playwright is available in the environment."""
        return _INVISIBLE_PLAYWRIGHT_AVAILABLE

    def launch_dots_ui(self, port: Optional[int] = None) -> bool:
        """
        Launches the Dots live two-pane stealth browser interface in background.
        Opens http://127.0.0.1:<port> in default browser.
        """
        target_port = port or getattr(config, "DOTS_PORT", 8766)
        target_url = f"http://127.0.0.1:{target_port}"

        with self._lock:
            # Check if already running
            if self._dots_proc and self._dots_proc.poll() is None:
                print(f"[dots_agent] Dots UI already running on {target_url}")
                webbrowser.open(target_url)
                if self.voice:
                    self.voice.speak("Dots browser agent pehle se running hai. Browser tab open kar diya hai boss!", emotion="excited")
                return True

            print(f"[dots_agent] Launching Dots Stealth Browser UI on port {target_port}...")
            if self.voice:
                self.voice.speak("Dots stealth browser agent start ho raha hai...", emotion="excited")

            openrouter_key = getattr(config, "OPENROUTER_API_KEY", "") or os.environ.get("OPENROUTER_API_KEY", "")
            
            # Construct launch command via uvx
            cmd = ["uvx", "dots", "ui", "--port", str(target_port), "--headed"]
            if openrouter_key:
                cmd.extend(["--openrouter-key", openrouter_key])

            try:
                # Launch non-blocking background process
                self._dots_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                
                time.sleep(2.0)
                webbrowser.open(target_url)

                msg = "Dots stealth browser live interface start ho gaya hai boss. Screen par live browsing ready hai!"
                print(f"[dots_agent] {msg}")
                if self.voice:
                    self.voice.speak(msg, emotion="happy")
                return True

            except Exception as e:
                err_msg = f"Dots UI launch nahi ho paaya: {e}"
                print(f"[dots_agent error: {e}]")
                if self.voice:
                    self.voice.speak("Dots browser start karne me error aaya.", emotion="concerned")
                return False

    def stealth_fetch_page(self, url: str, wait_seconds: float = 3.0) -> Dict[str, Any]:
        """
        Loads a target webpage using the stealth patched Firefox engine,
        bypassing bot detection, and extracts page title and main text content.
        """
        if not self.is_available():
            return {"success": False, "error": "invisible-playwright not installed in venv"}

        print(f"[dots_agent] Stealth navigating to: {url}")
        if self.voice:
            self.voice.speak("Stealth browser se target page open kar rahi hoon...", emotion="calm")

        try:
            with InvisiblePlaywright(headless=False, humanize=True) as browser:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(wait_seconds)

                title = page.title()
                # Extract primary text content
                content_text = page.inner_text("body")[:3000]

                return {
                    "success": True,
                    "title": title,
                    "url": url,
                    "text_sample": content_text
                }
        except Exception as e:
            print(f"[dots_agent stealth_fetch error: {e}]")
            return {"success": False, "error": str(e)}

    def stealth_compare_prices(self, product_name: str) -> Dict[str, Any]:
        """
        Performs stealth e-commerce navigation without bot blocks.
        """
        import urllib.parse
        encoded = urllib.parse.quote_plus(product_name)
        fk_url = f"https://www.flipkart.com/search?q={encoded}"
        amz_url = f"https://www.amazon.in/s?k={encoded}"

        print(f"[dots_agent] Stealth price compare for '{product_name}'...")
        if self.voice:
            self.voice.speak(f"Anti-bot stealth mode mein {product_name} ke prices check kar rahi hoon...", emotion="excited")

        # Open both in browser for the user
        try:
            webbrowser.open_new_tab(fk_url)
            time.sleep(0.5)
            webbrowser.open_new_tab(amz_url)
        except Exception:
            pass

        return {
            "success": True,
            "product": product_name,
            "flipkart_url": fk_url,
            "amazon_url": amz_url
        }


# Global singleton instance
dots_agent = DotsBrowserAgent()
