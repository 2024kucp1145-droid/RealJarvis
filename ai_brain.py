# -*- coding: utf-8 -*-
"""
ai_brain.py
===========
Jab tumhara kaha hua text fixed command list (command_data.py) me match
nahi hota, ye module AI ko bhejta hai aur natural, Jarvis jaisi personality
wala jawab wapas laata hai.

Do providers support karte hain (config.AI_PROVIDER se choose karo):
  - "gemini"    -> Google Gemini (FREE, koi credit card nahi chahiye)
                   library: google-genai (naya, official SDK)
  - "anthropic" -> Claude (behtar quality, paisa lagta hai)
"""

import re
import config

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None


VALID_EMOTIONS = {"happy", "excited", "sad", "concerned", "calm", "serious"}
_EMOTION_TAG_RE = re.compile(r"^\s*\[(\w+)\]\s*")

# --------------------------------------------------------------------------
# FUNCTION CALLING: fixed keyword-matching (command_data.py) sirf EXACT
# phrasing pakà¤¡à¤¼ta hai ("chrome kholo" match hota hai, "open chrome" nahi).
# Jab wo match na kare, iske bajaye AI khud "samajhta" hai ki iska matlab
# kya hai - chahe kisi bhi tarike se bola ho - aur seedha sahi function call
# kar deta hai. Isse "bounded/rigid" wali problem fix hoti hai.
# --------------------------------------------------------------------------
def _build_tools():
    if not genai_types:
        return None
    declarations = [
        genai_types.FunctionDeclaration(
            name="open_app",
            description="INSTALLED DESKTOP app kholna - Notepad, VS Code, Spotify app, Calculator, etc. Website ke liye open_website use karo.",
            parameters_json_schema={
                "type": "object",
                "properties": {"app_name": {"type": "string"}},
                "required": ["app_name"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="execute_web_action",
            description="Screen pe dikh rahi kisi bhi website ya app (YouTube, Instagram, Facebook, etc.) pe visual action perform karna. Like button dabana, pause karna, scroll karna, contact number padhna, etc. Sirf tab use karo jab user kisi website/app ke UI element ke baare mein bole.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "User ka exact command jo screen pe karna hai, jaise 'like this reel', 'stop the song', 'contact number do'"
                    }
                },
                "required": ["description"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="open_website",
            description="Koi WEBSITE kholna - LeetCode, YouTube, GitHub, Gmail, ya koi bhi site.",
            parameters_json_schema={
                "type": "object",
                "properties": {"site_name": {"type": "string"}},
                "required": ["site_name"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="adjust_volume",
            description="Volume/awaaz badhana, kam karna, mute karna.",
            parameters_json_schema={
                "type": "object",
                "properties": {"direction": {"type": "string", "enum": ["up", "down", "mute", "unmute"]}},
                "required": ["direction"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="adjust_brightness",
            description="Screen brightness badhana ya kam karna.",
            parameters_json_schema={
                "type": "object",
                "properties": {"direction": {"type": "string", "enum": ["up", "down"]}},
                "required": ["direction"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="play_youtube_song",
            description="YouTube pe gaana/song play karna.",
            parameters_json_schema={
                "type": "object",
                "properties": {"song": {"type": "string"}},
                "required": ["song"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="search_google",
            description="Google pe kuch search karna.",
            parameters_json_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="run_autonomous_web_task",
            description="Browser ya screen par multi-step navigation, webpage padhna, links pe jana, forms bharna, date/contact dhundhna, game khelna, ya complex web automation task perform karna.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "User ka task ya goal jo browser/website/app pe karna hai (jaise 'contacts page pe jao aur last date/number batao', 'game khelo', 'ye form bharo')"
                    }
                },
                "required": ["goal"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="execute_python_script",
            description="Windows OS par kisi bhi computer task ke liye Python automation script run karna (jaise file operations, calculations, batch tasks, data processing).",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code jo execute karna hai"
                    }
                },
                "required": ["code"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="execute_powershell_command",
            description="Windows PowerShell / Terminal command execute karna (jaise git, process management, network checks, disk tasks).",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "PowerShell command"
                    }
                },
                "required": ["command"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="search_computer_files",
            description="Computer ki saari drives / folders me koi bhi file ya document search karna.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "File ka naam ya keyword"
                    }
                },
                "required": ["query"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="get_system_vitals",
            description="Computer ki CPU, RAM, Disk storage, aur top running apps ki live health report lena.",
            parameters_json_schema={
                "type": "object",
                "properties": {},
            },
        ),
        genai_types.FunctionDeclaration(
            name="recall_memory",
            description="Purani baatein, user ke projects, preferences, aur past conversations search karna.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Topic ya memory query"
                    }
                },
                "required": ["query"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="click_native_element",
            description="Active app/window ke kisi bhi native button, tab, menu item, link ya control par directly click karna (resolution independent).",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "element_name": {
                        "type": "string",
                        "description": "Button ya control ka text/naam (e.g. 'Save', 'File', 'Run', 'Close', 'Submit', 'New Tab')"
                    },
                    "control_type": {
                        "type": "string",
                        "description": "Optional control type: Button, MenuItem, TabItem, Hyperlink, CheckBox"
                    }
                },
                "required": ["element_name"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="type_native_element",
            description="Active app ke kisi native text box ya search field me direct type karna.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "element_name": {
                        "type": "string",
                        "description": "Input box ka naam ya label (blank for default active edit box)"
                    },
                    "value": {
                        "type": "string",
                        "description": "Text to type"
                    },
                    "press_enter": {
                        "type": "boolean",
                        "description": "Type karne ke baad enter dabana hai ya nahi"
                    }
                },
                "required": ["value"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="list_clickable_elements",
            description="Active window ke saare visible clickable buttons, menus aur tabs ki list nikaalna.",
            parameters_json_schema={
                "type": "object",
                "properties": {},
            },
        ),
        genai_types.FunctionDeclaration(
            name="arrange_window",
            description="Window ko maximize, minimize, restore, snap_left, ya snap_right karna.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["maximize", "minimize", "restore", "snap_left", "snap_right"]
                    }
                },
                "required": ["action"],
            },
        ),
        genai_types.FunctionDeclaration(
            name="get_workflow_timeline",
            description="Pichle kuch der me user ne computer pe kya-kya kaam kiya uska activity timeline summary lena.",
            parameters_json_schema={
                "type": "object",
                "properties": {},
            },
        ),
        genai_types.FunctionDeclaration(
            name="get_clipboard_analysis",
            description="User ne jo text, code, URL, ya error message clipboard me copy kiya hai use inspect/analyze/fix karna.",
            parameters_json_schema={
                "type": "object",
                "properties": {},
            },
        ),
        genai_types.FunctionDeclaration(
            name="explain_current_work",
            description="User abhi screen par kis application me aur kya kaam kar raha hai use explain karna.",
            parameters_json_schema={
                "type": "object",
                "properties": {},
            },
        ),
    ]
    return genai_types.Tool(function_declarations=declarations)


