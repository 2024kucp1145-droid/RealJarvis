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
#   "hi-IN-SwaraNeural"            -> Pure Hindi Female (Sweet, Soft, Melodious - DEFAULT)
#   "en-IN-NeerjaNeural"           -> Calm Indian English / Hinglish Female
#   "en-IN-NeerjaExpressiveNeural" -> Expressive Indian English Female
#   "hi-IN-MadhurNeural"           -> Hindi Male
#   "en-US-ChristopherNeural"      -> Classic Iron Man JARVIS
ONLINE_VOICE = os.environ.get("ONLINE_VOICE", "hi-IN-SwaraNeural")
# Agar primary voice fail ho (edge endpoint glitch), ye order se try hogi
EDGE_VOICE_FALLBACKS = [
    "hi-IN-SwaraNeural",
    "en-IN-NeerjaNeural",
    "en-IN-NeerjaExpressiveNeural",
]
SPEECH_RATE = 160                    # offline voice ki speed
# ---------------- OUTPUT VOLUME (GAIN) ----------------
# Aapki female awaaz bahut dheemi thi. Do jagah se control hota hai:
#   1) TTS_VOLUME      -> edge-tts ka SSML volume ("+40%" = 40% loud)
#   2) TTS_MIXER_GAIN  -> pygame ka software volume (0.0-1.0, 1.0 = full)
# Dono mila kar total gain = TTS_VOLUME% + mixer scaling.
# Values: 0 = normal, +50 = aadha dheema, +100 = double awaaz.
# Zyada mat karo — 100% se upar clipping/distortion hoti hai.
TTS_VOLUME = "+45%"

# ── REAL OUTPUT GAIN ─────────────────────────────────────────────────────
# IMPORTANT: edge-tts ka `volume` parameter Microsoft ke neural voices par
# NEUTRALIZED hai — measurement me -50% se +100% tak ke beech RMS spread
# sirf 1.06 tha (yaani koi farak nahi). Isliye actual awaaz badhne ke liye
# audio decode karke samples par gain lagana padta hai.
#
#   1.0 = no change, 1.5 = +3.5 dB, 2.0 = +6 dB (perceptibly much louder),
#   3.0 = +9.5 dB (loud, distortion ka risk)
# Soft-clip lagaya jaata hai taaki clipping/crackling na ho.
TTS_AUDIO_GAIN = 2.5
TTS_MIXER_GAIN = 1.0
# TTS Speed Offset: edge-tts prosody ke liye global rate adjust (e.g. "-6%" = relaxed, sweet madhur tempo)
TTS_RATE_OFFSET = os.environ.get("TTS_RATE_OFFSET", "-6%")  # default -6% = sweet, pleasant tempo

# ================= VOICE CAPTURE — CAPTURE-FIRST ARCHITECTURE =================
# DESIGN CONTRACT (in par regress mat karna):
#   1. Mic PEHLE poora capture karta hai. Koi bhi ek filter user ka bolna
#      DELETE nahi kar sakta — filters sirf ADVISORY flag lagate hain.
#   2. End-of-speech tabhi maana jata hai jab DEFINITIVE signal mile: yaani
#      consecutive silent confirmation windows (END_OF_SPEECH_CONFIRMATIONS).
#   3. Ek sochne wala pause (2-4s) kabhi sentence beech me kat-ta nahi.
#   4. Assistant input capture + confirm hone tak SUNTA rahega, respond nahi karega.
VOICE_CAPTURE_PRIORITY = True

# STT (sunna): "google" (online, sabse accurate) ya "offline" (Sphinx, kam accurate)
STT_MODE = "auto"

# ---------------- MICROPHONE SELECTION ----------------
# Is machine par 6 input devices hain aur A/B test me ye pata chala:
#   idx=0 "Microsoft Sound Mapper - Input"  -> FAIL (khaali, dono rounds)
#   idx=1 "Microphone (High Definition...)" -> FAIL (sirf kamre ka shor)
#   idx=4 "Primary Sound Capture Driver"   -> OK   (sabse saaf awaaz, swing 3637)
#   idx=5                                  -> dead (flat signal)
#
# BUG: yahan pehle "default" likha tha, jabki comment me "4 force kiya gaya hai"
# likha tha. "default" se `_detect_best_microphone()` turant `None` return kar
# deta tha — scan kabhi chalta hi nahi tha — aur hamesha kharab default mic
# (idx=0/1) khulta raha. Isiliye STT ko sirf 'ow ow ow' / 'if' jaisa garbage
# milta tha, chahe aap kitna bhi sahi bolein.
#
# Ab "scan": sab devices probe hote hain, sabse saaf wala chuna jaata hai aur
# result data/best_microphone.json me cache hota hai (MIC_DETECT_CACHE_MINUTES).
# Doosre computers pe bhi ye sahi rehta hai. Force karna ho to 4 (int) daal do.
MICROPHONE_DEVICE_INDEX = "scan"
MIC_DETECT_DURATION = 1.5            # per-device measurement window (seconds)
MIC_DETECT_MAX_DEVICES = 8           # zyada devices probe karne ki zaroorat nahi
MIC_DETECT_CACHE_MINUTES = 30        # result cache — har startup me dobara na dhundhe

