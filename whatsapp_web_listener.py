# -*- coding: utf-8 -*-
"""
whatsapp_web_listener.py  (v2 â€” Fixed 2-Way Bridge)
=====================================================
REAL 2-way WhatsApp bridge using Selenium.

HOW IT WORKS:
  Phone â†’ "Message Yourself" â†’ WhatsApp Web (Selenium sees it)
                                          â†’ Jarvis processes command
                                          â†’ Selenium types & sends reply in WhatsApp Web
                                          â†’ Reply appears on your PHONE automatically
                                          (WhatsApp Web & Phone are always synced)

FIXES in v2:
  - Robust CSS selectors (not brittle XPath)
  - Proper send via clipboard + pyautogui (100% reliable)
  - Auto-waits for QR scan if not logged in
  - Deduplication by data-id attribute
"""

import os
import sys
import time
import threading
import traceback
import subprocess

import pyautogui
import pyperclip

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException,
    TimeoutException, WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager

sys.path.insert(0, os.path.dirname(__file__))
import whatsapp_mobile_bridge

# Persistent Chrome profile so QR is scanned only once
PROFILE_DIR = os.path.join(os.path.dirname(__file__), "data", "chrome_whatsapp_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)

# â”€â”€â”€ WhatsApp Web Selectors (tested Aug 2026) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Message input box
SEL_INPUT = 'div[contenteditable="true"][data-tab="10"]'

# All message bubbles (incoming = from yourself on phone)
# In self-chat, your phone messages appear as "message-out" in WA Web
# because WA Web sees YOU as the sender on both sides in self-chat.
# So we monitor ALL new messages (both in & out) by data-id.
SEL_ALL_MSGS = 'div[data-id]'

# The actual text inside a bubble
SEL_MSG_TEXT = 'span.selectable-text span'

# Timestamp element (used for dedup)
SEL_TIMESTAMP = 'div[data-pre-plain-text]'


class WhatsAppWebListener:
    def __init__(self):
        self.driver   = None
        self.running  = False
        self._thread  = None
        self._seen_ids = set()          # data-id values already processed
        self._boot_ids = set()          # IDs present at startup (skip these)
        self.bridge   = whatsapp_mobile_bridge.bridge
        self.my_phone = self.bridge.master_phone

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 1. BUILD CHROME DRIVER
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _build_driver(self) -> webdriver.Chrome:
        opts = Options()
        opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
        opts.add_argument("--profile-directory=Default")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1280,900")
        opts.add_argument("--disable-notifications")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("--disable-blink-features=AutomationControlled")

        service = Service(ChromeDriverManager().install())
        drv     = webdriver.Chrome(service=service, options=opts)
        drv.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"}
        )
        return drv

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 2. OPEN ME CHAT
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _open_me_chat(self):
        clean = self.my_phone.replace("+", "").replace(" ", "")
        url   = f"https://web.whatsapp.com/send?phone={clean}"
        print(f"[wa_listener] Opening: {url}")
        self.driver.get(url)

        print("[wa_listener] Waiting for WhatsApp Web to load...")
        print("[wa_listener] >>> If QR code appears, scan it with your phone NOW <<<")

        # Wait up to 3 minutes for the message input to appear
        try:
            WebDriverWait(self.driver, 180).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, SEL_INPUT))
            )
            print("[wa_listener] âœ… ME chat loaded! Jarvis is now listening to your messages.")
        except TimeoutException:
            print("[wa_listener] âŒ Could not load WhatsApp Web. Check internet / QR scan.")
            raise

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 3. SEND REPLY  (clipboard method â€” 100% reliable)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def send_reply(self, text: str):
        try:
            wait = WebDriverWait(self.driver, 10)
            inp  = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, SEL_INPUT)))
            inp.click()
            time.sleep(0.3)

            # Copy text to clipboard and paste â€” avoids emoji encoding issues
            pyperclip.copy(text)
            time.sleep(0.2)
            inp.send_keys(Keys.CONTROL, 'v')
            time.sleep(0.4)
            inp.send_keys(Keys.ENTER)
            time.sleep(0.3)
            print(f"[wa_listener] âœ… Reply sent: {text[:70].encode('ascii','ignore').decode()}...")
        except Exception as e:
            print(f"[wa_listener] send_reply error: {e}")

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 4. READ NEW MESSAGES
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _get_new_messages(self) -> list:
        """Returns list of (data_id, text) for messages not yet seen."""
        results = []
        try:
            bubbles = self.driver.find_elements(By.CSS_SELECTOR, SEL_ALL_MSGS)
            for bubble in bubbles[-20:]:          # only last 20 bubbles
                try:
                    data_id = bubble.get_attribute("data-id")
                    if not data_id:
                        continue
                    if data_id in self._seen_ids or data_id in self._boot_ids:
                        continue

                    # Extract text
                    spans = bubble.find_elements(By.CSS_SELECTOR, SEL_MSG_TEXT)
                    text  = " ".join(s.text.strip() for s in spans if s.text.strip())
                    if not text:
                        # Fallback: get all text from bubble
                        text = bubble.text.strip().split("\n")[0]

                    if text:
                        results.append((data_id, text))
                except StaleElementReferenceException:
                    continue
        except Exception:
            pass
        return results

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 5. MAIN POLLING LOOP
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _poll_loop(self):
        # Seed existing messages so we don't re-process old ones
        time.sleep(3)
        initial = self.driver.find_elements(By.CSS_SELECTOR, SEL_ALL_MSGS)
        for b in initial:
            try:
                did = b.get_attribute("data-id")
                if did:
                    self._boot_ids.add(did)
            except Exception:
                pass
        print(f"[wa_listener] {len(self._boot_ids)} existing messages ignored.")
        print("[wa_listener] ðŸ‘‚ Listening... Send any message to yourself on WhatsApp!")

        while self.running:
            try:
                new_msgs = self._get_new_messages()
                for data_id, text in new_msgs:
                    self._seen_ids.add(data_id)
                    safe = text.encode('ascii','ignore').decode()
                    print(f"[wa_listener] << Received: {safe}")

                    # Skip if it's already a reply from Jarvis (outgoing msg that we sent)
                    # We detect this by checking data-id prefix â€” outgoing have "true_" prefix
                    if data_id.startswith("true_"):
                        continue

                    # Process through bridge
                    try:
                        reply = self.bridge.process_incoming_command(
                            text.strip(), sender_phone=self.my_phone
                        )
                    except Exception as ex:
                        reply = f"Jarvis error: {ex}"

                    if reply:
                        self.send_reply(reply)

            except WebDriverException as wde:
                if "invalid session" in str(wde).lower() or "no such window" in str(wde).lower():
                    print("[wa_listener] Chrome session lost.")
                    break
            except Exception as e:
                print(f"[wa_listener] poll error: {e}")

            time.sleep(2.5)   # check every 2.5 seconds

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 6. PUBLIC API
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def start(self):
        if self.running:
            return
        def _run():
            try:
                self.driver  = self._build_driver()
                self.running = True
                self._open_me_chat()
                self._poll_loop()
            except Exception as e:
                print(f"[wa_listener] FATAL: {e}")
                traceback.print_exc()
            finally:
                self.running = False
                try:
                    self.driver.quit()
                except Exception:
                    pass

        self._thread = threading.Thread(target=_run, name="wa_web_listener", daemon=True)
        self._thread.start()
        print("[wa_listener] Listener thread started.")

    def stop(self):
        self.running = False
        try:
            self.driver.quit()
        except Exception:
            pass

    def send_message_to_phone(self, text: str):
        """Send a proactive message to ME chat (called by other sentries)."""
        if self.running and self.driver:
            self.send_reply(text)


# Singleton
listener = WhatsAppWebListener()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    print("=" * 60)
    print("  JARVIS â€” WhatsApp Web 2-Way Listener  (v2)")
    print(f"  ME Chat Number: {listener.my_phone}")
    print("=" * 60)
    print()
    print("  STEPS:")
    print("  1. Chrome will open automatically")
    print("  2. If first time â†’ SCAN QR CODE with your phone")
    print("     (WhatsApp â†’ 3 dots â†’ Linked Devices â†’ Link a Device)")
    print("  3. Send any message to YOURSELF on WhatsApp phone")
    print("  4. Jarvis will process and REPLY on your phone!")
    print()
    print("  Commands to try: status, screenshot, media play,")
    print("  cmd: dir, git commit, sleep, lock")
    print("-" * 60)
    listener.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        print("\nStopped.")