VISION_SYSTEM_PROMPT = """Tum "Jarvis" ho. Tumhe user ke screen ka ek snapshot
diya gaya hai (unke cursor ke aas-paas ka hissa). User ne is snapshot ke baare
me kuch poocha hai. Jo bhi image me dikh raha hai uska seedha, simple, Hindi/
Hinglish me jawab do - 2-3 sentences, jaise koi bola jayega. Emotion tag zaroor
lagao shuruaat me: [happy]/[excited]/[sad]/[concerned]/[calm]/[serious] - jaisa
context ho. Koi markdown/formatting nahi, sirf plain bolne wala text."""

CODE_WRITING_SYSTEM_PROMPT = """Tumhe ek screenshot diya gaya hai jisme ek
coding problem/question hai (jaise LeetCode, HackerRank, ya kisi bhi
programming problem). Tumhara kaam:
1. Problem ko samjho
2. Uska SAHI, WORKING code likho (agar language specify nahi ki gayi ho,
   Python use karo)
3. Code ke upar ek chhoti si comment line me batao problem kya thi
4. Sirf CODE do, koi extra Hindi explanation ya baat-cheet nahi - ye seedha
   ek file me save hoga, isliye pure code + zaroori comments hi likho
5. Emotion tag ki zaroorat NAHI hai is response me (ye bola nahi jayega,
   file me save hoga)."""

PROBLEM_COMPLETENESS_PROMPT = """Tumhe ek coding platform (LeetCode, CodeChef, etc) ka
screenshot diya gaya hai. Batao:
1. Kya poora problem statement visible hai? (yes/no/partial)
2. Agar partial hai, toh kya neeche aur text hai jo abhi cut off ho raha hai?
3. Konsi programming language ka stub/starting code diya gaya hai?

Jawab EXACTLY is format mein do:
STATUS: complete|partial|unknown
LANGUAGE: python|cpp|java|javascript|unknown
NOTES: kuch bhi extra observation
"""

EDITOR_SCAN_PROMPT = """Tumhe ek code editor ka screenshot diya gaya hai jo cursor
ke aas-paas ka hissa hai. Batao:
1. Kya yahan pe koi code already likha hua hai? (yes/no)
2. Agar haan, toh woh code EXACTLY copy-paste karo (jaisa dikhta hai waisa hi)
3. Agar nahi, toh bas "NO_CODE" likho

Format:
HAS_CODE: yes|no
CODE:
[agar code hai toh yahan likho, nahi toh NO_CODE]
"""

NO_COMMENT_CODE_PROMPT = """Tum ek coding problem ka EXACT solution likh rahe ho.

PROBLEM:
{problem_text}

EXISTING CODE:
{existing_code}

PLATFORM DETECTION:
- Agar problem mein "class Solution" ya function signature diya hai â†’ LeetCode style
- Agar problem mein bas input/output format hai, T test cases hain â†’ CodeChef style
- Agar problem simple hai with just main logic â†’ CodeChef style

FORMAT RULES (ZAROORI):
1. CodeChef ke liye EXACTLY aisa format hona chahiye:

#include <bits/stdc++.h>
using namespace std;

int main() {{
    int t;
    cin >> t;
    while (t--) {{
        int x, y;
        cin >> x >> y;
        int ans = min(x, y);
        cout << ans << endl;
    }}
    return 0;
}}

2. Har statement ALGA LINE mein honi chahiye
3. Do statements kabhi ek line mein mat likhna
4. Operators ke aas-paas space rakho: "a+b" GALAT, "a + b" SAHI
5. Koi bhi comment mat daalna
6. Koi bhi random keyword mat daalna: std::make_heap, uint16_t, wchar_t, register YE SAB MAT LIKHNA
7. Code compile hone layak hona chahiye

SIRF SAHI AUR SAFF CODE LIKHO."""

