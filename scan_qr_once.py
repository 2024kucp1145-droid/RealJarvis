# -*- coding: utf-8 -*-
"""
scan_qr_once.py
===============
Run this ONCE to log in to WhatsApp Web.
Session is saved permanently after scan.
After this, headless bridge works forever without QR.
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "chrome_whatsapp_profile")
os.makedirs(PROFILE_DIR, exist_ok=True)

print("=" * 50)
print("  WhatsApp QR Scan — One Time Setup")
print("=" * 50)
print()
print("  Chrome will open (visible this time).")
print("  1. Wait for QR code to appear")
print("  2. Open WhatsApp on phone")
print("  3. Go to: ⋮ menu → Linked Devices → Link a Device")
print("  4. Scan the QR code")
print("  5. Wait for 'Connected!' message below")
print("  6. This window will close automatically")
print()

opts = Options()
opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
opts.add_argument("--profile-directory=Default")
opts.add_argument("--start-maximized")
opts.add_argument("--disable-notifications")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])

svc    = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=svc, options=opts)
driver.get("https://web.whatsapp.com")

print("  Waiting for you to scan QR (up to 3 minutes)...")
INPUT_CSS = 'div[contenteditable="true"][data-tab="10"]'
try:
    WebDriverWait(driver, 180).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, INPUT_CSS))
    )
    print()
    print("  ✅ Connected! Session saved.")
    print("  You can now run: venv\\Scripts\\python.exe setup_whatsapp_bridge.py")
    print("  Chrome will close in 3 seconds...")
    time.sleep(3)
except Exception:
    print("  ❌ Timeout. Please try again.")
finally:
    driver.quit()
