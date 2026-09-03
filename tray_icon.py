# -*- coding: utf-8 -*-
"""
tray_icon.py
============
Jarvis background me chalta hai, taskbar ke neeche system tray me ek chota
icon dikhta hai. Right-click karke "Quit" se band kar sakte ho.
"""

import threading

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None


def _make_icon_image():
    img = Image.new("RGB", (64, 64), "black")
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill="deepskyblue")
    draw.text((22, 22), "J", fill="white")
    return img


def start_tray(on_quit):
    """Alag thread me tray icon chalata hai. on_quit() call hoga jab user Quit dabaye."""
    if not pystray:
        print("[pystray install nahi hai, tray icon skip - Jarvis phir bhi chalega]")
        return

    def _quit(icon, item):
        icon.stop()
        on_quit()

    menu = pystray.Menu(pystray.MenuItem("Jarvis chal raha hai", None, enabled=False),
                         pystray.MenuItem("Quit", _quit))
    icon = pystray.Icon("Jarvis", _make_icon_image(), "Real Jarvis", menu)
    threading.Thread(target=icon.run, daemon=True).start()
