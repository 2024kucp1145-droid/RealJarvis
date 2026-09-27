# RealJarvis v2.0

I'm a second-year CS student at IIIT Kota. Last semester I kept getting annoyed that every "AI assistant" either needed internet for everything or was basically just a glorified search wrapper. So I built my own.

This is RealJarvis — a personal autonomous agent that runs 24/7 on my Windows laptop. It wakes up when I call its name, understands what I'm doing on screen, remembers our past conversations, controls my system, and can even be commanded over WhatsApp from my phone. It's not perfect, but it's real and it runs.

---

## What it actually does

**Voice & Hearing**
- Wakes up on "Jarvis" (or 2 claps if you enable that)
- Far-field audio — you can talk from across the room, it auto-boosts quiet voices
- Suppresses keyboard typing sounds so it doesn't trigger mid-typing
- Detects if you're yawning, laughing, humming, or crying and responds accordingly
- Falls back to offline STT if internet is down

**Brain & Reasoning**
- Powered by Gemini (gemini-flash-lite by default, swap in config)
- Chain-of-Thought ReAct engine — reasons step-by-step before acting, not just if-else matching
- Reads your active window + screen context before answering, so it knows what you're working on

**Memory**
- Remembers everything across sessions using a hybrid vector search engine
- 3072-D embeddings via Google GenAI, stored locally in SQLite (no cloud DB dependency)
- Cosine similarity + BM25 lexical fusion for fast recall
- Sub-10ms lookup, works fully offline

**Self-Evolution**
- If you ask it to do something it doesn't know, it writes the Python code for that skill itself
- Runs it through an AST safety scanner and sandbox first
- Hot-reloads the new skill without restarting
- All self-written skills go into `custom_skills/` folder

**System Control**
- Volume, brightness, lock, sleep, shutdown, restart
- Opens any app — Notepad, Chrome, VS Code, anything
- File operations — create, rename, copy, delete, zip
- Keyboard shortcuts — copy/paste/undo/redo, etc.
- Email — send, read unread, search inbox

**WhatsApp Remote Control**
- Message yourself on WhatsApp to control the laptop remotely
- Commands: live screenshot, system stats (CPU/RAM/battery), send files to phone
- Remote terminal: `cmd: <any command>` executes it on laptop and sends output back
- Remote power control: lock, sleep, shutdown
- Secured by master phone number whitelist

**Background Sentries (runs automatically)**
- Hardware health monitor (CPU/RAM/battery alerts)
- Morning briefing at startup
- Download folder auto-organizer
- Desktop janitor
- Email watcher
- Proactive security guardian
- And a few more — all running silently in the background

**Other stuff**
- Eye control (webcam iris tracking → moves cursor, blink to click — honestly still rough but it works)
- Predictive copilot — watches what you're working on and suggests next steps
- WhatsApp Desktop + Mobile bridges for sending messages by voice
- Google Maps / travel queries
- Video notes (watches a video and takes notes for you)
- GUI with floating status icon (color shows what Jarvis is doing)
- "Avengers Assemble" command — runs a full 10-point system diagnostic and tells you what's working

---

## Setup (Windows)

### Requirements
- Python 3.10 or 3.11 (3.12+ has some library issues)
- A working microphone
- Internet for Gemini API + online TTS (works offline too, just degraded)

### Install
```bash
cd C:\RealJarvis_v2\RealJarvis
pip install -r requirements.txt
```

**Face recognition install krne mein dikkat aaye (common issue):**
```bash
pip install cmake
pip install dlib-bin
pip install face_recognition
```
Agar tab bhi fail ho — `config.py` mein `FACE_VERIFICATION_ENABLED = False` kar do, sirf password se kaam chal jayega.

### Configure
`config.py` kholo aur ye set karo:
```python
USER_NAME = "YourName"
GEMINI_API_KEY = "your-key-here"   # aistudio.google.com/apikey se free milti hai
EMAIL_ADDRESS = "your@gmail.com"
EMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"  # Gmail App Password, normal password nahi
```

Password hash set karna:
```bash
python config.py set-password
```

Face register karna (optional):
```bash
python setup_face.py
```

### Run
```bash
python main.py
```

Background mein silent run karna (no console window):
```bash
pythonw main.py
```

Windows startup pe automatically run karna:
```bash
python install_startup.py
# hatana ho to:
python install_startup.py remove
```

### Status icon colors
- **Grey** → waiting for wake word
- **Blue (pulsing)** → listening
- **Yellow** → thinking
- **Green (pulsing)** → speaking

Right-click the icon → Quit to close.

---

## Adding new commands

Open `command_data.py` and add an entry to the `COMMANDS` dict:
```python
"open_spotify": {
    "type": "run",
    "action": "spotify",
    "trigger": ["spotify kholo", "music app kholo"]
},
```
Type options: `run`, `keyboard`, `system`, `browser`, `file`, `email`

