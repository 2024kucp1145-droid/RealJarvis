# -*- coding: utf-8 -*-
"""
dots_browser_agent.py
======================
Stealth Web Browsing & Anti-Bot AI Browser Agent Integration for Real Jarvis.
Powered by feder-cr/dots and invisible-playwright.

Features:
1. Native, unblockable stealth browser launch (Patched C++ Firefox engine).
2. Works directly without needing an OpenRouter API key or local port servers.
3. Automatically powers normal commands: browser kholo, google search, website navigation.
4. Seamless fallback to default system browser if required.
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
    from invisible_playwright import InvisiblePlaywright, ensure_binary
    _INVISIBLE_PLAYWRIGHT_AVAILABLE = True
except ImportError:
    invisible_playwright = None
    InvisiblePlaywright = None
    ensure_binary = None
    _INVISIBLE_PLAYWRIGHT_AVAILABLE = False


class DotsBrowserAgent:
    """Manages stealth anti-bot browsing tasks and browser windows."""

    def __init__(self, voice=None, ai=None, gui=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self._bin_path: Optional[str] = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        """Checks if invisible-playwright is available in the environment."""
        return _INVISIBLE_PLAYWRIGHT_AVAILABLE

    def get_binary_path(self) -> Optional[str]:
        """Resolves the patched anti-detect Firefox executable path."""
        if self._bin_path and os.path.exists(self._bin_path):
            return self._bin_path
        if ensure_binary:
            try:
                self._bin_path = ensure_binary()
                return self._bin_path
            except Exception as e:
                print(f"[dots_agent get_binary_path error: {e}]")
        return None

    def launch_browser(self, url: str = "https://www.google.com") -> bool:
        """
        Launches the native stealth anti-detect Firefox browser directly.
        Opens the browser window cleanly on screen with zero port errors.
        """
        bin_path = self.get_binary_path()
        target_url = url if url.startswith("http") else f"https://{url}"

        if not bin_path or not os.path.exists(bin_path):
            print(f"[dots_agent] Stealth binary not found, using default browser for {target_url}")
            webbrowser.open(target_url)
            if self.voice:
                self.voice.speak("Browser khol diya hai boss.", emotion="happy")
            return True

        try:
            print(f"[dots_agent] Launching native stealth anti-bot browser: {target_url}")
            subprocess.Popen([bin_path, target_url])
            if self.voice:
                self.voice.speak("Anti-bot browser open kar diya hai boss.", emotion="happy")
            return True
        except Exception as e:
            print(f"[dots_agent direct launch error: {e}], falling back to system browser")
            webbrowser.open(target_url)
            if self.voice:
                self.voice.speak("Browser khol diya hai.", emotion="calm")
            return True

    def search(self, query: str) -> bool:
        """Searches Google directly inside the stealth browser."""
        import urllib.parse
        encoded = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?q={encoded}"
        return self.launch_browser(search_url)

    def open_website(self, site: str) -> bool:
        """Opens any website URL inside the stealth browser."""
        url = site if site.startswith("http") else f"https://{site}"
        return self.launch_browser(url)

    def stealth_fetch_page(self, url: str, wait_seconds: float = 3.0) -> Dict[str, Any]:
        """
        Background autonomous page scraper: loads page with stealth engine
        and extracts title and main text content without bot challenges.
        """
        if not self.is_available() or InvisiblePlaywright is None:
            return {"success": False, "error": "invisible-playwright not installed in venv"}

        print(f"[dots_agent] Background stealth navigating to: {url}")
        try:
            with InvisiblePlaywright(headless=False, humanize=True) as browser:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(wait_seconds)

                title = page.title()
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
            self.voice.speak(f"{product_name} ke prices check kar rahi hoon...", emotion="excited")

        bin_path = self.get_binary_path()
        if bin_path and os.path.exists(bin_path):
            try:
                subprocess.Popen([bin_path, fk_url])
                time.sleep(0.5)
                subprocess.Popen([bin_path, amz_url])
            except Exception:
                webbrowser.open_new_tab(fk_url)
                webbrowser.open_new_tab(amz_url)
        else:
            webbrowser.open_new_tab(fk_url)
            webbrowser.open_new_tab(amz_url)

        return {
            "success": True,
            "product": product_name,
            "flipkart_url": fk_url,
            "amazon_url": amz_url
        }


# Global singleton instance
dots_agent = DotsBrowserAgent()
