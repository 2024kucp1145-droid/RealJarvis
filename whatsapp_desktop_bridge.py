# -*- coding: utf-8 -*-
"""
whatsapp_desktop_bridge.py  (v1 â€” 100% Chrome-Free)
=====================================================
Reads messages from WhatsApp Desktop app via Windows Notification DB.
Sends replies by typing directly into WhatsApp Desktop app window.

Architecture:
  Phone sends message
    â†’ WhatsApp Desktop shows notification
    â†’ Windows stores it in wpndatabase.db (SQLite)
    â†’ This script polls DB every 2.5s for new WA notifications
    â†’ Extracts message text from notification XML payload
    â†’ Processes command via whatsapp_mobile_bridge
    â†’ Sends reply by keyboard-typing into WhatsApp Desktop app
    â†’ Reply appears on your phone (same WA account)

NO Chrome. NO Selenium. NO new windows. EVER.
"""

import os
import sys
import time
import shutil
import sqlite3
import hashlib
import tempfile
import threading
import subprocess
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import whatsapp_mobile_bridge

try:
    import pyperclip
    import pyautogui
    import pygetwindow as gw
except ImportError:
    pass  # handled at runtime

# â”€â”€ Config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
NOTIF_DB      = os.path.expandvars(
    r'%LOCALAPPDATA%\Microsoft\Windows\Notifications\wpndatabase.db')
WA_HANDLER_ID = 170          # WhatsApp Desktop's handler row ID in DB (discovered)
MY_PHONE      = "YOUR_PHONE_NUMBER"
POLL_INTERVAL = 2.5          # seconds between DB polls

bridge = whatsapp_mobile_bridge.bridge

# â”€â”€ Dedup State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_seen_notif_ids  = set()     # DB notification IDs already processed
_seen_text_hash  = {}        # {md5: last_epoch} â€” block same text for 60s
_last_notif_id   = 0         # highest notification ID seen so far
_send_lock       = threading.Lock()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 1. READ MESSAGES FROM WINDOWS NOTIFICATION DB
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _read_db_safe() -> list[tuple]:
    """
    Returns list of (notif_id, text) for new WhatsApp notifications.
    Copies DB to temp file first since wpndatabase.db is locked by OS.
    """
    global _last_notif_id
    results = []
    tmp = None
    try:
        tmp = tempfile.mktemp(suffix='.db')
        shutil.copy2(NOTIF_DB, tmp)

        conn = sqlite3.connect(tmp)
        cur  = conn.cursor()
        cur.execute(
            "SELECT Id, Payload FROM Notification "
            "WHERE HandlerId = ? AND Id > ? "
            "ORDER BY Id ASC",
            (WA_HANDLER_ID, _last_notif_id)
        )
        rows = cur.fetchall()
        conn.close()

        for notif_id, payload in rows:
            if notif_id in _seen_notif_ids:
                continue
            _last_notif_id = max(_last_notif_id, notif_id)
            text = _extract_text_from_payload(payload)
            if text:
                results.append((notif_id, text))

    except Exception as e:
        pass   # DB might be temporarily locked â€” skip this poll cycle
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except Exception:
                pass
    return results


def _extract_text_from_payload(payload) -> str:
    """Parse XML notification payload and return message body text."""
    if not payload:
        return ""
    try:
        # payload may be bytes or str
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode('utf-8', errors='replace')

        root  = ET.fromstring(payload)
        texts = []
        for el in root.iter():
            t = (el.text or "").strip()
            if t and t not in ("You may have new messages", "WhatsApp"):
                texts.append(t)
        return " | ".join(texts) if texts else ""
    except Exception:
        return str(payload)[:200]


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 2. SEND REPLY VIA WHATSAPP DESKTOP APP
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _find_whatsapp_window():
    """Returns the WhatsApp Desktop window or None."""
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle("WhatsApp")
        if wins:
            return wins[0]
    except Exception:
        pass
    return None