# !!! ENERGY THRESHOLD KE BAARE ME SAAF SOCH !!!
# Energy threshold ko room ke ambient noise se NEECHE clamp karna = mic kabhi
# "silent" hi nahi hoti. Phir SpeechRecognition apna pause_threshold kabhi
# satisfy nahi kar pata aur LISTEN HANG ho jata hai (koi reply nahi aata).
# Isliye MAX itna rakha hai jo NOISY rooms ko bhi cover kare. Agar aapka kamra
#bahut shor wala hai to ye number badhana pad sakta hai — mic test se pata
# chalega. MIN chhota rakha hai taaki bilkul shaant kamre me bhi door ki
# dheemi awaaz pakad me.
MIC_ENERGY_MIN = 50                  # was 60
MIC_ENERGY_MAX = 2000                # was 400 — 400 NOISE FLOOR (647) SE NEECHE THA
MIC_ENERGY_FLOOR_RATIO = 0.8         # threshold kamke se kam 80% — isse neeche = hang
# pause_threshold SR ko batata hai "ek chunk kab band karo". Ye CHUNKING hai,
# truncation nahi — user ka poora speech humara continuation loop jodta hai
# (voice.Voice.listen). Isliye ye moderate rakha hai taaki SR jaldi wapas aaye
# aur end-of-speech detection hamare haath me rahe, SR ke haath me nahi.
MIC_PAUSE_THRESHOLD = 0.9            # was 1.8 (1.8s = multi-minute hang in noisy room)
MIC_NON_SPEAKING_DURATION = 0.4      # was 0.7
MIC_DYNAMIC_ENERGY = True            # Continuously adapt to ambient room noise
MIC_DYNAMIC_ENERGY_RATIO = 1.2       # was hardcoded 1.5 — kam aggressive adaptation
FAR_FIELD_GAIN_MULTIPLIER = 3.0      # was 2.0 — across-room (3-5m) awaaz ke liye

# ---------------- ACOUSTIC SPEECH GATE ----------------
# STT se PEHLE energy check. Agar audio me sirf kamre ka shor hai to Google STT
# tak pahuche hi nahi. Ye zaroori tha: shor STT ko "and the what" jaisa garbage
# de raha tha, jisse end-of-speech detect hi nahi hota tha aur Jarvis ghich
# accumulate karta raha (ek test me 73 words / 4 minute).
# ---------------- MICROPHONE SELECTION ----------------
# IMPORTANT: Ye setting PEHLE do jagah define thi. Line ~146 par "scan" likha
# gaya tha, par line ~189 ka dobara "default" usse override kar deta tha — to
# `_detect_best_microphone()` turant `None` return karta tha, scan kabhi chalta
# hi nahi tha, aur hamesha kharab default mic (Microsoft Sound Mapper /
# High Definition) khulta raha. Live test me `mic index = None` + Google STT
# ka "ow ow ow" isi wajah se aa raha tha.
#
# Ab sirf EK definition hai, "scan":
#   "default" -> system default mic
#   "scan"    -> sab devices probe karke sabse saaf wala (30 min cache)
#   <int>     -> kisi ek device ko force (jaise 4)
# Doosre computers pe bhi "scan" sahi rehta hai — device indices alag ho sakte hain.
MICROPHONE_DEVICE_INDEX = "scan"

# ---------------- ACOUSTIC SPEECH GATE ----------------
# STT se PEHLE energy check. Kaam: kamre ka shor STT tak na pahunche, warna
# Google "and the what" jaisa garbage deta hai aur end-of-speech detection
# tod deta hai.
#
# Default OFF hai kyunki is machine par ambient level bahut unstable tha
# (172 -> 1335 -> 6734 ek hi session me), jisse gate apni hi calibration se
# lad raha tha aur speech reject kar raha tha. Mic theek hone par ON kar sakte
# hain — tab ye kaam karega.
SPEECH_GATE_ENABLED = False
SPEECH_PRESENCE_RATIO = 1.25         # p90 energy, ambient se itni gani chahiye
SPEECH_GATE_WINDOW = 0.5             # gate kitni der ka audio dekhta hai (seconds)
MIC_AMBIENT_CALIBRATION = 2.0        # ambient kitni der measure kare (seconds)
# In languages me try karega recognition (order matter karta hai - pehle wali
# pehle try hoti hai). "en-IN" Hinglish/English dono kaafi achhe se pakà¤¡à¤¼ leta
# hai. Chaho toh aur languages add kar sakte ho, e.g. "ta-IN" (Tamil), "te-IN" (Telugu).
RECOGNITION_LANGUAGES = ["en-IN", "hi-IN"]

