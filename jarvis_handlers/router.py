# -*- coding: utf-8 -*-
"""
router.py
=========
`handle_text()` — pura intent router.

Ye pehle main.py me ~550 line ka ek method tha jisme har feature ka apna
inline `if any(w in text.lower() ...)` block tha. Ab wo sirf *order* declare
karta hai; har step ka implementation respective module me hai.

Ek user sentence yahan is order me aata hai:

    1.  interview mode            (A+S hotkey mode — normal commands off)
    2.  paralinguistic event      (haansi, rona, yawn — emotion react)
    3.  video mode                (video drop kiya hua hai)
    4.  high-priority routes      (game synth, dots stealth browser)
    5.  fixed command match       (command_data.py trigger phrases)
    6.  macro learning            ("jab main boloon ... tab ...")
    7.  file intake               (file drop kiya hai + koi command nahi mili)
    8.  pending follow-ups        (haan / na / organize jaise jawab)
    9.  clipboard error diagnose
    10. feature routes            (copilot, avengers, skill scout, ...)
    11. self-written custom skill (dynamic hot reloader)
    12. agentic brain             (CoT + ReAct — AI ka apna faisla)
    13. post-brain routes         (morning briefing, web operator, maps)
    14. command fallback          (app open, shortcut, platform actions, vision)
    15. matched command ka type dispatch

Har step `True` return karta hai toh sentence consume ho jaata hai.
Return `False` ka matlab: session khatam (sleep / exit).
"""

import time

import platform_actions

from command_data import find_command
from commands import system_commands

from . import followups, keyword_routes
from .text_patterns import (APP_NAME_MAX_WORDS, APP_NAME_STOPWORDS,
                           EXPLICIT_VISUAL_KEYWORDS, OPEN_APP_PATTERN,
                           SHORTCUT_PATTERN)


