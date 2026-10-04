# -*- coding: utf-8 -*-
"""
ai_actions.py
=============
AI se jawab dene aur AI ke tool/function-calls execute karne wala hissa.

- speak_ai_stream: Gemini se streaming jawab leke sentence-by-sentence bolta hai
  (pehla sentence aate hi bolna shuru — perceived latency low)
- _dispatch_ai_action: AI ke decide kiye function-calls ko real code se chalaata
  hai (app kholo, volume badlo, file dhoondho, UI element pe click, ...)
"""

import activity_tracker
import desktop_context
import memory
import os_sandbox
import ui_controller

from commands import browser_commands, system_commands

from .optional_deps import deps


class AiActionsMixin:
    """Streaming chat + AI function-calling dispatch."""

    # -------------------------------------------------------------- streaming
    def speak_ai_stream(self, user_text: str) -> bool:
        """
        AI se streaming jawab leke turant-turant bolta hai - poore jawab
        generate hone ka wait nahi karta, jaise hi ek sentence ready hota hai
        bol deta hai. Isse response bahut fast lagta hai.
        Return True agar beech me interrupt hua.

        Memory: har naya exchange automatically yaad rehta hai - memory context
        AI ko deta hai aur fact-jaisi baatein permanent notes me save hoti hain.
        """
        memory_context = memory.build_memory_context(limit=6)
        workflow_ctx = activity_tracker.tracker.get_current_task_description()
        desktop_ctx = desktop_context.build_context_summary()
        combined_context = f"{memory_context}\n\n[Live Workflow]: {workflow_ctx}\n{desktop_ctx}"

        is_first = True
        full_reply = ""
        for sentence, emotion in self.ai.ask_stream(user_text, extra_context=combined_context):
            full_reply += sentence + " "
            interrupted = self.speak(sentence, interruptible=True, emotion=emotion,
                                    is_first_chunk=is_first)
            is_first = False
            if interrupted:
                memory.log_conversation(user_text, full_reply.strip() + " (beech me roka gaya)")
                if memory.looks_like_fact(user_text):
                    memory.save_note(f"{user_text} -> {full_reply.strip()}")
                return True

        memory.log_conversation(user_text, full_reply.strip())
        if memory.looks_like_fact(user_text):
            # Fact jaisi lagti baat hai (birthday, naam, pasand, etc) - isse
            # PERMANENT notes me bhi save karte hain taaki kabhi na bhoole,
            # sirf "recent conversations" tak limited na rahe.
            memory.save_note(f"{user_text} -> {full_reply.strip()}")
        return False

    # ------------------------------------------------------- function-calling
    def _dispatch_ai_action(self, function_name: str, args: dict):
        """AI ne jo function-call decide kiya, use actual code se execute karta hai."""
        try:
            if function_name == "open_app":
                system_commands.open_any_app(self.voice, name=args.get("app_name", ""))
            elif function_name == "open_website":
                browser_commands.open_website(self.voice, site=args.get("site_name", ""))
            elif function_name == "adjust_volume":
                direction = args.get("direction", "")
                {"up": system_commands.volume_up, "down": system_commands.volume_down,
                 "mute": system_commands.volume_mute, "unmute": system_commands.volume_unmute,
                 }.get(direction, lambda v: None)(self.voice)
            elif function_name == "adjust_brightness":
                direction = args.get("direction", "")
                {"up": system_commands.brightness_up,
                 "down": system_commands.brightness_down,
                 }.get(direction, lambda v: None)(self.voice)
            elif function_name == "play_youtube_song":
                browser_commands.play_youtube(self.voice, song=args.get("song", ""))
            elif function_name == "search_google":
                browser_commands.search_google(self.voice, query=args.get("query", ""))
            elif function_name == "execute_web_action":
                self._run_web_control("execute_web_action", args.get("description", ""))
            elif function_name == "run_autonomous_web_task":
                self._run_web_control("run_autonomous_web_task", args.get("goal", ""))
            elif function_name == "execute_python_script":
                code = args.get("code", "")
                self.speak("Script execute kar rahi hoon...", emotion="calm")
                res = os_sandbox.execute_python_code(code)
                if res["success"]:
                    out = res["output"][:300] if res["output"] else "Code execute ho gaya."
                    self.speak(out, emotion="happy")
                else:
                    err = res["error"][:200]
                    self.speak(f"Code execute karne me error aaya: {err}", emotion="concerned")
            elif function_name == "execute_powershell_command":
                cmd = args.get("command", "")
                self.speak("Command run kar rahi hoon...", emotion="calm")
                res = os_sandbox.execute_powershell(cmd)
                if res["success"]:
                    out = res["output"][:300] if res["output"] else "Command execute ho gaya."
                    self.speak(out, emotion="happy")
                else:
                    self.speak(f"Error: {res['error'][:200]}", emotion="concerned")
            elif function_name == "search_computer_files":
                q = args.get("query", "")
                self.speak(f"{q} dhoondh rahi hoon...")
                matches = os_sandbox.search_computer_files(q)
                if matches:
                    summary = ", ".join(f"{m['name']} ({m['size']})" for m in matches[:4])
                    self.speak(f"{len(matches)} files mili: {summary}", emotion="happy")
                else:
                    self.speak(f"Computer me {q} se related koi file nahi mili.")
            elif function_name == "get_system_vitals":
                vitals = os_sandbox.get_system_vitals()
                if "error" not in vitals:
                    self.speak(f"CPU usage hai {vitals['cpu_percent']} percent, "
                               f"RAM used hai {vitals['ram_percent']} percent, "
                               f"aur {vitals['ram_free_gb']} GB RAM khali hai.",
                               emotion="happy")
                else:
                    self.speak("System stats read nahi kar payi.")
            elif function_name == "recall_memory":
                q = args.get("query", "")
                recalled = memory.search_semantic_memory(q, limit=4)
                if recalled:
                    summary = "; ".join(recalled[:3])
                    self.speak(f"Mujhe ye yaad hai: {summary}", emotion="happy")
                else:
                    self.speak("Is baare me koi purani baat yaad nahi mili.")
            elif function_name == "click_native_element":
                el = args.get("element_name", "")
                c_type = args.get("control_type", None)
                self.speak(f"{el} button pe click kar rahi hoon...", emotion="calm")
                res = ui_controller.click_native_element(el, control_type=c_type)
                if res["success"]:
                    self.speak(res["message"], emotion="happy")
                else:
                    self.speak(res["message"], emotion="concerned")
            elif function_name == "type_native_element":
                val = args.get("value", "")
                el = args.get("element_name", "")
                p_enter = args.get("press_enter", False)
                res = ui_controller.set_native_edit_text(el, val, press_enter=p_enter)
                self.speak(res["message"], emotion="happy" if res["success"] else "concerned")
            elif function_name == "list_clickable_elements":
                elems = ui_controller.list_clickable_elements(limit=8)
                if elems:
                    summary = ", ".join(elems[:5])
                    self.speak(f"Screen pe ye elements mile: {summary}", emotion="calm")
                else:
                    self.speak("Active window me koi native control detect nahi hua.")
            elif function_name == "arrange_window":
                act = args.get("action", "")
                res = ui_controller.arrange_window(act)
                self.speak(res["message"], emotion="happy" if res["success"] else "concerned")
            elif function_name == "get_workflow_timeline":
                timeline = activity_tracker.tracker.get_timeline_summary(limit=6)
                self.speak(f"Aapka recent activity summary:\n{timeline}", emotion="calm")
            elif function_name == "get_clipboard_analysis":
                clip_data = activity_tracker.tracker.get_latest_clipboard()
                clip_text = clip_data.get("text", "")
                if clip_text:
                    self.speak("Clipboard content analyze kar rahi hoon...", emotion="calm")
                    prompt = (f"User ne ye text/code clipboard me copy kiya hai:\n\n"
                              f"{clip_text}\n\nIska seedha concise explanation ya solution do.")
                    reply, emotion = self.ai.ask(prompt)
                    self.speak(reply, emotion=emotion)
                else:
                    self.speak("Clipboard par abhi koi text ya code copy nahi mila.")
            elif function_name == "explain_current_work":
                task = activity_tracker.tracker.get_current_task_description()
                self.speak(f"Aap abhi is par kaam kar rahe hain: {task}", emotion="happy")
            else:
                self.speak("Ye action abhi maine implement nahi kiya.")
        except Exception as e:  # noqa: BLE001
            self.speak("Ye karte waqt error aa gaya.")
            print(f"[_dispatch_ai_action error: {e}]")

    def _run_web_control(self, function_name: str, text: str):
        """web_control ka optional function chalao (module missing ho to bol do)."""
        fn = deps.attr("web_control", function_name)
        if fn is None:
            self.speak("Web control available nahi hai abhi.", emotion="concerned")
            return None
        return fn(self.voice, self.ai, text)