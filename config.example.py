# -*- coding: utf-8 -*-
"""
config.example.py
=================
Template configuration file for RealJarvis.
Copy this to `config.py` and insert your personal settings and API keys.
"""

import hashlib
import os

# ---------------- IDENTITY ----------------
ASSISTANT_NAME = "jarvis"          # wake word (lowercase)
USER_NAME = "Boss"                 # User name

# ---------------- SECURITY ----------------
PASSWORD_HASH = ""                 # Run: python config.py set-password
FACE_VERIFICATION_ENABLED = False
FACE_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "owner_face.jpg")
AUTH_MODE = "either"

# ---------------- WAKE ----------------
CLAP_WAKE_ENABLED = False
CLAP_COUNT_REQUIRED = 2
CLAP_WINDOW_SECONDS = 1.5
PICOVOICE_ACCESS_KEY = ""

# ---------------- VOICE ----------------
TTS_MODE = "auto"
ONLINE_VOICE = "hi-IN-SwaraNeural"
SPEECH_RATE = 175
STT_MODE = "auto"
MIC_ENERGY_MIN = 40
MIC_ENERGY_MAX = 450
RECOGNITION_LANGUAGES = ["en-IN", "hi-IN"]

# ---------------- ACOUSTIC BIO-SENSING ----------------
ACOUSTIC_FILTER_ENABLED = True
KEYSTROKE_SUPPRESSION_ENABLED = True
FAR_FIELD_AGC_ENABLED = True
FAR_FIELD_GAIN_MULTIPLIER = 2.5
PARALINGUISTIC_DETECTION_ENABLED = True

# ---------------- EMAIL ----------------
EMAIL_ENABLED = False
EMAIL_ADDRESS = "your@gmail.com"
EMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ---------------- AI BRAIN ----------------
AI_ENABLED = True
AI_PROVIDER = "gemini"
GEMINI_API_KEY = "your-gemini-api-key-here"  # Get from https://aistudio.google.com/apikey
GEMINI_MODEL = "gemini-flash-latest"
BARGE_IN_THRESHOLD = 0.0018
AI_MAX_TOKENS = 350
AI_HISTORY_TURNS = 4
DEFAULT_WORKING_FOLDER = os.path.join(os.path.expanduser("~"), "Documents")

def hash_password(plain_text: str) -> str:
    return hashlib.sha256(plain_text.encode("utf-8")).hexdigest()

def verify_password(plain_text: str) -> bool:
    if not PASSWORD_HASH:
        return False
    return hash_password(plain_text) == PASSWORD_HASH

# ---------------- WHATSAPP ----------------
WHATSAPP_ENABLED = True
WHATSAPP_AUTO_START = True
WHATSAPP_CONTACTS_FILE = "data/whatsapp_contacts.json"
WHATSAPP_SESSION_DIR = "data/whatsapp_session"