# ---------------- DEFINITIVE END-OF-SPEECH CONFIRMATION ----------------
LISTEN_INITIAL_TIMEOUT = 20.0         # was 6 — pehle phrase ke liye lambi der wait
# HARD CEILING on a single capture window. 0/None mat karo — SpeechRecognition
# tab tak record karta rehta hai jab tak 1.8s ki SILENCE na aaye. Kamre ka
# ambient noise kabhi 1.8s ke liye perfect silent nahi hota, to unlimited capture
# me SR HAMESHA ke liye block ho jata tha (Jarvis na sunta, na reply karta).
# 120s = purane truncating 10s se 12x zyada — lambe monologue poore capture
# hote hain, aur hang hone ka possibility zero.
LISTEN_PHRASE_TIME_LIMIT = 120
# Capture-first mode me callers (main.py ke 6 call sites) ke purane chhote
# timeout/phrase_time_limit IGNORE hote hain. In floors ke neeche clamp kar
# diye jaate hain, taaki koi bhi call site contract tod na sake.
LISTEN_TIMEOUT_FLOOR = 20.0
MIC_MAX_UTTERANCE_SECONDS = 120       # pure DoS ceiling — normal use me kabhi nahi chhuta
END_OF_SPEECH_WINDOW = 0.8            # 0.8s snappy confirmation window (was 1.5s — too slow)
END_OF_SPEECH_CONFIRMATIONS = 2       # 2 consecutive silent windows (~1.6s) = definitive end (was 3 -> 6 rounds)
CONTINUATION_TIMEOUT = 6.0            # was 2.0 — sochne ke liye 6s dete hain
LONG_PAUSE_TIMEOUT = 4.0              # was 1.5
MAX_CONTINUATION_ROUNDS = 30          # was 60 — 30 se zyada chunks ek saans me nahi
MAX_TOTAL_WORDS = 400                 # was 800 — ~2.5 min speech, usse zyada nahi
# Stall guard: agar STT N baar baar wahi bakwaas de raha hai (kharab mic /
# background shor), to loop ruk jaata hai. Bina iske ek hi listen() 60 rounds
# aur 366 words tak chala tha — yahi "system respond nahi kar raha" bug tha.
LISTEN_STALL_LIMIT = 3

# ---------------- ACOUSTIC BIO-SENSING & FAR-FIELD ----------------
ACOUSTIC_FILTER_ENABLED = True
# Filters ab ADVISORY hain: ye "yeh mechanical click lag raha hai" bolte hain,
# khud delete nahi karte. Deletion ke liye filter + duration + corroboration
# sab ek saath chahiye (voice.py me _is_definitive_artifact).
ACOUSTIC_ADVISORY_ONLY = True
KEYSTROKE_SUPPRESSION_ENABLED = True   # Ab "confirm" mode — akela filter drop nahi karta
KEYSTROKE_DROP_ALLOWED = False        # True karo tabhi single filter delete kar sake
FAR_FIELD_AGC_ENABLED = True          # Boosts distant/quiet voices across room
PARALINGUISTIC_DETECTION_ENABLED = True  # Yawning, Laughing, Singing/Humming, Crying

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
# Barge-In: Default False for laptop speakers to prevent Jarvis from hearing her own voice and cutting off!
# Can be enabled via BARGE_IN_ENABLED=true in .env when using headphones/earphones.
BARGE_IN_ENABLED = os.environ.get("BARGE_IN_ENABLED", "false").lower() in ("true", "1", "yes")
BARGE_IN_THRESHOLD = float(os.environ.get("BARGE_IN_THRESHOLD", "0.035"))   # High acoustic threshold rejects speaker bleed
BARGE_IN_GRACE_SECONDS = float(os.environ.get("BARGE_IN_GRACE_SECONDS", "0.40"))  # Grace window before listening for barge-in
BARGE_IN_SUSTAIN_BLOCKS = int(os.environ.get("BARGE_IN_SUSTAIN_BLOCKS", "4"))    # ~80ms sustained loud voice needed
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




