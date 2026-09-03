# -*- coding: utf-8 -*-
"""
file_commands.py
=================
File Explorer wale kaam - folder banana, rename, copy, delete, zip.
Sab DEFAULT_WORKING_FOLDER (config.py, default Documents) ke andar hote hain,
jab tak specific path na diya jaye.
"""

import os
import shutil
import zipfile
import subprocess

import config


def _resolve(name: str) -> str:
    if os.path.isabs(name):
        return name
    return os.path.join(config.DEFAULT_WORKING_FOLDER, name)


def create_folder(voice, name="New Folder", **kw):
    path = _resolve(name)
    os.makedirs(path, exist_ok=True)
    voice.speak(f"{name} naam ka folder ban gaya.")


def rename(voice, old_name="", new_name="", **kw):
    if not old_name or not new_name:
        voice.speak("Purana aur naya naam dono batayein.")
        return
    os.rename(_resolve(old_name), _resolve(new_name))
    voice.speak(f"{old_name} ka naam badal ke {new_name} kar diya.")


def copy_file(voice, src="", dst="", **kw):
    if not src or not dst:
        voice.speak("Source aur destination dono batayein.")
        return
    shutil.copy2(_resolve(src), _resolve(dst))
    voice.speak("File copy kar di maine.")


def delete_file(voice, name="", **kw):
    if not name:
        voice.speak("Kaunsi file delete karu?")
        return
    path = _resolve(name)
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)
    voice.speak(f"{name} delete kar di.")


def zip_file(voice, name="", **kw):
    if not name:
        voice.speak("Kaunsi file/folder zip karu?")
        return
    path = _resolve(name)
    out = path + ".zip"
    if os.path.isdir(path):
        shutil.make_archive(path, "zip", path)
    else:
        with zipfile.ZipFile(out, "w") as z:
            z.write(path, os.path.basename(path))
    voice.speak("Zip ban gayi.")


def extract_zip(voice, name="", **kw):
    if not name:
        voice.speak("Kaunsi zip extract karu?")
        return
    path = _resolve(name)
    with zipfile.ZipFile(path, "r") as z:
        z.extractall(os.path.dirname(path))
    voice.speak("Extract kar diya maine.")


def open_downloads(voice, **kw):
    path = os.path.join(os.path.expanduser("~"), "Downloads")
    subprocess.Popen(f'explorer "{path}"', shell=True)
    voice.speak("Downloads folder khol diya.")


def open_documents(voice, **kw):
    subprocess.Popen(f'explorer "{config.DEFAULT_WORKING_FOLDER}"', shell=True)
    voice.speak("Documents folder khol diya.")


def open_music(voice, **kw):
    path = os.path.join(os.path.expanduser("~"), "Music")
    subprocess.Popen(f'explorer "{path}"', shell=True)
    voice.speak("Music folder khol diya.")


def open_videos(voice, **kw):
    path = os.path.join(os.path.expanduser("~"), "Videos")
    subprocess.Popen(f'explorer "{path}"', shell=True)
    voice.speak("Videos folder khol diya.")


def empty_recycle_bin(voice, **kw):
    try:
        import winshell
        winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        voice.speak("Recycle bin khali kar diya.")
    except Exception:
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"], timeout=3)
            voice.speak("Recycle bin khali kar diya.")
        except Exception:
            voice.speak("Recycle bin khali nahi ho paya.")


def find_file(voice, name="", **kw):
    """Fast, non-blocking file search across Desktop, Documents, Downloads."""
    if not name:
        voice.speak("Kaunsi file dhoondhni hai, naam batayein?")
        return

    name_clean = name.strip().lower()
    search_dirs = [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "Documents"),
        os.path.join(os.path.expanduser("~"), "Downloads"),
        config.DEFAULT_WORKING_FOLDER,
    ]

    found = []
    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        try:
            for root, _, files in os.walk(sdir):
                for f in files:
                    if name_clean in f.lower():
                        found.append(os.path.join(root, f))
                        if len(found) >= 3:
                            break
                if len(found) >= 3:
                    break
        except Exception:
            pass

    if found:
        first_match = found[0]
        voice.speak(f"File mil gayi: {os.path.basename(first_match)} folder {os.path.basename(os.path.dirname(first_match))} mein.")
    else:
        voice.speak(f"{name} naam ki file nahi mili.")


def open_file(voice, name="", **kw):
    """File dhoondh kar turant open karta hai."""
    if not name:
        voice.speak("Kaunsi file kholu, naam batayein?")
        return

    name_clean = name.strip().lower()
    search_dirs = [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "Documents"),
        os.path.join(os.path.expanduser("~"), "Downloads"),
        config.DEFAULT_WORKING_FOLDER,
    ]

    # Check direct path first
    if os.path.isfile(name):
        try:
            os.startfile(name)
            voice.speak(f"{os.path.basename(name)} khol diya.")
            return
        except Exception as e:
            print(f"[open_file direct error: {e}]")

    # Search in common user folders
    matched_file = None
    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        try:
            for root, _, files in os.walk(sdir):
                for f in files:
                    if name_clean in f.lower():
                        matched_file = os.path.join(root, f)
                        break
                if matched_file:
                    break
        except Exception:
            pass
        if matched_file:
            break

    if matched_file:
        try:
            os.startfile(matched_file)
            voice.speak(f"{os.path.basename(matched_file)} khol diya.")
        except Exception as e:
            voice.speak("File kholne mein error aa gaya.")
            print(f"[open_file error: {e}]")
    else:
        voice.speak(f"{name} file nahi mili.")

