# -*- coding: utf-8 -*-
"""
skills_manual_manager.py
========================
Maintains and opens the permanent User Manual for all skills learned by Jarvis.
Allows any user to clearly understand what the skill does and what exact voice
commands to use.
"""

import os
import sys
import time

MANUAL_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "JARVIS_SKILLS_USER_MANUAL.md")


class SkillsManualManager:
    def __init__(self, manual_path: str = MANUAL_FILE_PATH):
        self.manual_path = manual_path
        self._ensure_header()

    def _ensure_header(self):
        """Creates the manual file with an executive header if not present."""
        if not os.path.exists(self.manual_path):
            with open(self.manual_path, "w", encoding="utf-8") as f:
                f.write(
                    "# RealJarvis - Learned Skills & Voice Commands Manual\n\n"
                    "> **Yeh manual RealJarvis ke dwara seekhe gaye sabhi custom skills ki complete guide hai.**\n"
                    "> Har skill ka **Matlab (Kaam)** aur **Bolne ka Tarika (Voice Commands)** yahan detail mein darj hai.\n\n"
                    "---\n\n"
                )

    def record_learned_skill(self, skill_name: str, category: str, description: str, 
                             triggers: list, examples: list = None, technical_notes: str = ""):
        """
        Appends or updates a learned skill entry in the manual.
        """
        self._ensure_header()
        
        triggers_formatted = "\n".join([f"- `\"Jarvis, {t}\"`" for t in triggers])
        examples_formatted = ""
        if examples:
            examples_formatted = "\n**Live Examples:**\n" + "\n".join([f"- {ex}" for ex in examples]) + "\n"

        date_str = time.strftime("%Y-%m-%d %H:%M:%S")

        entry = f"""
## {skill_name}
- **Category / Domain:** `{category}`
- **Date Learned:** `{date_str}`

### Yeh Tool Kya Kaam Karta Hai (Matlab):
{description}

### Is Tool Ko Use Kaise Karein (Voice Commands):
Aap Jarvis se inme se koi bhi command bol sakte hain:
{triggers_formatted}
{examples_formatted}
{f"> *Technical Details:* {technical_notes}" if technical_notes else ""}

---
"""
        # Avoid duplicate entries for the same skill
        if os.path.exists(self.manual_path):
            with open(self.manual_path, "r", encoding="utf-8") as f:
                existing = f.read()
            if f"## {skill_name}" in existing:
                print(f"[skills_manual] Skill '{skill_name}' already documented in manual.")
                return

        with open(self.manual_path, "a", encoding="utf-8") as f:
            f.write(entry)
        print(f"[skills_manual] Recorded skill '{skill_name}' into {self.manual_path}")

    def open_manual(self) -> bool:
        """
        Opens the skills manual file on the user's desktop using native default editor.
        """
        self._ensure_header()
        try:
            if sys.platform == "win32":
                os.startfile(self.manual_path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", self.manual_path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", self.manual_path])
            return True
        except Exception as e:
            print(f"[skills_manual] Failed to open manual file: {e}")
            return False


manual_manager = SkillsManualManager()
