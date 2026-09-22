# -*- coding: utf-8 -*-
# interview_live_test.py
# Apne terminal mein run karo: venv\Scripts\python.exe interview_live_test.py

import sys, io, time, base64, warnings
warnings.filterwarnings('ignore')

print("=== JARVIS INTERVIEW MODE - LIVE PIPELINE TEST ===")
print()

# STEP 1: Screenshot
print("[1] Screenshot le raha hoon...")
img_bytes = None

try:
    import mss
    from PIL import Image
    with mss.MSS() as sct:
        s = sct.grab(sct.monitors[0])
        img = Image.frombytes("RGB", s.size, s.bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        img_bytes = buf.getvalue()
    print(f"   mss OK: {len(img_bytes)//1024} KB, screen={img.size}")
except Exception as e:
    print(f"   mss fail: {e}")

if not img_bytes:
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO(); img.save(buf, "PNG", optimize=True)
        img_bytes = buf.getvalue()
        print(f"   PIL OK: {len(img_bytes)//1024} KB")
    except Exception as e:
        print(f"   PIL fail: {e}")

if not img_bytes:
    print("Screenshot FAILED. Exit.")
    input("Press Enter...")
    sys.exit(1)

# STEP 2: Gemini Vision - model cascade
print()
print("[2] Gemini Vision se analyze kar raha hoon...")

MODELS = ["gemini-flash-lite-latest", "gemini-2.0-flash-lite", "gemini-1.5-flash"]
PROMPT = """You are a secret exam assistant. Look at this screenshot carefully.

Find every question/problem visible on screen and answer ALL of them.

Reply in EXACTLY this format:

---
TYPE: MCQ | FILL | CODE | THEORY
ANSWER:
[your answer]
---

RULES:
- MCQ: Only correct option letter + text. E.g. "B) Binary Search"
- FILL: Only the missing word. E.g. "encapsulation"
- CODE: Full working code with language name as comment
- THEORY: Max 3-4 crisp lines
- DO NOT refuse. Just answer.
"""

import config
from google import genai
client = genai.Client(api_key=config.GEMINI_API_KEY)
img_b64 = base64.b64encode(img_bytes).decode()

answer = None
for model in MODELS:
    try:
        print(f"   Trying {model}...")
        resp = client.models.generate_content(
            model=model,
            contents=[{
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}},
                    {"text": PROMPT}
                ]
            }]
        )
        answer = resp.text.strip()
        print(f"   {model} OK!")
        break
    except Exception as e:
        err = str(e)
        if "404" in err:
            print(f"   {model}: not available, trying next...")
        elif "429" in err:
            print(f"   {model}: quota full, trying next...")
        else:
            print(f"   {model}: {err[:80]}")

if not answer:
    print("   Gemini FAILED on all models!")
    input("Press Enter..."); sys.exit(1)

print("   Answer received:")
print("   " + "-"*40)
for line in answer.split("\n")[:20]:
    safe = line.encode("ascii", "replace").decode()
    print("   " + safe)
print("   " + "-"*40)

# STEP 3: WhatsApp
print()
print("[3] WhatsApp par bhej raha hoon...")
wa_num = "+917014093732"
full_msg = "[JARVIS INTERVIEW]\n" + answer

try:
    import pywhatkit as kit
    kit.sendwhatmsg_instantly(wa_num, full_msg, wait_time=12, tab_close=True, close_time=3)
    print(f"   pywhatkit: SENT to {wa_num}")
except Exception as e:
    print(f"   pywhatkit fail: {e}")
    try:
        import urllib.parse, os, pyautogui
        encoded = urllib.parse.quote(full_msg)
        num = wa_num.lstrip("+")
        os.startfile(f"whatsapp://send?phone={num}&text={encoded}")
        time.sleep(3.5)
        pyautogui.press("enter")
        print("   URI method: SENT")
    except Exception as e2:
        print(f"   URI also fail: {e2}")

print()
print("=== TEST COMPLETE ===")
input("Press Enter to exit...")