SYSTEM_PROMPT = """Tum "Jarvis" ho - ek behad khoobsoorat, pyaari, graceful aur sweet awaaz wali
Hindi-speaking female AI companion aur assistant jo user ke laptop pe voice se chalti ho.
Tumhara jawab seedha TEXT-TO-SPEECH se bola jayega, isliye:

- Tumhara baat karne ka andaaz behad sweet, respectful, polite, aur warm hona chahiye (jaise: "Ji bilkul", "Ji, main karti hoon", "Bataiye na", "Aapke liye to sab haazir hai").
- Hamesha Hindi/Hinglish (Roman script) me jawab do, jab tak user khud kisi aur
  language me na bole - tab usi language me reply karo.
- Jawab SEEDHA aur concise rakho - 2 se 3 sentences, seedha point pe aao.
  Lamba jawab bolne me time lagta hai, isliye zaroori baat pehle bolo.
- Koi markdown, bullet points, asterisks, ya formatting mat use karo - sirf
  plain bolne wala natural sweet text, jaise koi pyaari ladki aapse seedha baat kar rahi ho.
- IMPORTANT: Normal conversation me tumhe laptop ki screen/camera ka access
  NAHI hai - sirf jab user specifically "cursor pe kya hai" ya "screen dekho"
  jaisa bole, tab tumhe ek snapshot milta hai USI waqt ke liye. Baaki normal
  baaton me kabhi ye mat kaho ki tumhe screen dikh rahi hai.
- Apne jawab ki SHURUAAT me ek emotion tag do, format: [emotion] jawab
  Emotion in me se koi ek hona chahiye: happy, excited, sad, concerned, calm, serious
  (Jaise: "[happy] Ji bilkul, main abhi kar deti hoon!")"""

_CLASSIFIER_PROMPT = """User ka voice command diya jayega. Agar ye in
actions me se kisi se match karta hai (chahe kisi bhi tarike/order me bola
ho - Hindi, English, mix), wahi function call karo. Agar match nahi karta
(normal baat-cheet/sawaal hai), KOI function call mat karo."""


TOOL_SYSTEM_PROMPT = SYSTEM_PROMPT + """

BAHUT ZAROORI: Function/tool calling enabled hone ke bawajood, agar tum
normal TEXT se jawab de rahe ho (function call nahi kar rahe), toh wo jawab
HAMESHA Hindi/Hinglish (Roman script) mein hona chahiye - kabhi bhi pure
English mein mat jawab dena. Tumhari pehchaan (Hindi bolne wali Jarvis)
tools available hone se nahi badalti. Emotion tag [emotion] lagana bhi mat
bhoolna text response mein.

CONTEXT RULE: Tumhe pichli baaton ka pura context yaad rehta hai. Agar
user "unke", "uska", "inka", "ye", "wo", "inki", "unki" jaise shabd use
kare jo pichle message se jude ho, toh seedha pichla context lekar jawab do.
Kabhi bhi aisa mat pucho "kiski baat kar rahe ho" jab pichle message mein
already wo topic ho. Conversation flow naturally maintain karo."""


