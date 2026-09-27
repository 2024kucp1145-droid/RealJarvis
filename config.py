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
import hmac
import os
import secrets

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
#   "edge"       -> Microsoft Neural, FREE + UNLIMITED (same sweet female Jarvis tone)
#   "auto"       -> ElevenLabs pehle, quota/error par turant Edge (silent nahi)
#   "elevenlabs" -> ElevenLabs try, fail par Edge
#   "offline"    -> SAPI5 / espeak (internet nahi)
# Default edge: 11labs free quota (~10k chars/month) khatam hote hi awaaz band na ho.
TTS_MODE = os.environ.get("TTS_MODE", "edge")

# ElevenLabs Ultra-Realistic Setup (.env mein set karein):
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
# Female Voices:
#   "cgSgspJ2msm6clMCkdW9" -> Jessica (Playful, Bright, Sweet & Warm Female Voice - DEFAULT)
#   "EXAVITQu4vr4xnSDxMaL" -> Sarah (Mature, Reassuring, Confident Female Voice)
#   "hpp4J3VqNfWAUOO0d1Us" -> Bella (Soft, Professional Female Voice)
#   "pNInz6obpgDQGcFmaJgB" -> Adam (Deep Male JARVIS voice)
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "cgSgspJ2msm6clMCkdW9")
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"   # Hindi, Hinglish & English natural synthesis

# 100% Free Unlimited Neural Voices (Microsoft Edge TTS):
#   "en-IN-NeerjaExpressiveNeural" -> Jessica-like sweet Hinglish female (DEFAULT, unlimited)
#   "hi-IN-SwaraNeural"            -> Hindi Female
#   "hi-IN-MadhurNeural"           -> Hindi Male
#   "en-US-ChristopherNeural"      -> Classic Iron Man JARVIS
ONLINE_VOICE = os.environ.get("ONLINE_VOICE", "en-IN-NeerjaExpressiveNeural")
# Agar primary voice fail ho (edge endpoint glitch), ye order se try hogi
EDGE_VOICE_FALLBACKS = [
    "en-IN-NeerjaExpressiveNeural",
    "en-IN-NeerjaNeural",
    "hi-IN-SwaraNeural",
]
SPEECH_RATE = 160                    # offline voice ki speed
# TTS Speed Offset: edge-tts prosody ke liye global rate adjust (e.g. "-10%" = 10% slow down = meethi madhur tempo)
TTS_RATE_OFFSET = os.environ.get("TTS_RATE_OFFSET", "-12%")  # ← default -12% slow = zyada meethi awaaz

# STT (sunna): "google" (online, sabse accurate) ya "offline" (Sphinx, kam accurate)
STT_MODE = "auto"
MIC_ENERGY_MIN = 100                 # Raised: ignores fan/AC background hum, only real speech triggers
MIC_ENERGY_MAX = 300                 # Tighter max: prevents mic from going deaf in loud rooms
MIC_PAUSE_THRESHOLD = 0.80          # 0.80s pause = natural breath gap, won't cut mid-sentence
MIC_NON_SPEAKING_DURATION = 0.30    # 0.30s non-speaking buffer (natural speech gaps)
MIC_DYNAMIC_ENERGY = True           # Continuously adapt to ambient room noise
FAR_FIELD_GAIN_MULTIPLIER = 2.0     # Reduced: 2x boost is enough, 3.5x was amplifying background noise too
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
BARGE_IN_THRESHOLD = 0.012          # Raised: Speaker echo won't trigger this; only real loud human voice will
BARGE_IN_GRACE_SECONDS = 0.40       # 400ms grace: speaker pop + room echo settles before barge-in opens
BARGE_IN_SUSTAIN_BLOCKS = 4        # ~80ms of sustained voice needed (prevents false triggers from room echo)
AI_MAX_TOKENS = 350       # kam tokens = AI response faster aata hai
AI_HISTORY_TURNS = 4      # sirf last 4 exchanges context mein, request chhoti rehti hai
DEFAULT_WORKING_FOLDER = os.path.join(os.path.expanduser("~"), "Documents")
PBKDF2_ITERATIONS = 260000


def hash_password(plain_text: str) -> str:
    """PBKDF2-HMAC-SHA256 + random per-password salt.

    SECURITY: Pehle ye unsalted SHA-256 tha (hashlib.sha256(pw).hexdigest()).
    Unsalted hash rainbow tables se seconds me crack ho jaate hain, aur ye
    hash repo me plaintext commit ho jaata tha. Ab salted PBKDF2 (260k
    iterations) use hota hai, format: pbkdf2_sha256$<iter>$<salt>$<hash>
    """
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        plain_text.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${derived.hex()}"


def verify_password(plain_text: str) -> bool:
    if not PASSWORD_HASH or not plain_text:
        return False

    stored = PASSWORD_HASH.strip()

    # New PBKDF2 format
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iter_str, salt_hex, hash_hex = stored.split("$")
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                plain_text.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iter_str),
            )
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(derived.hex(), hash_hex)

    # Legacy unsalted SHA-256 (purana format) - backward compatible login.
    # Naya password set karte hi PBKDF2 format me migrate ho jayega:
    #   python config.py set-password
    legacy = hashlib.sha256(plain_text.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored)


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

# ============================================================
# 24/7 DAEMON GATEWAY (remote REST API)
# ============================================================
# SECURITY: DAEMON_AUTH_TOKEN ka koi hardcoded fallback nahi hai.
# Blank chhoda toh daemon start hi nahi hoga (fail-fast).
DAEMON_AUTH_TOKEN = os.environ.get("DAEMON_AUTH_TOKEN", "")
DAEMON_HOST = os.environ.get("DAEMON_HOST", "127.0.0.1")
DAEMON_PORT = int(os.environ.get("DAEMON_PORT", "8765"))

# Twilio Auth Token - iske bina WhatsApp webhook signature verify nahi hoti,
# aur bina verify webhook requests reject ho jaati hain.
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")