Restart and the command works immediately. That's it.

---

## Project structure (quick map)

| File | What it does |
|---|---|
| `main.py` | Entry point, orchestrates everything |
| `ai_brain.py` | Core AI response engine |
| `agentic_cot_brain.py` | Chain-of-Thought ReAct reasoning |
| `memory.py` | Vector memory engine (SQLite + embeddings) |
| `voice.py` | STT + TTS pipeline |
| `acoustic_filter_engine.py` | Far-field audio, keystroke suppression, bio-sensing |
| `wake_engine.py` | Wake word + clap detection |
| `self_evolution_engine.py` | Skill synthesis + hot-reload |
| `whatsapp_mobile_bridge.py` | Phone to laptop remote control |
| `avengers_protocol.py` | Full system diagnostic |
| `universal_predictive_copilot.py` | Workflow prediction |
| `eye_control.py` | Webcam iris tracking mouse control |
| `command_data.py` | All voice command definitions |
| `config.py` | All your personal settings |
| `custom_skills/` | Self-written skills land here |

---

## Known issues / honest notes

- Eye control is approximate — normal webcam se pixel-perfect accuracy possible nahi hai, it drifts
- Face recognition requires dlib which is painful to install on Windows
- Gemini API has rate limits on free tier; if you hit them Jarvis falls back gracefully to offline mode
- WhatsApp bridge needs WhatsApp Web open in a browser session to work

---

## Security hardening (critical fixes)

Ye cheezein harden kar di gayi hain — purane behavior me real vulnerabilities the:

1. **Daemon gateway token** — pehle `daemon_api_server.py` me ek hardcoded fallback token
   (`realjarvis-daemon-secure-token`) tha, isliye bina config ke poori remote API khuli rehti thi.
   Ab koi fallback nahi hai: `DAEMON_AUTH_TOKEN` set nahi hai toh daemon start hi nahi hota
   (fail-fast). Generate karo:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
   `.env` me `DAEMON_AUTH_TOKEN=<value>` daalo. Gateway ab default me `127.0.0.1` par bind hota hai
   (public exposure ke liye `DAEMON_HOST=0.0.0.0` explicitly set karo).

2. **Webhook signature verification** — pehle `/api/webhook/*` par **koi authentication nahi** thi,
   yaani koi bhi anonymous request `daemon.execute_command()` chala sakta tha (remote command
   execution). Ab Incoming WhatsApp webhook par Twilio ki `X-Twilio-Signature` (HMAC-SHA1)
   verify hoti hai — `TWILIO_AUTH_TOKEN` set nahi hai toh webhook reject hota hai.

3. **AST safety scanner allowlist** — pehle ye blocklist tha (sirf `rmtree`, `format`, `fork`...),
   jisse `subprocess.run(["format","C:"])`, `os.system(...)`, `os.remove(...)`, aliased imports
   (`import os as o`) — kuch bhi pakda nahi jaata tha. Ab **allowlist model** hai: sirf approved
   safe modules import ho sakte hain; `subprocess`, `ctypes`, `os` (sirf `os.path`), `shutil`,
   `socket`, `win32*`, `pickle` etc. blocked hain, aur dunder sandbox-escape / `eval` / `exec` /
   `__import__` / file-write `open(mode="w")` bhi flagged hote hain.

4. **Memory engine (offline recall)** — local fallback embeddings Python ke built-in `hash()` se
   ban rahe the, jo per-process randomized hota hai, isliye restart ke baad offline vectors match
   hi nahi karte the. Ab deterministic `blake2b` hashing hai, aur Gemini embedding dimension
   (`output_dimensionality=768`) pinned hai taaki online store ki hui memory offline query se
   compare ho sake.

5. **Password hashing** — `PASSWORD_HASH` pehle unsalted SHA-256 tha (rainbow-table crackable).
   Ab salted **PBKDF2-HMAC-SHA256 (260k iterations)** hai. Purana SHA-256 hash backward-compatible
   verify hota rahega; naya password set karte hi migrate ho jayega:
   ```bash
   python config.py set-password
   ```

**Regression tests:** `tests/test_critical_fixes.py` (38 tests) in sab fixes ko lock karta hai —
bypass attempts ab CI me fail honge.
```bash
venv\Scripts\python.exe -m pytest tests -v
```

> ⚠️ Agar tumne pehle kabhi `config.py` ya `.env` commit kiya tha, toh localStorage se secrets
> rotate kar do (Gemini key, Gmail app password, ElevenLabs key) — git history permanently
> public rehti hai.

---

## Built by

Piyush — IIIT Kota, 2024 batch
GitHub: https://github.com/2024kucp1145-droid
