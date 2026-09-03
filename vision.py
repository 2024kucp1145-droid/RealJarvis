# -*- coding: utf-8 -*-
"""
vision.py
=========
Screen dekhne wala module. ON-DEMAND kaam karta hai - matlab sirf jab
tum "cursor pe kya hai" ya "screen dekho" jaisa bologe, tabhi ek
screenshot leta hai. Hamesha chup-chaap record NAHI karta - ye jaan-bujh
kar aisa rakha hai taaki privacy bani rahe.
"""
import time
try:
    import pyautogui
except ImportError:
    pyautogui = None


def available() -> bool:
    return pyautogui is not None


def get_cursor_position():
    if not pyautogui:
        return None
    return pyautogui.position()


def capture_cursor_region(radius: int = 350):
    """
    Poori screen ka screenshot leke cursor ke aas-paas ka hissa crop karke
    return karta hai (PIL Image). Poori screen ke bajaye sirf cursor ke
    najdeek ka hissa bhejte hain AI ko - taaki wahi samjhaye jispe user
    point kar raha hai, na ki poori screen ka context confuse kare.
    """
    if not pyautogui:
        return None
    screenshot = pyautogui.screenshot()
    x, y = pyautogui.position()
    left = max(0, x - radius)
    top = max(0, y - radius)
    right = min(screenshot.width, x + radius)
    bottom = min(screenshot.height, y + radius)
    return screenshot.crop((left, top, right, bottom))


def capture_full_screen():
    if not pyautogui:
        return None
    return pyautogui.screenshot()

def capture_region(left: int, top: int, width: int, height: int):
    """Kisi specific region ka screenshot le."""
    if not pyautogui:
        return None
    screenshot = pyautogui.screenshot()
    right = min(screenshot.width, left + width)
    bottom = min(screenshot.height, top + height)
    return screenshot.crop((left, top, right, bottom))


def scroll_and_capture_full_page(max_scrolls: int = 3):
    """
    Poora page capture karne ke liye multiple screenshots leta hai.
    Pehle current view, phir neeche scroll karke.
    Returns: list of PIL Images (top to bottom order)
    """
    if not pyautogui:
        return []
    images = []
    # Pehla screenshot (current view)
    images.append(pyautogui.screenshot())
    
    for i in range(max_scrolls):
        pyautogui.scroll(-6)  # Thoda kam scroll karo (pehle -8 tha)
        time.sleep(0.4)
        images.append(pyautogui.screenshot())
    
    # Wapas upar le jao — same amount
    for i in range(max_scrolls):
        pyautogui.scroll(6)
        time.sleep(0.15)
    
    return images


def get_cursor_region(width: int = 600, height: int = 400):
    """
    Cursor ke aas-paas ka region capture karta hai — code editor
    detect karne ke liye.
    """
    if not pyautogui:
        return None
    x, y = pyautogui.position()
    left = max(0, x - width // 2)
    top = max(0, y - height // 2)
    return capture_region(left, top, width, height)
