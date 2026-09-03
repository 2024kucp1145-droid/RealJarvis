# -*- coding: utf-8 -*-
"""
custom_functions.py
====================
Ye file Jarvis KHUD likhta hai - jab tum "modify yourself" bolke koi naya
feature maangte ho, AI jo code likhta hai, wo yahan append hota hai.

Manually bhi edit kar sakte ho agar chaho, lekin normally isse Jarvis khud
manage karta hai.
"""


def take_screenshot(voice, **kw):
    import pyautogui
    import datetime
    import os
    try:
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"screenshots/screenshot_{timestamp}.png"
        pyautogui.screenshot(filename)
        voice.speak("Maine screen ka photo khich liya hai, aapke folder mein save ho gaya.")
    except Exception as e:
        voice.speak("Mujhse screenshot lene mein galti ho gayi, shayad koi error hai.")


def change_assistant_name(voice, **kw):
    try:
        import config
        config.ASSISTANT_NAME = "Memo"
        voice.speak("Theek hai, ab se aap mujhe Memo bula sakte hain. Main ab Memo hoon.")
    except Exception as e:
        voice.speak("Maaf kijiye, main apna naam nahi badal payi. Koi takneeki dikkat hai.")


def generate_and_save_ai_image(voice, **kw):
    import os
    from PIL import Image
    from io import BytesIO
    from google import genai
    
    prompt = kw.get("prompt") or kw.get("text")
    if not prompt:
        voice.speak("Bhai, aapne yeh toh bataya hi nahi ki kafi tasveer banani hai.")
        return
        
    try:
        voice.speak("Thoda rukiye, main aapke liye nayi tasveer bana rahi hoon.")
        import config
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        result = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=prompt,
            config=dict(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="1:1"
            )
        )
        
        save_dir = os.path.expanduser("~/Jarvis images")
        os.makedirs(save_dir, exist_ok=True)
        
        for generated_image in result.generated_images:
            image = Image.open(BytesIO(generated_image.image.image_bytes))
            filename = f"image_{os.urandom(4).hex()}.jpg"
            full_path = os.path.join(save_dir, filename)
            image.save(full_path)
            
        voice.speak("Tasveer ban gayi hai aur Jarvis images folder mein save ho chuki hai.")
    except Exception as e:
        voice.speak("Maaf kijiye, tasveer generate karne mein kuch gadbadi ho gayi.")


def save_birthday(voice, **kw):
    try:
        import os
        import json

        data_path = os.path.join(os.path.dirname(__file__), "data", "birthdays.json")
        os.makedirs(os.path.dirname(data_path), exist_ok=True)

        data = {}
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        name = kw.get("name", "user")
        date = kw.get("date", "unknown")

        data[name] = date

        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        voice.speak(f"{name} ki birthday save kar di hai.")

    except Exception as e:
        voice.speak("Maaf kijiye, birthday save karne me kuch gadbad ho gayi.")
        print(f"[save_birthday error: {e}]")
        
def create_database_folder(voice, **kw):
    import os
    import config
    try:
        db_folder = os.path.join(config.DEFAULT_WORKING_FOLDER, "Databases")
        os.makedirs(db_folder, exist_ok=True)
        voice.speak("Databases naam ka folder Documents mein bana diya.")
    except Exception as e:
        voice.speak("Folder banane mein dikkat aa gayi.")
        print(f"[create_database_folder error: {e}]")