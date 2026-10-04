# -*- coding: utf-8 -*-
"""
info_actions.py
===============
`command_data.py` ke "info" type commands — yaani wo actions jo koi argument
nahi leti, seedha ek reply deti hain ("greet", "sleep", "git status", ...).

handle_info() pehle 120+ line ka if/elif chain tha. Ab:
  - control-flow wale actions (sleep / exit / dictation / chat mode) top pe,
    kyunki ye session ka direction hi badal dete hain
  - baaki grouped helpers me — core (chhote replies), monitoring (system/git/
    disk/clipboard), evolution & bridge (macros, diagnostics, WhatsApp)

Order matter karta tha sirf is liye ki ek action ek hi branch me chare — jo
action names unique hain wo ab bhi hain.
"""

import random

import config

from .optional_deps import deps
from .text_patterns import GREETINGS


class InfoActionsMixin:
    """Simple, no-argument actions."""

    # -------------------------------------------------------------- dispatcher
    def handle_info(self, action: str) -> bool:
        # --- Session control (return value matter karta hai) ---
        if action == "sleep_assistant":
            self.speak(f"Theek hai, main sone ja rahi hoon. "
                       f"'{config.ASSISTANT_NAME}' bolke jagana.")
            self.gui.set_state("sleeping")  # <- AANKHEIN BAND
            return False

        if action == "exit_assistant":
            self.shutdown()
            return False

        if action == "chat_mode_on":
            self.toggle_chat_mode_on()
            return True

        if action == "chat_mode_off":
            self.toggle_chat_mode_off()
            return True

        if action == "start_dictation":
            self.dictation_mode = True
            self.speak("Theek hai, ab jo boliye wahi type hoga. "
                       "Rukne ke liye 'likhna band karo' boliye.")
            return True

        if action == "modify_self":
            self.awaiting_modification = True
            self.speak("Kya karna hai boss? Debugging karu, ya naya feature add karu?")
            return True

        # --- Eye cursor (silent, koi reply nahi) ---
        if action in ("start_eye_cursor", "stop_eye_cursor"):
            if self.eye_cursor is None:
                self.speak("Eye control available nahi hai.", emotion="concerned")
                return True
            if action == "start_eye_cursor":
                self.eye_cursor.start(self.voice)
            else:
                self.eye_cursor.stop(self.voice)
            return True

        # --- Screen monitor ---
        if action in ("screen_monitor_start", "screen_monitor_stop"):
            if self.screen_monitor is None:
                self.speak("Screen monitoring available nahi hai.", emotion="concerned")
                return True
            if action == "screen_monitor_start":
                self.screen_monitor.start(self.voice)
                self.speak("Screen monitoring chalu kar di. Ab main hamesha dekh rahi hoon "
                           "aap kya kar rahe ho.")
            else:
                self.screen_monitor.stop(self.voice)
                self.speak("Screen monitoring band kar di.")
            return True

        if action == "stop_web_agent":
            stop_agent = deps.attr("web_control", "stop_autonomous_agent")
            if stop_agent is not None:
                stop_agent()
            self.speak("Browser automation rok diya gaya hai.")
            return True

        for group in (self._info_core, self._info_monitoring, self._info_evolution_bridge):
            if group(action):
                return True

        return True   # <- YE SABSE END MEIN HONA CHAHIYE

    # ------------------------------------------------------------------- core
    def _info_core(self, action: str) -> bool:
        """Chhote conversational replies — koi system call nahi."""
        if action == "greet":
            self.speak(random.choice(GREETINGS))
            return True

        if action == "who_are_you":
            self.speak("Main aapka apna Jarvis hoon, poori tarah aapke laptop ke liye bana.")
            return True

        if action == "my_email_address":
            if config.EMAIL_ENABLED and config.EMAIL_ADDRESS:
                self.speak(f"Aapka email hai {config.EMAIL_ADDRESS}")
            else:
                self.speak("Email abhi config me set nahi kiya gaya hai.")
            return True

        # Focus / workspace modes (health coach + workspace harmonizer)
        if action == "focus_time_check":
            return self._sentry_reply("health_focus_coach", "coach",
                                      "get_focus_summary", emotion="happy",
                                      lead="")

        if action in ("coding_mode_on", "study_mode_on"):
            method = ("launch_coding_workspace" if action == "coding_mode_on"
                      else "launch_study_workspace")
            return self._sentry_reply("workspace_harmonizer", "harmonizer", method,
                                      emotion="happy", lead="")

        if action in ("meeting_mode_on", "meeting_mode_off"):
            return self._sentry_reply("workspace_harmonizer", "harmonizer",
                                      "toggle_meeting_shield",
                                      on=(action == "meeting_mode_on"),
                                      emotion="calm" if action == "meeting_mode_on" else "happy",
                                      lead="")

        return False

    # ------------------------------------------------------------- monitoring
    def _info_monitoring(self, action: str) -> bool:
        """Project / git / disk / janitor diagnostics."""
        if action == "git_auto_commit":
            self.speak("Git status check kar rahi hoon...", emotion="calm")
            return self._sentry_reply("project_auto_doctor", "doctor",
                                      "auto_git_commit_and_sync", emotion="happy")

        if action == "git_status_check":
            return self._sentry_reply("project_auto_doctor", "doctor",
                                      "get_git_status_summary", emotion="happy")

        if action.startswith("free_port_"):
            port = action.rsplit("_", 1)[-1]
            self.speak(f"Port {port} free kar rahi hoon...", emotion="calm")
            return self._sentry_reply("project_auto_doctor", "doctor", "free_port",
                                      port, emotion="happy")

        if action == "organize_desktop":
            self.speak("Desktop organize kar rahi hoon, please ek second...", emotion="calm")
            return self._sentry_reply("desktop_janitor", "janitor",
                                      "organize_desktop", emotion="happy")

        if action == "clean_old_downloads":
            self.speak("Downloads folder scan kar rahi hoon...", emotion="calm")
            return self._sentry_reply("desktop_janitor", "janitor",
                                      "find_old_downloads", emotion="concerned")

        if action == "find_duplicate_files":
            self.speak("Duplicate files dhundh rahi hoon...", emotion="calm")
            return self._sentry_reply("desktop_janitor", "janitor",
                                      "find_duplicates", emotion="concerned")

        if action == "disk_space_report":
            return self._sentry_reply("desktop_janitor", "janitor",
                                      "report_disk_space", emotion="happy")

        return False

    # -------------------------------------------------- evolution + messaging
    def _info_evolution_bridge(self, action: str) -> bool:
        """Autonomous evolution + WhatsApp mobile bridge actions."""
        if action == "system_diagnostic":
            evolution = deps.singleton("autonomous_evolution", "evolution")
            if evolution is not None:
                evolution.run_system_diagnostic()
            return True

        if action == "list_macros":
            return self._sentry_reply("autonomous_evolution", "evolution",
                                      "list_learned_macros", emotion="happy")

        if action == "send_laptop_telemetry_whatsapp":
            bridge = deps.singleton("whatsapp_mobile_bridge", "bridge")
            if bridge is None:
                self.speak("WhatsApp bridge abhi available nahi hai.", emotion="concerned")
                return True
            if not bridge.master_phone:
                self.speak("Aapka master WhatsApp number configure nahi hai. "
                           "Pehle WhatsApp bridge mein number set kijiye.", emotion="concerned")
                return True
            self.speak("Laptop telemetry status WhatsApp par bhej rahi hoon...", emotion="calm")
            telemetry = bridge.get_telemetry_status()
            bridge.send_whatsapp_message(telemetry)
            return True

        if action == "send_screenshot_whatsapp":
            bridge = deps.singleton("whatsapp_mobile_bridge", "bridge")
            if bridge is None:
                self.speak("WhatsApp bridge abhi available nahi hai.", emotion="concerned")
                return True
            self.speak("Live screenshot capture karke WhatsApp par bhej rahi hoon...",
                       emotion="calm")
            reply = bridge.dispatch_screenshot_to_whatsapp()
            self.speak(reply, emotion="happy")
            return True

        if action == "show_wol_instructions":
            import remote_boot_wol
            info = remote_boot_wol.get_wol_configuration_info()
            self.speak("Remote boot aur Wake-on-LAN ki settings WhatsApp par bhej di hain.",
                       emotion="happy")
            bridge = deps.singleton("whatsapp_mobile_bridge", "bridge")
            if bridge is not None:
                bridge.send_whatsapp_message(info)
            return True

        return False

    # ----------------------------------------------------------------- helper
    def _sentry_reply(self, module: str, attr: str, method: str, *args,
                      emotion: str = "happy", lead: str = None, **kwargs) -> bool:
        """
        Sentries ka standard pattern: method call karo, jo string return ho wo
        bol do. Optional module missing ho to user ko bata do, crash nahi hoga.
        """
        instance = deps.singleton(module, attr)
        if instance is None:
            self.speak("Ye feature abhi available nahi hai.", emotion="concerned")
            return True
        try:
            if lead:
                self.speak(lead, emotion="calm")
            reply = getattr(instance, method)(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            print(f"[info:{module}.{method}] failed: {exc}")
            self.speak("Ye karte waqt error aa gaya.", emotion="concerned")
            return True
        if isinstance(reply, str) and reply:
            self.speak(reply, emotion=emotion)
        return True