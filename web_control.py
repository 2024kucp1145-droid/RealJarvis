# -*- coding: utf-8 -*-
"""
web_control.py
==============
Autonomous Browser & Computer Use Engine for Real Jarvis.
Vision AI + PyAutoGUI + Multi-step Agentic Loop se koi bhi website,
web application, game, ya form control karta hai bina haath lagaye.
"""

import time
import re
import threading

try:
    import pyautogui
    pyautogui.PAUSE = 0.02
    pyautogui.FAILSAFE = True  # Cursor corner me le jane se emergency stop
except ImportError:
    pyautogui = None
    print("[web_control] pyautogui not installed — web automation disabled. Install: pip install pyautogui")

try:
    import vision
except ImportError:
    vision = None

try:
    import pyperclip
except ImportError:
    pyperclip = None


def _pct_to_pixel(x_pct, y_pct):
    """Percentage (0-100) ko actual screen pixels mein convert karo."""
    screen_w, screen_h = pyautogui.size()
    
    # Extract numbers from strings like "75%", "75", or float
    if isinstance(x_pct, (int, float)):
        x_num = float(x_pct)
    else:
        m = re.search(r"[-+]?\d*\.\d+|\d+", str(x_pct))
        x_num = float(m.group()) if m else 50.0

    if isinstance(y_pct, (int, float)):
        y_num = float(y_pct)
    else:
        m = re.search(r"[-+]?\d*\.\d+|\d+", str(y_pct))
        y_num = float(m.group()) if m else 50.0

    x = int(screen_w * (x_num / 100.0))
    y = int(screen_h * (y_num / 100.0))
    return max(0, min(x, screen_w - 1)), max(0, min(y, screen_h - 1))


def _type_safely(text: str):
    """Windows pe Unicode aur special characters ko safely type ya paste karo."""
    if not text:
        return
    try:
        if pyperclip:
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.1)
        else:
            pyautogui.write(text, interval=0.02)
    except Exception as e:
        print(f"[_type_safely error: {e}]")
        pyautogui.write(text, interval=0.02)


def execute_web_action(voice, ai, description: str):
    """
    Single-shot visual action (for quick commands like 'like button dabao', 'pause karo').
    """
    if not vision.available():
        voice.speak("Screen control ke liye pyautogui install nahi hai.")
        return False

    img = vision.capture_full_screen()
    if img is None:
        voice.speak("Screenshot nahi le paayi.")
        return False

    voice.speak("Screen dekh rahi hoon...", emotion="calm")

    # AI se action plan lo
    action_data = ai.get_web_action(description, img)
    if action_data is None:
        voice.speak("Screen samajhne mein dikkat aa gayi.")
        return False

    action = action_data.get("action", "none")
    target = action_data.get("target", "")
    x_pct = action_data.get("x_pct", "50")
    y_pct = action_data.get("y_pct", "50")
    value = action_data.get("value", "")
    reason = action_data.get("reason", "")

    print(f"[web_control] action={action}, target={target}, coords={x_pct}%, {y_pct}%")

    if action == "none":
        voice.speak(reason or "Ye action screen pe possible nahi dikh raha.")
        return False

    # ---- CLICK ----
    if action == "click":
        x, y = _pct_to_pixel(x_pct, y_pct)
        try:
            pyautogui.click(x, y)
            voice.speak(f"{target} pe click kar diya.", emotion="happy")
            return True
        except Exception as e:
            print(f"[web_control click error: {e}]")
            voice.speak("Click karne mein error aa gaya.")
            return False

    # ---- TYPE ----
    if action == "type":
        if value:
            x, y = _pct_to_pixel(x_pct, y_pct)
            try:
                pyautogui.click(x, y)
                time.sleep(0.15)
                _type_safely(value)
                voice.speak(f"{target} pe type kar diya.")
                return True
            except Exception as e:
                print(f"[web_control type error: {e}]")
                voice.speak("Type karne mein error aa gaya.")
                return False
        else:
            voice.speak("Kya type karu, wo nahi samajh aaya.")
            return False

    # ---- SCROLL ----
    if action == "scroll_down":
        try:
            pyautogui.scroll(-800)
            voice.speak("Neeche scroll kar diya.")
            return True
        except Exception as e:
            print(f"[web_control scroll error: {e}]")
            return False

    if action == "scroll_up":
        try:
            pyautogui.scroll(800)
            voice.speak("Upar scroll kar diya.")
            return True
        except Exception as e:
            print(f"[web_control scroll error: {e}]")
            return False

    # ---- READ (contact number, email, etc.) ----
    if action == "read":
        voice.speak(f"{target} dhoondh rahi hoon...")
        reply, emotion = ai.extract_info_from_screen(description, img)
        voice.speak(reply, emotion=emotion)
        return True

    voice.speak("Ye action abhi support nahi hai.")
    return False


def extract_screen_info(voice, ai, query: str, max_scrolls: int = 2):
    """
    Screen aur webpage se specific jaankari dhoondh kar batata hai (jaise last date, contact, etc).
    Agar current view pe na mile toh scroll down karke check karta hai.
    """
    if not vision.available():
        voice.speak("Screen check karne ke liye libraries install nahi hain.")
        return

    voice.speak("Page scan kar rahi hoon...", emotion="calm")
    
    for attempt in range(max_scrolls + 1):
        img = vision.capture_full_screen()
        if img is None:
            break
        
        reply, emotion = ai.extract_info_from_screen(query, img)
        if reply and not any(w in reply.lower() for w in ("nahi mila", "nahi mil rahi", "scroll", "niche dekhna")):
            voice.speak(reply, emotion=emotion)
            return
        
        if attempt < max_scrolls:
            voice.speak("Neeche scroll karke dhoondh rahi hoon...")
            pyautogui.scroll(-700)
            time.sleep(1.0)
        else:
            voice.speak(reply, emotion=emotion)


