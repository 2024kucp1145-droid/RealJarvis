# -*- coding: utf-8 -*-
# interview_test.py - Run this directly to test interview mode
# Double-click this file OR: python interview_test.py

import sys, io, time, os

print("=== JARVIS INTERVIEW MODE TEST ===")
print("Ye script test karega ki screenshot kaam karta hai ya nahi.")
print()

results = []

# Test 1: mss
try:
    import mss
    from PIL import Image
    with mss.mss() as sct:
        s = sct.grab(sct.monitors[0])
        img = Image.frombytes("RGB", s.size, s.bgra, "raw", "BGRX")
        buf = io.BytesIO(); img.save(buf, "PNG")
        size = len(buf.getvalue())
    results.append(("mss", True, f"{size//1024} KB"))
except Exception as e:
    results.append(("mss", False, str(e)[:60]))

# Test 2: PIL ImageGrab
try:
    from PIL import ImageGrab
    img = ImageGrab.grab()
    buf = io.BytesIO(); img.save(buf, "PNG")
    results.append(("PIL ImageGrab", True, f"{len(buf.getvalue())//1024} KB"))
except Exception as e:
    results.append(("PIL ImageGrab", False, str(e)[:60]))

# Test 3: pyautogui
try:
    import pyautogui
    img = pyautogui.screenshot()
    buf = io.BytesIO(); img.save(buf, "PNG")
    results.append(("pyautogui", True, f"{len(buf.getvalue())//1024} KB"))
except Exception as e:
    results.append(("pyautogui", False, str(e)[:60]))

# Test 4: Clipboard PrintScreen
try:
    import ctypes, win32clipboard, win32con, struct
    _VK = 0x2C
    ctypes.windll.user32.keybd_event(_VK, 0, 0, 0)
    ctypes.windll.user32.keybd_event(_VK, 0, 0x0002, 0)
    time.sleep(0.3)
    win32clipboard.OpenClipboard()
    avail = win32clipboard.IsClipboardFormatAvailable(win32con.CF_DIB)
    if avail:
        data = win32clipboard.GetClipboardData(win32con.CF_DIB)
        win32clipboard.CloseClipboard()
        results.append(("Clipboard PrtScr", True, f"{len(data)//1024} KB raw DIB"))
    else:
        win32clipboard.CloseClipboard()
        results.append(("Clipboard PrtScr", False, "CF_DIB not available"))
except Exception as e:
    results.append(("Clipboard PrtScr", False, str(e)[:60]))

print("RESULTS:")
any_ok = False
for name, ok, info in results:
    status = "OK" if ok else "FAIL"
    print(f"  {name}: {status} - {info}")
    if ok: any_ok = True

print()
if any_ok:
    print("SUCCESS! At least one screenshot method works.")
    print("Interview Mode will work on this machine.")
else:
    print("PROBLEM: No screenshot method working.")
    print("Possible fix: Run as Administrator")

input("\nPress Enter to exit...")