class IntentRouterMixin:
    """Text -> intent ka pura pipeline."""

    def handle_text(self, text: str) -> bool:
        """Return False agar conversation/session yahi khatam karni ho."""

        # 1 + 2. Interview mode aur paralinguistic (bio-event) reactions.
        # Ye dono session ka mode badal dete hain, isliye sabse pehle.
        if self._route_interview_mode(text):
            return True
        if self._route_paralinguistic_event(text):
            return True

        # 3. Video drop mode — isme sirf video commands chalte hain.
        if getattr(self, "video_mode", False):
            return self._handle_video_commands(text)

        # 4. Fixed command table se pehle wale high-priority features.
        if keyword_routes.dispatch(self, keyword_routes.PRE_COMMAND_ROUTES, text):
            return True

        # 5. Fixed command table match.
        cmd_id, data, matched_trigger = find_command(text)
        if cmd_id:
            self._log_command_in_ai_history(text, cmd_id)

        # 6. Macro learning / learned macro execution.
        if self._route_macro(text, cmd_id):
            return True

        # 7. File intake mode.
        if self.active_file:
            if self.file_release_requested(text):
                self.clear_active_file()
                return True
            if not cmd_id:
                # Koi command nahi mili -> is file ke context me sawaal ka jawab
                return self.handle_file_question(text)
            # Command mili hai (jaise "volume badhao") -> wo normal flow me chalegi

        # 8. Pending follow-ups (permission prompts ka jawab).
        if followups.run(self, text, followups.RULES_BEFORE_CLIPBOARD):
            return True

        # 9. Clipboard me terminal error hai -> auto-diagnose.
        if followups.inspect_clipboard_error(self, text):
            return True

        if followups.run(self, text, followups.RULES_AFTER_CLIPBOARD):
            return True

        # 10. Keyword-triggered features.
        if keyword_routes.dispatch(self, keyword_routes.PRE_BRAIN_ROUTES, text):
            return True

        # 11. Self-written (self-evolved) custom skills.
        if self._run_custom_skill(text):
            return True

        # 12. Intent-first agentic brain — CoT/ReAct.
        if self._route_agentic_brain(text):
            return True

        # 13. Brain ke baad wale features.
        if keyword_routes.dispatch(self, keyword_routes.POST_BRAIN_ROUTES, text):
            return True

        # 14. Fixed command na mili toh generic fallbacks.
        if not cmd_id:
            return self._handle_unmatched_text(text)

        # 15. Command table se match hua hai -> uska type dispatch karo.
        return self.dispatch_command(data, text, matched_trigger)

    # ------------------------------------------------------- 1-2. mode guards
    def _route_interview_mode(self, text: str) -> bool:
        """Interview mode trigger check; active mode me normal commands skip."""
        try:
            from interview_mode import check_interview_trigger, interview_mode as _imode
            if check_interview_trigger(text, gui=self.gui, voice=self.voice,
                                       chat_gui=getattr(self, "chat_gui", None)):
                return True
            # Interview mode active hai toh sirf A+S hotkey kaam karega
            return _imode.is_active
        except Exception as e:  # noqa: BLE001
            print(f"[interview_mode hook error: {e}]")
            return False

    def _route_paralinguistic_event(self, text: str) -> bool:
        """Yawn / laugh / hum / cry detect karke usi hisaab se react karo."""
        try:
            from acoustic_filter_engine import acoustic_filter
            bio_event = acoustic_filter.detect_paralinguistic_event(b"", text=text)
            if bio_event.get("event") != "none" and bio_event.get("message"):
                self.speak(bio_event["message"], emotion=bio_event.get("emotion", "calm"))
                return True
            return False
        except Exception as e:  # noqa: BLE001
            print(f"[paralinguistic bio-event error: {e}]")
            return False

    # ------------------------------------------------------------ 5-6. macros
    def _log_command_in_ai_history(self, text: str, cmd_id: str):
        """Fixed command ko AI history me log karo taaki context bana rahe."""
        try:
            self.ai.history.append({"role": "user", "parts": [{"text": text}]})
            self.ai.history.append({"role": "model",
                                    "parts": [{"text": f"[Command executed: {cmd_id}]"}]})
        except Exception:  # noqa: BLE001
            pass

    def _route_macro(self, text: str, cmd_id) -> bool:
        """"Jab main boloon X tab Y" -> macro seekho; ya seekha hua macro chalao."""
        evolution = _autonomous_evolution()
        if evolution is None:
            return False

        text_lower = text.lower()
        if any(w in text_lower for w in ("jab main boloon", "jab bhi main bolu", "jab main kahu")):
            evolution.learn_macro_from_voice(text)
            return True

        if not cmd_id and evolution.check_and_execute_macro(text):
            return True
        return False

    # -------------------------------------------------------- 11. custom skill
    def _run_custom_skill(self, text: str) -> bool:
        """Self-evolution engine ne likhi hui skills (custom_skills/) yahan se chalti hain."""
        try:
            import dynamic_hot_reloader
            result = dynamic_hot_reloader.hot_reloader.match_and_execute(
                text, context={"gui": self.gui})
            if not result:
                return False
            self.speak(result.get("message", "Task successfully execute ho gaya hai."),
                       emotion="happy")
            return True
        except Exception as e:  # noqa: BLE001
            print(f"[custom_skill execution error: {e}]")
            return False

    # ------------------------------------------------------------- 12. brain
    def _route_agentic_brain(self, text: str) -> bool:
        """
        Intent-first CoT brain: memory + desktop context ke saath reason karo,
        phir step execute karo (ya jawab bolo).
        Failure pe chup-chaap aage ke steps ban jaate hain (offline rules).
        """
        if not self.ai.available():
            return False

        try:
            import agentic_cot_brain
            import desktop_context
            import memory

            mem_ctx = memory.build_memory_context(current_query=text, limit=4) if memory else ""
            desktop_ctx = desktop_context.build_context_summary() if desktop_context else ""
            full_ctx = f"{mem_ctx}\n\n{desktop_ctx}".strip()

            step = agentic_cot_brain.cot_brain.reason_and_plan(text, context=full_ctx)

            if step.action_name and step.action_name != "none":
                if step.response_text:
                    self.speak(step.response_text, emotion=step.emotion)
                agentic_cot_brain.cot_brain.execute_step_action(step, jarvis_instance=self)
                return True

            if step.response_text:
                interrupted = self.speak(step.response_text, interruptible=True,
                                        emotion=step.emotion)
                if interrupted:
                    return self._handle_cut_in_follow_up()
                return True

            interrupted = self.speak_ai_stream(text)
            if interrupted:
                return self._handle_cut_in_follow_up()
            return True
        except Exception as e:  # noqa: BLE001
            print(f"[intent-first brain routing note: {e}], falling back to offline rules...")
            return False

    def _handle_cut_in_follow_up(self) -> bool:
        """User AI bolte-bolte beech me bol diya — uski baat sun lo."""
        follow_up = self.listen(timeout=6, phrase_time_limit=10)
        if follow_up:
            self.gui.show_message(f"Aapne kaha: {follow_up}")
            return self.handle_text(follow_up)
        return True

    # ------------------------------------------------------------ 14. fallback
    def _handle_unmatched_text(self, text: str) -> bool:
        """Fixed command na mili — generic app/shortcut/platform/vision tries."""
        # STT trailing punctuation (., ?) add kar deta hai — hata ke match karte hain,
        # warna pattern silently fail ho jaata tha.
        clean_text = text.strip().rstrip(".?!,")

        if self._open_generic_app(clean_text):
            return True

        shortcut_match = SHORTCUT_PATTERN.match(clean_text)
        if shortcut_match and shortcut_match.group(1).strip():
            if self._press_shortcut(shortcut_match.group(1).strip()):
                return True

        # Jo bhi platform khula ho (YouTube/Instagram/WhatsApp/etc) us par seedha
        # adapt karke action karo — AI ko call karne ki zaroorat nahi.
        if platform_actions.route_platform_action(text, self.voice, self.ai):
            return True

        if self._handle_explicit_vision(text):
            return True

        # Last resort: kuch nahi chala toh skill seekhne ki koshish karo.
        from .optional_deps import deps
        engine = deps.singleton("self_evolution_engine", "evolution_engine")
        if engine is not None and engine.triage_missing_skill(text):
            return True

        self.speak("Samajh nahi paayi, dobara boliye ya thoda alag tarike se kahiye.")
        return True

    def _open_generic_app(self, clean_text: str) -> bool:
        """"X kholo" pattern — fixed list se bahar ke apps bhi naam se khul jaate hain."""
        app_match = OPEN_APP_PATTERN.match(clean_text)
        if not app_match:
            return False
        app_name = app_match.group(1).strip()
        if not app_name:
            return False
        # Guard: lambe complex prompts ya game requests ko app mat samjhein
        if len(app_name.split()) > APP_NAME_MAX_WORDS:
            return False
        if any(word in app_name.lower() for word in APP_NAME_STOPWORDS):
            return False
        print(f"[generic app-open matched: '{app_name}']")
        system_commands.open_any_app(self.voice, name=app_name)
        return True

    def _handle_explicit_vision(self, text: str) -> bool:
        """'screen par kya hai' jaise commands — screen monitor lazy-start hota hai."""
        if not any(keyword in text.lower() for keyword in EXPLICIT_VISUAL_KEYWORDS):
            return False
        if self.screen_monitor is None:
            self.speak("Screen monitoring available nahi hai.", emotion="concerned")
            return True
        if not self.screen_monitor.is_running():
            self.screen_monitor.start()  # Lazy start — pehli baar zaroorat par
            time.sleep(2.6)             # Pehla screenshot lene do
        if self.screen_monitor.get_latest():
            return bool(self.handle_monitor_vision(text))
        return False


def _autonomous_evolution():
    """Optional module — import fail ho to None (macro features skip ho jayenge)."""
    from .optional_deps import deps
    return deps.singleton("autonomous_evolution", "evolution")