# -*- coding: utf-8 -*-
"""
whatsapp_commands.py
====================
Complete WhatsApp integration for Jarvis
"""

import os
import re
import time
import socket
import webbrowser
import threading
import subprocess
from datetime import datetime

try:
    import pywhatkit as kit
except ImportError:
    kit = None

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    webdriver = None
    By = None
    Keys = None
    WebDriverWait = None
    EC = None
    Service = None
    ChromeDriverManager = None
    Options = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

# Global driver
_driver = None
_whatsapp_ready = False


def _has_internet():
    """Check internet connection without affecting global socket timeout"""
    try:
        conn = socket.create_connection(("8.8.8.8", 53), timeout=2)
        conn.close()
        return True
    except Exception:
        return False


def _is_phone_number(text):
    """Check if text looks like a phone number"""
    digits_only = re.sub(r'[^0-9]', '', text)
    return len(digits_only) >= 7


def _strip_trigger_words(text):
    """Remove common command trigger words from message text"""
    triggers = [
        "whatsapp", "whats app", "whatsaap", "message", "bhejo", "bhej do",
        "send karo", "send", "pe", "par", "ko", "number", "phone"
    ]
    cleaned = text
    for trigger in triggers:
        cleaned = re.sub(r'\b' + re.escape(trigger) + r'\b', '', cleaned, flags=re.IGNORECASE)
    return ' '.join(cleaned.split())


def _open_whatsapp_web(voice):
    """Internal function to open WhatsApp Web"""
    global _driver, _whatsapp_ready
    
    if _whatsapp_ready and _driver:
        try:
            _driver.current_url
            return True
        except Exception:
            _whatsapp_ready = False
    
    if not _has_internet():
        voice.speak("Internet nahi hai. WhatsApp Web ke liye internet chahiye.")
        return False
    
    voice.speak("WhatsApp Web khol rahi hoon...")
    
    try:
        # Try Selenium first
        if webdriver and ChromeDriverManager:
            try:
                options = Options()
                options.add_argument("--disable-notifications")
                options.add_argument("--disable-popup-blocking")
                options.add_experimental_option("detach", True)
                
                service = Service(ChromeDriverManager().install())
                _driver = webdriver.Chrome(service=service, options=options)
                _driver.get("https://web.whatsapp.com")
                
                voice.speak("WhatsApp Web open hai. Mobile se QR code scan karo.")
                
                # Background wait
                def wait_for_load():
                    global _whatsapp_ready
                    try:
                        WebDriverWait(_driver, 30).until(
                            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
                        )
                        _whatsapp_ready = True
                        voice.speak("WhatsApp Web ready hai!")
                    except Exception:
                        voice.speak("QR scan nahi hua. Browser me manually kholo.")
                
                threading.Thread(target=wait_for_load, daemon=True).start()
                return True
                
            except Exception as e:
                print(f"[Selenium Error] {e}")
                voice.speak("Selenium se nahi khul paaya, browser me khol rahi hoon...")
        
        # Fallback: Open in browser
        webbrowser.open("https://web.whatsapp.com")
        voice.speak("Browser me WhatsApp Web khol diya. QR code scan karo.")
        return True
        
    except Exception as e:
        voice.speak("WhatsApp open karte waqt error aa gaya.")
        print(f"[WhatsApp Error] {e}")
        return False


def _wait_for_chat(voice, contact_name, timeout=15):
    """Wait for chat to load"""
    global _driver
    
    if not _driver:
        return False
    
    try:
        # Search for contact
        search_box = WebDriverWait(_driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@contenteditable='true']"))
        )
        search_box.click()
        
        # Properly clear contenteditable div
        if Keys:
            search_box.send_keys(Keys.CONTROL + "a")
            search_box.send_keys(Keys.DELETE)
        else:
            search_box.clear()
        
        for char in contact_name:
            search_box.send_keys(char)
            time.sleep(0.05)
        
        time.sleep(1)
        
        # Try multiple ways to find contact
        try:
            contact = WebDriverWait(_driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//span[@title='{contact_name}']"))
            )
            contact.click()
            time.sleep(0.5)
            return True
        except Exception:
            try:
                contact = _driver.find_element(By.XPATH, f"//div[contains(@title, '{contact_name}')]")
                contact.click()
                time.sleep(0.5)
                return True
            except Exception:
                pass
        
        return False
        
    except Exception as e:
        print(f"[Wait for chat error] {e}")
        return False


