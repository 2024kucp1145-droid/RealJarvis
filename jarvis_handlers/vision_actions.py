# -*- coding: utf-8 -*-
"""
vision_actions.py
=================
Screen dekhne wale saare actions + file intake.

- handle_read_screen / handle_vision / handle_monitor_vision — screenshot leke
  AI se poochte hain
- handle_write_code — screen se problem padho, code generate karo, cursor pe
  type karo (LeetCode-style flow)
- on_file_dropped / handle_file_question / clear_active_file — user file icon
  pe drag-drop kare to usi file ke context me Q&A

Screenshots hamesha `_capture_clean_screenshot()` se aati hain (lifecycle mixin)
taaki Jarvis ka apna floating icon frame me na aaye.
"""

import re
import time

from file_intake import FileIntake

from .text_patterns import FILE_RELEASE_PHRASES


class VisionActionsMixin:
    """Vision + file-intake handlers."""

    # ----------------------------------------------------------- screen read
    def handle_read_screen(self, user_text: str):
        """Poori screen ka content padh kar sunata hai - jaise LeetCode
        problem, article, ya kisi bhi page ka poora text."""
        import vision
        if not vision.available():
            self.speak("Screen dekhne wali library install nahi hai.")
            return
        if not self.ai.available():
            self.speak("AI setup nahi hai.")
            return

        self.gui.set_state("thinking")
        self.gui.show_message("Poora page padh rahi hoon...")
        image = self._capture_clean_screenshot(full=True)
        if image is None:
            self.speak("Screenshot lene me dikkat aa gayi.")
            return

        reply, emotion = self.ai.ask_about_image(user_text, image)
        self.speak(reply, interruptible=True, emotion=emotion)

    def handle_vision(self, user_text: str):
        """Screen/cursor ke baare me sawaal - ek snapshot + window info leke AI se poochta hai."""
        import vision
        import desktop_context

        if not vision.available():
            self.speak("Screen dekhne wali library install nahi hai - pyautogui chahiye.")
            return
        if not self.ai.available():
            self.speak("AI setup nahi hai, isliye screen samajh nahi paungi.")
            return

        self.gui.set_state("thinking")
        image = self._capture_clean_screenshot(full=False)
        if image is None:
            self.speak("Screenshot lene me dikkat aa gayi.")
            return

        context_info = desktop_context.build_context_summary()
        full_question = f"{user_text}\n\n(Extra context: {context_info})"

        reply, emotion = self.ai.ask_about_image(full_question, image)
        self.speak(reply, interruptible=True, emotion=emotion)

    def handle_monitor_vision(self, user_text: str):
        """Screen monitor se latest image leke AI se jawab mangta hai."""
        import desktop_context

        if not self.ai.available():
            self.speak("AI setup nahi hai, isliye screen samajh nahi paungi.")
            return True

        if self.screen_monitor is None:
            self.speak("Screen monitoring available nahi hai.")
            return True

        image = self.screen_monitor.get_latest()
        if image is None:
            self.speak("Screen capture abhi available nahi hai, dobara try kijiye.")
            return True

        self.gui.set_state("thinking")
        self.gui.show_message("Screen dekh kar jawab de rahi hoon...")

        context_info = desktop_context.build_context_summary()
        full_question = (
            f"{user_text}\n\n"
            f"(Extra context: {context_info})\n\n"
            f"NOTE: Ye user ke screen ka latest snapshot hai. Jo bhi screen pe dikh raha hai "
            f"uska analysis do aur user ki madad karo."
        )

        reply, emotion = self.ai.ask_about_image(full_question, image)
        self.speak(reply, interruptible=True, emotion=emotion)
        return True

    # ----------------------------------------------------------- code writer
    def handle_write_code(self, user_text: str):
        """
        Smart code writing:
        1. Full problem screen se padhta hai (scroll karke agar poora na dikhe)
        2. Cursor region mein existing code detect karta hai
        3. Agar code hai -> verify + fix with comments
        4. Agar nahi hai -> scratch se likhta hai
        5. Cursor pe type karta hai (cursor busy/rotating rahega)
        """
        import vision
        if not vision.available():
            self.speak("Screen dekhne wali library install nahi hai.")
            return
        if not self.ai.available():
            self.speak("AI setup nahi hai.")
            return

        self.gui.set_state("thinking")
        self.speak("Screen dekh rahi hoon...")

        # ---- STEP 1: Clean screenshot — Jarvis ki apni window bina ----
        first_img = self._capture_clean_screenshot(full=True)
        if first_img is None:
            self.speak("Screenshot lene me dikkat aa gayi.")
            return

        status, language = self.ai.is_problem_complete_from_image(first_img)
        print(f"[problem check] status={status}, language={language}")

        all_images = [first_img]

        # Agar partial hai ya unknown hai, tabhi scroll karo — warna mat karo
        if status in ("partial", "unknown"):
            self.speak("Problem neeche bhi hai, scroll kar ke dekh rahi hoon...")
            self.gui.show_message("Neeche scroll kar rahi hoon...")
            try:
                self.gui.root.withdraw()
                time.sleep(0.3)
            except Exception:  # noqa: BLE001
                pass
            scroll_images = vision.scroll_and_capture_full_page(max_scrolls=3)
            try:
                self.gui.root.deiconify()
            except Exception:  # noqa: BLE001
                pass
            # Pehla hata do (duplicate hai), baaki add karo
            for img in scroll_images[1:]:
                if img:
                    all_images.append(img)

        # ---- STEP 2: Har image se problem text nikaalo ----
        self.gui.show_message("Problem padh rahi hoon...")
        problem_parts = []

        for i, img in enumerate(all_images):
            self.gui.show_message(f"Page {i+1} analyze kar rahi hoon...")
            part_text = self.ai.extract_problem_from_image(img)
            if part_text and part_text not in "\n\n".join(problem_parts):
                problem_parts.append(part_text)
                print(f"[page {i}] extracted {len(part_text)} chars")

        full_problem = "\n\n".join(problem_parts)
        if not full_problem or len(full_problem) < 20:
            self.speak("Problem padhne me dikkat aa gayi, dobara try kijiye.")
            return

        print(f"[full problem length: {len(full_problem)} chars]")

        # ---- STEP 3: Cursor pe existing code detect karo ----
        self.gui.show_message("Editor check kar rahi hoon...")
        time.sleep(0.5)
        editor_img = vision.get_cursor_region(width=700, height=450)
        existing_code = None

        if editor_img:
            existing_code = self.ai.extract_existing_code(editor_img)
            if existing_code:
                self.gui.show_message("Existing code verify kar rahi hoon...")
                print(f"[existing code detected, length: {len(existing_code)}]")

                # === GARBAGE DETECTION ===
                # Agar existing code bahut chhota hai ya sab ek line mein hai ya
                # bahut zyada syntax errors dikh rahe hain, toh ignore karo
                lines = existing_code.split('\n')
                if len(existing_code) < 30 or len(lines) == 1 and len(existing_code) > 80:
                    # Either too short, or everything crammed in one line = garbage
                    print(f"[garbage code detected, ignoring. Lines: {len(lines)}, "
                          f"Length: {len(existing_code)}]")
                    existing_code = None

        # ---- STEP 4: Code generate karo ----
        self.gui.show_message("Code likh rahi hoon...")
        code = self.ai.generate_smart_code(full_problem, existing_code, language)

        if not code:
            self.speak("Code generate karne me dikkat aa gayi, dobara try kijiye.")
            return

        # === FORCE FORMATTING & CLEANING ===
        # Markdown fences hatao
        code = code.replace("```python", "").replace("```cpp", "").replace("```java", "")
        code = code.replace("```javascript", "").replace("```", "").strip()

        # Sab comments hatao
        code = re.sub(r'^\s*//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'^\s*#.*$', '', code, flags=re.MULTILINE)

        # GARBAGE DETECTION
        garbage_keywords = ['std::make_heap', 'uint16_t', 'wchar_t', 'register',
                            'intint', 'retureturn', 'endelse', 'ncase']
        lower_code = code.lower().replace(' ', '')
        if any(g.replace(' ', '') in lower_code for g in garbage_keywords):
            self.speak("Code generate karte waqt kuch galat ho gaya. Dobara try kijiye.")
            print("[GARBAGE DETECTED]")
            return

        # Force newlines around braces and semicolons
        code = re.sub(r';\s+', ';\n', code)
        code = re.sub(r'\{\s*', '{\n', code)
        code = re.sub(r'\}\s*', '}\n', code)

        # Clean lines
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Multiple statements in one line? Split by semicolon
            if ';' in line and line.count(';') > 1 and not line.startswith('#'):
                parts = [p.strip() + ';' for p in line.split(';') if p.strip()]
                cleaned_lines.extend(parts)
            else:
                cleaned_lines.append(line)

        # Normalize indentation (left align properly)
        indents = [len(l) - len(l.lstrip()) for l in cleaned_lines if l.lstrip()]
        if indents:
            min_indent = min(i for i in indents if i > 0) if any(i > 0 for i in indents) else 4
            final_lines = []
            for line in cleaned_lines:
                stripped = line.lstrip()
                current = len(line) - len(stripped)
                if current > 0 and min_indent > 0:
                    level = max(0, current // min_indent)
                    final_lines.append('    ' * level + stripped)
                else:
                    final_lines.append(stripped)
            cleaned_lines = final_lines

        code = '\n'.join(cleaned_lines)

        if len(cleaned_lines) <= 2 and len(code) > 50:
            self.speak("Code formatting theek nahi hui. Dobara try kijiye.")
            return

        print(f"[final code: {len(cleaned_lines)} lines]")

        # ---- STEP 5: Cursor pe click karke type karo ----
        try:
            import pyautogui
            import time as _time
            import threading

            x, y = pyautogui.position()
            pyautogui.click(x, y)
            _time.sleep(0.3)

            if existing_code:
                pyautogui.keyDown('ctrl')
                pyautogui.keyDown('a')
                pyautogui.keyUp('a')
                pyautogui.keyUp('ctrl')
                _time.sleep(0.2)

            # === CURSOR BUSY ===
            _stop_cursor = threading.Event()
            _normal_cursor = None

            def _rotate_cursor():
                try:
                    import win32gui
                    import win32con
                    busy = win32gui.LoadCursor(0, win32con.IDC_APPSTARTING)
                    normal = win32gui.LoadCursor(0, win32con.IDC_ARROW)
                    nonlocal _normal_cursor
                    _normal_cursor = normal
                    while not _stop_cursor.is_set():
                        win32gui.SetCursor(busy)
                        _stop_cursor.wait(0.15)
                except Exception:  # noqa: BLE001
                    pass

            cursor_thread = threading.Thread(target=_rotate_cursor, daemon=True)
            cursor_thread.start()

            try:
                # Line by line type karo taaki left alignment sahi rahe
                for line in code.split('\n'):
                    pyautogui.write(line, interval=0.01)
                    pyautogui.keyDown('return')
                    pyautogui.keyUp('return')
                    _time.sleep(0.03)
            finally:
                _stop_cursor.set()
                _time.sleep(0.2)
                try:
                    import win32gui
                    import win32con
                    if _normal_cursor:
                        win32gui.SetCursor(_normal_cursor)
                except Exception:  # noqa: BLE001
                    pass

            self.speak("Code likh diya.", interruptible=True)

        except Exception as e:  # noqa: BLE001
            self.speak("Code type karte waqt error aa gaya.")
            print(f"[handle_write_code type error: {e}]")

    # ------------------------------------------------------------- file intake
    def on_file_dropped(self, filepath: str):
        """User ne file drag karke Jarvis icon pe drop ki."""
        import os

        print(f"[main] File dropped: {filepath}")
        self.gui.set_state("file_intake")
        self.speak("File aa gayi, andar le rahi hoon...")

        # Purana video mode clear karo agar nayi file aayi hai
        if self.video_mode:
            self.video_mode = False
            self.video_path = None

        self.active_file = FileIntake(filepath)
        print(f"[main] Type check: image={self.active_file.is_image}, "
              f"video={self.active_file.is_video}, "
              f"folder={self.active_file.is_folder}, valid={self.active_file.is_valid()}")

        if not self.active_file.is_valid():
            self.speak(f"Sorry, {self.active_file.filename} read nahi kar payi.")
            self.active_file = None
            return

        if self.active_file.is_video:
            self.video_path = filepath
            self.video_mode = True
            self.active_file = None
            filename = os.path.basename(filepath)
            self.speak(f"{filename} video aa gayi. Kya karna hai? "
                       f"'notes banao', 'summary do', ya 'transcribe karo'?")
            return

        if self.active_file.is_folder:
            item_count = self.active_file.content.count('\n')
            self.speak(f"{self.active_file.filename} folder aa gaya. Isme approximately "
                       f"{item_count} items hain. Ab kuch bhi pooch sakte ho. "
                       f"'complete' bolke bahar nikaal do.")
            return

        if self.active_file.is_image:
            self.speak(f"{self.active_file.filename} image aa gayi. Ab kuch bhi pooch "
                       f"sakte ho. 'complete' bolke bahar nikaal do.")
        else:
            lines = self.active_file.content.count('\n') + 1
            chars = len(self.active_file.content)
            self.speak(f"{self.active_file.filename} andar aa gayi. {lines} lines, "
                       f"{chars} characters. Ab kuch bhi pooch sakte ho. "
                       f"'complete' bolke bahar nikaal do.")

    def handle_file_question(self, text: str) -> bool:
        """Active file ke context mein sawaal ka jawab."""
        if not self.active_file:
            return False

        self.gui.set_state("thinking")
        self.gui.show_message("File padh rahi hoon...")

        try:
            # Image file -> vision use karo
            if self.active_file.is_image:
                from PIL import Image
                image = Image.open(self.active_file.filepath)
                reply, emotion = self.ai.ask_about_image(text, image)
                self.speak(reply, interruptible=True, emotion=emotion)
                return True

            # Text file -> AI ko prompt bhejo
            prompt = self.active_file.build_prompt(text)
            reply, emotion = self.ai.ask(prompt, skip_history_append=True)
            self.speak(reply, interruptible=True, emotion=emotion)
            return True

        except Exception as e:  # noqa: BLE001
            self.speak("File padhne mein dikkat aa gayi.")
            print(f"[handle_file_question error: {e}]")
            return True

    def clear_active_file(self):
        """File intake mode band karo."""
        if self.active_file:
            name = self.active_file.filename
            self.active_file = None
            self.speak(f"{name} bahar nikaal di. Ab normal baat-cheet.")
        else:
            self.speak("Koi file andar nahi hai.")

    @staticmethod
    def file_release_requested(text: str) -> bool:
        """'complete' / 'ho gaya' jaise phrases — file intake band karne ke liye."""
        lowered = (text or "").lower()
        return any(phrase in lowered for phrase in FILE_RELEASE_PHRASES)