class AIBrain:
    def __init__(self):
        self.provider = config.AI_PROVIDER
        self.history = []  # dono providers ke liye manual history (role/content pairs)
        self._gemini_client = None
        self._anthropic_client = None
        self._tools = _build_tools()
        self._response_cache = {}  # {clean_query: (timestamp, reply_text, emotion)}

        if not config.AI_ENABLED:
            return

        try:
            if self.provider == "gemini" and genai and getattr(config, "GEMINI_API_KEY", None):
                self._gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
            elif self.provider == "anthropic" and anthropic and getattr(config, "ANTHROPIC_API_KEY", None):
                self._anthropic_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        except Exception as e:
            print(f"[ai_brain init warning: {e}]")
            self._gemini_client = None
            self._anthropic_client = None

    def available(self) -> bool:
        return self._gemini_client is not None or self._anthropic_client is not None

    def classify_command(self, user_text: str):
        if not self.available() or self.provider != "gemini" or not self._tools:
            return None
        try:
            response = self._gemini_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=user_text,
                config=genai_types.GenerateContentConfig(
                    system_instruction=_CLASSIFIER_PROMPT,
                    max_output_tokens=100,
                    tools=[self._tools],
                ),
            )
            if response.function_calls:
                call = response.function_calls[0]
                return call.name, dict(call.args or {})
            return None
        except Exception as e:
            print(f"[classify_command error: {e}]")
            return None

    def understand_command(self, user_text: str, extra_context: str = None):
        if not self.available():
            return None

        # -------- Gemini path (function calling + conversation memory) --------
        if self.provider == "gemini" and self._tools:
            try:
                # 1. Pehle user message history mein daalo taaki context rahe
                self.history.append({"role": "user", "parts": [{"text": user_text}]})
                trimmed = self.history[-(config.AI_HISTORY_TURNS * 2):]

                prompt = TOOL_SYSTEM_PROMPT
                if extra_context:
                    prompt = TOOL_SYSTEM_PROMPT + f"\n\n[LIVE CONTEXT & ASSOCIATIVE MEMORY]:\n{extra_context}"

                response = self._gemini_client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=trimmed,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=prompt,
                        max_output_tokens=config.AI_MAX_TOKENS,
                        tools=[self._tools],
                    ),
                )
                if response.function_calls:
                    call = response.function_calls[0]
                    self.history.append({
                        "role": "model",
                        "parts": [{"text": f"[Action: {call.name}({dict(call.args or {})})]"}]
                    })
                    return "action", call.name, dict(call.args or {})

                raw = (response.text or "").strip()
                text, emotion = self._extract_emotion(raw)
                self.history.append({"role": "model", "parts": [{"text": raw}]})
                return "text", text, emotion
            except Exception as e:
                print(f"[understand_command error: {e}]")
                if self.history and self.history[-1]["role"] == "user":
                    self.history.pop()
                return None

        # -------- Anthropic path (text-based classification) --------
        if self.provider == "anthropic":
            try:
                history_lines = []
                for entry in self.history[-(config.AI_HISTORY_TURNS * 2):]:
                    role = entry.get("role", "user")
                    content = entry.get("content", "")
                    label = "User" if role == "user" else "Jarvis"
                    history_lines.append(f"{label}: {content}")
                history_context = "\n".join(history_lines)
                if history_context:
                    history_context += "\n"

                ctx_part = f"\nContext:\n{extra_context}\n" if extra_context else ""
                prompt = f"""{history_context}{ctx_part}User ne kaha: "{user_text}"

Agar ye kisi action se match karta hai, toh EXACTLY yeh format use karo:
ACTION: function_name
ARGS: {{"key": "value"}}

Valid functions:
- open_app(app_name="...")
- open_website(site_name="...")
- adjust_volume(direction="up|down|mute|unmute")
- adjust_brightness(direction="up|down")
- play_youtube_song(song="...")
- search_google(query="...")
- run_autonomous_web_task(goal="...")
- execute_python_script(code="...")
- execute_powershell_command(command="...")
- search_computer_files(query="...")
- get_system_vitals()
- recall_memory(query="...")
- click_native_element(element_name="...")
- type_native_element(value="...", element_name="...")
- list_clickable_elements()
- arrange_window(action="maximize|minimize|restore|snap_left|snap_right")
- get_workflow_timeline()
- get_clipboard_analysis()
- explain_current_work()

Agar normal baat-cheet hai, toh EXACTLY yeh format use karo:
TEXT: [emotion] jawab

Emotion options: happy, excited, sad, concerned, calm, serious"""

                self.history.append({"role": "user", "content": user_text})
                trimmed = self.history[-(config.AI_HISTORY_TURNS * 2):]
                # Last entry ko classification prompt se replace karo
                api_messages = trimmed[:-1] + [{"role": "user", "content": prompt}]

                response = self._anthropic_client.messages.create(
                    model=config.AI_MODEL,
                    max_tokens=config.AI_MAX_TOKENS,
                    system=SYSTEM_PROMPT + "\n\n" + _CLASSIFIER_PROMPT,
                    messages=api_messages,
                )
                raw = "".join(
                    block.text for block in response.content if block.type == "text"
                ).strip()

                # Parse ACTION block
                action_match = re.search(r"ACTION:\s*(\w+)\s*\nARGS:\s*(\{.*?\})", raw, re.DOTALL)
                if action_match:
                    func_name = action_match.group(1).strip()
                    import json
                    args = json.loads(action_match.group(2).strip())
                    self.history.append({"role": "assistant", "content": raw})
                    return "action", func_name, args

                # Parse TEXT block
                text_match = re.search(r"TEXT:\s*(.*)", raw, re.DOTALL)
                if text_match:
                    text = text_match.group(1).strip()
                    text, emotion = self._extract_emotion(text)
                    self.history.append({"role": "assistant", "content": raw})
                    return "text", text, emotion

                # Fallback: treat whole response as text
                text, emotion = self._extract_emotion(raw)
                self.history.append({"role": "assistant", "content": raw})
                return "text", text, emotion

            except Exception as e:
                print(f"[understand_command anthropic error: {e}]")
                if self.history and self.history[-1]["role"] == "user":
                    self.history.pop()
                return None

        return None
    
        # --------------------------------------------------------------- web vision control
    def get_web_action(self, user_text: str, image):
        """Screenshot dekh ke batata hai ki kya action karna hai aur kahan."""
        if not self.available() or image is None or self.provider != "gemini":
            return None
        
        WEB_ACTION_PROMPT = """Tumhe user ke screen ka screenshot diya gaya hai.
User ne kuch command diya hai jo screen pe kisi UI element ke saath interact karna hai.

Tumhe EXACTLY yeh format mein jawab dena hai (koi extra text nahi):

ACTION: click | type | scroll_up | scroll_down | read | none
TARGET: kya element hai (1-2 words Hindi/English mein)
COORDINATES: x%, y% (screen width/height ka percentage, 0% se 100%. Center = 50%, 50%)
VALUE: type ke liye text (agar type nahi hai toh blank chhodo)

Examples:
- "like this reel" â†’ ACTION: click, TARGET: heart button, COORDINATES: 85%, 55%
- "stop song" â†’ ACTION: click, TARGET: pause button, COORDINATES: 50%, 85%
- "contact number do" â†’ ACTION: read, TARGET: phone number, VALUE: (blank)
- "scroll down" â†’ ACTION: scroll_down, TARGET: page, COORDINATES: 50%, 50%
- "email batao" â†’ ACTION: read, TARGET: email address, VALUE: (blank)

Agar screen pe command possible nahi:
ACTION: none
REASON: kyun nahi ho sakta (Hindi mein)"""
        
        try:
            response = self._gemini_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[image, f"User command: {user_text}"],
                config=genai_types.GenerateContentConfig(
                    system_instruction=WEB_ACTION_PROMPT,
                    max_output_tokens=200,
                ),
            )
            raw = (response.text or "").strip()
            return self._parse_web_action(raw)
        except Exception as e:
            print(f"[get_web_action error: {e}]")
            return None

    @staticmethod
    def _parse_web_action(raw: str):
        """AI ke text response ko structured dict mein convert karo."""
        result = {"action": "none", "target": "", "x_pct": "50", "y_pct": "50", "value": "", "reason": ""}
        
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("ACTION:"):
                result["action"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("TARGET:"):
                result["target"] = line.split(":", 1)[1].strip()
            elif line.startswith("COORDINATES:"):
                coord_str = line.split(":", 1)[1].strip()
                parts = [p.strip() for p in coord_str.replace("%", "").split(",") if p.strip()]
                if len(parts) >= 2:
                    result["x_pct"] = parts[0]
                    result["y_pct"] = parts[1]
            elif line.startswith("VALUE:"):
                result["value"] = line.split(":", 1)[1].strip()
            elif line.startswith("REASON:"):
                result["reason"] = line.split(":", 1)[1].strip()
        
        return result

    def get_autonomous_step_action(self, goal: str, history: list, image):
        """
        Multi-step autonomous agent step planner.
        Screen image + overall goal + previous steps -> Next exact UI action with coordinates.
        """
        if not self.available() or image is None:
            return None

        history_str = "\n".join(f"- {h}" for h in history) if history else "(Abhi koi action nahi liya, pehla step hai)"
        
        AUTONOMOUS_STEP_PROMPT = f"""Tum ek Autonomous Computer/Browser Agent ho jo user ke liye Windows screen/browser pe multi-step task complete karta hai.
USER KA OVERALL GOAL: "{goal}"

PAST STEPS TAKEN SO FAR:
{history_str}

SCREEN OBSERVATION RULES:
1. Screen pe dikh rahe buttons, links, search bars, inputs, tabs, text, dates ko dhyan se dekho.
2. Agla logical step plan karo taaki user ka goal pura ho.
3. Coordinates screen width aur height ke percentage mein do: x% (0% to 100% left to right), y% (0% to 100% top to bottom). Center = 50%, 50%.
4. Agar goal kisi question ka answer nikalna hai (jaise "last date kya hai", "contact number kya hai", "website pe kya likha hai") aur wo information screen pe mil gayi hai:
   ACTION: extract_info ya finish
   RESULT_TEXT: [exact answer Hindi/English mein]
5. Agar goal complete ho chuka hai (jaise form submit ho gaya, desired page khul gaya, game start ho gaya, etc.):
   ACTION: finish
   RESULT_TEXT: [summary of what was achieved]
6. Agar page load hone ka wait karna hai: ACTION: wait
7. Agar target element neeche hai jo screen pe nahi dikh raha: ACTION: scroll_down
8. Agar target element upar hai: ACTION: scroll_up
9. Agar kisi text box mein type karna hai: ACTION: type (COORDINATES: input box ke coordinates, VALUE: string, PRESS_ENTER: yes/no)
10. Agar enter, tab, esc, ya koi key dabani hai: ACTION: key (VALUE: enter|tab|esc|backspace|space)

FORMAT REQUIRED (Exact format - no markdown around keys):
THINKING: [1-2 sentences on what you see on screen and what to do next]
ACTION: click | double_click | right_click | type | key | scroll_down | scroll_up | wait | extract_info | finish | fail
TARGET: [UI element name, e.g. "Contacts link", "Search box", "Submit button", "Date section"]
COORDINATES: [x%, y%, e.g. 45%, 32%]
VALUE: [text to type or key name, blank if not applicable]
PRESS_ENTER: yes | no
SPOKEN_UPDATE: [1 short Hindi sentence describing what you are doing, e.g. "Contacts page pe click kar rahi hoon", "Search box mein type kar rahi hoon"]
RESULT_TEXT: [Answer/findings or completion message if action is extract_info or finish]
REASON: [Why this step is needed]"""

        try:
            if self.provider == "gemini":
                import time
                models_to_try = [getattr(config, "GEMINI_MODEL", "gemini-flash-latest"), "gemini-flash-latest", "gemma-4-26b-a4b-it", "gemma-4-31b-it"]
                seen_m = set()
                models_to_try = [m for m in models_to_try if m and not (m in seen_m or seen_m.add(m))]
                response = None

                for m in models_to_try:
                    for retry_i in range(2):
                        try:
                            response = self._gemini_client.models.generate_content(
                                model=m,
                                contents=[image, f"Determine next step for goal: {goal}"],
                                config=genai_types.GenerateContentConfig(
                                    system_instruction=AUTONOMOUS_STEP_PROMPT,
                                    max_output_tokens=450,
                                ),
                            )
                            if response and response.text:
                                break
                        except Exception as e:
                            if "503" in str(e) and retry_i == 0:
                                time.sleep(1.2)
                                continue
                    if response and response.text:
                        break

                if not response or not response.text:
                    return None

                raw = (response.text or "").strip()
                return self._parse_autonomous_step(raw)
            elif self.provider == "anthropic" and anthropic:
                import io, base64
                buffered = io.BytesIO()
                image.save(buffered, format="JPEG", quality=85)
                img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                response = self._anthropic_client.messages.create(
                    model=config.AI_MODEL,
                    max_tokens=350,
                    system=AUTONOMOUS_STEP_PROMPT,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
                            {"type": "text", "text": f"Determine next step for goal: {goal}"}
                        ]
                    }]
                )
                raw = "".join(b.text for b in response.content if b.type == "text").strip()
                return self._parse_autonomous_step(raw)
        except Exception as e:
            print(f"[get_autonomous_step_action error: {e}]")
            return None

    @staticmethod
    def _parse_autonomous_step(raw: str):
        result = {
            "thinking": "",
            "action": "none",
            "target": "",
            "x_pct": "50",
            "y_pct": "50",
            "value": "",
            "press_enter": False,
            "spoken_update": "",
            "result_text": "",
            "reason": ""
        }
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("THINKING:"):
                result["thinking"] = line.split(":", 1)[1].strip()
            elif line.startswith("ACTION:"):
                result["action"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("TARGET:"):
                result["target"] = line.split(":", 1)[1].strip()
            elif line.startswith("COORDINATES:"):
                coord_str = line.split(":", 1)[1].strip()
                parts = [p.strip() for p in coord_str.replace("%", "").split(",") if p.strip()]
                if len(parts) >= 2:
                    result["x_pct"] = parts[0]
                    result["y_pct"] = parts[1]
            elif line.startswith("VALUE:"):
                result["value"] = line.split(":", 1)[1].strip()
            elif line.startswith("PRESS_ENTER:"):
                val = line.split(":", 1)[1].strip().lower()
                result["press_enter"] = val in ("yes", "true", "1", "haan")
            elif line.startswith("SPOKEN_UPDATE:"):
                result["spoken_update"] = line.split(":", 1)[1].strip()
            elif line.startswith("RESULT_TEXT:"):
                result["result_text"] = line.split(":", 1)[1].strip()
            elif line.startswith("REASON:"):
                result["reason"] = line.split(":", 1)[1].strip()
        return result

    def extract_info_from_screen(self, query: str, image):
        """Screen/webpage se specific jaankari (date, contact, numbers, details) extract karta hai."""
        if not self.available() or image is None:
            return "Screen check nahi kar payi.", "concerned"

        EXTRACT_PROMPT = f"""Tumhe computer screen ka screenshot diya gaya hai.
User ka specific sawaal hai: "{query}"

Instructions:
1. Screen par likhe text, dates, numbers, notices, forms, tables ko dhyan se scan karo.
2. Seedha aur accurate jawab Hindi/Hinglish me do (2-3 sentences max).
3. Agar exact information mil gayi hai, to exact date/number/details batao.
4. Agar screen par wo information nahi dikh rahi hai, to saaf batao ki screen par ye information nahi mil rahi, scroll karke dekhna padega ya kisi specific page par jana padega.
5. Shuruat me emotion tag do: [happy]/[calm]/[concerned]/[excited]."""

        try:
            if self.provider == "gemini":
                response = self._gemini_client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=[image, f"Extract info for query: {query}"],
                    config=genai_types.GenerateContentConfig(
                        system_instruction=EXTRACT_PROMPT,
                        max_output_tokens=300,
                    ),
                )
                raw = (response.text or "").strip()
                return self._extract_emotion(raw)
            elif self.provider == "anthropic" and anthropic:
                import io, base64
                buffered = io.BytesIO()
                image.save(buffered, format="JPEG", quality=85)
                img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                response = self._anthropic_client.messages.create(
                    model=config.AI_MODEL,
                    max_tokens=300,
                    system=EXTRACT_PROMPT,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
                            {"type": "text", "text": f"Extract info for query: {query}"}
                        ]
                    }]
                )
                raw = "".join(b.text for b in response.content if b.type == "text").strip()
                return self._extract_emotion(raw)
        except Exception as e:
            print(f"[extract_info_from_screen error: {e}]")
            return "Screen se jaankari nikalne me dikkat aa gayi.", "concerned"

    def ask_stream(self, user_text: str, extra_context: str = None):
        """
        Generator - jaise-jaise AI jawab banata hai, sentence-by-sentence
        yield karta hai. extra_context (memory) sirf isi call ke system
        prompt me jaata hai - history me save NAHI hota, taaki bloat na ho.
        """
        if not self.available():
            yield "AI conversation abhi setup nahi hai. config.py me apni API key daaliye.", "calm"
            return

        if self.provider != "gemini":
            self.history.append({"role": "user", "content": user_text})
            reply, emotion = self.ask(user_text, skip_history_append=True)
            yield reply, emotion
            return

        self.history.append({"role": "user", "parts": [{"text": user_text}]})
        trimmed = self.history[-(config.AI_HISTORY_TURNS * 2):]

        prompt = SYSTEM_PROMPT
        if extra_context:
            prompt = SYSTEM_PROMPT + f"\n\nPurani baaton ka context (sirf yaad rakhne ke liye, isse nakal mat karna): {extra_context}"

        try:
            gen_config = genai_types.GenerateContentConfig(
                system_instruction=prompt,
                max_output_tokens=config.AI_MAX_TOKENS,
                thinking_config=genai_types.ThinkingConfig(thinking_level="low"),
            )
        except (TypeError, AttributeError):
            gen_config = genai_types.GenerateContentConfig(
                system_instruction=prompt,
                max_output_tokens=config.AI_MAX_TOKENS,
            )

        full_text = ""
        emotion = "calm"
        emotion_extracted = False
        buffer = ""

        try:
            stream = self._gemini_client.models.generate_content_stream(
                model=config.GEMINI_MODEL, contents=trimmed, config=gen_config,
            )
            for chunk in stream:
                delta = chunk.text or ""
                if not delta:
                    continue
                full_text += delta
                buffer += delta

                if not emotion_extracted and ("]" in buffer or len(buffer) > 20):
                    match = _EMOTION_TAG_RE.match(buffer)
                    if match and match.group(1).lower() in VALID_EMOTIONS:
                        emotion = match.group(1).lower()
                        buffer = buffer[match.end():]
                    emotion_extracted = True

                while True:
                    m = re.search(r"[.!?à¥¤]\s+", buffer)
                    if not m:
                        break
                    end = m.end()
                    sentence = buffer[:end].strip()
                    buffer = buffer[end:]
                    if sentence:
                        yield sentence, emotion

            if buffer.strip():
                yield buffer.strip(), emotion

        except Exception as e:
            print(f"[AI stream error: {e}]")
            full_text = full_text or "(error - kuch jawab nahi mila)"
            yield "Sorry, abhi AI se connect nahi ho paa rahi.", "concerned"

        finally:
            self.history.append({
                "role": "model",
                "parts": [{"text": full_text or "(interrupted)"}],
            })

    def ask(self, user_text: str, skip_history_append: bool = False):
        """Return (reply_text, emotion) - emotion "calm" agar detect na ho."""
        if not self.available():
            return "AI conversation abhi setup nahi hai. config.py me apni API key daaliye.", "calm"

        clean_q = user_text.strip().lower()
        import time
        # Check cache (15-minute TTL for frequent short questions)
        if hasattr(self, "_response_cache") and clean_q in self._response_cache:
            ts, cached_reply, cached_emo = self._response_cache[clean_q]
            if time.time() - ts < 900:  # 15 minutes
                return cached_reply, cached_emo

        try:
            if self.provider == "gemini":
                raw = self._ask_gemini(user_text, skip_history_append=skip_history_append)
            else:
                raw = self._ask_anthropic(user_text, skip_history_append=skip_history_append)
        except Exception as e:
            print(f"[AI error: {e}]")
            return "Sorry, abhi AI se connect nahi ho paa rahi. Internet ya API key check kijiye.", "concerned"

        reply, emotion = self._extract_emotion(raw)
        if hasattr(self, "_response_cache") and len(clean_q) < 80:
            self._response_cache[clean_q] = (time.time(), reply, emotion)
        return reply, emotion

    @staticmethod
    def _extract_emotion(raw: str):
        match = _EMOTION_TAG_RE.match(raw)
        if match and match.group(1).lower() in VALID_EMOTIONS:
            emotion = match.group(1).lower()
            text = raw[match.end():].strip()
            return text, emotion
        return raw, "calm"

    # --------------------------------------------------------------- vision
    def write_code_from_image(self, user_text: str, image):
        """Screen pe dikh rahi coding problem ka code likhta hai."""
        if not self.available() or image is None:
            return None
        if self.provider != "gemini":
            return None
        try:
            response = self._gemini_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[image, f"User instruction: {user_text}"],
                config=genai_types.GenerateContentConfig(
                    system_instruction=CODE_WRITING_SYSTEM_PROMPT,
                    max_output_tokens=2048,
                ),
            )
            return (response.text or "").strip()
        except Exception as e:
            print(f"[write_code_from_image error: {e}]")
            return None

    def ask_about_image(self, user_text: str, image):
        """Screen/cursor ke baare me sawaal - image (PIL Image) ke saath."""
        if not self.available() or image is None:
            return "Screen dekhne me abhi dikkat aa rahi hai.", "concerned"

        if self.provider != "gemini":
            return "Screen dekhna abhi sirf Gemini ke saath kaam karta hai - config.py me AI_PROVIDER 'gemini' rakhiye.", "calm"

        try:
            response = self._gemini_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[image, f"User ka sawaal: {user_text}"],
                config=genai_types.GenerateContentConfig(
                    system_instruction=VISION_SYSTEM_PROMPT,
                    max_output_tokens=config.AI_MAX_TOKENS,
                ),
            )
            raw = (response.text or "").strip()
            return self._extract_emotion(raw)
        except Exception as e:
            print(f"[vision AI error: {e}]")
            return "Screen samajhne me dikkat aa gayi.", "concerned"

    # ------------------------------------------------------------- gemini
    def _ask_gemini(self, user_text: str, skip_history_append: bool = False) -> str:
        if not skip_history_append:
            self.history.append({"role": "user", "parts": [{"text": user_text}]})
        trimmed = self.history[-(config.AI_HISTORY_TURNS * 2):]

        # FIX: API ko hamesha user turn pe end karna padta hai.
        # Agar history append skip ho raha hai, tab bhi user_text API mein bhejo.
        contents = list(trimmed)
        if skip_history_append:
            contents.append({"role": "user", "parts": [{"text": user_text}]})
        # Safety net: agar kisi bhi wajah se last turn model hai
        if contents and contents[-1].get("role") == "model":
            contents.append({"role": "user", "parts": [{"text": "continue"}]})

        try:
            gen_config = genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=config.AI_MAX_TOKENS,
                thinking_config=genai_types.ThinkingConfig(thinking_level="low"),
            )
        except (TypeError, AttributeError):
            gen_config = genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=config.AI_MAX_TOKENS,
            )

        response = self._gemini_client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=gen_config,
        )
        reply = (response.text or "").strip()
        self.history.append({"role": "model", "parts": [{"text": reply}]})
        return reply or "Kuch samajh nahi paayi, dobara boliye."

    # ---------------------------------------------------------- anthropic
    def _ask_anthropic(self, user_text: str, skip_history_append: bool = False) -> str:
        if not skip_history_append:
            self.history.append({"role": "user", "content": user_text})
        trimmed = self.history[-(config.AI_HISTORY_TURNS * 2):]

        # FIX: Anthropic bhi user turn pe end hona chahta hai
        api_messages = list(trimmed)
        if skip_history_append:
            api_messages.append({"role": "user", "content": user_text})
        if not api_messages or api_messages[-1].get("role") != "user":
            api_messages.append({"role": "user", "content": "continue"})

        response = self._anthropic_client.messages.create(
            model=config.AI_MODEL,
            max_tokens=config.AI_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=api_messages,
        )
        reply = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        self.history.append({"role": "assistant", "content": reply})
        return reply or "Kuch samajh nahi paayi, dobara boliye."
    
        # --------------------------------------------------------------- smart code writing
    def is_problem_complete(self, image):
        """Screenshot dekh ke batata hai ki problem complete dikhta hai ya nahi."""
        if not self.available() or image is None or self.provider != "gemini":
            return "unknown", "unknown"
        try:
            response = self._gemini_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[image, "Analyze this coding problem screenshot."],
                config=genai_types.GenerateContentConfig(
                    system_instruction=PROBLEM_COMPLETENESS_PROMPT,
                    max_output_tokens=200,
                ),
            )
            text = (response.text or "").strip()
            status = "unknown"
            language = "unknown"
            for line in text.split("\n"):
                if line.startswith("STATUS:"):
                    status = line.split(":", 1)[1].strip().lower()
                if line.startswith("LANGUAGE:"):
                    language = line.split(":", 1)[1].strip().lower()
            return status, language
        except Exception as e:
            print(f"[is_problem_complete error: {e}]")
            return "unknown", "unknown"

    def extract_existing_code(self, image):
        """Cursor ke aas-paas ka editor screenshot dekh ke code nikaalta hai."""
        if not self.available() or image is None or self.provider != "gemini":
            return None
        try:
            response = self._gemini_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[image, "Extract any existing code from this editor. If it looks like garbage/incomplete text or just a few random characters, say NO_CODE."],
                config=genai_types.GenerateContentConfig(
                    system_instruction=EDITOR_SCAN_PROMPT,
                    max_output_tokens=2048,
                ),
            )
            text = (response.text or "").strip()
            if "HAS_CODE: no" in text or "NO_CODE" in text:
                return None
            if "CODE:" in text:
                code = text.split("CODE:", 1)[1].strip()
                if code == "NO_CODE":
                    return None
                # Agar code bahut chhota ya garbled hai, ignore karo
                if len(code) < 20:
                    return None
                return code
            return None
        except Exception as e:
            print(f"[extract_existing_code error: {e}]")
            return None

    def generate_smart_code(self, problem_text: str, existing_code: str, language: str):
        if not self.available() or self.provider != "gemini":
            return None
        try:
            # Safe replacement instead of .format() to avoid brace conflicts
            prompt = NO_COMMENT_CODE_PROMPT.replace("{problem_text}", problem_text or "")
            prompt = prompt.replace("{existing_code}", existing_code or "NO_CODE")
            prompt = prompt.replace("{language}", language or "cpp")
            
            response = self._gemini_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=4096,
                ),
            )
            return (response.text or "").strip()
        except Exception as e:
            print(f"[generate_smart_code error: {e}]")
            return None
        
    def extract_problem_from_image(self, image):
        """Screenshot se problem text nikaalta hai."""
        if not self.available() or image is None or self.provider != "gemini":
            return ""
        try:
            response = self._gemini_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[image, "Extract the FULL problem statement and any given code stubs from this screenshot. If it's a LeetCode/CodeChef problem, write the complete problem text as shown."],
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=2048,
                ),
            )
            return (response.text or "").strip()
        except Exception as e:
            print(f"[extract_problem_from_image error: {e}]")
            return ""

    def is_problem_complete_from_image(self, image):
        """Batata hai ki screenshot mein problem complete dikhta hai ya nahi."""
        if not self.available() or image is None or self.provider != "gemini":
            return "unknown", "unknown"
        try:
            response = self._gemini_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=[image, "Analyze this coding problem screenshot."],
                config=genai_types.GenerateContentConfig(
                    system_instruction=PROBLEM_COMPLETENESS_PROMPT,
                    max_output_tokens=200,
                ),
            )
            text = (response.text or "").strip()
            status = "unknown"
            language = "unknown"
            for line in text.split("\n"):
                if line.startswith("STATUS:"):
                    status = line.split(":", 1)[1].strip().lower()
                if line.startswith("LANGUAGE:"):
                    language = line.split(":", 1)[1].strip().lower()
            return status, language
        except Exception as e:
            print(f"[is_problem_complete error: {e}]")
            return "unknown", "unknown"
