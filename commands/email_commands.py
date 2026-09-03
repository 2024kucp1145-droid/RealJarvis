# -*- coding: utf-8 -*-
"""
email_commands.py
==================
Email bhejna, unread mails padhna, inbox me search karna.
Gmail ke liye: normal password nahi chalega, "App Password" banana padega
(Google Account -> Security -> 2-Step Verification -> App Passwords).
config.py me EMAIL_ENABLED = True karke apni details bharo.
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.header import decode_header

import config


def _check_enabled(voice) -> bool:
    if not config.EMAIL_ENABLED or not config.EMAIL_APP_PASSWORD:
        voice.speak("Email abhi set up nahi hai. config.py me email details bhariye pehle.")
        return False
    return True


def send_email(voice, to="", subject="Jarvis se message", body="", **kw):
    if not _check_enabled(voice):
        return
    if not to:
        voice.speak("Kisko email bhejun, address batayein.")
        return
    try:
        msg = MIMEText(body or "")
        msg["Subject"] = subject
        msg["From"] = config.EMAIL_ADDRESS
        msg["To"] = to

        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
            server.send_message(msg)

        voice.speak(f"{to} ko email bhej diya maine.")
    except Exception as e:
        voice.speak("Email bhejne me dikkat aa gayi.")
        print(f"[send_email error: {e}]")


def _decode(value):
    if value is None:
        return ""
    parts = decode_header(value)
    out = ""
    for text, enc in parts:
        out += text.decode(enc or "utf-8") if isinstance(text, bytes) else text
    return out


def read_unread(voice, limit=5, **kw):
    if not _check_enabled(voice):
        return
    try:
        imap = imaplib.IMAP4_SSL(config.IMAP_SERVER)
        imap.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
        imap.select("inbox")

        status, data = imap.search(None, "UNSEEN")
        ids = data[0].split()
        if not ids:
            voice.speak("Koi nayi email nahi hai.")
            imap.logout()
            return

        voice.speak(f"{len(ids)} nayi emails hain. Sunayein?")
        for eid in ids[-limit:]:
            _, msg_data = imap.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            sender = _decode(msg.get("From"))
            subject = _decode(msg.get("Subject"))
            voice.speak(f"{sender} se: {subject}")
        imap.logout()
    except Exception as e:
        voice.speak("Email check karne me dikkat aa gayi.")
        print(f"[read_unread error: {e}]")


def search_inbox(voice, keyword="", **kw):
    if not _check_enabled(voice):
        return
    if not keyword:
        voice.speak("Kya search karu inbox me?")
        return
    try:
        imap = imaplib.IMAP4_SSL(config.IMAP_SERVER)
        imap.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
        imap.select("inbox")
        status, data = imap.search(None, f'(SUBJECT "{keyword}")')
        ids = data[0].split()
        voice.speak(f"{keyword} se related {len(ids)} emails mili.")
        imap.logout()
    except Exception as e:
        voice.speak("Search karne me dikkat aa gayi.")
        print(f"[search_inbox error: {e}]")
