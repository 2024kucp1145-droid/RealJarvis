# 🧬 JARVIS AUTONOMOUS SELF-EVOLUTION ENGINE (USER MANUAL)

Yeh manual aapko sikhata hai ki aap apne **Jarvis ko naye skills kaise sikha sakte hain** aur yeh system under-the-hood kaise kaam karta hai.

---

## 🌟 1. Jarvis Naye Skills Kaise Sikhta Hai? (Interactive Permission Flow)

Jab aap koi aisa task bolte hain jo Jarvis ko pehle se nahi aata, Jarvis ab **seedha aapse permission maangti hai**:

```
[Aapne Bola]
"Jarvis, desktop par jitne bhi .png files hain unka ek zip bana do"
                     │
                     ▼
[Jarvis Ka Jawab (Permission Request)]
"Boss, yeh skill mujhe abhi nahi aati hai. 
 Kya main iska naya Python automation skill seekh kar bana doon? (Haan / Nahi)"
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    [Aapne Kaha: "Haan"]    [Aapne Kaha: "Nahi"]
         │                       │
         ▼                       ▼
[16-Phase Engine Start]    [Cancelled Safely]
```

---

## ⚡ 2. 16-Phase Engine Kya Karta Hai (In 60 Seconds):

1. **📸 Context Sniffing:** Aapke desktop ka active app aur window state capture karta hai.
2. **📝 Spec Formulation:** Naye skill ka unique Trigger, Name aur Category define karta hai.
3. **✍️ Code Synthesis:** Gemini AI se safe, modular Python automation code likhta hai.
4. **🛡️ AST Safety & Guardrails:** Code scan karta hai taaki koi virus, infinite loop ya crash bug na ho.
5. **🧪 Sandbox Execution:** Ek isolated temporary subprocess mein code chala kar test karta hai.
6. **🔄 Self-Correction:** Agar koi error aayi, toh AI khud error fix karke dobara test karta hai.
7. **💾 Disk & SQLite Registry:** Skill ko `custom_skills/<skill_name>.py` aur database mein permanently save karta hai.
8. **🔥 Dynamic Hot-Reloading:** Bina Jarvis ko restart kiye live memory (RAM) mein load kar deta hai!
9. **📢 Completion Voice & WhatsApp Broadcast:** Aapko bol kar batata hai:
   > *"Boss, naya skill 'PNG Zipper' successfully seekh liya hai aur live load ho gaya hai! Kya abhi chala kar dekhna hai?"*

---

## 🎙️ 3. Jarvis Ko Train Karne Ke Sample Commands:

Aap in tarike se Jarvis ko naye skills seekhne ko keh sakte hain:

### Example A: File Automation
* *"Jarvis, naya skill seekho jo Downloads folder ke saare PDF ko Documents mein move kar de."*

### Example B: Web / Browser Automation
* *"Jarvis, naya feature seekh lo jo Speedtest website khol kar internet speed check kare."*

### Example C: System Productivity
* *"Jarvis, ek naya skill banao jo active window ka title aur time notepad file mein log kare."*

---

## 🔍 4. Seekhe Hue Skills Check & Inspect Kaise Karein?

1. **🗣️ Voice Command Se Puchhein:**
   - *"Jarvis, tumne kya-kya seekha hai?"*
   - *"Jarvis, apne skills batao"*
   - *(Jarvis voice mein summary degi aur aapki screen par **Visual Tkinter Skill Dashboard** open kar degi!)*

2. **🛠️ Skill Ko Refine / Update Kaise Karein (Phase 15 Delta Engine):**
   - Agar kisi seekhe hue skill mein badlaav karna ho:
   - *"Jarvis, 'Speedtest' skill mein yeh change karo ki speed result WhatsApp par bhi bheje."*
   - Jarvis code ko update karke sandbox mein dobara re-verify aur hot-reload kar degi!

---

## 🔒 5. Safety & Security Guarantee:

* **No System Damage:** AST Static Scanner kisi bhi dangerous OS call (`rmdir /s /q`, formatting, kernel overrides) ko block kar deta hai.
* **Isolated Sandbox:** Har naya code pehle dummy context mein run hota hai — agar code fail hua toh permanent memory mein save nahi hota.
* **Permission First:** Bina aapke *"Haan"* bole Jarvis kabhi bhi naya code generate nahi karegi!

---

> **Tip:** Jab bhi koi unlearned task bole aur Jarvis pooche *"Kya main seekh loon?"*, bas boliye **"Haan"** ya **"Seekh lo"** — 60 seconds mein naya skill aapke computer par live ho jayega! 🚀
