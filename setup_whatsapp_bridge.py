# -*- coding: utf-8 -*-
"""
setup_whatsapp_bridge.py  (v4 — Truly Invisible, No Popup, No Spam)
=====================================================================
- Chrome runs in HEADLESS mode = zero visible window, ever
- Messages processed EXACTLY once using data-id + text-hash dedup
- Jarvis's own replies never re-read (ID snapshot after every send)
- All bridge alerts (battery, etc.) also route through headless driver
"""

import sys
import os
import time
import threading
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Dependencies ───────────────────────────────────────────────────────────────
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        WebDriverException, StaleElementReferenceException, TimeoutException
    )
    from webdriver_manager.chrome import ChromeDriverManager
    import pyperclip
except ImportError as e:
    print(f"[JARVIS] Missing: {e}. Run: venv\\Scripts\\pip install selenium webdriver-manager pyperclip")
    sys.exit(1)

import whatsapp_mobile_bridge
bridge    = whatsapp_mobile_bridge.bridge
MY_PHONE  = bridge.master_phone          # "+917014093732"
CLEAN_PH  = MY_PHONE.replace("+", "")

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "chrome_whatsapp_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)

INPUT_CSS    = 'div[contenteditable="true"][data-tab="10"]'
ALL_MSGS_CSS = 'div[data-id]'
TEXT_CSS     = 'span.selectable-text span'

# ── Dedup state ────────────────────────────────────────────────────────────────
seen_ids      = set()   # data-id strings already handled
seen_hashes   = {}      # {text_hash: last_seen_epoch} — block exact-same text for 60s
_send_lock    = threading.Lock()
driver        = None

# ── Build HEADLESS Chrome (no window at all) ───────────────────────────────────
def build_driver():
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
    opts.add_argument("--profile-directory=Default")

    # ✅ HEADLESS = completely invisible
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1366,768")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    # Make headless look like real Chrome to avoid WhatsApp Web detection
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/127.0.0.0 Safari/537.36")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    svc = Service(ChromeDriverManager().install())
    drv = webdriver.Chrome(service=svc, options=opts)
    drv.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"}
    )
    return drv

# ── Send reply (no new windows, same driver) ───────────────────────────────────
def send_reply(text: str):
    global seen_ids
    with _send_lock:
        try:
            inp = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, INPUT_CSS))
            )
            inp.click()
            time.sleep(0.2)
            pyperclip.copy(text)
            inp.send_keys(Keys.CONTROL + 'v')
            time.sleep(0.3)
            inp.send_keys(Keys.ENTER)
            time.sleep(0.8)
            # ✅ ADD (not replace) new IDs so dedup set only grows
            seen_ids.update(_get_all_ids())
            safe = text[:80].encode('ascii', 'ignore').decode()
            print(f"[jarvis >> phone] {safe}...")
        except Exception as e:
            print(f"[send_reply error] {e}")

# ── Patch bridge's send so battery/email alerts also use this driver ───────────
bridge.send_whatsapp_message = lambda msg, phone=None: (
    threading.Thread(target=send_reply, args=(msg,), daemon=True).start() or True
)

# ── Get all current data-ids ───────────────────────────────────────────────────
def _get_all_ids():
    ids = set()
    try:
        for el in driver.find_elements(By.CSS_SELECTOR, ALL_MSGS_CSS):
            try:
                did = el.get_attribute("data-id")
                if did:
                    ids.add(did)
            except Exception:
                pass
    except Exception:
        pass
    return ids

# ── Extract text from bubble ───────────────────────────────────────────────────
def _bubble_text(bubble) -> str:
    try:
        spans = bubble.find_elements(By.CSS_SELECTOR, TEXT_CSS)
        t = " ".join(s.text.strip() for s in spans if s.text.strip())
        if t:
            return t
        for line in bubble.text.strip().split("\n"):
            if line.strip():
                return line.strip()
    except Exception:
        pass
    return ""

# ── Is this message a duplicate (same text within 60s)? ──────────────────────
def _is_duplicate_text(text: str) -> bool:
    h   = hashlib.md5(text.strip().lower().encode()).hexdigest()
    now = time.time()
    if h in seen_hashes and (now - seen_hashes[h]) < 60:
        return True
    seen_hashes[h] = now
    return False

# ── Polling loop ───────────────────────────────────────────────────────────────
def poll_loop():
    global seen_ids
    time.sleep(2)
    # Seed: ignore everything already in the chat
    seen_ids = _get_all_ids()
    print(f"[jarvis] {len(seen_ids)} old messages ignored.")
    print(f"[jarvis] WhatsApp bridge LIVE — send a message to yourself!\n")

    while True:
        try:
            bubbles = driver.find_elements(By.CSS_SELECTOR, ALL_MSGS_CSS)
            for bubble in bubbles[-30:]:
                try:
                    data_id = bubble.get_attribute("data-id")

                    # ── Skip if no id or already seen ─────────────────────
                    if not data_id or data_id in seen_ids:
                        continue

                    text = _bubble_text(bubble)

                    # ── Mark seen IMMEDIATELY to prevent double-processing ─
                    seen_ids.add(data_id)

                    if not text:
                        continue

                    # ── Skip Jarvis's own outgoing replies ─────────────────
                    # In self-chat, our OWN sent messages have "true_" prefix
                    # We only process messages that ARRIVED (sent from phone)
                    # Both sides are "true_" in self-chat, so we use text-hash
                    # dedup to ensure we never process the same text twice in 60s
                    if _is_duplicate_text(text):
                        continue

                    safe = text.encode('ascii', 'ignore').decode()
                    print(f"[phone >> jarvis] {safe}")

                    # ── Process & reply in background thread ───────────────
                    def handle(t=text):
                        try:
                            reply = bridge.process_incoming_command(
                                t.strip(), sender_phone=MY_PHONE
                            )
                        except Exception as ex:
                            reply = f"Error: {ex}"
                        if reply:
                            send_reply(reply)

                    threading.Thread(target=handle, daemon=True).start()

                except StaleElementReferenceException:
                    continue
                except Exception:
                    continue

        except WebDriverException as e:
            if "invalid session" in str(e).lower():
                print("[jarvis] Session lost. Restart bridge.")
                break
        except Exception as e:
            print(f"[poll error] {e}")

        time.sleep(2.5)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  JARVIS WhatsApp Bridge  (v4 — Headless, Silent)")
    print(f"  Phone: {MY_PHONE}")
    print("=" * 55)
    print("[1/3] Starting headless browser (NO window will open)...")

    driver = build_driver()

    print("[2/3] Connecting to WhatsApp Web...")
    print("      (First time only: switch to non-headless, scan QR, then back)")

    driver.get(f"https://web.whatsapp.com/send?phone={CLEAN_PH}")

    try:
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, INPUT_CSS))
        )
        print("[3/3] Connected! Bridge is ACTIVE — no window visible.\n")
    except TimeoutException:
        print()
        print("  ❌ WhatsApp Web login required (QR scan).")
        print("  Run this ONCE to scan QR:")
        print()
        print("  venv\\Scripts\\python.exe scan_qr_once.py")
        print()
        driver.quit()
        sys.exit(1)

    # Startup confirmation to phone
    send_reply("🤖 Jarvis online! Koi bhi command bhejo:\nstatus, screenshot, media play/pause, volume up/down, cmd: <command>, git commit, sleep, lock")

    try:
        poll_loop()
    except KeyboardInterrupt:
        print("\nStopped.")
        driver.quit()
