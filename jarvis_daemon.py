# -*- coding: utf-8 -*-
"""
jarvis_daemon.py
================
24/7 Always-On Autonomous Background Daemon for RealJarvis.

Features:
1. Persistent Execution: Runs 24/7 independently of desktop Tkinter GUI.
2. Direct AI Integration: Uses Google Gemini (gemini-flash-lite-latest / gemini-3.8-flash) via .env credentials.
3. Persistent Mission Scheduler: SQLite database (daemon_memory.db) tracking alarms, recurring checks, and tasks.
4. Hybrid Local + Cloud Router: Dispatches cloud intelligence tasks instantly; delegates hardware actions to local PC or sends Wake-on-LAN if sleeping.
5. Proactive Background Worker: Evaluates scheduled missions and alerts every 30 seconds.
"""

import os
import sys
import time
import json
import sqlite3
import datetime
import threading
import subprocess
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config

try:
    from google import genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False

import remote_boot_wol

# Database location
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "daemon_memory.db")


class JarvisDaemon:
    def __init__(self):
        self.running = False
        self._worker_thread: Optional[threading.Thread] = None
        self.start_time = time.time()
        self._lock = threading.Lock()
        self._init_db()
        self._init_ai()

    def _init_db(self):
        """Initializes SQLite tables for persistent missions, telemetry, and audit logs."""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Missions / Scheduled Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS missions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    target_time REAL NOT NULL,
                    repeat_interval_sec INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending', -- pending, running, completed, failed
                    result TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            # System events and telemetry history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            conn.commit()

    def _init_ai(self):
        """Sets up Gemini API client using working model cascade."""
        self.gemini_key = getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        self.client = None
        if _GENAI_AVAILABLE and self.gemini_key:
            try:
                self.client = genai.Client(api_key=self.gemini_key)
            except Exception as e:
                print(f"[Daemon] AI Init Warning: {e}")

        # Cascade of models
        self.models = [
            "gemini-flash-lite-latest",
            "gemini-flash-latest",
            "gemini-3.8-flash",
            "gemini-3.5-flash",
        ]

    # ── MISSION / TASK SCHEDULER (SQLite PERSISTENT) ──────────────────────────

    def schedule_mission(self, task_name: str, prompt: str, delay_seconds: float = 0,
                         target_timestamp: float = 0, repeat_interval_sec: int = 0) -> int:
        """
        Schedules an autonomous mission to run at a specific time.
        Survives laptop restart and power-off because it is stored in SQLite.
        """
        now = time.time()
        if target_timestamp > 0:
            scheduled_for = target_timestamp
        else:
            scheduled_for = now + max(0, delay_seconds)

        with self._lock, sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO missions (task_name, prompt, target_time, repeat_interval_sec, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """, (task_name, prompt, scheduled_for, repeat_interval_sec, now, now))
            mission_id = cursor.lastrowid
            conn.commit()

        dt_str = datetime.datetime.fromtimestamp(scheduled_for).strftime("%I:%M:%S %p, %d %b")
        print(f"[Daemon] Mission #{mission_id} ('{task_name}') scheduled for {dt_str}")
        self.log_event("MISSION_SCHEDULED", f"ID={mission_id} Name='{task_name}' Target={dt_str}")
        return mission_id

    def list_missions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns list of pending and recent missions."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, task_name, prompt, target_time, repeat_interval_sec, status, result, created_at, updated_at
                FROM missions ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def log_event(self, event_type: str, detail: str):
        """Records an audit event in the database."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO audit_logs (event_type, detail, timestamp) VALUES (?, ?, ?)",
                               (event_type, detail, time.time()))
                conn.commit()
        except Exception:
            pass

    # ── AI REASONING / CORE DISPATCH ──────────────────────────────────────────

    def ask_ai(self, query: str, context: str = "") -> str:
        """Executes a cloud AI query using Gemini cascade."""
        if not self.client:
            return "AI Brain is offline (API Key missing or invalid)."

        system_instruction = (
            "You are RealJarvis 24/7 Cloud Daemon. You assist the user autonomously at all times.\n"
            "Keep answers concise, direct, helpful, and natural in Hinglish/English.\n"
            f"Context: {context}\n"
        )
        full_prompt = f"{system_instruction}\nUser Query: {query}"

        for model in self.models:
            try:
                resp = self.client.models.generate_content(
                    model=model,
                    contents=full_prompt
                )
                text = (resp.text or "").strip()
                if text:
                    return text
            except Exception as e:
                err_str = str(e)
                if "429" in err_str:
                    continue  # try next model
                elif "404" in err_str:
                    continue
                else:
                    print(f"[Daemon] AI {model} Error: {err_str[:60]}")

        return "Main abhi is request ko process nahi kar pa raha hoon. Kripya thodi der baad prayas karein."

    def execute_command(self, raw_text: str, sender: str = "remote") -> Dict[str, Any]:
        """
        Master Router: Analyzes incoming prompt from WhatsApp/REST/Webhook
        and decides whether to run a cloud task or local hardware task.
        """
        text = raw_text.strip()
        lower = text.lower()
        now_str = datetime.datetime.now().strftime("%I:%M %p")

        # 1. Telemetry / Health Check
        if any(w in lower for w in ("status", "health", "vitals", "uptime", "battery", "ram", "cpu")):
            status_data = self.get_telemetry()
            formatted = (
                f"[REALJARVIS 24/7 DAEMON STATUS]\n"
                f"* Time: {now_str}\n"
                f"* Daemon Uptime: {status_data['uptime_str']}\n"
                f"* Battery: {status_data.get('battery', 'N/A')}\n"
                f"* RAM: {status_data.get('ram', 'N/A')}\n"
                f"* CPU Load: {status_data.get('cpu', 'N/A')}\n"
                f"* Pending Missions: {status_data['pending_missions_count']}\n"
                f"* Status: Always-On Cloud & Local Engine Active"
            )
            return {"success": True, "type": "telemetry", "reply": formatted}

        # 2. Remote Power Control (Lock, Sleep, Restart, Shutdown)
        if any(w in lower for w in ("lock laptop", "laptop lock", "screen lock", "lock pc")):
            msg = remote_boot_wol.execute_power_action("lock")
            return {"success": True, "type": "power", "reply": f"[LOCK] {msg}"}

        if any(w in lower for w in ("sleep laptop", "laptop sleep", "pc sleep")):
            msg = remote_boot_wol.execute_power_action("sleep")
            return {"success": True, "type": "power", "reply": f"[SLEEP] {msg}"}

        # 3. Wake-on-LAN Information or Trigger
        if "wol" in lower or "wake on lan" in lower or "laptop on karo" in lower:
            wol_info = remote_boot_wol.get_wol_configuration_info()
            return {"success": True, "type": "wol", "reply": wol_info}

        # 4. Scheduling a Mission / Reminder
        # e.g.: "remind me in 10 minutes to submit assignment"
        if lower.startswith("remind me in") or lower.startswith("schedule:") or "baad yaad dilana" in lower:
            delay = 300  # default 5 minutes
            import re
            m = re.search(r"(\d+)\s*(minute|min|sec|second|ghanta|hour)", lower)
            if m:
                val = int(m.group(1))
                unit = m.group(2)
                if "hour" in unit or "ghanta" in unit:
                    delay = val * 3600
                elif "min" in unit:
                    delay = val * 60
                else:
                    delay = val

            clean_prompt = text
            mid = self.schedule_mission(task_name=f"User Reminder ({now_str})", prompt=clean_prompt, delay_seconds=delay)
            target_str = datetime.datetime.fromtimestamp(time.time() + delay).strftime("%I:%M:%S %p")
            return {
                "success": True,
                "type": "schedule",
                "reply": f"Mission #{mid} schedule kar diya hai!\nTarget Time: {target_str}\nMain time par automatically execute karke notify kar dunga."
            }

        # 5. General AI Intelligence & Reasoning
        ai_reply = self.ask_ai(text)
        return {"success": True, "type": "ai", "reply": ai_reply}

    # ── TELEMETRY & HARDWARE METRICS ──────────────────────────────────────────

    def get_telemetry(self) -> Dict[str, Any]:
        """Collects cross-platform telemetry."""
        uptime_sec = int(time.time() - self.start_time)
        hrs, rem = divmod(uptime_sec, 3600)
        mins, secs = divmod(rem, 60)
        uptime_str = f"{hrs}h {mins}m {secs}s"

        bat_str = "N/A"
        ram_str = "N/A"
        cpu_str = "N/A"

        if _PSUTIL_AVAILABLE:
            try:
                bat = psutil.sensors_battery()
                if bat:
                    plug = "Plugged (Charging)" if bat.power_plugged else "Discharging (Battery)"
                    bat_str = f"{int(bat.percent)}% ({plug})"
            except Exception:
                pass

            try:
                mem = psutil.virtual_memory()
                ram_str = f"{int(mem.percent)}% ({round(mem.used/(1024**3), 1)}GB used)"
            except Exception:
                pass

            try:
                cpu_str = f"{int(psutil.cpu_percent(interval=None))}%"
            except Exception:
                pass

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM missions WHERE status = 'pending'")
            pending_count = cursor.fetchone()[0]

        return {
            "uptime_seconds": uptime_sec,
            "uptime_str": uptime_str,
            "battery": bat_str,
            "ram": ram_str,
            "cpu": cpu_str,
            "pending_missions_count": pending_count,
            "ai_online": bool(self.client is not None),
        }

    # ── BACKGROUND AUTONOMOUS WORKER LOOP ─────────────────────────────────────

    def _worker_loop(self):
        """Persistent background thread checking scheduled missions every 30 seconds."""
        print("[Daemon] Persistent Mission Scheduler Worker thread started.")
        while self.running:
            try:
                now = time.time()
                due_missions = []
                with self._lock, sqlite3.connect(DB_PATH) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, task_name, prompt, target_time, repeat_interval_sec
                        FROM missions
                        WHERE status = 'pending' AND target_time <= ?
                    """, (now,))
                    due_missions = [dict(r) for r in cursor.fetchall()]

                    # Mark them running
                    for m in due_missions:
                        cursor.execute("UPDATE missions SET status = 'running', updated_at = ? WHERE id = ?", (now, m["id"]))
                    conn.commit()

                # Execute each due mission
                for m in due_missions:
                    self._execute_mission(m)

            except Exception as e:
                print(f"[Daemon] Worker loop error: {e}")

            time.sleep(15)  # check every 15 seconds

    def _execute_mission(self, mission: Dict[str, Any]):
        """Executes a due mission and records result."""
        mid = mission["id"]
        name = mission["task_name"]
        prompt = mission["prompt"]
        print(f"[Daemon] Executing due Mission #{mid}: '{name}'...")

        try:
            # Run with AI
            result = self.ask_ai(f"Execute autonomous scheduled mission: {prompt}")

            now = time.time()
            with self._lock, sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                if mission.get("repeat_interval_sec", 0) > 0:
                    # Reschedule recurring task
                    next_time = now + mission["repeat_interval_sec"]
                    cursor.execute("""
                        UPDATE missions
                        SET status = 'pending', target_time = ?, result = ?, updated_at = ?
                        WHERE id = ?
                    """, (next_time, result[:500], now, mid))
                else:
                    cursor.execute("""
                        UPDATE missions
                        SET status = 'completed', result = ?, updated_at = ?
                        WHERE id = ?
                    """, (result[:1000], now, mid))
                conn.commit()

            print(f"[Daemon] Mission #{mid} completed successfully.")
            self.log_event("MISSION_COMPLETED", f"ID={mid} Result preview: {result[:80]}")

            # Notify user via WhatsApp if phone is configured
            try:
                wa_phone = getattr(config, "WHATSAPP_MASTER_PHONE", "") or os.environ.get("WHATSAPP_MASTER_PHONE", "")
                if wa_phone:
                    from interview_mode import _send_whatsapp
                    notification = f"🔔 *SCHEDULED MISSION COMPLETED*\n• *Task:* {name}\n• *Outcome:* {result}"
                    _send_whatsapp(notification, wa_phone)
            except Exception as _e_wa:
                print(f"[Daemon] Proactive notify error: {_e_wa}")

        except Exception as e:
            print(f"[Daemon] Mission #{mid} execution failed: {e}")
            with self._lock, sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE missions SET status = 'failed', result = ?, updated_at = ? WHERE id = ?",
                               (str(e), time.time(), mid))
                conn.commit()

    def start(self):
        """Starts the daemon background services."""
        if self.running:
            return
        self.running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="daemon-worker")
        self._worker_thread.start()
        print("[Daemon] RealJarvis 24/7 Always-On Daemon is active.")

    def stop(self):
        """Stops the daemon background worker gracefully."""
        self.running = False
        print("[Daemon] RealJarvis Daemon stopped.")


# Singleton Instance
daemon = JarvisDaemon()


def get_daemon_status() -> Dict[str, Any]:
    return daemon.get_telemetry()


if __name__ == "__main__":
    print("=" * 60)
    print("  RealJarvis 24/7 Always-On Remote Daemon")
    print("=" * 60)
    daemon.start()

    # Test sample command
    test_result = daemon.execute_command("status")
    print("\n[Initial Test Status]")
    print(test_result["reply"])
    print("\nDaemon is running in foreground. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        daemon.stop()
        print("Daemon terminated.")
