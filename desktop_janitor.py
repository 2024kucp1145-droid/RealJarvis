# -*- coding: utf-8 -*-
"""
desktop_janitor.py
==================
Phase 9: Autonomous Desktop Janitor & Cleanup Automations.

Features:
1. Smart Desktop Organizer — type-based auto-sort into subfolders.
2. Old File Graveyard Cleaner — Downloads 30-day+ large files -> Recycle Bin.
3. Duplicate File Finder — same-name or same-size duplicates in Downloads/Desktop.
4. Live Disk Space Reporter — C: drive breakdown + top space-hogging folders.
"""

import os
import time
import shutil
import hashlib
import threading
import datetime
import send2trash

# File category map: extension -> subfolder name
FILE_CATEGORIES = {
    # Documents
    ".pdf":  "Documents",
    ".docx": "Documents",
    ".doc":  "Documents",
    ".txt":  "Documents",
    ".pptx": "Documents",
    ".ppt":  "Documents",
    ".xlsx": "Documents",
    ".xls":  "Documents",
    ".csv":  "Documents",

    # Code
    ".py":   "Code",
    ".js":   "Code",
    ".ts":   "Code",
    ".html": "Code",
    ".css":  "Code",
    ".java": "Code",
    ".cpp":  "Code",
    ".c":    "Code",
    ".go":   "Code",
    ".rs":   "Code",
    ".json": "Code",
    ".yaml": "Code",
    ".yml":  "Code",
    ".sh":   "Code",
    ".bat":  "Code",

    # Images / Screenshots
    ".png":  "Screenshots",
    ".jpg":  "Screenshots",
    ".jpeg": "Screenshots",
    ".gif":  "Screenshots",
    ".bmp":  "Screenshots",
    ".webp": "Screenshots",
    ".svg":  "Screenshots",

    # Videos
    ".mp4":  "Videos",
    ".mkv":  "Videos",
    ".avi":  "Videos",
    ".mov":  "Videos",
    ".wmv":  "Videos",

    # Audio
    ".mp3":  "Audio",
    ".wav":  "Audio",
    ".flac": "Audio",

    # Archives
    ".zip":  "Archives",
    ".rar":  "Archives",
    ".7z":   "Archives",
    ".tar":  "Archives",
    ".gz":   "Archives",

    # Installers
    ".exe":  "Installers",
    ".msi":  "Installers",
    ".dmg":  "Installers",
    ".deb":  "Installers",
}


