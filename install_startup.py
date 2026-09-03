# -*- coding: utf-8 -*-
"""
install_startup.py
===================
EK BAAR chalao - ye Windows ke Startup folder me ek shortcut bana dega jo
"pythonw.exe" (bina console wala Python) se main.py ko chalayega. Iske baad
jab bhi laptop ON hoga / login hoga, Jarvis khud-ba-khud background me
start ho jayega - koi Command Prompt nahi dikhega, bas wo chota floating
icon.

Chalane ka tareeka (venv activate karke):
    python install_startup.py

Hatana ho toh:
    python install_startup.py remove
"""

import os
import sys
import subprocess

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(PROJECT_DIR, "main.py")
VENV_PYTHONW = os.path.join(PROJECT_DIR, "venv", "Scripts", "pythonw.exe")

STARTUP_DIR = os.path.join(
    os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu",
    "Programs", "Startup"
)
SHORTCUT_PATH = os.path.join(STARTUP_DIR, "RealJarvis.lnk")

# Agar venv ka pythonw mil jaye use karo (isolated deps), warna system wala
PYTHONW = VENV_PYTHONW if os.path.exists(VENV_PYTHONW) else sys.executable.replace("python.exe", "pythonw.exe")


VBS_TEMPLATE = """
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target}"
oLink.Arguments = "{args}"
oLink.WorkingDirectory = "{workdir}"
oLink.WindowStyle = 7
oLink.IconLocation = "{target}"
oLink.Save
"""


def install():
    os.makedirs(STARTUP_DIR, exist_ok=True)
    vbs_content = VBS_TEMPLATE.format(
        shortcut=SHORTCUT_PATH,
        target=PYTHONW,
        args=f'"{MAIN_SCRIPT}"',
        workdir=PROJECT_DIR,
    )
    vbs_path = os.path.join(PROJECT_DIR, "_make_shortcut.vbs")
    with open(vbs_path, "w") as f:
        f.write(vbs_content)

    subprocess.run(["cscript", "//nologo", vbs_path], check=True)
    os.remove(vbs_path)

    print("Ho gaya! Jarvis ab laptop start/login hote hi khud chalu hoga.")
    print(f"Shortcut yaha bana hai: {SHORTCUT_PATH}")
    print("Hataana ho toh: python install_startup.py remove")


def remove():
    if os.path.exists(SHORTCUT_PATH):
        os.remove(SHORTCUT_PATH)
        print("Startup se hata diya. Ab boot pe khud nahi chalega.")
    else:
        print("Koi startup shortcut mila hi nahi - shayad pehle se nahi tha.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        remove()
    else:
        install()
