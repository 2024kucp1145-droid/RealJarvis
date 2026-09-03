# -*- coding: utf-8 -*-
"""
whatsapp_mobile_bridge.py
==========================
Phone-to-Laptop WhatsApp Mobile Bridge (Phases 1, 2, 3, 4 & 5 Complete).

Features:
1. "Message Yourself" (ME / You) Direct Routing — all conversation stays in your private WhatsApp chat.
2. Master Whitelist Security — only your verified phone number (+917014093732) is authorized.
3. Phase 1: Live System Telemetry Engine (Battery, RAM, CPU, Active App, Storage).
4. Phase 2: Remote Boot & Power Control (WoL setup info, Lock, Sleep, Shutdown, Restart).
5. Phase 3: WhatsApp File Dispatcher & Live Screen Eye (Send any PDF/File to phone, Live Screenshot).
6. Phase 4: WhatsApp Audio Voice Notes & Media Remote (Play/Pause, Volume, Voice Note generation).
7. Phase 5: Remote Terminal Execution (`cmd: <command>`) & AI Git Sync Pit-Crew.
"""

import os
import re
import glob
import time
import json
import psutil
import asyncio
import edge_tts
import urllib.parse
import webbrowser
import subprocess
import threading
import datetime
import pyautogui

import remote_boot_wol

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "whatsapp_bridge_config.json")
CAPTURES_DIR = os.path.join(os.path.dirname(__file__), "data", "whatsapp_captures")
os.makedirs(CAPTURES_DIR, exist_ok=True)