class DesktopJanitor:
    def __init__(self, voice=None, ai=None, gui=None, speak_fn=None):
        self.voice = voice
        self.ai = ai
        self.gui = gui
        self.speak_fn = speak_fn
        self.running = False
        self.enabled = True

        self._pending_old_files = []      # For follow-up "haan daal do"
        self._pending_duplicates = []     # For follow-up "haan delete karo"
        self._lock = threading.Lock()

        # Common paths
        self.desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        self.downloads = os.path.join(os.path.expanduser("~"), "Downloads")

    def start(self, voice=None, ai=None, gui=None, speak_fn=None):
        if voice:   self.voice = voice
        if ai:      self.ai = ai
        if gui:     self.gui = gui
        if speak_fn: self.speak_fn = speak_fn
        self.running = True
        print("[desktop_janitor] Desktop Janitor started.")

    def stop(self):
        self.running = False

    def _speak(self, message: str, emotion: str = "happy"):
        print(f"[desktop_janitor] {message}")
        if self.speak_fn:
            self.speak_fn(message, emotion=emotion)
        elif self.voice:
            self.voice.speak(message, interruptible=True, emotion=emotion)

    # =========================================================================
    # 1. SMART DESKTOP ORGANIZER
    # =========================================================================
    def organize_desktop(self) -> str:
        if not os.path.isdir(self.desktop):
            return "Desktop folder nahi mila."

        moved = 0
        skipped = 0
        folders_created = set()

        for fname in os.listdir(self.desktop):
            fpath = os.path.join(self.desktop, fname)

            # Skip folders, hidden files, shortcuts
            if os.path.isdir(fpath):
                continue
            if fname.startswith(".") or fname.endswith(".lnk"):
                continue

            ext = os.path.splitext(fname)[1].lower()
            category = FILE_CATEGORIES.get(ext, "Misc")

            dest_dir = os.path.join(self.desktop, category)
            os.makedirs(dest_dir, exist_ok=True)
            folders_created.add(category)

            dest_path = os.path.join(dest_dir, fname)
            if os.path.exists(dest_path):
                base, extension = os.path.splitext(fname)
                dest_path = os.path.join(dest_dir, f"{base}_{int(time.time())}{extension}")

            try:
                shutil.move(fpath, dest_path)
                moved += 1
            except Exception as e:
                print(f"[desktop_janitor move error: {e}]")
                skipped += 1

        if moved == 0:
            return "Desktop already clean hai, koi file organize karne ke liye nahi mili."

        folders_str = ", ".join(sorted(folders_created))
        return f"Desktop organize ho gaya! {moved} files ko {len(folders_created)} folders mein sort kiya: {folders_str}."

    # =========================================================================
    # 2. OLD FILE GRAVEYARD CLEANER
    # =========================================================================
    def find_old_downloads(self, days_old: int = 30, min_size_mb: float = 20.0) -> str:
        if not os.path.isdir(self.downloads):
            return "Downloads folder nahi mila."

        cutoff = time.time() - (days_old * 86400)
        old_files = []

        for fname in os.listdir(self.downloads):
            fpath = os.path.join(self.downloads, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                stat = os.stat(fpath)
                age_days = (time.time() - stat.st_mtime) / 86400
                size_mb = stat.st_size / (1024 * 1024)
                if stat.st_mtime < cutoff and size_mb >= min_size_mb:
                    old_files.append({
                        "path": fpath,
                        "name": fname,
                        "size_mb": round(size_mb, 1),
                        "age_days": int(age_days)
                    })
            except Exception:
                continue

        if not old_files:
            return f"Downloads mein koi {days_old} din se purani badi file nahi mili. Sab clean hai!"

        total_mb = sum(f["size_mb"] for f in old_files)
        total_str = f"{round(total_mb/1024, 1)} GB" if total_mb >= 1024 else f"{int(total_mb)} MB"

        with self._lock:
            self._pending_old_files = old_files

        return (
            f"Boss, Downloads mein {len(old_files)} purani files hain jo {total_str} le rahi hain. "
            f"Kya inhe Recycle Bin mein daal doon? Bolo 'haan daal do'."
        )

    def trash_old_downloads(self) -> str:
        with self._lock:
            files = list(self._pending_old_files)
            self._pending_old_files = []

        if not files:
            return "Koi pending purani file nahi hai."

        trashed = 0
        failed = 0
        for f in files:
            try:
                send2trash.send2trash(f["path"])
                trashed += 1
            except Exception as e:
                print(f"[trash error: {f['name']}: {e}]")
                failed += 1

        result = f"{trashed} purani files Recycle Bin mein daal di gayi hain."
        if failed:
            result += f" {failed} files move nahi ho payin."
        return result

    def has_pending_old_files(self) -> bool:
        with self._lock:
            return bool(self._pending_old_files)

    # =========================================================================
    # 3. DUPLICATE FILE FINDER
    # =========================================================================
    def find_duplicates(self) -> str:
        search_dirs = [self.desktop, self.downloads]
        seen_names = {}    # basename -> [paths]
        seen_sizes = {}    # size -> [paths]
        duplicates = []

        for folder in search_dirs:
            if not os.path.isdir(folder):
                continue
            for fname in os.listdir(folder):
                fpath = os.path.join(folder, fname)
                if not os.path.isfile(fpath):
                    continue
                try:
                    size = os.path.getsize(fpath)
                    # Name duplicates
                    seen_names.setdefault(fname, []).append(fpath)
                    # Size duplicates (only for files > 100KB)
                    if size > 102400:
                        seen_sizes.setdefault(size, []).append(fpath)
                except Exception:
                    continue

        dup_by_name = {n: paths for n, paths in seen_names.items() if len(paths) > 1}
        dup_by_size = {s: paths for s, paths in seen_sizes.items() if len(paths) > 1}

        for name, paths in dup_by_name.items():
            duplicates.extend(paths[1:])   # Keep first, flag rest
        for size, paths in dup_by_size.items():
            for p in paths[1:]:
                if p not in duplicates:
                    duplicates.append(p)

        if not duplicates:
            return "Desktop aur Downloads mein koi duplicate file nahi mili. Sab unique hai!"

        total_mb = sum(os.path.getsize(p) for p in duplicates if os.path.exists(p)) / (1024 * 1024)
        size_str = f"{round(total_mb/1024, 1)} GB" if total_mb >= 1024 else f"{int(total_mb)} MB"

        with self._lock:
            self._pending_duplicates = duplicates

        return (
            f"Boss, {len(duplicates)} possible duplicate files mili hain jo {size_str} le rahi hain. "
            f"Kya inhe Recycle Bin mein daal doon? Bolo 'haan duplicates hatao'."
        )

    def trash_duplicates(self) -> str:
        with self._lock:
            files = list(self._pending_duplicates)
            self._pending_duplicates = []

        if not files:
            return "Koi pending duplicate nahi hai."

        trashed = 0
        for fpath in files:
            try:
                send2trash.send2trash(fpath)
                trashed += 1
            except Exception as e:
                print(f"[trash duplicate error: {e}]")

        return f"{trashed} duplicate files Recycle Bin mein daal di gayi hain."

    def has_pending_duplicates(self) -> bool:
        with self._lock:
            return bool(self._pending_duplicates)

    # =========================================================================
    # 4. LIVE DISK SPACE REPORTER
    # =========================================================================
    def report_disk_space(self) -> str:
        try:
            import psutil
            usage = psutil.disk_usage("C:\\")
            total_gb = round(usage.total / (1024 ** 3), 1)
            used_gb  = round(usage.used  / (1024 ** 3), 1)
            free_gb  = round(usage.free  / (1024 ** 3), 1)
            pct      = usage.percent

            # Top space-hogging user folders
            user_home = os.path.expanduser("~")
            folders_to_check = {
                "Downloads": self.downloads,
                "Desktop":   self.desktop,
                "Documents": os.path.join(user_home, "Documents"),
                "Videos":    os.path.join(user_home, "Videos"),
                "Pictures":  os.path.join(user_home, "Pictures"),
            }

            folder_sizes = []
            for name, path in folders_to_check.items():
                if os.path.isdir(path):
                    try:
                        size = sum(
                            os.path.getsize(os.path.join(dp, f))
                            for dp, dn, fnames in os.walk(path)
                            for f in fnames
                            if os.path.isfile(os.path.join(dp, f))
                        )
                        folder_sizes.append((name, round(size / (1024 ** 3), 2)))
                    except Exception:
                        pass

            folder_sizes.sort(key=lambda x: x[1], reverse=True)
            top3 = folder_sizes[:3]
            top3_str = ", ".join(f"{n} ({s} GB)" for n, s in top3) if top3 else "N/A"

            return (
                f"C Drive ka breakdown: Total {total_gb} GB, "
                f"Use ho raha hai {used_gb} GB ({int(pct)}%), "
                f"Free {free_gb} GB. "
                f"Sabse zyada space le rahe hain: {top3_str}."
            )
        except Exception as e:
            return f"Disk space check karne mein error: {e}"


janitor = DesktopJanitor()
