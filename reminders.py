# -*- coding: utf-8 -*-
"""
reminders.py
============
Item #4 - Reminders. "X minute baad"/"5 baje" jaisi phrases parse karta hai.
"""

import re
import datetime
import memory


def parse_and_set_reminder(instruction: str) -> str:
    if not instruction:
        return "Kya aur kab yaad dilana hai, dono batayein."
    remind_at = _parse_time(instruction)
    if remind_at is None:
        return "Time samajh nahi paayi. 'X minute baad' ya '5 baje' jaisa boliye."
    message = _strip_time_words(instruction) or "Reminder"
    ok = memory.add_reminder(remind_at.isoformat(), message)
    if ok:
        return f"Theek hai, {remind_at.strftime('%I:%M %p')} baje yaad dila dungi: {message}"
    return "Reminder set karte waqt dikkat aa gayi."


def _parse_time(text: str):
    text = text.lower()
    now = datetime.datetime.now()
    m = re.search(r"(\d+)\s*(minute|min)", text)
    if m:
        return now + datetime.timedelta(minutes=int(m.group(1)))
    m = re.search(r"(\d+)\s*(ghante|ghanta|hour)", text)
    if m:
        return now + datetime.timedelta(hours=int(m.group(1)))
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*baje", text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2) or 0)
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        return target
    return None


def _strip_time_words(text: str) -> str:
    text = re.sub(r"\d+\s*(minute|min|ghante|ghanta|hour)\s*(baad|mein|me)?", "", text, flags=re.I)
    text = re.sub(r"\d{1,2}(?::\d{2})?\s*baje", "", text, flags=re.I)
    text = re.sub(r"\b(yaad dilana|yaad dilao|reminder lagao|mujhe)\b", "", text, flags=re.I)
    return text.strip(" ,.-")


def check_and_speak_due_reminders(voice):
    for reminder_id, message in memory.get_due_reminders():
        voice.speak(f"Reminder: {message}")
        memory.mark_reminder_done(reminder_id)
