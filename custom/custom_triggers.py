# -*- coding: utf-8 -*-
"""
custom_triggers.py
===================
Jarvis khud yahan naye command triggers add karta hai jab tum use
"modify yourself" se koi naya feature banwate ho.
"""

CUSTOM_COMMANDS = {}

CUSTOM_COMMANDS["take_screenshot"] = {"type": "custom", "action": "take_screenshot", "trigger": ['screenshot lo', 'screen ka photo khicho', 'ek screenshot le lo']}

CUSTOM_COMMANDS["change_assistant_name"] = {"type": "custom", "action": "change_assistant_name", "trigger": ['ab se tumhara naam memo hai', 'apna naam badal kar memo rakh lo', 'ab tum memo ho']}

CUSTOM_COMMANDS["generate_and_save_ai_image"] = {"type": "custom", "action": "generate_and_save_ai_image", "trigger": ['ek tasveer banao', 'ai image generate karo', 'jarvis images folder mein photo save karo']}

CUSTOM_COMMANDS["save_birthday"] = {"type": "custom", "action": "save_birthday", "trigger": ['meri birth date yaad rakho', 'mera birthday save karo', 'meri janm tithi yaad rakho']}

CUSTOM_COMMANDS["create_database_folder"] = {"type": "custom", "action": "create_database_folder", "trigger": ['database folder bana do', 'databases ke liye folder create karo', 'naya folder banao']}
