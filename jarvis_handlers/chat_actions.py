# -*- coding: utf-8 -*-
"""
chat_actions.py
===============
Chat mode — floating widget band, text/voice chat window khola.

Chat mode me bhi har message scheduler ke through jaata hai
(`enqueue_query`), taaki voice aur chat dono ek hi FIFO queue share karein
— collision nahi hoga.
"""

import threading


class ChatActionsMixin:
    """Chat mode on/off + chat ke andar se aaye messages."""

    def toggle_chat_mode_on(self):
        """Floating widget band, chat window kholo."""
        self.chat_mode = True
        self.gui.hide()
        if self.chat_gui:
            self.chat_gui.show()
        self.speak("Chat Mode chalu ho gaya. Yahan type karke, voice se, ya file drop "
                   "karke baat kar sakte ho.", emotion="happy")

    def toggle_chat_mode_off(self):
        """Chat window band, floating widget wapas."""
        self.chat_mode = False
        if self.chat_gui:
            self.chat_gui.hide()
        self.gui.show()
        self.speak("Floating Mode mein wapas aa gayi. Ab robot widget pe kaam karungi.",
                   emotion="calm")

    def handle_chat_message(self, text: str):
        """Chat se typed message aaya — queue me schedule karo (FIFO execution, zero collision)."""
        if not text:
            return
        if self.chat_gui:
            self.chat_gui.set_typing(True)
        try:
            self.enqueue_query(text, source="chat", wait=False)
        except Exception as e:  # noqa: BLE001
            print(f"[chat message error: {e}]")
            self.speak("Kuch error aa gayi chat mein.", emotion="concerned")
        finally:
            if self.chat_gui:
                self.chat_gui.set_typing(False)

    def handle_chat_voice(self):
        """Chat mode mein voice button dabaya."""
        if not self.chat_mode or not self.chat_gui:
            return
        self.chat_gui.set_typing(True)
        self.chat_gui.add_jarvis_message("Sun rahi hoon...", "calm")

        def _listen_thread():
            text = self.voice.listen(timeout=7, phrase_time_limit=10)
            if text:
                self.chat_gui.add_user_message(text)
                self.enqueue_query(text, source="chat_voice", wait=False)
            else:
                self.chat_gui.add_jarvis_message("Kuch sunayi nahi diya, dobara boliye.",
                                                "concerned")
            self.chat_gui.set_typing(False)

        threading.Thread(target=_listen_thread, daemon=True).start()