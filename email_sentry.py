# -*- coding: utf-8 -*-
"""
email_sentry.py
================
Phase 5: Urgent Email & Critical Alert Sentry.

Features:
1. Real-time background IMAP watcher for unread emails.
2. AI-powered urgency & priority classification (filters out spam/promotions).
3. Proactive voice heads-up for critical emails (College deadlines, Interviews, Bank alerts).
4. 1-word voice actions:
   - "haan sunao" / "padho" -> Reads 2-sentence concise AI summary.
   - "inbox kholo" / "open karo" -> Opens Gmail web in browser.
"""

import re
import time
import email
import imaplib
import threading
import datetime
import webbrowser
from email.header import decode_header

import config

# Quick spam/promotional blacklist keywords to bypass AI calls for obvious newsletters
PROMOTIONAL_KEYWORDS = [
    "unsubscribe", "sale", "discount", "off your next", "limited time offer",
    "newsletter", "promotional", "terms and conditions apply", "no-reply@swiggy",
    "no-reply@zomato", "marketing", "deals of the day"
]


class EmailSentry:
    def __init__(self, voice=None, ai=None, gui=None, speak_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        self.running = False
        self._thread = None
        self.enabled = True

        self._seen_email_ids = set()
        self._pending_email = None  # { 'id': str, 'sender': str, 'subject': str, 'summary': str, 'timestamp': datetime }
        self._lock = threading.Lock()

    def start(self, voice=None, ai=None, gui=None, speak_fn=None):
        if voice:
            self.voice = voice
        if ai:
            self.ai = ai
        if gui:
            self.gui = gui
        if speak_fn:
            self.speak_fn = speak_fn

        if self.running or not getattr(config, "EMAIL_ENABLED", False) or not getattr(config, "EMAIL_APP_PASSWORD", None):
            return

        # Baseline snapshot of current unseen emails so we only alert on genuinely NEW arrivals
        self._init_baseline_unseen()

        self.running = True
        self._thread = threading.Thread(target=self._sentry_loop, daemon=True)
        self._thread.start()
        print("[email_sentry] Urgent Email & Critical Alert Sentry started.")

    def stop(self):
        self.running = False

    def _decode_str(self, val):
        if val is None:
            return ""
        try:
            parts = decode_header(val)
            out = ""
            for text, enc in parts:
                out += text.decode(enc or "utf-8", errors="replace") if isinstance(text, bytes) else str(text)
            return out
        except Exception:
            return str(val)

    def _init_baseline_unseen(self):
        try:
            imap = imaplib.IMAP4_SSL(config.IMAP_SERVER)
            imap.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
            imap.select("inbox")
            _, data = imap.search(None, "UNSEEN")
            if data and data[0]:
                self._seen_email_ids = set(data[0].split())
            imap.logout()
        except Exception as e:
            print(f"[email_sentry baseline error: {e}]")

    def _speak_alert(self, message: str, emotion: str = "happy", priority: str = "normal"):
        """Thread-safe proactive speech alert."""
        try:
            import workspace_harmonizer
            if not workspace_harmonizer.harmonizer.can_speak_proactively(priority=priority):
                return
        except Exception:
            pass
        try:
            if self.speak_fn:
                self.speak_fn(message, emotion=emotion)
            elif self.voice:
                self.voice.speak(message, interruptible=True, emotion=emotion)
        except Exception as e:
            print(f"[email_sentry alert error: {e}]")

    def _extract_body_text(self, msg_obj) -> str:
        body = ""
        try:
            if msg_obj.is_multipart():
                for part in msg_obj.walk():
                    ctype = part.get_content_type()
                    cdispo = str(part.get("Content-Disposition"))
                    if ctype == "text/plain" and "attachment" not in cdispo:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode("utf-8", errors="replace") + " "
            else:
                payload = msg_obj.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="replace")
        except Exception:
            pass
        return body.strip()

    def _classify_and_summarize(self, sender: str, subject: str, body: str) -> tuple:
        """Uses AI to determine if email is URGENT/IMPORTANT and generate 2-sentence summary."""
        # Fast rule check for obvious promotions
        comb = (sender + " " + subject + " " + body[:300]).lower()
        if any(kw in comb for kw in PROMOTIONAL_KEYWORDS):
            return False, ""

        if not self.ai or not self.ai.available():
            # Fallback heuristic
            urgent_keywords = ["exam", "deadline", "interview", "assessment", "urgent", "important", "alert", "notice", "iiit", "college"]
            is_urg = any(k in comb for k in urgent_keywords)
            return is_urg, f"{sender} se subject '{subject}' par email aayi hai."

        prompt = f"""Tum ek executive email classifier ho.
User ko ye email aayi hai:

SENDER: {sender}
SUBJECT: {subject}
BODY SNIPPET:
{body[:700]}

Batao:
1. Kya ye email URGENT ya IMPORTANT hai (College/Exam/Assignment/Job/Interview/Banking/Security alert)? (Promotions, news, marketing, generic newsletters are NOT urgent)
2. Agar urgent hai, toh 1-2 sentence ka simple spoken Hinglish summary do.

FORMAT EXACTLY LIKE THIS:
IS_URGENT: YES ya NO
SUMMARY: [2-sentence summary in Hinglish]"""

        try:
            res, _ = self.ai.ask(prompt, skip_history_append=True)
            is_urgent = "IS_URGENT: YES" in res
            summary = ""
            for line in res.splitlines():
                if line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
            return is_urgent, summary
        except Exception as e:
            print(f"[email_sentry ai error: {e}]")
            return False, ""

    def _sentry_loop(self):
        while self.running:
            try:
                if not self.enabled:
                    time.sleep(15.0)
                    continue

                imap = imaplib.IMAP4_SSL(config.IMAP_SERVER)
                imap.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
                imap.select("inbox")

                _, data = imap.search(None, "UNSEEN")
                current_unseen = set(data[0].split()) if (data and data[0]) else set()
                new_arrivals = current_unseen - self._seen_email_ids

                for eid in new_arrivals:
                    self._seen_email_ids.add(eid)
                    _, msg_data = imap.fetch(eid, "(RFC822)")
                    if not msg_data or not msg_data[0]:
                        continue

                    msg = email.message_from_bytes(msg_data[0][1])
                    sender_raw = self._decode_str(msg.get("From", ""))
                    subject_raw = self._decode_str(msg.get("Subject", "No Subject"))
                    body_text = self._extract_body_text(msg)

                    # Clean sender name
                    sender_clean = re.sub(r"<.+?>", "", sender_raw).replace('"', '').strip()

                    is_urgent, summary = self._classify_and_summarize(sender_clean, subject_raw, body_text)
                    if is_urgent:
                        with self._lock:
                            self._pending_email = {
                                "id": eid,
                                "sender": sender_clean,
                                "subject": subject_raw,
                                "summary": summary or f"{sender_clean} se '{subject_raw}' par email aayi hai.",
                                "timestamp": datetime.datetime.now()
                            }

                        # Proactive voice announcement
                        alert_msg = f"Boss, {sender_clean} se ek zaroori email aayi hai: '{subject_raw}'. Kya main iska summary padh kar sunau?"
                        self._speak_alert(alert_msg, emotion="concerned")
                        break  # Alert one email at a time

                imap.logout()

            except Exception as e:
                # Network or timeout errors
                pass

            time.sleep(120.0)  # Check every 2 minutes

    def has_pending_email(self) -> bool:
        with self._lock:
            if not self._pending_email:
                return False
            elapsed = (datetime.datetime.now() - self._pending_email["timestamp"]).total_seconds()
            return elapsed < 300

    def read_pending_summary(self) -> str:
        with self._lock:
            pemail = self._pending_email
            self._pending_email = None

        if not pemail:
            return "Abhi koi nayi urgent email pending nahi hai."

        return f"Email ka summary ye hai: {pemail['summary']}"

    def open_gmail_inbox(self) -> str:
        with self._lock:
            self._pending_email = None
        try:
            webbrowser.open("https://mail.google.com")
            return "Gmail inbox browser mein open kar diya hai."
        except Exception as e:
            print(f"[open_gmail_inbox error: {e}]")
            return "Inbox open karne mein dikkat aayi."


sentry = EmailSentry()
