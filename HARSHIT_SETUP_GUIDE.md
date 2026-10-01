# 🤖 RealJarvis — Harshit ke Liye Setup Guide

> **Ye guide Harshit ke liye hai** — Piyush ke Jarvis ko apne Windows PC pe run karne ke liye.

---

## ✅ Requirements (Pehle Ye Karo)

| Kya chahiye | Download Link |
|---|---|
| **Python 3.10+** | https://www.python.org/downloads/ |
| **Git** | https://git-scm.com/download/win |
| **Google Gemini API Key** (FREE) | https://aistudio.google.com/apikey |

> ⚠️ Python install karte waqt **"Add Python to PATH"** checkbox zaroor tick karo!

---

## 🚀 Method 1: One-Click Automatic Setup (Sabse Aasaan)

1. Ye file download karo ya copy karo apne PC pe:  
   **`setup_for_harshit.bat`**

2. **Double-click** karo `setup_for_harshit.bat`

3. Script apne aap:
   - Repo clone karega
   - Python environment banayega
   - Saari libraries install karega
   - `.env` file open karega (tum fill karo)
   - Password setup karega

4. Done! `start_jarvis.bat` double-click karo aur Jarvis chal jayegi!

---

## 🛠️ Method 2: Manual Step-by-Step

### Step 1 — Repo Clone Karo

```cmd
git clone https://github.com/2024kucp1145-droid/RealJarvis.git C:\RealJarvis
cd C:\RealJarvis
```

### Step 2 — Virtual Environment Banao

```cmd
python -m venv venv
venv\Scripts\activate
```

### Step 3 — Libraries Install Karo

```cmd
pip install -r requirements.txt
```

> Isme 3-5 minute lag sakte hain, chill karo ☕

### Step 4 — `.env` File Setup Karo

```cmd
copy .env.example .env
notepad .env
```

`.env` file mein ye fields **zaroor** fill karo:

```env
USER_NAME=Harshit
GEMINI_API_KEY=your_google_gemini_api_key_here
```

Baaki fields optional hain (WhatsApp, Email, etc.)

### Step 5 — Password Set Karo

```cmd
python config.py set-password
```

Jarvis login ke liye ek password choose karo.

### Step 6 — Jarvis Run Karo! 🎉

```cmd
python main.py
```

---

## 🔑 API Key Kaise Milegi (FREE)?

1. **Google Gemini (ZAROOR):**
   - https://aistudio.google.com/apikey pe jao
   - Google account se login karo
   - "Create API Key" click karo
   - Copy karo → `.env` mein `GEMINI_API_KEY=` ke baad paste karo

2. **ElevenLabs Voice (Optional — Agar sweet female voice chahiye):**
   - https://elevenlabs.io pe free account banao
   - Profile → API Keys → Generate
   - `.env` mein `ELEVENLABS_API_KEY=` ke baad paste karo

---

## 🗣️ Jarvis Ko Kaise Use Karein?

| Command | Kya hoga |
|---|---|
| **"Jarvis"** (bolke) | Jarvis activate hogi |
| **"Kaise ho Jarvis?"** | Jarvis jawab degi |
| **"Screenshot lo"** | Screenshot legi |
| **"Battery kitni bachi hai"** | Battery status batayegi |
| **"YouTube kholo"** | Browser mein YouTube open hoga |
| **"Aaj ka mausam kaisa hai"** | Weather batayegi |
| **"Email check karo"** | Unread emails padhegi |
| **"Sone ka time ho gaya"** | PC sleep mode mein chali jayegi |

---

## ❓ Common Problems

**Problem: "Python not found"**
```
Python uninstall karke dobara install karo.
Install karte waqt "Add Python to PATH" tick karo.
```

**Problem: "pip install fail ho raha hai"**
```cmd
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**Problem: "Mic nahi sun raha Jarvis"**
- Windows Settings → Sound → Input → sahi mic select karo
- Jarvis start hone ke baad thoda wait karo, mic calibrate hoti hai

**Problem: "Awaaz nahi aa rahi"**
- Internet connection check karo (Edge-TTS internet se aati hai)
- Volume check karo 😄

---

## 📁 Important Files

```
C:\RealJarvis\
├── main.py          ← Jarvis start karo: python main.py
├── .env             ← Teri settings (API keys, naam, etc.)
├── config.py        ← Advanced settings
├── voice.py         ← Awaaz ka engine
└── start_jarvis.bat ← Double-click shortcut
```

---

## 💬 Need Help?

Piyush se contact karo — usne ye banaya hai aur wahi best explain kar sakta hai! 😄

---

*RealJarvis by Piyush | Setup Guide for Harshit*
