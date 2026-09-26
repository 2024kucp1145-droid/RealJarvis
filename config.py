# -*- coding: utf-8 -*-
"""
config.py
=========
YE FILE TUMHARI PERSONAL SETTINGS HAI. Isme apni details daal do,
baaki poora system yahi se chalega.

SECRETS (.env file mein rakhiye, config.py mein KABHI MAT LIKHIYE):
  GEMINI_API_KEY, EMAIL_ADDRESS, EMAIL_APP_PASSWORD, WHATSAPP_MASTER_PHONE
"""

import hashlib
import os

# --- .env file se secrets load karo (agar python-dotenv installed nahi hai toh manual parse) ---
def _load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key and val and key not in os.environ:
                os.environ[key] = val

_load_env()

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
PASSWORD_HASH = "5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5"  # Run: python config.py set-password  # yaha auto-generate hoke aayega

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

# ---------------- VOICE & TTS ----------------
# TTS ENGINE & PROVIDERS:
#   "auto"       -> ElevenLabs (agar key set ho), warna high-speed Microsoft Neural (Madhur / NeerjaExpressive / Christopher)
#   "elevenlabs" -> ElevenLabs Ultra-Realistic AI Voice (10k chars free/month per account on elevenlabs.io)
#   "edge"       -> 100% Free Unlimited Neural Voice (Deep human clarity, zero cost)
#   "offline"    -> SAPI5 / espeak offline fallback
TTS_MODE = os.environ.get("TTS_MODE", "auto")

# ElevenLabs Ultra-Realistic Setup (.env mein set karein):
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
# Default Voices:
#   "pNInz6obpgDQGcFmaJgB" -> Adam (Deep, authoritative Hollywood JARVIS voice)
#   "21m00Tcm4TlvDq8ikWAM" -> Rachel (Warm, natural female AI voice)
#   "ErXwobaYiN019PkySvjV" -> Antoni (Conversational, smooth)
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"   # Hindi, Hinglish & English natural synthesis

# 100% Free Unlimited Neural Voices:
#   "hi-IN-MadhurNeural"           -> Hindi Male (Deep, clear, confident - 10x better than old Swara)
#   "en-IN-NeerjaExpressiveNeural" -> Indian English Expressive Female (Rich emotion & intonation)
#   "en-US-ChristopherNeural"      -> Classic Iron Man JARVIS (Deep, British/American butler tone)
#   "hi-IN-SwaraNeural"            -> Hindi Female
ONLINE_VOICE = os.environ.get("ONLINE_VOICE", "hi-IN-MadhurNeural")
SPEECH_RATE = 175                    # offline voice ki speed

# STT (sunna): "google" (online, sabse accurate) ya "offline" (Sphinx, kam accurate)
STT_MODE = "auto"
MIC_ENERGY_MIN = 80                  # Avoid picking up subtle keyboard key clicks
MIC_ENERGY_MAX = 250                 # Capped at 250 so mic never locks deaf
MIC_PAUSE_THRESHOLD = 0.80          # 0.80s natural speech pause threshold (no mid-sentence cut-off)
MIC_NON_SPEAKING_DURATION = 0.35    # 0.35s non-speaking buffer
MIC_DYNAMIC_ENERGY = True           # Continuously adapt to ambient room noise
# In languages me try karega recognition (order matter karta hai - pehle wali
# pehle try hoti hai). "en-IN" Hinglish/English dono kaafi achhe se pakà¤¡à¤¼ leta
# hai. Chaho toh aur languages add kar sakte ho, e.g. "ta-IN" (Tamil), "te-IN" (Telugu).
RECOGNITION_LANGUAGES = ["en-IN", "hi-IN"]

# ---------------- ACOUSTIC BIO-SENSING & FAR-FIELD ----------------
ACOUSTIC_FILTER_ENABLED = True
KEYSTROKE_SUPPRESSION_ENABLED = True      # Suppresses typing keystroke clicks from triggering voice
FAR_FIELD_AGC_ENABLED = True              # Boosts distant/quiet voices across room by 2.5x
FAR_FIELD_GAIN_MULTIPLIER = 2.5
PARALINGUISTIC_DETECTION_ENABLED = True   # Detects human emotional acoustics: Yawning, Laughing, Singing/Humming, Crying

# ---------------- EMAIL ----------------
EMAIL_ENABLED = True
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "")          # .env mein set karo
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "")  # .env mein set karo
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ---------------- MISC ----------------
AI_ENABLED = True
AI_PROVIDER = "gemini"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")          # .env mein set karo
GEMINI_MODEL = "gemini-flash-lite-latest"   # gemini-flash-latest = 20/day quota; flash-lite has no such limit
BARGE_IN_ENABLED = True
BARGE_IN_THRESHOLD = 0.0030
BARGE_IN_GRACE_SECONDS = 0.15        # Instant reaction (150ms speaker pop shield)
BARGE_IN_SUSTAIN_BLOCKS = 2         # ~40ms speech triggers instant speech cut-off
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




