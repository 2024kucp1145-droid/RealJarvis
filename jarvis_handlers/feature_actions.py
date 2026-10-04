# -*- coding: utf-8 -*-
"""
feature_actions.py
==================
Command table se aane wale "feature" actions — memory aur email.

Inke liye `command_data.py` me command `type` "memory" / "email_ai" /
"email_ui" hota hai, aur yahan ke handlers execute hote hain.
"""

import config
import memory
import reminders


class FeatureActionsMixin:
    """Memory + email handlers."""

    # ----------------------------------------------------------------- memory
    def handle_memory(self, action: str, param: str):
        """Memory system — notes save/recall/search aur reminders."""
        if action == "save_note":
            if not param:
                self.speak("Kya yaad rakhu? Kuch bataiye.")
                return
            ok = memory.save_note(param)
            self.speak("Yaad rakh liya." if ok else "Yaad rakhne me dikkat aa gayi.")

        elif action == "recall_notes":
            notes = memory.get_recent_notes(limit=5)
            if not notes:
                self.speak("Abhi tak kuch yaad rakhne ko nahi mila.")
                return
            summary = "; ".join(content for _, content in notes)
            self.speak(f"Ye yaad hai: {summary}")

        elif action == "search_notes":
            if not param:
                self.speak("Kis baare mein yaad dilau?")
                return
            notes = memory.search_notes(param, limit=3)
            if not notes:
                self.speak(f"{param} ke baare mein kuch yaad nahi hai.")
                return
            summary = "; ".join(content for _, content in notes)
            self.speak(f"Ye mila: {summary}")

        elif action == "set_reminder":
            msg = reminders.parse_and_set_reminder(param)
            self.speak(msg)

    # ------------------------------------------------------------------ email
    def handle_open_email_window(self):
        """Email inbox ko ek proper window me kholta hai - scroll/click karke
        padh sakte ho."""
        from commands import email_commands

        if not config.EMAIL_ENABLED or not config.EMAIL_APP_PASSWORD:
            self.speak("Email abhi set up nahi hai. config.py me EMAIL_ADDRESS aur "
                       "EMAIL_APP_PASSWORD bhariye pehle.")
            return

        self.speak("Email khol rahi hoon...")
        emails = email_commands.get_recent_emails(limit=20)

        if not emails:
            self.speak("Koi email nahi mili ya connect karne me dikkat aa rahi hai.")
            return

        self.gui.open_email_inbox(emails)
        self.speak(f"{len(emails)} emails khol di hain, dekh lijiye.")

    def handle_email_query(self, user_text: str, filter_who: str = None):
        """
        Email ke baare me natural sawaal.
        - filter_who diya gaya hai (jaise "Rahul ka email dikhao") -> usi
          naam/subject se match karke emails dhoondhta hai.
        - filter_who nahi diya (generic sawaal jaise "email me kya hai") ->
          seedha SABSE NAYI email dikhata hai.
        """
        from commands import email_commands

        if not config.EMAIL_ENABLED or not config.EMAIL_APP_PASSWORD:
            self.speak("Email abhi set up nahi hai. config.py me EMAIL_ADDRESS aur "
                       "EMAIL_APP_PASSWORD bhariye pehle (Gmail App Password chahiye hoga).")
            return
        if not self.ai.available():
            self.speak("AI setup nahi hai, isliye email samajh kar bata nahi paungi.")
            return

        self.gui.set_state("thinking")
        self.gui.show_message("Email check kar rahi hoon...")

        if filter_who:
            emails = email_commands.search_emails_content(filter_who, limit=5)
        else:
            emails = email_commands.get_recent_emails(limit=1)  # generic sawaal -> sirf latest

        if not emails:
            if filter_who:
                self.speak(f"{filter_who} se related koi email nahi mili.")
            else:
                self.speak("Koi email nahi mili, ya connect karne me dikkat aa rahi hai.")
            return

        email_summary = "\n\n".join(
            f"From: {e['from']}\nSubject: {e['subject']}\nDate: {e['date']}\nBody: {e['body']}"
            for e in emails
        )
        full_question = (
            f"User ka sawaal: {user_text}\n\n"
            f"Ye user ki asli email(s) hai (sirf yahi data sach hai):\n{email_summary}\n\n"
            f"IMPORTANT: Sirf UPAR diye gaye asli email data ka use karke jawab do. "
            f"Kabhi bhi khud se sender ka naam, email address, ya content mat banao/imagine "
            f"mat karo. Agar upar diye gaye data me sawaal ka jawab nahi hai, saaf keh do "
            f"'mujhe ye jaankari nahi mili' - guess mat karo."
        )
        reply, emotion = self.ai.ask(full_question)
        self.speak(reply, interruptible=True, emotion=emotion)