class AutonomousWebAgent:
    """
    Multi-Step Autonomous Agent for Browser & Screen Automation.
    Iteratively plans, acts, verifies, and communicates progress in voice.
    """
    def __init__(self, voice, ai):
        self.voice = voice
        self.ai = ai
        self.running = False
        self.stop_requested = False

    def stop(self):
        self.stop_requested = True
        self.running = False

    def run_goal(self, goal: str, max_steps: int = 12):
        if not vision.available():
            self.voice.speak("Screen dekhne ke liye pyautogui install nahi hai.")
            return False
        if not self.ai.available():
            self.voice.speak("AI connection active nahi hai.")
            return False

        self.running = True
        self.stop_requested = False
        step_history = []

        self.voice.speak(f"Ji, main ispe kaam shuru kar rahi hoon: {goal}", emotion="excited")
        time.sleep(0.5)

        for step in range(1, max_steps + 1):
            if self.stop_requested:
                self.voice.speak("Theek hai, maine browser automation rok diya.")
                break

            print(f"\n[AutonomousAgent] Step {step}/{max_steps} executing...")
            time.sleep(0.6)  # Give browser time to settle

            # 1. Capture screen
            img = vision.capture_full_screen()
            if img is None:
                self.voice.speak("Screenshot nahi le paayi, dobara try kar rahi hoon.")
                time.sleep(1.0)
                continue

            # 2. Plan next step with AI
            plan = self.ai.get_autonomous_step_action(goal, step_history, img)
            if not plan:
                self.voice.speak("Agla step plan karne mein dikkat aayi.")
                break

            action = plan.get("action", "none")
            target = plan.get("target", "")
            x_pct = plan.get("x_pct", "50")
            y_pct = plan.get("y_pct", "50")
            value = plan.get("value", "")
            press_enter = plan.get("press_enter", False)
            spoken_update = plan.get("spoken_update", "")
            result_text = plan.get("result_text", "")

            print(f"[AutonomousAgent] Plan: action={action}, target={target}, coords={x_pct}%,{y_pct}%, value={value}")

            # 3. Spoken update to user
            if spoken_update and action not in ("finish", "extract_info"):
                self.voice.speak(spoken_update, emotion="calm")

            # 4. Check for Finish or Information extraction
            if action == "finish":
                final_msg = result_text or f"Aapka kaam pura ho gaya hai: {target}"
                self.voice.speak(final_msg, emotion="happy")
                self.running = False
                return True

            if action == "extract_info":
                msg = result_text or f"Screen pe mila: {target}"
                self.voice.speak(msg, emotion="happy")
                step_history.append(f"Extracted info: {msg}")
                self.running = False
                return True

            if action == "fail":
                fail_msg = result_text or plan.get("reason", "") or "Ye task screen pe pura nahi ho pa raha."
                self.voice.speak(fail_msg, emotion="concerned")
                self.running = False
                return False

            # 5. Execute Physical UI Actions
            if action == "click":
                x, y = _pct_to_pixel(x_pct, y_pct)
                pyautogui.click(x, y)
                step_history.append(f"Clicked on {target} at ({x_pct}%, {y_pct}%)")

            elif action == "double_click":
                x, y = _pct_to_pixel(x_pct, y_pct)
                pyautogui.doubleClick(x, y)
                step_history.append(f"Double clicked on {target}")

            elif action == "right_click":
                x, y = _pct_to_pixel(x_pct, y_pct)
                pyautogui.rightClick(x, y)
                step_history.append(f"Right clicked on {target}")

            elif action == "type":
                x, y = _pct_to_pixel(x_pct, y_pct)
                pyautogui.click(x, y)
                time.sleep(0.2)
                _type_safely(value)
                if press_enter:
                    time.sleep(0.1)
                    pyautogui.press('enter')
                step_history.append(f"Typed '{value}' into {target} (enter={press_enter})")

            elif action == "key":
                key_name = value.lower().strip() or "enter"
                if "+" in key_name:
                    pyautogui.hotkey(*key_name.split("+"))
                else:
                    pyautogui.press(key_name)
                step_history.append(f"Pressed key '{key_name}'")

            elif action == "scroll_down":
                pyautogui.scroll(-750)
                step_history.append("Scrolled down")

            elif action == "scroll_up":
                pyautogui.scroll(750)
                step_history.append("Scrolled up")

            elif action == "wait":
                time.sleep(2.0)
                step_history.append("Waited for page load")

            else:
                step_history.append(f"Action '{action}' performed")

        self.voice.speak("Task ke saare steps complete ho gaye hain.")
        self.running = False
        return True


# Global active agent instance
_active_agent = None


def run_autonomous_web_task(voice, ai, goal: str):
    """Global helper to run autonomous agent."""
    global _active_agent
    _active_agent = AutonomousWebAgent(voice, ai)
    return _active_agent.run_goal(goal)


def stop_autonomous_agent():
    """Emergency stop helper."""
    global _active_agent
    if _active_agent:
        _active_agent.stop()