# ============================================================
# MAIN COMMAND FUNCTIONS
# ============================================================

def open_whatsapp(voice, **kwargs):
    """Open WhatsApp Web"""
    if _open_whatsapp_web(voice):
        voice.speak("WhatsApp Web khol diya.")


def close_whatsapp(voice, **kwargs):
    """Close WhatsApp Web"""
    global _driver, _whatsapp_ready
    if _driver:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None
    _whatsapp_ready = False
    voice.speak("WhatsApp band kar diya.")


def send_whatsapp_message(voice, contact="", message="", **kwargs):
    """Send WhatsApp message to contact"""
    if not contact:
        voice.speak("Kisko bhejna hai?")
        return
    if not message:
        voice.speak("Kya bhejna hai?")
        return
    
    # Try pywhatkit first ONLY if contact looks like a phone number
    if kit and _is_phone_number(contact):
        try:
            voice.speak(f"{contact} ko message bhej rahi hoon...")
            kit.sendwhatmsg_instantly(contact, message, wait_time=15)
            voice.speak("Message send kar diya.")
            return
        except Exception as e:
            print(f"[Pywhatkit Error] {e}")
            voice.speak("Pywhatkit se nahi bheja, Selenium se try kar rahi hoon...")
    
    # Fallback: Selenium
    if not _open_whatsapp_web(voice):
        return
    
    try:
        voice.speak(f"{contact} ko message bhej rahi hoon...")
        
        if not _wait_for_chat(voice, contact):
            voice.speak(f"{contact} nahi mila. Sahi naam batao.")
            return
        
        msg_box = WebDriverWait(_driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true' and @data-tab='10']"))
        )
        
        for char in message:
            msg_box.send_keys(char)
            time.sleep(0.02)
        
        time.sleep(0.3)
        
        send_button = WebDriverWait(_driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Send']"))
        )
        send_button.click()
        
        voice.speak(f"Message send kar diya {contact} ko.")
        
    except Exception as e:
        voice.speak("Message bhejne me dikkat aa gayi.")
        print(f"[Send Error] {e}")


def send_whatsapp_quick(voice, instruction="", **kwargs):
    """User bolta hai: 'whatsapp pe bhejo 9876543210 hello kaise ho'"""
    if not kit:
        voice.speak("Pywhatkit install nahi hai.")
        return
    
    if not instruction:
        voice.speak("Phone number aur message batayein.")
        return
    
    # Phone number nikaalo (pehle continuous digits, + sign allow karo)
    match = re.search(r'([\+]?\d[\d\s\-]{7,})', instruction)
    if not match:
        voice.speak("Phone number nahi mila. Number ke saath message boliye.")
        return
    
    raw_phone = match.group(1).replace(" ", "").replace("-", "")
    phone = re.sub(r'[^0-9]', '', raw_phone)
    
    # Number ke baad ka text = message (pehle ka text mein trigger words hain)
    after = instruction[match.end():].strip()
    before = instruction[:match.start()].strip()
    
    # Agar 'after' mein kuch hai toh use karo, warna before se trigger words hatao
    if after:
        message = after
    else:
        message = _strip_trigger_words(before)
    
    if not message:
        voice.speak("Kya message bhejna hai, wo bhi batayein.")
        return
    
    # India code add karo agar missing hai (sirf 10 digit Indian numbers ke liye)
    if not phone.startswith('91') and len(phone) == 10:
        phone = '91' + phone
    
    try:
        import urllib.parse
        voice.speak(f"{phone} ko message bhej rahi hoon...")
        
        encoded_text = urllib.parse.quote(message)
        wa_uri = f"whatsapp://send?phone={phone}&text={encoded_text}"
        os.startfile(wa_uri)

        # Background focus and auto-enter sender
        def _auto_press_enter_commands():
            for delay in (2.0, 3.5, 5.0):
                time.sleep(1.5 if delay > 2.0 else 2.0)
                try:
                    import win32gui
                    import win32con
                    import ctypes

                    def enum_handler(hwnd, extra):
                        if win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd)
                            if "whatsapp" in title.lower():
                                extra.append(hwnd)

                    wa_hwnds = []
                    win32gui.EnumWindows(enum_handler, wa_hwnds)
                    if wa_hwnds:
                        target_hwnd = wa_hwnds[0]
                        try:
                            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(target_hwnd)
                        except Exception:
                            pass
                        time.sleep(0.15)

                    # Send Enter
                    ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
                    time.sleep(0.05)
                    ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)

                    try:
                        import pyautogui
                        pyautogui.press('enter')
                    except Exception:
                        pass
                except Exception:
                    pass

        threading.Thread(target=_auto_press_enter_commands, daemon=True).start()
        voice.speak("Message bhej diya.")
    except Exception as e:
        voice.speak("Message bhejne mein dikkat aa gayi.")
        print(f"[Quick Send Error] {e}")