def send_reply_via_desktop(text: str) -> bool:
    """
    Types `text` into the WhatsApp Desktop app and presses Enter.
    The window is briefly brought to front, message sent, then minimized again.
    """
    with _send_lock:
        wa_win = _find_whatsapp_window()
        if not wa_win:
            # WhatsApp Desktop not running â€” launch it
            try:
                wa_exe = os.path.expandvars(r'%LOCALAPPDATA%\WhatsApp\WhatsApp.exe')
                if not os.path.exists(wa_exe):
                    # Microsoft Store version
                    subprocess.Popen(
                        'explorer.exe shell:appsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App',
                        shell=True
                    )
                else:
                    subprocess.Popen([wa_exe])
                time.sleep(4)
                wa_win = _find_whatsapp_window()
            except Exception as e:
                print(f"[wa_desktop] Could not launch WhatsApp: {e}")
                return False

        if not wa_win:
            print("[wa_desktop] WhatsApp window not found.")
            return False

        try:
            was_minimized = wa_win.isMinimized

            # Bring to front briefly
            wa_win.restore()
            wa_win.activate()
            time.sleep(0.5)

            # Paste reply into message box
            pyperclip.copy(text)
            import pyautogui
            # Click roughly in the message input area (bottom of window)
            left  = wa_win.left
            top   = wa_win.top
            width = wa_win.width
            height= wa_win.height
            # Message input is at ~bottom 8% of window
            click_x = left + width // 2
            click_y = top  + int(height * 0.93)
            pyautogui.click(click_x, click_y)
            time.sleep(0.3)

            # Paste and send
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(0.4)

            # Restore minimized state
            if was_minimized:
                wa_win.minimize()

            safe = text[:70].encode('ascii', 'ignore').decode()
            print(f"[jarvis >> phone] {safe}...")
            return True

        except Exception as e:
            print(f"[wa_desktop] send_reply error: {e}")
            return False


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 3. DEDUP HELPERS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _is_duplicate(notif_id: int, text: str) -> bool:
    """Returns True if this message was already processed."""
    if notif_id in _seen_notif_ids:
        return True
    h   = hashlib.md5(text.strip().lower().encode('utf-8', errors='replace')).hexdigest()
    now = time.time()
    if h in _seen_text_hash and (now - _seen_text_hash[h]) < 60:
        return True   # same text within 60 seconds â€” skip
    _seen_text_hash[h] = now
    return False


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 4. PATCH BRIDGE'S SEND SO ALL ALERTS USE DESKTOP APP
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _patched_send(message: str, phone: str = None) -> bool:
    threading.Thread(
        target=send_reply_via_desktop, args=(message,), daemon=True
    ).start()
    return True

bridge.send_whatsapp_message = _patched_send


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 5. MAIN POLL LOOP
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _poll_loop():
    global _last_notif_id

    # Seed _last_notif_id to current max so we skip old notifications
    try:
        tmp = tempfile.mktemp(suffix='.db')
        shutil.copy2(NOTIF_DB, tmp)
        conn = sqlite3.connect(tmp)
        cur  = conn.cursor()
        cur.execute("SELECT MAX(Id) FROM Notification WHERE HandlerId = ?", (WA_HANDLER_ID,))
        row = cur.fetchone()
        if row and row[0]:
            _last_notif_id = row[0]
        conn.close()
        os.unlink(tmp)
    except Exception:
        pass

    print(f"[wa_desktop] Bridge ACTIVE â€” no Chrome, no popups.")
    print(f"[wa_desktop] Listening on WhatsApp Desktop (last notif ID: {_last_notif_id})")
    print(f"[wa_desktop] Send a message to yourself on WhatsApp!\n")

    while True:
        new_msgs = _read_db_safe()
        for notif_id, text in new_msgs:
            if _is_duplicate(notif_id, text):
                _seen_notif_ids.add(notif_id)
                continue

            _seen_notif_ids.add(notif_id)
            safe = text.encode('ascii', 'ignore').decode()
            print(f"[phone >> jarvis] {safe}")

            # Process in background thread â€” no spam because dedup already applied
            def handle(t=text):
                try:
                    reply = bridge.process_incoming_command(
                        t.strip(), sender_phone=MY_PHONE
                    )
                except Exception as ex:
                    reply = f"Error: {ex}"
                if reply:
                    send_reply_via_desktop(reply)

            threading.Thread(target=handle, daemon=True).start()

        time.sleep(POLL_INTERVAL)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 6. PUBLIC API (for main.py integration)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class WhatsAppDesktopBridge:
    def __init__(self):
        self._thread = None
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(
            target=_poll_loop, name="wa_desktop_bridge", daemon=True
        )
        self._thread.start()
        print("[wa_desktop] Bridge thread started.")

    def stop(self):
        self.running = False


desktop_bridge = WhatsAppDesktopBridge()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    # Check dependencies
    missing = []
    for pkg in ("pyperclip", "pyautogui", "pygetwindow"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Install missing packages: venv\\Scripts\\pip install {' '.join(missing)}")
        sys.exit(1)

    print("=" * 55)
    print("  JARVIS WhatsApp Desktop Bridge  (No Chrome!)")
    print(f"  Phone: {MY_PHONE}")
    print("=" * 55)
    print()
    print("  Make sure WhatsApp Desktop is open (or minimized).")
    print("  Send any message to YOURSELF on WhatsApp phone.")
    print("  Jarvis will reply directly through WhatsApp Desktop.")
    print()
    print("  Commands: status, screenshot, media play/pause,")
    print("            volume up/down, cmd: <shell>, git commit,")
    print("            sleep, lock, wol setup")
    print("-" * 55)

    desktop_bridge.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")

