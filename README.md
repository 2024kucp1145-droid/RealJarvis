# Real Jarvis 🎙️

Tumhare Windows laptop ke liye personal AI assistant — naam se ya taali se
jaagta hai, password + face se verify karta hai, Hindi mein pyaari female
awaaz mein baat karta hai, aur bina touch kiye laptop ke kaam karta hai
(brightness, volume, apps kholna, YouTube gaana, files, email, aur bahut kuch).

---

## 1. Sach-sach baat pehle

Tumne jo 3 PDFs bheji thi ("50,000 commands", "12,000 commands") — unme
asal me sirf **~250 unique commands** the, baaki sab "variant 1, variant 2..."
karke repeat kiya gaya padding tha. Maine wo saare 250 nikaal kar
`command_data.py` mein daal diye hain, categorized aur executable bana kar.
Naya command add karna ho toh bas ek line add karni hai — system khud samajh
jayega (neeche "Naya command kaise add karein" dekho).

Kuch cheezein jo honestly clear kar deni chahiye:
- **Face recognition** Windows pe install karna sabse tricky part hai (dlib
  library ko compile karna padta hai) — neeche step-by-step diya hai.
- **Online voice (edge-tts)** ke liye internet chahiye; **offline voice**
  (pyttsx3) tumhare Windows me installed voice pack pe depend karta hai —
  agar Hindi female voice nahi mili to system automatically best available
  voice use karega.
- Ye ek **desktop-level personal automation tool** hai — apne hi laptop pe,
  apne data ke access ke saath chalega. Poora control config.py file me
  tumhare paas hai.

---

## 2. Install Steps (Windows)