def read_whatsapp_unread(voice, **kwargs):
    """Read unread WhatsApp messages"""
    if not _open_whatsapp_web(voice):
        return
    
    try:
        voice.speak("Unread messages check kar rahi hoon...")
        
        # Find chat list items with unread indicator
        unread_chats = _driver.find_elements(
            By.XPATH, 
            "//span[contains(@aria-label, 'unread') or contains(@data-testid, 'unread')]"
        )
        
        if not unread_chats:
            voice.speak("Koi unread message nahi hai.")
            return
        
        voice.speak(f"{len(unread_chats)} unread chats hain.")
        
        # Click first unread chat and read recent messages
        try:
            unread_chats[0].click()
            time.sleep(1)
            
            messages = _driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'message') and contains(@class, 'in')]"
            )
            
            recent = messages[-3:] if len(messages) >= 3 else messages
            for i, msg in enumerate(recent):
                try:
                    text_span = msg.find_element(By.XPATH, ".//span[contains(@class, 'selectable-text')]")
                    text = text_span.text.strip()
                    if text:
                        voice.speak(f"Message: {text[:100]}")
                except Exception:
                    pass
                    
        except Exception as e:
            print(f"[Read unread click error] {e}")
            voice.speak("Unread messages read karne mein dikkat aa gayi.")
            
    except Exception as e:
        voice.speak("Unread messages check karne mein dikkat aa gayi.")
        print(f"[Read Unread Error] {e}")


def search_whatsapp(voice, query="", **kwargs):
    """Search messages in WhatsApp"""
    if not _open_whatsapp_web(voice):
        return
    
    if not query:
        voice.speak("Kya search karna hai?")
        return
    
    try:
        voice.speak(f"'{query}' search kar rahi hoon...")
        
        search_btn = WebDriverWait(_driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='chat-list-search']"))
        )
        search_btn.click()
        time.sleep(0.5)
        
        search_input = WebDriverWait(_driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-testid='search-input']"))
        )
        search_input.click()
        search_input.clear()
        search_input.send_keys(query)
        time.sleep(1)
        
        results = _driver.find_elements(By.XPATH, "//div[contains(@class, 'result')]")
        
        if not results:
            voice.speak("Koi result nahi mila.")
            return
        
        voice.speak(f"{len(results)} results mile.")
        
        for i, result in enumerate(results[:3]):
            text = result.text.strip()
            if text:
                voice.speak(f"Result {i+1}: {text[:50]}")
        
        # Clear search safely
        try:
            clear_btn = _driver.find_element(By.XPATH, "//button[@aria-label='Clear search']")
            clear_btn.click()
        except Exception:
            pass
        
    except Exception as e:
        voice.speak("Search karne me dikkat aa gayi.")
        print(f"[Search Error] {e}")


def get_whatsapp_contacts(voice, **kwargs):
    """List recent WhatsApp contacts"""
    if not _open_whatsapp_web(voice):
        return
    
    try:
        voice.speak("Recent contacts dhoond rahi hoon...")
        
        chats = _driver.find_elements(By.XPATH, "//div[@data-testid='chat-list']//div[contains(@class, 'chat-title')]")
        
        contacts = []
        for chat in chats[:10]:
            try:
                name = chat.find_element(By.XPATH, ".//span").text
                if name:
                    contacts.append(name)
            except Exception:
                pass
        
        if contacts:
            voice.speak(f"Mile hain: {', '.join(contacts[:5])}")
        else:
            voice.speak("Koi contacts nahi mile.")
            
    except Exception as e:
        voice.speak("Contacts dhoondne me dikkat aa gayi.")
        print(f"[Contacts Error] {e}")


