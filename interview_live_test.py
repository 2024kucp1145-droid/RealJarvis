# -*- coding: utf-8 -*-
# interview_live_test.py
# Run this in YOUR terminal: venv\Scripts\python.exe interview_live_test.py

import sys, io, time, base64, warnings
warnings.filterwarnings('ignore')

print('=== JARVIS INTERVIEW MODE - LIVE PIPELINE TEST ===')
print()

# STEP 1: Screenshot
print('[1] Screenshot le raha hoon...')
img_bytes = None

try:
    import mss
    from PIL import Image
    with mss.MSS() as sct:
        s = sct.grab(sct.monitors[0])
        img = Image.frombytes('RGB', s.size, s.bgra, 'raw', 'BGRX')
        buf = io.BytesIO()
        img.save(buf, 'PNG', optimize=True)
        img_bytes = buf.getvalue()
    print(f'   mss OK: {len(img_bytes)//1024} KB, screen={img.size}')
except Exception as e:
    print(f'   mss fail: {e}')

if not img_bytes:
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        buf = io.BytesIO(); img.save(buf, 'PNG', optimize=True)
        img_bytes = buf.getvalue()
        print(f'   PIL OK: {len(img_bytes)//1024} KB')
    except Exception as e:
        print(f'   PIL fail: {e}')

if not img_bytes:
    print('Screenshot FAILED. Exit.')
    input('Press Enter...')
    sys.exit(1)

# STEP 2: Gemini Vision
print()
print('[2] Gemini Vision se analyze kar raha hoon...')
try:
    import config
    from google import genai

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    img_b64 = base64.b64encode(img_bytes).decode()

    prompt = """You are a secret exam assistant. Look at this screenshot carefully.

Find every question/problem visible on screen and answer ALL of them.

Reply in EXACTLY this format (no extra text before or after):

---
TYPE: MCQ | FILL | CODE | THEORY
ANSWER:
[your answer]
---

RULES:
- MCQ: Only correct option letter + text
- FILL: Only the missing word/phrase
- CODE: Full working code with language name
- THEORY: Max 3-4 crisp lines
"""

    resp = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[{
            'role': 'user',
            'parts': [
                {'inline_data': {'mime_type': 'image/png', 'data': img_b64}},
                {'text': prompt}
            ]
        }]
    )
    answer = resp.text.strip()
    print('   Gemini Answer:')
    print('   ' + '-'*40)
    for line in answer.split('\n')[:20]:
        print('   ' + line)
    print('   ' + '-'*40)
except Exception as e:
    print(f'   Gemini FAIL: {e}')
    import traceback; traceback.print_exc()
    input('Press Enter...'); sys.exit(1)

# STEP 3: WhatsApp bhejo
print()
print('[3] WhatsApp par bhej raha hoon...')
wa_num = '+917014093732'
try:
    import pywhatkit as kit
    full_msg = '[JARVIS INTERVIEW]\n' + answer
    kit.sendwhatmsg_instantly(wa_num, full_msg, wait_time=12, tab_close=True, close_time=3)
    print(f'   WhatsApp OK! Sent to {wa_num}')
except Exception as e:
    print(f'   pywhatkit fail: {e}')
    print(f'   Trying URI method...')
    import urllib.parse, os
    encoded = urllib.parse.quote('[JARVIS INTERVIEW]\n' + answer)
    num = wa_num.lstrip('+')
    uri = f'whatsapp://send?phone={num}&text={encoded}'
    try:
        os.startfile(uri)
        time.sleep(3)
        import pyautogui
        pyautogui.press('enter')
        print('   URI method OK!')
    except Exception as e2:
        print(f'   URI also fail: {e2}')

print()
print('=== TEST COMPLETE ===')
input('Press Enter to exit...')
