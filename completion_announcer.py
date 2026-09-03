# -*- coding: utf-8 -*-
"""
completion_announcer.py  (Phase 13: Multi-Channel Completion Announcer)
========================================================================
Announces skill synthesis completion across Voice, Desktop GUI, and WhatsApp.
"""

import sys
import os
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_spec_formulator import SkillSpec


class CompletionAnnouncer:
    """Delivers multi-channel completion announcements."""

    def __init__(self, voice=None, gui=None, speak_fn=None):
        self.voice = voice
        self.gui = gui
        self.speak_fn = speak_fn

    def announce_completion(self, spec: SkillSpec):
        """Dispatches vocal, visual, and mobile notifications for learned skill."""
        spoken_text = f"Ho gaya boss! Maine '{spec.skill_name}' seekh liya hai, ab aap ise use kar sakte hain."
        safe_spoken = spoken_text.encode('ascii', 'ignore').decode()
        print(f"[completion_announcer] [>>] Announcement: {safe_spoken}")

        # 1. Spoken Audio Announcement
        try:
            if self.speak_fn:
                self.speak_fn(spoken_text, emotion="happy")
            elif self.voice:
                self.voice.speak(spoken_text, interruptible=True, emotion="happy")
        except Exception as e:
            print(f"[completion_announcer voice error: {e}]")

        # 2. Desktop GUI Floating Message
        try:
            if self.gui:
                self.gui.show_message(f"✨ Skill Learned: {spec.skill_name}\nTriggers: {', '.join(spec.triggers[:2])}", ms=4000)
        except Exception as e:
            print(f"[completion_announcer gui error: {e}]")

        # 3. WhatsApp Mobile Sync
        try:
            import whatsapp_mobile_bridge
            wa_msg = (
                f"🧠 *JARVIS SELF-EVOLUTION UPDATE*\n\n"
                f"Boss, maine ek naya skill successfully seekh liya hai!\n"
                f"• *Skill:* `{spec.skill_name}`\n"
                f"• *Category:* `{spec.category}`\n"
                f"• *Voice Triggers:* {', '.join(spec.triggers[:3])}\n\n"
                f"Ab aap yeh command kisi bhi waqt bol sakte hain!"
            )
            whatsapp_mobile_bridge.bridge.send_whatsapp_message(wa_msg)
        except Exception as e:
            print(f"[completion_announcer whatsapp error: {e}]")


announcer = CompletionAnnouncer()
