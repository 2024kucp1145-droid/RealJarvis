# -*- coding: utf-8 -*-
"""
hardware_sentry.py
===================
Phase 2: Autonomous Hardware & Battery Sentry.

Real-time background monitor for:
1. Real-time Charger Plug / Unplug detection (< 1 sec latency via Windows Kernel API).
2. Battery Danger Zone Range (25% - 30%) with early shutdown protection.
3. RAM choke (> 88%) & top memory-hogging process detector with 1-word kill capability.
4. CPU sustained overload & thermal throttle protection.
5. Low disk space warning on system C: drive.
"""

import time
import ctypes
import threading
import datetime
from ctypes import wintypes

try:
    import psutil
except ImportError:
    psutil = None


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', wintypes.BYTE),       # 0 = Offline (Battery), 1 = Online (AC), 255 = Unknown
        ('BatteryFlag', wintypes.BYTE),
        ('BatteryLifePercent', wintypes.BYTE),  # 0 to 100, 255 = Unknown
        ('SystemStatusFlag', wintypes.BYTE),
        ('BatteryLifeTime', wintypes.DWORD),
        ('BatteryFullLifeTime', wintypes.DWORD),
    ]


class HardwareSentry:
    def __init__(self, voice=None, ai=None, gui=None, speak_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        self.running = False
        self._thread = None
        self.enabled = True

        # Battery tracking state
        self._last_power_plugged = None
        self._alerted_battery_levels = set()
        self._last_danger_zone_alert_time = 0

        # RAM choke tracking
        self._last_ram_alert_time = 0
        self._ram_cooldown_seconds = 600
        self._pending_kill_process = None

        # CPU overload tracking
        self._cpu_high_count = 0
        self._last_cpu_alert_time = 0

        # Disk alert tracking
        self._last_disk_alert_time = 0

        self._lock = threading.Lock()

    def start(self, voice=None, ai=None, gui=None, speak_fn=None):
        if voice:
            self.voice = voice
        if ai:
            self.ai = ai
        if gui:
            self.gui = gui
        if speak_fn:
            self.speak_fn = speak_fn

        if self.running:
            return

        # Snapshot initial battery state
        status = self._get_battery_status()
        if status:
            self._last_power_plugged = status["plugged"]

        self.running = True
        self._thread = threading.Thread(target=self._sentry_loop, daemon=True)
        self._thread.start()
        print("[hardware_sentry] Autonomous Hardware & Battery Sentry started (0.8s responsive loop).")

    def stop(self):
        self.running = False

    def _get_battery_status(self) -> dict:
        """Native Windows Kernel Level power status query (microsecond latency)."""
        try:
            sps = SYSTEM_POWER_STATUS()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
                ac = sps.ACLineStatus
                pct = int(sps.BatteryLifePercent)
                if pct > 100:
                    pct = 100
                plugged = (ac == 1)
                return {"plugged": plugged, "percent": pct, "ac_raw": ac}
        except Exception:
            pass

        # Fallback to psutil
        if psutil:
            try:
                bat = psutil.sensors_battery()
                if bat:
                    return {"plugged": bool(bat.power_plugged), "percent": int(bat.percent), "ac_raw": 1 if bat.power_plugged else 0}
            except Exception:
                pass
        return None

    def _speak_alert(self, message: str, emotion: str = "concerned", priority: str = "normal"):
        """Thread-safe speech alert with terminal logging."""
        print(f"[hardware_sentry] PROACTIVE ALERT: {message}")
        try:
            import workspace_harmonizer
            if not workspace_harmonizer.harmonizer.can_speak_proactively(priority=priority):
                print("[hardware_sentry] Proactive alert muted by Meeting/Class Shield.")
                return
        except Exception:
            pass

        try:
            if self.speak_fn:
                self.speak_fn(message, emotion=emotion)
            elif self.voice:
                self.voice.speak(message, interruptible=True, emotion=emotion)
        except Exception as e:
            print(f"[hardware_sentry alert error: {e}]")

    def _sentry_loop(self):
        tick = 0
        while self.running:
            try:
                if not self.enabled:
                    time.sleep(1.0)
                    continue

                # 1. Fast Battery Check (Every 0.8s)
                self._check_battery()

                # 2. Slower System Vitals Check (Every 6.4s = 8 ticks)
                tick += 1
                if tick >= 8:
                    tick = 0
                    self._check_ram()
                    self._check_cpu()
                    self._check_disk()

            except Exception as e:
                print(f"[hardware_sentry loop error: {e}]")

            time.sleep(0.8)

    def _check_battery(self):
        status = self._get_battery_status()
        if not status:
            return

        percent = status["percent"]
        plugged = status["plugged"]

        # 1. Charger Plugged / Unplugged Event Detection
        if self._last_power_plugged is not None:
            if plugged and not self._last_power_plugged:
                self._last_power_plugged = True
                self._last_danger_zone_alert_time = 0
                self._alerted_battery_levels.discard(100)
                print(f"[hardware_sentry] AC Charger Connected (Battery: {percent}%)")
                self._speak_alert("Charger connect ho gaya hai, power charging on.", emotion="happy", priority="emergency")
                return
            elif not plugged and self._last_power_plugged:
                self._last_power_plugged = False
                self._last_danger_zone_alert_time = 0
                self._alerted_battery_levels.discard(100)
                print(f"[hardware_sentry] AC Charger Disconnected (Battery: {percent}%)")
                self._speak_alert(f"Charger disconnect ho gaya hai, laptop ab battery par hai ({percent}% bachi hai).", emotion="concerned", priority="emergency")
                return

        self._last_power_plugged = plugged

        # 2. Battery Danger Zone Range (25% to 30% when unplugged)
        if not plugged:
            now = time.time()
            # <= 26% Emergency Alert (1% before 25% shutdown lock)
            if percent <= 26:
                if (now - self._last_danger_zone_alert_time) > 120:  # Every 2 mins
                    self._last_danger_zone_alert_time = now
                    self._speak_alert(f"Emergency alert! Battery sirf {percent}% bachi hai, laptop 25% par lock hone wala hai! Turant charger lagaiye!", emotion="serious", priority="emergency")
                    try:
                        import whatsapp_mobile_bridge
                        whatsapp_mobile_bridge.bridge.send_proactive_battery_alert(percent)
                    except Exception:
                        pass

            # 25% - 30% Warning Zone (e.g. 27%, 28%, 29%, 30%)
            elif 25 <= percent <= 30:
                if (now - self._last_danger_zone_alert_time) > 240:  # Every 4 mins
                    self._last_danger_zone_alert_time = now
                    self._speak_alert(f"Boss, battery {percent}% par hai. Laptop 25% par lock ho jata hai, isliye please abhi charger connect kar lijiye.", emotion="concerned", priority="emergency")
            elif percent < 25:
                if (now - self._last_danger_zone_alert_time) > 90:
                    self._last_danger_zone_alert_time = now
                    self._speak_alert(f"Critical: Battery {percent}% par aa chuki hai. Laptop shutdown ho sakta hai!", emotion="serious", priority="emergency")

        # 3. 100% Full Charge Milestone (While plugged)
        if plugged and percent >= 99 and 100 not in self._alerted_battery_levels:
            self._alerted_battery_levels.add(100)
            self._speak_alert("Battery 100% full charge ho chuki hai. Battery health ke liye aap charger disconnect kar sakte hain.", emotion="happy")

    def _check_ram(self):
        if not psutil:
            return
        try:
            now = time.time()
            if (now - self._last_ram_alert_time) < self._ram_cooldown_seconds:
                return

            mem = psutil.virtual_memory()
            if mem.percent >= 88.0:
                procs = []
                for p in psutil.process_iter(['pid', 'name', 'memory_info']):
                    try:
                        mem_mb = p.info['memory_info'].rss / (1024 * 1024)
                        procs.append({'pid': p.info['pid'], 'name': p.info['name'], 'mem_mb': mem_mb})
                    except Exception:
                        pass

                if procs:
                    procs.sort(key=lambda x: x['mem_mb'], reverse=True)
                    top_p = procs[0]
                    ram_val = f"{round(top_p['mem_mb']/1024, 1)} GB" if top_p['mem_mb'] >= 1024 else f"{int(top_p['mem_mb'])} MB"

                    with self._lock:
                        self._pending_kill_process = top_p
                        self._last_ram_alert_time = now

                    alert = f"Boss, RAM usage {int(mem.percent)}% par pahunch gaya hai. {top_p['name']} sabse zyada memory ({ram_val}) le raha hai. Kya main ise close kar doon?"
                    self._speak_alert(alert, emotion="concerned")

        except Exception as e:
            print(f"[hardware_sentry ram error: {e}]")

    def _check_cpu(self):
        if not psutil:
            return
        try:
            now = time.time()
            cpu_pct = psutil.cpu_percent(interval=None)

            if cpu_pct >= 92.0:
                self._cpu_high_count += 1
            else:
                self._cpu_high_count = 0

            if self._cpu_high_count >= 4 and (now - self._last_cpu_alert_time) > 300:
                self._last_cpu_alert_time = now
                self._cpu_high_count = 0
                self._speak_alert(f"CPU usage lagatar {int(cpu_pct)}% par chal raha hai. Laptop garam ho sakta hai.", emotion="concerned")

        except Exception as e:
            print(f"[hardware_sentry cpu error: {e}]")

    def _check_disk(self):
        if not psutil:
            return
        try:
            now = time.time()
            if (now - self._last_disk_alert_time) > 3600:
                drive_letter = (os.path.splitdrive(os.path.abspath('.'))[0] + '\\') or "C:\\"
                usage = psutil.disk_usage(drive_letter)
                free_gb = usage.free / (1024 ** 3)
                if free_gb < 5.0:
                    self._last_disk_alert_time = now
                    self._speak_alert(f"Warning: {drive_letter} Drive mein sirf {round(free_gb, 1)} GB space bacha hai.", emotion="serious")
        except Exception:
            pass

    def has_pending_kill_action(self) -> bool:
        with self._lock:
            return bool(self._pending_kill_process)

    def kill_culprit_process(self) -> str:
        with self._lock:
            proc_info = self._pending_kill_process
            self._pending_kill_process = None

        if not proc_info or not psutil:
            return "Abhi koi heavy process close karne ke liye pending nahi hai."

        pid = proc_info['pid']
        name = proc_info['name']

        try:
            p = psutil.Process(pid)
            p.terminate()
            return f"{name} ko safely close kar diya gaya hai. RAM free ho gayi hai."
        except psutil.NoSuchProcess:
            return f"{name} pehle hi close ho chuka hai."
        except Exception as e:
            print(f"[kill_culprit_process error: {e}]")
            return f"{name} ko close karne mein permission error aa gaya."


sentry = HardwareSentry()
