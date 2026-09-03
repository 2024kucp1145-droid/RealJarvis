# -*- coding: utf-8 -*-
"""
download_janitor.py
====================
Phase 4: Proactive Download & Desktop File Janitor.

Features:
1. Real-time background watcher on Downloads (including subfolders like Telegram Desktop) & Desktop.
2. Detects new completed downloads (PDF, ZIP, Code, Docs, Media, Installers).
3. Proactive voice heads-up: "Boss, aapne <file> download kiya hai. Kya open karoon ya organize kar doon?"
4. 1-word voice actions:
   - "open karo" -> Opens the file immediately.
   - "organize karo" -> Moves to appropriate category folder.
   - "extract karo" -> Unzips archive and reveals files.
"""

import os
import time
import glob
import shutil
import zipfile
import threading
import datetime

CATEGORY_FOLDERS = {
    "documents": [".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".txt", ".epub"],
    "code": [".py", ".cpp", ".c", ".java", ".js", ".ts", ".html", ".css", ".json", ".sql", ".rs", ".go"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "images": [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"],
    "media": [".mp4", ".mkv", ".mp3", ".wav", ".avi", ".mov"],
    "installers": [".exe", ".msi", ".iso"]
}


class DownloadJanitor:
    def __init__(self, voice=None, ai=None, gui=None, speak_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        self.running = False
        self._thread = None
        self.enabled = True

        self.downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        self.documents_dir = os.path.join(os.path.expanduser("~"), "Documents")

        self.watch_dirs = [self.downloads_dir, self.desktop_dir]
        telegram_dir = os.path.join(self.downloads_dir, "Telegram Desktop")
        if os.path.exists(telegram_dir):
            self.watch_dirs.append(telegram_dir)

        # State tracking: maps file_path -> modified_time
        self._known_file_mtimes = {}
        self._pending_file = None
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

        # Snapshot current files and mtimes as baseline
        self._snapshot_baseline()

        self.running = True
        self._thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._thread.start()
        print(f"[download_janitor] Proactive Download Janitor started. Watching {len(self.watch_dirs)} directories.")

    def stop(self):
        self.running = False

    def _snapshot_baseline(self):
        self._known_file_mtimes.clear()
        for wdir in self.watch_dirs:
            if not os.path.exists(wdir):
                continue
            try:
                for entry in os.listdir(wdir):
                    fpath = os.path.join(wdir, entry)
                    if os.path.isfile(fpath):
                        try:
                            self._known_file_mtimes[fpath] = os.path.getmtime(fpath)
                        except Exception:
                            pass
            except Exception:
                pass

    def _speak_alert(self, message: str, emotion: str = "happy", priority: str = "normal"):
        """Thread-safe proactive speech alert."""
        try:
            import workspace_harmonizer
            if not workspace_harmonizer.harmonizer.can_speak_proactively(priority=priority):
                return
        except Exception:
            pass
        try:
            if self.speak_fn:
                self.speak_fn(message, emotion=emotion)
            elif self.voice:
                self.voice.speak(message, interruptible=True, emotion=emotion)
        except Exception as e:
            print(f"[download_janitor alert error: {e}]")

    def _get_category(self, ext: str) -> str:
        ext_lower = ext.lower()
        for cat, ext_list in CATEGORY_FOLDERS.items():
            if ext_lower in ext_list:
                return cat
        return "other"

    def _watcher_loop(self):
        while self.running:
            try:
                if not self.enabled:
                    time.sleep(2.0)
                    continue

                for wdir in self.watch_dirs:
                    if not os.path.exists(wdir):
                        continue

                    try:
                        entries = os.listdir(wdir)
                    except Exception:
                        continue

                    for fname in entries:
                        # Ignore temporary / in-progress downloads
                        if (fname.endswith(".crdownload") or fname.endswith(".tmp") or
                            fname.endswith(".part") or fname.startswith(".") or
                            fname.startswith("~$")):
                            continue

                        fpath = os.path.join(wdir, fname)
                        if not os.path.isfile(fpath):
                            continue

                        try:
                            mtime = os.path.getmtime(fpath)
                            size = os.path.getsize(fpath)
                        except Exception:
                            continue

                        # Check if this file is genuinely new or modified
                        if fpath not in self._known_file_mtimes:
                            # Verify file is not empty (still being created)
                            if size == 0:
                                continue

                            # Register file
                            self._known_file_mtimes[fpath] = mtime
                            _, ext = os.path.splitext(fname)
                            category = self._get_category(ext)

                            size_kb = size / 1024
                            size_str = f"{round(size_kb/1024, 1)} MB" if size_kb >= 1024 else f"{int(size_kb)} KB"

                            with self._lock:
                                self._pending_file = {
                                    "path": fpath,
                                    "name": fname,
                                    "ext": ext,
                                    "category": category,
                                    "size_str": size_str,
                                    "timestamp": datetime.datetime.now()
                                }

                            print(f"[download_janitor] New download detected: {fname} ({size_str})")

                            # Proactive Voice Alert
                            if category == "archives":
                                msg = f"Boss, aapne '{fname}' download kiya hai. Kya main ise extract ya open kar doon?"
                            elif category == "documents":
                                msg = f"Boss, aapne '{fname}' document download kiya hai. Kya ise open karoon ya folder mein organize kar doon?"
                            elif category == "code":
                                msg = f"Boss, naya code file '{fname}' download hua hai. Kya main ise open kar doon?"
                            else:
                                msg = f"Boss, aapne '{fname}' ({size_str}) download kiya hai. Kya ise open karoon?"

                            self._speak_alert(msg, emotion="happy")
                            break

            except Exception as e:
                print(f"[download_janitor loop error: {e}]")

            time.sleep(1.8)

    def has_pending_file_action(self) -> bool:
        with self._lock:
            if not self._pending_file:
                return False
            elapsed = (datetime.datetime.now() - self._pending_file["timestamp"]).total_seconds()
            return elapsed < 300

    def open_pending_file(self) -> str:
        with self._lock:
            pfile = self._pending_file
            self._pending_file = None

        if not pfile or not os.path.exists(pfile["path"]):
            return "File nahi mili ya pehle hi move ho chuki hai."

        try:
            os.startfile(pfile["path"])
            return f"{pfile['name']} open kar diya hai."
        except Exception as e:
            print(f"[open_pending_file error: {e}]")
            return "File open karne mein error aa gaya."

    def organize_pending_file(self) -> str:
        with self._lock:
            pfile = self._pending_file
            self._pending_file = None

        if not pfile or not os.path.exists(pfile["path"]):
            return "File nahi mili ya pehle hi move ho chuki hai."

        cat = pfile["category"]
        src = pfile["path"]
        fname = pfile["name"]

        if cat == "documents":
            target_dir = os.path.join(self.documents_dir, "Study_Documents")
        elif cat == "code":
            target_dir = os.path.join(self.documents_dir, "Code_Downloads")
        elif cat == "images":
            target_dir = os.path.join(os.path.expanduser("~"), "Pictures", "Downloaded_Images")
        elif cat == "media":
            target_dir = os.path.join(os.path.expanduser("~"), "Videos", "Downloaded_Media")
        elif cat == "archives":
            target_dir = os.path.join(self.downloads_dir, "Extracted_Archives")
        else:
            target_dir = os.path.join(self.documents_dir, "Organized_Downloads")

        try:
            os.makedirs(target_dir, exist_ok=True)
            dst = os.path.join(target_dir, fname)
            shutil.move(src, dst)
            folder_name = os.path.basename(target_dir)
            return f"{fname} ko {folder_name} folder mein organize kar diya hai."
        except Exception as e:
            print(f"[organize_pending_file error: {e}]")
            return "File move karne mein error aa gaya."

    def extract_pending_archive(self) -> str:
        with self._lock:
            pfile = self._pending_file
            self._pending_file = None

        if not pfile or not os.path.exists(pfile["path"]):
            return "Archive file nahi mili."

        src = pfile["path"]
        fname = pfile["name"]
        extract_to = os.path.join(self.downloads_dir, os.path.splitext(fname)[0])

        try:
            os.makedirs(extract_to, exist_ok=True)
            with zipfile.ZipFile(src, "r") as z:
                z.extractall(extract_to)
            os.startfile(extract_to)
            return f"{fname} extract kar diya hai aur folder open kar diya."
        except Exception as e:
            print(f"[extract_pending_archive error: {e}]")
            return "Extract karne mein error aa gaya."


janitor = DownloadJanitor()