def reply_to_whatsapp(voice, message="", **kwargs):
    """Reply to current WhatsApp chat"""
    if not _open_whatsapp_web(voice):
        return
    
    if not message:
        voice.speak("Kya reply bhejna hai?")
        return
    
    try:
        msg_box = WebDriverWait(_driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true' and @data-tab='10']"))
        )
        
        for char in message:
            msg_box.send_keys(char)
            time.sleep(0.02)
        
        time.sleep(0.3)
        
        send_button = WebDriverWait(_driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Send']"))
        )
        send_button.click()
        
        voice.speak("Reply send kar diya.")
        
    except Exception as e:
        voice.speak("Reply bhejne me dikkat aa gayi.")
        print(f"[Reply Error] {e}")


def send_whatsapp_file(voice, contact="", file_path="", **kwargs):
    """Send file via WhatsApp"""
    if not _open_whatsapp_web(voice):
        return
    
    if not contact:
        voice.speak("Kisko bhejna hai?")
        return
    
    if not file_path or not os.path.exists(file_path):
        voice.speak("File nahi mili.")
        return
    
    try:
        voice.speak(f"{contact} ko file bhej rahi hoon...")
        
        if not _wait_for_chat(voice, contact):
            voice.speak(f"{contact} nahi mila.")
            return
        
        attach_btn = WebDriverWait(_driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@title='Attach']"))
        )
        attach_btn.click()
        time.sleep(0.5)
        
        # File input is usually hidden, use presence not clickability
        doc_btn = WebDriverWait(_driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@accept='*/*']"))
        )
        doc_btn.send_keys(file_path)
        time.sleep(1)
        
        send_btn = WebDriverWait(_driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send']"))
        )
        send_btn.click()
        
        voice.speak("File send kar di.")
        
    except Exception as e:
        voice.speak("File bhejne me dikkat aa gayi.")
        print(f"[File Send Error] {e}")


# ============================================================
# COMMAND REGISTRATION
# ============================================================

WHATSAPP_COMMANDS = {
    "open_whatsapp": {
        "type": "whatsapp", 
        "action": "open_whatsapp",
        "trigger": [
            "whatsapp kholo", 
            "whatsapp open karo",
            "whatsapp web kholo",
            "whatsapp chalu karo"
        ]
    },
    "close_whatsapp": {
        "type": "whatsapp", 
        "action": "close_whatsapp",
        "trigger": [
            "whatsapp band karo",
            "whatsapp close karo",
            "whatsapp web band karo"
        ]
    },
    "send_whatsapp_message": {
        "type": "whatsapp", 
        "action": "send_whatsapp_message",
        "trigger": [
            "whatsapp message bhejo",
            "whatsapp pe bhejo",
            "whatsapp send karo",
            "whatsapp par message bhejo"
        ]
    },
    "send_whatsapp_quick": {
        "type": "whatsapp", 
        "action": "send_whatsapp_quick",
        "param": "instruction",
        "trigger": [
            "whatsapp number pe bhejo",
            "whatsapp phone pe bhejo"
        ]
    },
    "read_whatsapp_unread": {
        "type": "whatsapp", 
        "action": "read_whatsapp_unread",
        "trigger": [
            "whatsapp unread padho",
            "new whatsapp messages",
            "whatsapp pe kya aaya",
            "whatsapp messages padho"
        ]
    },
    "search_whatsapp": {
        "type": "whatsapp", 
        "action": "search_whatsapp",
        "trigger": [
            "whatsapp search karo",
            "whatsapp pe dhoondo",
            "whatsapp mein khojo"
        ]
    },
    "get_whatsapp_contacts": {
        "type": "whatsapp", 
        "action": "get_whatsapp_contacts",
        "trigger": [
            "whatsapp contacts dikhao",
            "whatsapp pe kaun hai",
            "whatsapp contacts batao"
        ]
    },
    "reply_to_whatsapp": {
        "type": "whatsapp", 
        "action": "reply_to_whatsapp",
        "trigger": [
            "whatsapp reply karo",
            "whatsapp pe jawab do",
            "whatsapp ka reply do"
        ]
    },
    "send_whatsapp_file": {
        "type": "whatsapp", 
        "action": "send_whatsapp_file",
        "trigger": [
            "whatsapp file bhejo",
            "whatsapp document bhejo",
            "whatsapp photo bhejo"
        ]
    }
}