### Step 1 — Python install karo
[python.org](https://python.org) se **Python 3.10 ya 3.11** install karo
(3.12+ me kuch libraries ka support abhi kam hai). Install karte waqt
"Add Python to PATH" zaroor check karo.

### Step 2 — Project folder laptop pe copy karo
Is poore `RealJarvis` folder ko kahi bhi rakh do, jaise `C:\RealJarvis`.

### Step 3 — Dependencies install karo
Command Prompt kholo us folder me:
```
cd C:\RealJarvis
pip install -r requirements.txt
```

**Agar `face_recognition` install fail ho** (ye sabse common issue hai,
kyunki iske andar `dlib` hai jo compile hota hai):
1. [CMake](https://cmake.org/download/) install karo, "Add to PATH" check karo
2. Visual Studio "Build Tools" install karo (C++ build tools wala option)
3. Fir dubara try karo: `pip install face_recognition`
4. Agar phir bhi fail ho, precompiled wheel use karo:
   `pip install dlib-bin` phir `pip install face_recognition`

Agar face recognition bilkul install nahi hota, chinta mat karo — `config.py`
me `FACE_VERIFICATION_ENABLED = False` kar do, sirf password se kaam chal
jayega. Baad me try kar lena.

### Step 4 — Apni details config.py me daalo
`config.py` kholo aur:
- `USER_NAME` apna naam daalo
- Password set karo: `python config.py set-password` chalao, jo hash aaye
  wo `PASSWORD_HASH` me paste karo
- Email chahiye to `EMAIL_ENABLED = True` karo, apna Gmail aur
  [App Password](https://myaccount.google.com/apppasswords) daalo
  (normal Gmail password kaam NAHI karega)

### Step 5 — Apna chehra register karo (face verification ke liye)
```
python setup_face.py
```
Webcam khulega, SPACE dabao photo lene ke liye.

### Step 6 — Chalao!
```
python main.py
```
Ek chota floating circle icon screen ke top-left corner me dikhega (usse
kahi bhi drag kar sakte ho). "Jarvis" bolo ya 2 baar taali maro. Pehli baar
password ek popup box me maangega (terminal me nahi), uske baad jab tak app
chal rahi hai dobara nahi maangega.

**Icon ka color batata hai Jarvis kya kar raha hai:**
- Grey = so raha hai (wake ka wait)
- Blue (pulsing) = sun raha hai
- Yellow = samajh/process kar raha hai
- Green (pulsing) = bol raha hai

Icon pe **right-click** karke "Quit" se band kar sakte ho.

---

## 3. Background me / Startup pe chalane ke liye (bina Command Prompt dikhe)

Ab poori tarah Command Prompt free chalta hai — bas `python` ki jagah
`pythonw` use karo (ye console window nahi kholta):
```
pythonw main.py
```

**Windows start/login hote hi khud chale, iske liye (automatic tareeka):**
```
python install_startup.py
```
Bas ek baar chalao — ye khud Startup folder me shortcut bana dega jo
`pythonw.exe` se `main.py` chalayega. Ab jab bhi laptop on/login hoga,
Jarvis khud background me start ho jayega, koi kaali screen nahi dikhegi,
bas wahi chota floating icon.

Hataana ho (auto-start band karna ho) toh:
```
python install_startup.py remove
```

**.exe banana ho (optional, taaki Python installed na hone par bhi chale):**
```
pip install pyinstaller
pyinstaller --onefile --noconsole --name Jarvis main.py
```
`dist\Jarvis.exe` ban jayega.

---

## 4. Kya-kya kar sakta hai abhi (Phase 1)

| Category | Examples |
|---|---|
| System | brightness/volume badhao-kam karo, lock/shutdown/restart/sleep, wifi/bluetooth, storage/RAM/battery batao |
| Apps | notepad, calculator, paint, task manager, control panel, cmd, powershell, settings, file explorer, device/disk manager, registry editor |
| Keyboard | copy/paste/cut/undo/redo/select all/find/save/print, tabs, browser back-forward |
| Files | folder banana, rename, copy, delete, zip/unzip, downloads/documents kholna |
| Browser/YouTube | website kholna, Google search, gaana play/pause/next/previous |
| Email | email bhejna, unread mails padhna, inbox search |
| Baat-cheet | "kaise ho", "tum kaun ho", "so jao", "bye jarvis" |

Sab Hindi (Hinglish) me bol kar chala sakte ho, jaise:
- "Jarvis, brightness kam karo"
- "gaana chalao [song name]"
- "notepad kholo"
- "naya folder banao"

---

## 5. AI Conversation (jaisa Claude khud karta hai)

Ab Jarvis fixed command list ke bahar bhi kuch bhi pucho toh natural
jawab de sakta hai - Claude AI se connect karke.

1. Yaha se free API key banao: https://console.anthropic.com/settings/keys
2. `config.py` me:
   ```python
   AI_ENABLED = True
   ANTHROPIC_API_KEY = "yaha_apni_key_paste_karo"
   ```
3. `pip install anthropic` (agar requirements.txt se already install nahi hua)

Ab jo bhi command match na ho, Jarvis Claude se pooch kar natural, chhota
jawab dega, bole hue awaaz me. (Note: har jawab ka thoda sa API cost lagta
hai - shuru me free credits milte hain.)

---

## 6. Naya command kaise add karein

`command_data.py` kholo, `COMMANDS` dictionary me ek naya entry daalo:

```python
"open_spotify": {"type": "run", "action": "spotify",
    "trigger": ["spotify kholo", "gaane sunne ka app kholo"]},
```

`"type"` decide karta hai kaunsa executor chalega:
- `"run"` → koi bhi program/Run command (`action` = program ka naam)
- `"keyboard"` → koi bhi keyboard shortcut (`action` = jaise `"ctrl+c"`)
- `"system"` / `"browser"` / `"file"` / `"email"` → `commands/` folder ki
  respective file me naya function likho usi naam se jo `action` me diya hai

Bas itna hi — dobara chalao, naya command turant kaam karega.

---

## 7. Roadmap — aage kya add ho sakta hai

- Zyada natural conversation (chhote AI model se emotional replies)
- WhatsApp/Instagram automation
- Smart-home style device control
- Multiple-user face profiles
- Custom wake-word engine (Porcupine) — abhi ka wake system "sunte rehna aur
  match karna" tarike se kaam karta hai jo thoda zyada CPU/internet use karta
  hai; Porcupine se ye fully offline aur halka ho jayega

Jo bhi next feature chahiye ho, bata dena — isi structure me add karte
jayenge.
