# -*- coding: utf-8 -*-
"""
command_dispatch.py
===================
`command_data.py` se match hone wale fixed commands ka executor.

Router sirf ye karta hai: "text se koi command match hui?" -> haan toh
`dispatch_command()` ko data (type/action/param/confirm) ke saath bhej do.
Uske baad ka pura branching yahan hai:

    type "info"     -> handle_info()
    type "vision"   -> read_screen / write_code / coding hint / webpage summary / vision
    type "web*"     -> web_control ke browser automation functions
    type "email_ai" -> AI se email ka jawab
    type "memory"   -> notes / reminders
    type "run"      -> app launch (fixed list)
    type "keyboard" -> fixed shortcut
    type "dots"     -> stealth browser agent
    type "guardian" -> clipboard fix
    baaki           -> EXECUTORS map se commands/*.py ka matching function

Destructive commands (`"confirm": True`) — file delete, shutdown, restart —
pehle user se confirm puchte hain. Ye jaan-boojh kar sabse aakhir me hai:
sirf tabhi, jab koi beech ka type/action match na ho.
"""

from commands import browser_commands, email_commands, file_commands, system_commands
from commands import whatsapp_commands
from custom import custom_functions

from .optional_deps import deps
from .prompts import EXECUTE_CONFIRM_WORDS, contains_any

EXECUTORS = {
    "system": system_commands,
    "browser": browser_commands,
    "file": file_commands,
    "email": email_commands,
    "custom": custom_functions,
    "whatsapp": whatsapp_commands,
}


class CommandDispatchMixin:
    """Fixed-command routing + parameter extraction."""

    def dispatch_command(self, data: dict, text: str, matched_trigger: str) -> bool:
        """
        Matched command ka `data` dict se action chalao.
        `data` shape (command_data.py se): type, action, optional param, optional confirm.
        """
        ctype = data["type"]
        action = data["action"]

        if ctype == "info":
            return self.handle_info(action)

        if ctype == "vision":
            return self._dispatch_vision(action, text)

        # ---- WEB / APP VISUAL & AUTONOMOUS CONTROL ----
        if ctype == "web":
            self._run_web_control("execute_web_action", text)
            return True

        if ctype == "web_agent":
            self._run_web_control("run_autonomous_web_task", text)
            return True

        if ctype == "web_extract":
            self._run_web_control("extract_screen_info", text)
            return True

        if ctype == "email_ai":
            filter_who = self._param_or_none(data, text, matched_trigger)
            self.handle_email_query(text, filter_who=filter_who)
            return True

        if ctype == "memory":
            param = self._param_or_none(data, text, matched_trigger) or ""
            self.handle_memory(action, param)
            return True

        if ctype == "email_ui":
            self.handle_open_email_window()
            return True

        if ctype == "run":
            self.run_program(action)
            return True

        if ctype == "keyboard":
            self.send_shortcut(action)
            return True

        if ctype == "guardian":
            if action == "replace_at_cursor":
                guardian = deps.singleton("proactive_guardian", "guardian")
                if guardian is not None:
                    reply = guardian.replace_at_cursor()
                    self.speak(reply, emotion="happy")
                return True

        if ctype == "dots":
            return self._dispatch_dots(action, data, text, matched_trigger)

        executor_module = EXECUTORS.get(ctype)
        if executor_module and hasattr(executor_module, action):
            return self._run_executor(executor_module, data, action, text, matched_trigger)

        self.speak("Ye feature abhi maine implement nahi kiya, jaldi add karungi.")
        return True

    # ------------------------------------------------------------- sub-dispatch
    def _dispatch_vision(self, action: str, text: str) -> bool:
        assistant = deps.singleton("web_workflow_assistant", "assistant")

        if action == "read_full_screen":
            self.handle_read_screen(text)
        elif action == "write_code_for_screen":
            self.handle_write_code(text)
        elif action == "provide_coding_hint":
            if assistant is not None:
                assistant.provide_coding_hint(capture_fn=self._capture_clean_screenshot)
        elif action == "summarize_active_webpage":
            if assistant is not None:
                assistant.summarize_active_webpage(capture_fn=self._capture_clean_screenshot)
        elif action == "what_am_i_doing":
            self.handle_monitor_vision(text)
        else:
            self.handle_vision(text)
        return True

    def _dispatch_dots(self, action: str, data: dict, text: str, matched_trigger: str) -> bool:
        import dots_browser_agent

        agent = dots_browser_agent.dots_agent
        agent.voice = self.voice
        agent.ai = self.ai
        agent.gui = self.gui
        if action == "launch_dots_ui":
            agent.launch_browser("https://www.google.com")
        elif action == "stealth_search":
            query = self._param_or_none(data, text, matched_trigger) or text
            agent.search(query)
        return True

    def _run_executor(self, executor_module, data: dict, action: str,
                      text: str, matched_trigger: str) -> bool:
        """commands/*.py ya custom_functions.py ka function chalao."""
        # Security/Permission Manager: destructive commands (file delete,
        # shutdown, restart) pehle confirm karwate hain.
        if data.get("confirm") and not self._confirm_destructive_command():
            return True

        kwargs = {}
        remainder = self._param_or_none(data, text, matched_trigger)
        if remainder:
            kwargs[data["param"]] = remainder

        try:
            getattr(executor_module, action)(self.voice, **kwargs)
        except Exception as e:  # noqa: BLE001
            self.speak("Sorry, ye karte waqt error aa gaya.")
            print(f"[executor error: {e}]")
        return True

    def _confirm_destructive_command(self) -> bool:
        self.speak("Pakka? Haan boliye confirm karne ke liye, warna cancel kar deti hoon.")
        confirmation = self.listen(timeout=6, phrase_time_limit=5)
        if not confirmation or not contains_any(confirmation, EXECUTE_CONFIRM_WORDS):
            self.speak("Theek hai, cancel kar diya.")
            return False
        return True

    def _param_or_none(self, data: dict, text: str, matched_trigger: str):
        """Command ka `param` declared hai aur trigger ke baad kuch bacha hai?"""
        if not data.get("param"):
            return None
        return self._extract_param(text, matched_trigger) or None

    # ------------------------------------------------------------------ param
    @staticmethod
    def _extract_param(text: str, matched_trigger: str) -> str:
        """
        Bole gaye text me se trigger phrase hata kar jo bacha hai wahi
        actual naam/query hai. Jaise "gaana chalao kesariya" me se
        "gaana chalao" hata ke "kesariya" bachta hai.
        """
        if not matched_trigger:
            return ""
        lower = text.lower()
        idx = lower.find(matched_trigger)
        if idx == -1:
            return ""
        remainder = text[:idx] + text[idx + len(matched_trigger):]
        remainder = remainder.strip(" ,.-:")
        # chhote filler words hata do shuru/end se
        for filler in ("ka", "ke", "ki", "naam", "se", "ko"):
            words = remainder.split()
            if words and words[0] == filler:
                words = words[1:]
            if words and words[-1] == filler:
                words = words[:-1]
            remainder = " ".join(words)
        return remainder.strip()