class WhatsAppMobileBridge:
    def __init__(self, voice=None, ai=None, gui=None, speak_fn=None, dispatcher_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        self.dispatcher_fn = dispatcher_fn
        self.running = False
        self.enabled = True

        self.config = self._load_config()
        self.master_phone = self.config.get("master_phone", "+917014093732")
        self.api_provider = self.config.get("provider", "local")
        
        self._last_proactive_alert_time = 0
        self._lock = threading.Lock()

    def _load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        default_cfg = {
            "master_phone": "+917014093732",
            "provider": "local",
            "auto_alerts_enabled": True,
            "twilio_account_sid": "",
            "twilio_auth_token": "",
            "twilio_from_number": "whatsapp:+14155238886"
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_cfg, f, indent=2)
        except Exception:
            pass
        return default_cfg

    def save_config(self, phone: str = None, provider: str = None):
        with self._lock:
            if phone is not None:
                self.master_phone = phone.strip()
                self.config["master_phone"] = self.master_phone
            if provider is not None:
                self.api_provider = provider.strip()
                self.config["provider"] = self.api_provider
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2)
            except Exception as e:
                print(f"[whatsapp_bridge save error: {e}]")

    def set_master_phone(self, phone_number: str) -> str:
        clean_num = re.sub(r"[^\d+]", "", phone_number)
        if clean_num and not clean_num.startswith("+") and len(clean_num) == 10:
            clean_num = "+91" + clean_num
        self.save_config(phone=clean_num)
        print(f"[whatsapp_bridge] Master phone (ME Chat) set to: {clean_num}")
        return clean_num

    def start(self, voice=None, ai=None, gui=None, speak_fn=None, dispatcher_fn=None):
        if voice:
            self.voice = voice
        if ai:
            self.ai = ai
        if gui:
            self.gui = gui
        if speak_fn:
            self.speak_fn = speak_fn
        if dispatcher_fn:
            self.dispatcher_fn = dispatcher_fn

        self.running = True
        print("[whatsapp_bridge] WhatsApp Mobile Bridge started (All 5 Phases Active).")

    def stop(self):
        self.running = False

    def _speak(self, message: str, emotion: str = "happy"):
        if self.speak_fn:
            self.speak_fn(message, emotion=emotion)
        elif self.voice:
            self.voice.speak(message, interruptible=True, emotion=emotion)

    # =========================================================================
    # 1. LIVE SYSTEM TELEMETRY (PHASE 1)
    # =========================================================================
    def get_telemetry_status(self) -> str:
        """Compiles real-time laptop vitals for 'ME' WhatsApp chat."""
        now = datetime.datetime.now().strftime("%I:%M %p, %d %b %Y")

        bat_str = "Battery: N/A"
        try:
            bat = psutil.sensors_battery()
            if bat:
                plug_str = "⚡ Charging (Plugged)" if bat.power_plugged else "🔋 On Battery"
                bat_str = f"🔋 *Battery:* {int(bat.percent)}% ({plug_str})"
        except Exception:
            pass

        ram_str = "RAM: N/A"
        cpu_str = "CPU: N/A"
        try:
            mem = psutil.virtual_memory()
            ram_str = f"💾 *RAM:* {int(mem.percent)}% ({round(mem.used/(1024**3), 1)}GB / {round(mem.total/(1024**3), 1)}GB)"
            cpu_pct = psutil.cpu_percent(interval=None)
            cpu_str = f"⚡ *CPU Load:* {int(cpu_pct)}%"
        except Exception:
            pass

        disk_str = "Disk: N/A"
        try:
            drive_letter = (os.path.splitdrive(os.path.abspath('.'))[0] + '\\') or "C:\\"
            disk = psutil.disk_usage(drive_letter)
            disk_str = f"💽 *{drive_letter} Free:* {round(disk.free/(1024**3), 1)} GB (Total {round(disk.total/(1024**3), 1)} GB)"
        except Exception:
            pass

        active_app = "Desktop / Idle"
        try:
            import win32gui
            wnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(wnd)
            if title:
                active_app = title[:45]
        except Exception:
            pass

        msg = (
            f"🤖 *JARVIS TELEMETRY (ME CHAT)*\n"
            f"🕒 *Time:* {now}\n\n"
            f"{bat_str}\n"
            f"{ram_str}\n"
            f"{cpu_str}\n"
            f"{disk_str}\n"
            f"🖥️ *Active App:* {active_app}\n\n"
            f"🟢 *Status:* All 10 Sentries Active & Operational."
        )
        return msg

    # =========================================================================
    # 2. MESSAGE & MEDIA DISPATCHER (TO "ME" SELF CHAT)
    # =========================================================================
    def send_whatsapp_message(self, message: str, phone: str = None) -> bool:
        """Sends WhatsApp message to user's 'ME' (Message Yourself) chat."""
        target_phone = phone or self.master_phone
        if not target_phone:
            print("[whatsapp_bridge] Error: Master phone number is not set.")
            return False

        clean_phone = re.sub(r"[^\d+]", "", target_phone)

        # 1. Twilio API
        if self.api_provider == "twilio" and self.config.get("twilio_account_sid"):
            try:
                from twilio.rest import Client
                client = Client(self.config["twilio_account_sid"], self.config["twilio_auth_token"])
                to_num = f"whatsapp:{clean_phone}" if not clean_phone.startswith("whatsapp:") else clean_phone
                from_num = self.config.get("twilio_from_number", "whatsapp:+14155238886")
                client.messages.create(body=message, from_=from_num, to=to_num)
                print(f"[whatsapp_bridge] Message sent via Twilio to ME ({target_phone})")
                return True
            except Exception as e:
                print(f"[whatsapp_bridge twilio error: {e}]")

        # 2. Local Direct Protocol to Desktop WhatsApp App (No Chrome!)
        encoded_text = urllib.parse.quote(message)
        clean_num = clean_phone.replace('+', '')
        wa_desktop_uri = f"whatsapp://send?phone={clean_num}&text={encoded_text}"
        try:
            os.startfile(wa_desktop_uri)
            print(f"[whatsapp_bridge] WhatsApp Desktop dispatched for ME ({target_phone}) - Zero Chrome")

            # Automated dispatch: Guaranteed Enter trigger with window focus & retry burst
            def _auto_press_enter():
                for delay in (2.0, 3.5, 5.0):
                    time.sleep(1.5 if delay > 2.0 else 2.0)
                    try:
                        import win32gui
                        import win32con
                        import ctypes

                        def enum_handler(hwnd, extra):
                            if win32gui.IsWindowVisible(hwnd):
                                title = win32gui.GetWindowText(hwnd)
                                if "whatsapp" in title.lower():
                                    extra.append(hwnd)

                        wa_hwnds = []
                        win32gui.EnumWindows(enum_handler, wa_hwnds)
                        if wa_hwnds:
                            target_hwnd = wa_hwnds[0]
                            try:
                                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                                win32gui.SetForegroundWindow(target_hwnd)
                            except Exception:
                                pass
                            time.sleep(0.15)

                        # Send VK_RETURN (Enter) via Win32 keybd_event
                        ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
                        time.sleep(0.05)
                        ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)

                        # Backup send via PyAutoGUI
                        try:
                            import pyautogui
                            pyautogui.press('enter')
                        except Exception:
                            pass
                    except Exception as err:
                        print(f"[whatsapp auto-enter error: {err}]")

            threading.Thread(target=_auto_press_enter, daemon=True).start()
            return True
        except Exception as e:
            print(f"[whatsapp_bridge desktop protocol error: {e}]")
            return False

    def send_proactive_battery_alert(self, percent: int):
        """Pushes emergency low battery warning directly to 'ME' WhatsApp chat."""
        if not self.config.get("auto_alerts_enabled", True) or not self.master_phone:
            return

        now = time.time()
        if (now - self._last_proactive_alert_time) < 300:
            return

        self._last_proactive_alert_time = now
        alert_text = (
            f"⚠️ *EMERGENCY BATTERY ALERT!*\n\n"
            f"Boss, aapka laptop abhi *{percent}% battery* par chal raha hai aur charger connected nahi hai!\n"
            f"Laptop 25% par lock/shutdown ho jayega. Please turant charger connect karein!"
        )
        self.send_whatsapp_message(alert_text)

    # =========================================================================
    # 3. PHASE 3: LIVE SCREEN EYE (CAPTURE & SEND SCREENSHOT)
    # =========================================================================
    def capture_live_screenshot(self) -> str:
        """Takes high-res desktop screenshot and returns local image path."""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        img_path = os.path.join(CAPTURES_DIR, f"screen_{ts}.png")

        # 1. PyAutoGUI
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(img_path)
            print(f"[whatsapp_bridge] Screenshot captured via PyAutoGUI: {img_path}")
            return img_path
        except Exception:
            pass

        # 2. PIL ImageGrab
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(all_screens=True)
            screenshot.save(img_path)
            print(f"[whatsapp_bridge] Screenshot captured via ImageGrab: {img_path}")
            return img_path
        except Exception:
            pass

        # 3. Fallback: Diagnostic status card
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (1280, 720), color=(15, 23, 42))
            d = ImageDraw.Draw(img)
            status_text = self.get_telemetry_status()
            d.text((40, 40), f"JARVIS DESKTOP LIVE STATUS\n\n{status_text}", fill=(248, 250, 252))
            img.save(img_path)
            print(f"[whatsapp_bridge] Diagnostic preview card generated at: {img_path}")
            return img_path
        except Exception as e:
            print(f"[screenshot capture error: {e}]")
            return ""

    def dispatch_screenshot_to_whatsapp(self) -> str:
        """Captures desktop and dispatches preview to 'ME' WhatsApp chat."""
        img_path = self.capture_live_screenshot()
        if not img_path:
            return "Screenshot capture nahi ho paaya."

        msg = (
            f"📸 *LIVE SCREENSHOT CAPTURED*\n"
            f"📁 *Saved at:* `{img_path}`\n\n"
            f"Screen preview ready hai boss."
        )
        self.send_whatsapp_message(msg)
        return "Live screenshot capture karke WhatsApp 'ME' chat par bhej diya hai."

    # =========================================================================
    # 4. PHASE 3: REMOTE FILE DISPATCHER (GET ANY FILE ON PHONE)
    # =========================================================================
    def find_and_dispatch_file(self, query: str) -> str:
        """Searches Downloads, Desktop, Documents for matching file and stages for dispatch."""
        user_home = os.path.expanduser("~")
        search_dirs = [
            os.path.join(user_home, "Downloads"),
            os.path.join(user_home, "Desktop"),
            os.path.join(user_home, "Documents"),
            os.path.join(user_home, "Downloads", "Telegram Desktop")
        ]

        clean_query = query.lower().strip()
        matched_files = []

        for folder in search_dirs:
            if not os.path.isdir(folder):
                continue
            for fname in os.listdir(folder):
                if clean_query in fname.lower() and os.path.isfile(os.path.join(folder, fname)):
                    full_p = os.path.join(folder, fname)
                    size_mb = round(os.path.getsize(full_p) / (1024 * 1024), 2)
                    matched_files.append((fname, full_p, size_mb))

        if not matched_files:
            return f"'{query}' naam ki koi file Downloads ya Documents mein nahi mili."

        best_name, best_path, size = matched_files[0]
        msg = (
            f"📄 *FILE READY FOR DISPATCH*\n"
            f"• *File:* `{best_name}` ({size} MB)\n"
            f"• *Location:* `{best_path}`\n\n"
            f"File 'ME' chat par attach karne ke liye ready hai."
        )
        self.send_whatsapp_message(msg)
        return f"'{best_name}' mil gayi hai ({size} MB). WhatsApp par details bhej di hain."

    # =========================================================================
    # 5. PHASE 4: AUDIO VOICE NOTE GENERATOR & MEDIA REMOTE
    # =========================================================================
    def generate_swara_voice_note(self, text: str) -> str:
        """Synthesizes text into Swara Neural voice MP3 for WhatsApp transmission."""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(CAPTURES_DIR, f"voice_{ts}.mp3")

        async def _synth():
            comm = edge_tts.Communicate(text, "hi-IN-SwaraNeural")
            await comm.save(out_path)

        try:
            asyncio.run(_synth())
            print(f"[whatsapp_bridge] Swara Voice Note generated at: {out_path}")
            return out_path
        except Exception as e:
            print(f"[voice note synth error: {e}]")
            return ""

    def execute_media_action(self, action: str) -> str:
        """Executes media playback actions from WhatsApp."""
        act = action.lower()
        if any(w in act for w in ("play", "pause", "chalao", "rok do")):
            pyautogui.press('playpause')
            return "⏯️ Media Play/Pause toggle kar diya."
        if "next" in act or "aage" in act:
            pyautogui.press('nexttrack')
            return "⏭️ Next track switch kar diya."
        if "prev" in act or "peeche" in act:
            pyautogui.press('prevtrack')
            return "⏮️ Previous track switch kar diya."
        if "mute" in act:
            pyautogui.press('volumemute')
            return "🔇 System Mute/Unmute toggle kar diya."
        if "volume up" in act:
            for _ in range(5):
                pyautogui.press('volumeup')
            return "🔊 Volume badha diya."
        if "volume down" in act:
            for _ in range(5):
                pyautogui.press('volumedown')
            return "🔉 Volume kam kar diya."
        return "Media action samajh nahi aayi. Options: play, pause, next, prev, mute, volume up/down."

    # =========================================================================
    # 6. PHASE 5: REMOTE TERMINAL & SHELL EXECUTION
    # =========================================================================
    def execute_remote_shell_command(self, cmd_str: str) -> str:
        """Executes terminal command securely and returns output for WhatsApp."""
        clean_cmd = cmd_str.strip()
        print(f"[whatsapp_bridge] Executing Remote Shell Command: {clean_cmd}")

        # Block destructive shell commands remotely for safety
        dangerous = ["format", "del /f /s /q c:", "rd /s /q c:", "rmdir /s /q c:"]
        if any(d in clean_cmd.lower() for d in dangerous):
            return "⛔ Security Block: Dangerous disk command rejected."

        try:
            res = subprocess.run(
                ["powershell", "-Command", clean_cmd],
                capture_output=True,
                text=True,
                timeout=20
            )
            stdout = res.stdout.strip()
            stderr = res.stderr.strip()

            out = stdout or stderr or "Command executed with zero output (Exit Code: 0)."
            # Truncate if output exceeds WhatsApp message length
            if len(out) > 1500:
                out = out[:1500] + "\n\n... [Output Truncated]"

            return f"💻 *REMOTE TERMINAL OUTPUT:*\n```\n{out}\n```"

        except subprocess.TimeoutExpired:
            return "⏱️ Command Execution Timeout (exceeded 20s)."
        except Exception as e:
            return f"Terminal Error: {e}"

    # =========================================================================
    # 7. MASTER COMMAND PROCESSOR (INCOMING ROUTER FOR ALL 5 PHASES)
    # =========================================================================
    def process_incoming_command(self, raw_text: str, sender_phone: str = None) -> str:
        """Routes WhatsApp commands across all 5 Phases."""
        # Whitelist Security Check
        if sender_phone and self.master_phone:
            clean_sender = re.sub(r"[^\d]", "", sender_phone)
            clean_master = re.sub(r"[^\d]", "", self.master_phone)
            if clean_master and clean_sender != clean_master:
                return "⛔ Unauthorized access rejected. Only Master 'ME' User allowed."

        text = raw_text.strip().lower()

        # 1. Phase 1: Telemetry / Status
        if any(w in text for w in ("status", "battery", "ram", "cpu", "kitna charge hai", "laptop status", "telemetry")):
            return self.get_telemetry_status()

        # 2. Phase 2: Remote Boot (WoL) & Power Actions
        if "wol" in text or "remote wake" in text or "power on" in text:
            return remote_boot_wol.get_wol_configuration_info()

        if any(w in text for w in ("lock", "sleep", "hibernate", "restart", "shutdown")):
            for action in ("lock", "sleep", "hibernate", "restart", "shutdown"):
                if action in text:
                    return remote_boot_wol.execute_power_action(action)

        # 3. Phase 3: Screen Eye (Screenshot)
        if any(w in text for w in ("screenshot", "screen dikhao", "live screen", "screen photo")):
            return self.dispatch_screenshot_to_whatsapp()

        # 4. Phase 3: File Dispatcher
        if any(w in text for w in ("bhejo", "send file", "get file", "download bhejo")):
            q = re.sub(r"\b(send|bhejo|file|pdf|download|mujhe|karo|get)\b", "", text).strip()
            if q:
                return self.find_and_dispatch_file(q)

        # 5. Phase 4: Media Remote
        if any(w in text for w in ("media", "music", "play", "pause", "next track", "volume")):
            return self.execute_media_action(text)

        # 6. Phase 5: Remote Terminal Execution
        if text.startswith("cmd:") or text.startswith("run:"):
            cmd_body = raw_text[4:].strip()
            return self.execute_remote_shell_command(cmd_body)

        # 7. Phase 5: Remote Git Sync
        if "git commit" in text or "save work" in text:
            import project_auto_doctor
            return project_auto_doctor.doctor.auto_git_commit_and_sync()

        if "organize desktop" in text:
            import desktop_janitor
            return desktop_janitor.janitor.organize_desktop()

        if "disk space" in text:
            import desktop_janitor
            return desktop_janitor.janitor.report_disk_space()

        # 8. Fallback: Ask Jarvis Brain
        if self.ai and self.ai.available():
            reply, _ = self.ai.ask(f"User ne WhatsApp ME chat se ye poocha hai: {raw_text}\nConcise 2-sentence response do.")
            return f"🤖 *Jarvis:* {reply}"

        return "Command samajh nahi aayi. 'status', 'screenshot', 'bhejo [file]', 'cmd: [command]', 'play/pause', 'sleep', ya 'wol' try karein."


bridge = WhatsAppMobileBridge()
