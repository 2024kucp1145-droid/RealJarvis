# -*- coding: utf-8 -*-
"""
config.py
=========
YE FILE TUMHARI PERSONAL SETTINGS HAI. Isme apni details daal do,
baaki poora system yahi se chalega.
"""

import hashlib
import os

# ---------------- IDENTITY ----------------
ASSISTANT_NAME = "jarvis"          # wake word (lowercase). "jarvis" bolne se activate hoga
USER_NAME = "Piyush"                  # Jarvis tumhe kis naam se bulaye

# ---------------- SECURITY ----------------
# Password yaha PLAIN TEXT me kabhi mat rakhna. Neeche wala helper function
# use karke ek baar hash generate karo aur wahi hash yaha paste kar do.
#
#   >>> python config.py set-password
#
# ye tumse password poochega aur hash yaha likh dega.
PASSWORD_HASH = "5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5"  # yaha auto-generate hoke aayega

FACE_VERIFICATION_ENABLED = False
FACE_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "owner_face.jpg")

# Password ya face me se KITNE chahiye login ke liye?
#   "both"   -> password AND face dono zaroori (sabse secure)
#   "either" -> password YA face, koi bhi ek chalega
AUTH_MODE = "either"

# ---------------- WAKE ----------------
CLAP_WAKE_ENABLED = False
CLAP_COUNT_REQUIRED = 2
CLAP_WINDOW_SECONDS = 1.5          # dono taaliyon ke beech max gap
PICOVOICE_ACCESS_KEY = ""          # Optional: Picovoice free key for 0.01s instant edge wake-word

# ---------------- VOICE ----------------
# TTS ENGINE:
#   "offline" -> pyttsx3 (Windows ki built-in SAPI5 voice, bilkul offline)
#   "online"  -> edge-tts (Microsoft ka natural Hindi female voice "hi-IN-SwaraNeural",
#                internet chahiye, lekin bahut zyada pyaari/natural sunayi deti hai)
#   "auto"    -> jab internet ho tab online, warna offline (RECOMMENDED)
TTS_MODE = "auto"
ONLINE_VOICE = "hi-IN-SwaraNeural"   # pyaari Hindi female voice (Microsoft Edge TTS)
SPEECH_RATE = 175                    # offline voice ki speed

# STT (sunna): "google" (online, sabse accurate) ya "offline" (Sphinx, kam accurate)
STT_MODE = "auto"
MIC_ENERGY_MIN = 50
MIC_ENERGY_MAX = 400
# In languages me try karega recognition (order matter karta hai - pehle wali
# pehle try hoti hai). "en-IN" Hinglish/English dono kaafi achhe se pakड़ leta
# hai. Chaho toh aur languages add kar sakte ho, e.g. "ta-IN" (Tamil), "te-IN" (Telugu).
RECOGNITION_LANGUAGES = ["en-IN", "hi-IN"]

# ---------------- EMAIL ----------------
EMAIL_ENABLED = True
EMAIL_ADDRESS = "2024kucp1145@iiitkota.ac.in"
EMAIL_APP_PASSWORD = "uxcg tzzb ajbi mdqw"         # Gmail "App Password" (normal password nahi chalega)
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ---------------- MISC ----------------
AI_ENABLED = True
AI_PROVIDER = "gemini"
GEMINI_API_KEY = "AQ.Ab8RN6IbtyH1EOqVOmuchQh_6AaWBBPEqN44z4pkDERqnHH4Gg"
GEMINI_MODEL = "gemini-flash-lite-latest"
BARGE_IN_THRESHOLD = 0.0018
AI_MAX_TOKENS = 350       # kam tokens = AI response faster aata hai
AI_HISTORY_TURNS = 4      # sirf last 4 exchanges context mein, request chhoti rehti hai
DEFAULT_WORKING_FOLDER = os.path.join(os.path.expanduser("~"), "Documents")
def hash_password(plain_text: str) -> str:
    return hashlib.sha256(plain_text.encode("utf-8")).hexdigest()


def verify_password(plain_text: str) -> bool:
    if not PASSWORD_HASH:
        return False
    return hash_password(plain_text) == PASSWORD_HASH


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "set-password":
        import getpass
        pw = getpass.getpass("Naya password set karo: ")
        h = hash_password(pw)
        print("\nYe hash apni config.py me PASSWORD_HASH = \"...\" me paste kar do:\n")
        print(h)
# ============================================================
# WHATSAPP SETTINGS
# ============================================================
WHATSAPP_ENABLED = True
WHATSAPP_AUTO_START = True  # Auto-open WhatsApp Web on launch
WHATSAPP_CONTACTS_FILE = "data/whatsapp_contacts.json"  # Save contacts
WHATSAPP_SESSION_DIR = "data/whatsapp_session"  # Persist session