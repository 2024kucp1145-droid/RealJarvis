# -*- coding: utf-8 -*-
"""
system_actions.py
=================
Keyboard aur app-launch actions: `run_program`, `send_shortcut`,
`_press_shortcut`.

Yahan ek safety cheez bhi hai: `run_program` user ke bole hue program name se
shell command banata hai, isliye shell metacharacters strip hote hain aur
`shell=False` rehta hai.
"""

from .text_patterns import KEY_ALIASES


class SystemActionsMixin:
    """App launch + keyboard automation."""

    # ----------------------------------------------------------- run / keyboard
    def run_program(self, program: str):
        """`command_data.py` ke `run` type commands — fixed app names."""
        import subprocess
        try:
            safe_program = (program.strip().replace('"', '').replace('&', '')
                            .replace('|', '').replace('>', '').replace('<', ''))
            if safe_program.startswith("ms-settings"):
                subprocess.run(["powershell", "-Command", f"Start-Process {safe_program}"])
            else:
                subprocess.Popen([safe_program], shell=False)
            self.speak("Khol diya.")
        except Exception as e:  # noqa: BLE001
            self.speak("Ye open nahi ho paaya.")
            print(f"[run_program error: {e}]")

    def send_shortcut(self, combo: str):
        """`command_data.py` ke `keyboard` type commands — fixed combos."""
        try:
            import pyautogui
            import time as _time
            _time.sleep(0.05)

            parts = combo.lower().split("+")
            if len(parts) == 1:
                pyautogui.press(parts[0])
            else:
                pyautogui.hotkey(*parts)
            self.speak("Kar diya.")
        except Exception as e:  # noqa: BLE001
            self.speak("Shortcut bhejne me dikkat aa gayi.")
            print(f"[send_shortcut error: {e}]")

    def _press_shortcut(self, phrase: str) -> bool:
        """
        "ctrl c" jaisa bola gaya phrase ko actual keyboard combo me badal
        kar dabata hai. Return False agar koi valid key na mile (jisse
        AI conversation try ho sake), True agar dabaya (successfully ya
        error ke saath dono).
        """
        words = phrase.lower().replace("+", " ").split()
        keys = []
        for w in words:
            if w in KEY_ALIASES:
                keys.append(KEY_ALIASES[w])
            elif len(w) == 1 and (w.isalnum()):
                keys.append(w)  # single letter/number jaisa "c", "4"
            elif w.isdigit():
                keys.append(w)
            else:
                # pehchana nahi gaya word - shayad ye shortcut hai hi nahi,
                # kisi aur cheez ka sawaal hai ("mujhe kal ka plan batao" jaisa)
                return False

        if not keys:
            return False

        combo = "+".join(keys)
        try:
            import pyautogui
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)
            self.speak(f"{combo} dabaya.")
        except Exception as e:  # noqa: BLE001
            self.speak("Ye shortcut nahi dabaa payi.")
            print(f"[shortcut error: {e}]")
        return True