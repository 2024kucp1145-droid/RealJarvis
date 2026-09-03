# -*- coding: utf-8 -*-
"""
command_data.py
================
Teeno uploaded PDFs (50,000 / 12,000 / v2-realistic) me se saare UNIQUE
actions nikaal kar yaha categorize kiya gaya hai (duplicate "variant 1,
variant 2..." wali entries hata di gayi hain - wo sirf padding thi).

Har action ke liye:
  - "type"    : kaunsa executor handle karega (system / run / keyboard /
                browser / file / email / info)
  - "trigger" : Hindi + English keywords jo bolne par ye action match hoga
  - "action"  : commands/ ke andar wale function ka naam

Naya command add karna ho toh bas isi dictionary me ek entry add karo -
baaki system automatically use samajh jayega. Isse tumhara "Jarvis"
hazaro commands tak scale ho sakta hai bina code duplicate kiye.

NOTE: "custom" type wale commands Jarvis KHUD add karta hai jab tum
"modify yourself" se koi naya feature banwate ho - wo custom/custom_triggers.py
me store hote hain aur yahan neeche automatically merge ho jaate hain.
"""

try:
    from custom.custom_triggers import CUSTOM_COMMANDS
except Exception:
    CUSTOM_COMMANDS = {}

try:
    from commands.whatsapp_commands import WHATSAPP_COMMANDS
except Exception:
    WHATSAPP_COMMANDS = {}

COMMANDS = {

    # ---------------- SYSTEM / HARDWARE ----------------
    "brightness_up": {"type": "system", "action": "brightness_up",
        "trigger": ["brightness badhao", "brightness increase karo", "roshni badhao", "screen brighten karo"]},
    "brightness_down": {"type": "system", "action": "brightness_down",
        "trigger": ["brightness kam karo", "brightness decrease karo", "roshni kam karo", "screen dim karo"]},
    "brightness_set": {"type": "system", "action": "brightness_set",
        "trigger": ["brightness set karo", "brightness kar do"]},
    "volume_up": {"type": "system", "action": "volume_up",
        "trigger": ["volume badhao", "awaz badhao", "sound badhao"]},
    "volume_down": {"type": "system", "action": "volume_down",
        "trigger": ["volume kam karo", "awaz kam karo", "sound kam karo"]},
    "volume_mute": {"type": "system", "action": "volume_mute",
        "trigger": ["mute karo", "volume band karo", "chup karo awaz"]},
    "volume_unmute": {"type": "system", "action": "volume_unmute",
        "trigger": ["unmute karo", "awaz chalu karo"]},
    "lock_pc": {"type": "system", "action": "lock_pc",
        "trigger": ["laptop lock karo", "pc lock karo", "screen lock karo", "win+l"]},
    "shutdown_pc": {"type": "system", "action": "shutdown_pc", "confirm": True,
        "trigger": ["laptop band karo", "shutdown karo", "computer band karo"]},
    "restart_pc": {"type": "system", "action": "restart_pc", "confirm": True,
        "trigger": ["restart karo", "laptop restart karo", "reboot karo"]},
    "sleep_pc": {"type": "system", "action": "sleep_pc",
        "trigger": ["sleep mode", "laptop sone do", "sleep karo"]},
    "show_desktop": {"type": "system", "action": "show_desktop",
        "trigger": ["desktop dikhao", "sab minimize karo", "win+d"]},
    "screenshot": {"type": "system", "action": "screenshot",
        "trigger": ["screenshot lo", "screen capture karo"]},
    "storage_check": {"type": "system", "action": "storage_check",
        "trigger": ["storage kitna bacha hai", "disk space check karo", "storage usage batao"]},
    "ram_check": {"type": "system", "action": "ram_check",
        "trigger": ["ram usage batao", "ram kitni use ho rahi hai", "memory usage batao"]},
    "battery_check": {"type": "system", "action": "battery_check",
        "trigger": ["battery kitni hai", "battery percentage batao", "charge kitna hai"]},
    "wifi_on": {"type": "system", "action": "wifi_on", "trigger": ["wifi on karo", "wifi chalu karo"]},
    "wifi_off": {"type": "system", "action": "wifi_off", "trigger": ["wifi off karo", "wifi band karo"]},
    "bluetooth_on": {"type": "system", "action": "bluetooth_on", "trigger": ["bluetooth on karo", "bluetooth chalu karo"]},
    "bluetooth_off": {"type": "system", "action": "bluetooth_off", "trigger": ["bluetooth off karo", "bluetooth band karo"]},
    "time_check": {"type": "system", "action": "time_check", "trigger": ["time kya hua hai", "abhi kitne baje hain"]},
    "date_check": {"type": "system", "action": "date_check", "trigger": ["aaj ki date kya hai", "date batao"]},
    "focus_time_check": {"type": "info", "action": "focus_time_check",
        "trigger": ["kitni der se kaam kar raha hoon", "kitni der se baitha hoon", "mera focus time batao", "screen time batao", "active time batao", "focus time kitna hua"]},
    "click_here": {"type": "system", "action": "click_here",
        "trigger": ["click karo", "yahan click karo", "click kar do"]},
    "double_click_here": {"type": "system", "action": "double_click_here",
        "trigger": ["double click karo", "do baar click karo"]},
    "scroll_down": {"type": "system", "action": "scroll_down",
        "trigger": ["neeche scroll karo", "scroll down karo", "niche karo"]},
    "scroll_up": {"type": "system", "action": "scroll_up",
        "trigger": ["upar scroll karo", "scroll up karo", "upar karo"]},
    "read_full_screen": {"type": "vision", "action": "read_full_screen",
        "trigger": ["page padho", "ye page mein kya likha hai", "screen padh kar sunao",
                    "poora page padho", "isse padh kar sunao"]},
    "write_code_for_screen": {"type": "vision", "action": "write_code_for_screen",
        "trigger": ["iska code likho", "is question ka code likho", "is problem ka code likho",
                    "code likh do", "solution likho"]},
    
    # ---------------- WEB & BROWSER WORKFLOW ASSISTANT (PHASE 7) ----------------
    "provide_coding_hint": {"type": "vision", "action": "provide_coding_hint",
        "trigger": ["hint do", "is problem ka hint do", "approach kya hogi", "approach batao", "kaise solve karein", "algorithm hint do"]},
    "summarize_active_webpage": {"type": "vision", "action": "summarize_active_webpage",
        "trigger": ["page samjhao", "page ka summary do", "summary sunao", "kya likha hai short me", "article summarize karo", "short me batao kya hai"]},
    "yt_forward": {"type": "system", "action": "yt_forward",
        "trigger": ["10 second aage karo", "aage karo video", "skip karo 10 second", "forward karo video"]},
    "yt_backward": {"type": "system", "action": "yt_backward",
        "trigger": ["10 second peeche karo", "peeche karo video", "rewind karo video"]},
    "yt_subtitles": {"type": "system", "action": "yt_subtitles",
        "trigger": ["subtitles on karo", "subtitles chalu karo", "cc chalu karo", "captions on karo", "subtitles band karo"]},
    "yt_speed_up": {"type": "system", "action": "yt_speed_up",
        "trigger": ["video speed badhao", "speed 1.5x karo", "speed 2x karo", "fast forward karo video"]},
    "yt_speed_down": {"type": "system", "action": "yt_speed_down",
        "trigger": ["video speed kam karo", "speed normal karo", "slow karo video"]},
    "yt_theater": {"type": "system", "action": "yt_theater",
        "trigger": ["theater mode on", "theater mode karo", "theater mode chalu karo"]},

    
    #chatbot-------------------------------------------------
    "chat_mode_on": {"type": "info", "action": "chat_mode_on",
        "trigger": ["chat mode on", "chat mode chalu karo", "chat mode start karo",
                    "jarvis turn on chat mode", "chat mode", "chatting mode on",
                    "message mode on", "text mode on"]},
    "chat_mode_off": {"type": "info", "action": "chat_mode_off",
        "trigger": ["chat mode off", "chat mode band karo", "floating mode",
                    "widget mode", "robot mode", "chat band karo", "back to robot"]},
    
    # ---------------- WORKSPACE HARMONIZER (PHASE 6) ----------------
    "coding_mode_on": {"type": "info", "action": "coding_mode_on",
        "trigger": ["coding mode on", "coding mode chalu karo", "dev mode on", "coding environment ready karo"]},
    "study_mode_on": {"type": "info", "action": "study_mode_on",
        "trigger": ["study mode on", "study mode chalu karo", "padhai mode on", "problem solving mode on"]},
    "meeting_mode_on": {"type": "info", "action": "meeting_mode_on",
        "trigger": ["meeting mode on", "meeting mode chalu karo", "silent mode on", "call mode on", "class mode on"]},
    "meeting_mode_off": {"type": "info", "action": "meeting_mode_off",
        "trigger": ["meeting mode off", "meeting mode band karo", "silent mode off", "call mode off", "class mode off"]},

    # ---------------- PROJECT & GIT AUTO-DOCTOR (PHASE 8) ----------------
    "git_auto_commit": {"type": "info", "action": "git_auto_commit",
        "trigger": ["git commit karo", "aaj ka kaam save karo", "code commit karo", "changes save karo", "git commit aur push karo"]},
    "git_status_check": {"type": "info", "action": "git_status_check",
        "trigger": ["git status batao", "git status kya hai", "uncommitted changes batao", "repo status batao"]},
    "free_port_3000": {"type": "info", "action": "free_port_3000",
        "trigger": ["port 3000 free karo", "port 3000 clean karo", "port 3000 kill karo", "port 3000 band karo"]},
    "free_port_8000": {"type": "info", "action": "free_port_8000",
        "trigger": ["port 8000 free karo", "port 8000 clean karo", "port 8000 kill karo", "port 8000 band karo"]},
    "free_port_5000": {"type": "info", "action": "free_port_5000",
        "trigger": ["port 5000 free karo", "port 5000 clean karo", "port 5000 kill karo"]},

    # ---------------- DESKTOP JANITOR (PHASE 9) ----------------
    "organize_desktop": {"type": "info", "action": "organize_desktop",
        "trigger": ["desktop organize karo", "desktop saaf karo", "desktop clean karo",
                    "desktop sort karo", "desktop files organize karo"]},
    "clean_old_downloads": {"type": "info", "action": "clean_old_downloads",
        "trigger": ["purani files saaf karo", "downloads clean karo", "purani downloads hatao",
                    "old files clean karo", "downloads folder saaf karo"]},
    "find_duplicate_files": {"type": "info", "action": "find_duplicate_files",
        "trigger": ["duplicate files dhundho", "duplicate files batao", "same files dhundho",
                    "duplicate files check karo"]},
    "disk_space_report": {"type": "info", "action": "disk_space_report",
        "trigger": ["disk space batao", "laptop mein kitna space bacha hai", "storage kitni bachi hai",
                    "drive space check karo", "kitna space hai laptop mein", "c drive kitna full hai"]},

    # ---------------- AUTONOMOUS EVOLUTION & DIAGNOSTICS (PHASE 10) ----------------
    "system_diagnostic": {"type": "info", "action": "system_diagnostic",
        "trigger": ["apna health check karo", "system diagnostic chalao", "diagnostics run karo",
                    "health check karo", "subsystems check karo", "system status batao", "sab theek chal raha hai"]},
    "list_macros": {"type": "info", "action": "list_macros",
        "trigger": ["apni routines batao", "tumne kya seekha hai", "custom macros batao", "learned routines batao"]},

    # ---------------- WHATSAPP MOBILE BRIDGE (PHASES 1, 2 & 3) ----------------
    "send_laptop_telemetry_whatsapp": {"type": "info", "action": "send_laptop_telemetry_whatsapp",
        "trigger": ["laptop status whatsapp par bhejo", "telemetry whatsapp karo", "whatsapp par status bhejo", "phone par status bhejo"]},
    "send_screenshot_whatsapp": {"type": "info", "action": "send_screenshot_whatsapp",
        "trigger": ["screenshot whatsapp par bhejo", "screen photo whatsapp par bhejo", "screen photo phone par bhejo", "live screenshot whatsapp karo"]},
    "show_wol_instructions": {"type": "info", "action": "show_wol_instructions",
        "trigger": ["laptop ko phone se on kaise kare", "wake on lan setup batao", "remote boot setting batao", "phone se on karne ki setting batao"]},


    # ---------------- RUN / PROGRAMS ----------------

    "open_notepad": {"type": "run", "action": "notepad", "trigger": ["notepad kholo", "notepad open karo"]},
    "open_calculator": {"type": "run", "action": "calc", "trigger": ["calculator kholo", "calculator open karo"]},
    "open_paint": {"type": "run", "action": "mspaint", "trigger": ["paint kholo", "paint open karo"]},
    "open_task_manager": {"type": "run", "action": "taskmgr", "trigger": ["task manager kholo", "ctrl shift esc"]},
    "open_control_panel": {"type": "run", "action": "control", "trigger": ["control panel kholo"]},
    "open_cmd": {"type": "run", "action": "cmd", "trigger": ["command prompt kholo", "cmd kholo"]},
    "open_powershell": {"type": "run", "action": "powershell", "trigger": ["powershell kholo"]},
    "open_settings": {"type": "run", "action": "ms-settings:", "trigger": ["windows settings kholo", "win+i"]},
    "open_file_explorer": {"type": "run", "action": "explorer", "trigger": ["file explorer kholo", "win+e"]},
    "open_device_manager": {"type": "run", "action": "devmgmt.msc", "trigger": ["device manager kholo"]},
    "open_disk_management": {"type": "run", "action": "diskmgmt.msc", "trigger": ["disk management kholo"]},
    "open_services": {"type": "run", "action": "services.msc", "trigger": ["services kholo"]},
    "open_msconfig": {"type": "run", "action": "msconfig", "trigger": ["msconfig kholo", "system configuration kholo"]},
    "open_regedit": {"type": "run", "action": "regedit", "trigger": ["registry editor kholo", "regedit kholo"]},
    "open_appwiz": {"type": "run", "action": "appwiz.cpl", "trigger": ["programs uninstall karna hai", "apps uninstall list kholo"]},
    "open_cleanmgr": {"type": "run", "action": "cleanmgr", "trigger": ["disk cleanup kholo"]},
    "open_eventvwr": {"type": "run", "action": "eventvwr", "trigger": ["event viewer kholo"]},
    "open_firewall": {"type": "run", "action": "firewall.cpl", "trigger": ["firewall settings kholo"]},

        # ---------------- WEB / APP VISUAL CONTROL ----------------
    "web_like": {"type": "web", "action": "web_action",
        "trigger": ["like karo", "like kar do", "like this", "reel like karo", "post like karo",
                    "photo like karo", "video like karo", "heart dabao"]},
    "web_pause": {"type": "web", "action": "web_action",
        "trigger": ["stop the song", "gaana band karo", "pause karo", "video pause karo",
                    "stop karo", "music band karo", "pause the video"]},
    "web_play": {"type": "web", "action": "web_action",
        "trigger": ["play karo", "chalao", "resume karo", "gaana chalao", "video play karo",
                    "start karo"]},
    "web_scroll_down": {"type": "web", "action": "web_action",
        "trigger": ["neeche scroll karo", "scroll down karo", "aage badho", "next karo",
                    "age badho", "niche karo"]},
    "web_scroll_up": {"type": "web", "action": "web_action",
        "trigger": ["upar scroll karo", "scroll up karo", "peeche jao", "pichla dikhao"]},
    "web_contact": {"type": "web", "action": "web_action",
        "trigger": ["contact number do", "phone number batao", "email batao", "address batao",
                    "number do", "mobile batao", "email id do", "contact do"]},
    "web_click": {"type": "web", "action": "web_action",
        "trigger": ["ispe click karo", "yahan click karo", "button dabao", "click kar do",
                    "is button pe click karo", "yeh dabao"]},
    "web_type": {"type": "web", "action": "web_action",
        "trigger": ["yahan type karo", "ispe likho", "type kar do", "yeh likh do"]},
    # ---------------- KEYBOARD SHORTCUTS (works in any focused window) ----------------
    "copy": {"type": "keyboard", "action": "ctrl+c", "trigger": ["copy karo"]},
    "paste": {"type": "keyboard", "action": "ctrl+v", "trigger": ["paste karo"]},
    "cut": {"type": "keyboard", "action": "ctrl+x", "trigger": ["cut karo"]},
    "delete_key": {"type": "keyboard", "action": "delete",
        "trigger": ["delete karo", "delete kar do", "delete key dabao"]},
    "undo": {"type": "keyboard", "action": "ctrl+z", "trigger": ["undo karo"]},
    "redo": {"type": "keyboard", "action": "ctrl+y", "trigger": ["redo karo"]},
    "select_all": {"type": "keyboard", "action": "ctrl+a", "trigger": ["sab select karo", "select all karo"]},
    "find": {"type": "keyboard", "action": "ctrl+f", "trigger": ["find karo", "search karo isme"]},
    "save": {"type": "keyboard", "action": "ctrl+s", "trigger": ["save karo"]},
    "print": {"type": "keyboard", "action": "ctrl+p", "trigger": ["print karo"]},
    "switch_app": {"type": "keyboard", "action": "alt+tab", "trigger": ["app switch karo", "dusri window pe jao"]},
    "new_tab": {"type": "keyboard", "action": "ctrl+t", "trigger": ["naya tab kholo", "new tab kholo"]},
    "close_tab": {"type": "keyboard", "action": "ctrl+w", "trigger": ["tab band karo"]},
    "reopen_tab": {"type": "keyboard", "action": "ctrl+shift+t", "trigger": ["band tab wapas kholo"]},
    "next_tab": {"type": "keyboard", "action": "ctrl+tab", "trigger": ["agla tab", "next tab"]},
    "address_bar": {"type": "keyboard", "action": "ctrl+l", "trigger": ["address bar pe jao"]},
    "browser_back": {"type": "keyboard", "action": "alt+left", "trigger": ["peeche jao", "back jao"]},
    "browser_forward": {"type": "keyboard", "action": "alt+right", "trigger": ["aage jao", "forward jao"]},
    "refresh_page": {"type": "keyboard", "action": "f5", "trigger": ["page refresh karo", "reload karo"]},

    # ---------------- FILE / FOLDER OPERATIONS ----------------
    "create_folder": {"type": "file", "action": "create_folder", "trigger": ["naya folder banao", "folder create karo"]},
    "rename_file": {"type": "file", "action": "rename", "trigger": ["file ka naam badlo", "rename karo"]},
    "copy_file": {"type": "file", "action": "copy_file", "trigger": ["file copy karo"]},
    "delete_file": {"type": "file", "action": "delete_file", "confirm": True,
        "trigger": ["file delete karo", "file hatao"]},
    "zip_file": {"type": "file", "action": "zip_file", "trigger": ["zip banao", "compress karo"]},
    "extract_zip": {"type": "file", "action": "extract_zip", "trigger": ["zip extract karo", "unzip karo"]},
    "open_downloads": {"type": "file", "action": "open_downloads", "trigger": ["downloads folder kholo"]},
    "open_documents": {"type": "file", "action": "open_documents", "trigger": ["documents folder kholo"]},
    "open_music": {"type": "file", "action": "open_music", "trigger": ["music folder kholo"]},
    "open_videos": {"type": "file", "action": "open_videos", "trigger": ["videos folder kholo"]},
    "empty_recycle_bin": {"type": "file", "action": "empty_recycle_bin", "confirm": True,
        "trigger": ["recycle bin khali karo", "recycle bin empty karo"]},
    "open_display_settings": {"type": "system", "action": "open_display_settings",
        "trigger": ["display settings kholo", "screen settings kholo"]},
    "open_sound_settings": {"type": "system", "action": "open_sound_settings",
        "trigger": ["sound settings kholo", "audio settings kholo"]},
    "open_network_settings": {"type": "system", "action": "open_network_settings",
        "trigger": ["network settings kholo", "internet settings kholo"]},
    "system_info": {"type": "system", "action": "system_info",
        "trigger": ["system info batao", "laptop ki details batao", "system ki jaankari do"]},
    "wifi_name_check": {"type": "system", "action": "wifi_name_check",
        "trigger": ["kaunse wifi se connected hoon", "wifi ka naam batao"]},
    "ip_address_check": {"type": "system", "action": "ip_address_check",
        "trigger": ["ip address batao", "mera ip kya hai"]},
    "find_file": {"type": "file", "action": "find_file", "param": "name",
        "trigger": ["file dhoondo", "file kaha hai", "file khojo", "find file"]},
    "open_file": {"type": "file", "action": "open_file", "param": "name",
        "trigger": ["file kholo", "file open karo"]},

    # ---------------- DESKTOP AWARENESS (active window, open apps) ----------------
    "whats_active": {"type": "vision", "action": "explain_cursor",
        "trigger": ["main kya kar rahi hoon", "main kya kar raha hoon", "abhi kya khula hai",
                    "kaunsa app khula hai", "kitni windows khuli hain", "abhi kis par kaam kar raha hoon",
                    "abhi kis par kaam kar rahi hoon"]},

    # ---------------- BROWSER / WEB / YOUTUBE ----------------
    "open_browser": {"type": "browser", "action": "open_browser", "trigger": ["browser kholo"]},
    "open_website": {"type": "browser", "action": "open_website", "param": "site", "trigger": ["website kholo", "site kholo"]},
    "search_google": {"type": "browser", "action": "search_google", "param": "query", "trigger": ["google pe search karo", "search karo"]},
    "leetcode_search": {"type": "browser", "action": "leetcode_search", "param": "query",
        "trigger": ["leetcode pe search karo", "leetcode problem search karo", "leetcode par dhoondo"]},
    "write_code_for_screen": {"type": "vision", "action": "write_code_for_screen",
        "trigger": ["iska code likho", "is question ka code likho", "is problem ka code likho",
                    "code likh do", "solution likho", "code banao", "solve kar do",
                    "iska solution likho", "code verify karo", "code theek karo",
                    "bug fix karo", "code complete karo"]},
    "play_youtube_song": {"type": "browser", "action": "play_youtube", "param": "song", "trigger": ["gaana chalao", "song play karo", "youtube pe play karo", "music chalao"]},
    "pause_media": {"type": "keyboard", "action": "playpause", "trigger": ["pause karo", "gaana roko"]},
    "next_track": {"type": "keyboard", "action": "nexttrack", "trigger": ["agla gaana", "next song"]},
    "prev_track": {"type": "keyboard", "action": "prevtrack", "trigger": ["pichla gaana", "previous song"]},

    # ---------------- EMAIL ----------------
    "send_email": {"type": "email", "action": "send_email", "trigger": ["email bhejo", "mail bhejo", "email compose karo"]},
    "read_unread_email": {"type": "email", "action": "read_unread", "trigger": ["nayi email padho", "unread mail batao", "email check karo"]},
    "search_inbox": {"type": "email", "action": "search_inbox", "trigger": ["inbox me dhoondo", "email search karo"]},
    "my_email_address": {"type": "info", "action": "my_email_address",
        "trigger": ["mera email kya hai", "mera email address kya hai", "mera email id kya hai", "mera email batao"]},
    "email_latest": {"type": "email_ai", "action": "email_latest",
        "trigger": ["email me kya likha hai", "naya email aaya hai", "koi email aaya hai",
                    "email padh kar batao", "email ka summary do", "last email kis ka hai",
                    "latest email batao", "latest email dikhao", "email check karo",
                    "mail check karo", "naya mail aaya", "mail me kya hai", "meri email dikhao",
                    "email dikhao", "mera email check karo", "email me kya hai",
                    "email padho", "mail padho", "mail dikhao", "email ka access", "mera inbox"]},
    "email_filtered": {"type": "email_ai", "action": "email_filtered", "param": "who",
        "trigger": ["ka email dikhao", "se aaya email dikhao", "wala email sunao", "email dhoondo"]},
    "open_email_window": {"type": "email_ui", "action": "open_email_window",
        "trigger": ["email kholo", "inbox kholo", "email ka window kholo", "email tab kholo"]},

    # ---------------- SCREEN / CURSOR SAMAJHNA ----------------
    "explain_cursor": {"type": "vision", "action": "explain_cursor",
        "trigger": ["ye kya hai", "iska matlab batao", "cursor pe kya hai",
                    "screen dekho", "screen par kya hai", "yaha kya likha hai",
                    "ye kya likha hai", "iska explanation do"]},
    
        # ---------------- SCREEN MONITORING (Always-On Vision) ----------------
    "screen_monitor_start": {"type": "info", "action": "screen_monitor_start",
        "trigger": ["screen monitor on karo", "monitoring chalu karo", "screen dekhna shuru karo", 
                    "monitor on karo", "hamesha screen dekho", "screen watch karo"]},
    "screen_monitor_stop": {"type": "info", "action": "screen_monitor_stop",
        "trigger": ["screen monitor band karo", "monitoring band karo", "screen dekhna band karo", 
                    "monitor off karo", "screen mat dekho"]},
    "what_am_i_doing": {"type": "vision", "action": "what_am_i_doing",
        "trigger": ["main kya kar raha hoon", "main kya kar rahi hoon", "abhi kya chal raha hai", 
                    "screen pe kya hai", "abhi kya ho raha hai", "kya kaam kar raha hoon"]},

    # ---------------- ASSISTANT / SMALL TALK ----------------
    "greet": {"type": "info", "action": "greet", "trigger": ["kaise ho", "kya haal hai", "hello", "hi jarvis"]},
    "time_now": {"type": "system", "action": "time_check", "trigger": ["abhi time kya hai"]},
    "who_are_you": {"type": "info", "action": "who_are_you", "trigger": ["tum kaun ho", "apna naam batao"]},
    "sleep_assistant": {"type": "info", "action": "sleep_assistant", "trigger": ["so jao", "band ho jao", "chup ho jao"]},
    "exit_assistant": {"type": "info", "action": "exit_assistant", "trigger": ["bye jarvis", "exit karo", "assistant band karo"]},
    "start_dictation": {"type": "info", "action": "start_dictation",
        "trigger": ["likhna shuru karo", "type karo", "likhna hai", "dictation shuru karo",
                    "type mode chalu karo", "type mode on karo"]},
    "start_eye_cursor": {"type": "info", "action": "start_eye_cursor",
        "trigger": ["cursor eyes", "eye cursor shuru karo", "eyes cursor chalu karo",
                    "aankho se cursor chalao", "eye cursor on karo", "cursor eyes on"]},
    "stop_eye_cursor": {"type": "info", "action": "stop_eye_cursor",
        "trigger": ["stop eyes cursor", "eye cursor band karo", "eyes cursor band karo",
                    "aankho wala cursor band karo", "eye cursor off karo", "cursor eyes off",
                    "eyes cursor off", "cursor eyes band"]},
    "modify_self": {"type": "info", "action": "modify_self",
        "trigger": ["modify yourself", "khud ko modify karo", "apne aap ko modify karo",
                    "khud ko update karo", "apne app ko modify karo"]},

    # ---------------- MEMORY (item #1 - naya, additive) ----------------
    "save_note": {"type": "memory", "action": "save_note", "param": "content",
        "trigger": ["yaad rakho", "ye yaad rakho", "note karo", "note kar lo"]},
    "recall_notes": {"type": "memory", "action": "recall_notes",
        "trigger": ["kya yaad hai", "mujhe kya yaad rakhna hai", "notes sunao", "kya note kiya tha"]},
    "search_notes": {"type": "memory", "action": "search_notes", "param": "keyword",
        "trigger": ["yaad dilao", "ke baare mein yaad dilao", "kya yaad hai ki"]},
    "set_reminder": {"type": "memory", "action": "set_reminder", "param": "instruction",
        "trigger": ["yaad dilana", "reminder lagao", "mujhe yaad dilana"]},
    "whatsapp_send_quick": {
        "type": "whatsapp",
        "action": "send_whatsapp_quick",
        "trigger": [
            "whatsapp pe bhejo", "whatsapp send", "send whatsapp",
            "wa pe bhejo", "wa send", "whatsapp pe message"
        ]
    },

    # ---------------- AUTONOMOUS WEB & SCREEN AGENT ----------------
    "autonomous_web_task": {
        "type": "web_agent",
        "action": "run_autonomous_web_task",
        "trigger": [
            "website pe kaam karo", "browser automate karo", "browser par task karo",
            "form bharo", "game khelo", "contacts page par jao", "pura kaam karo"
        ]
    },
    "extract_page_info": {
        "type": "web_extract",
        "action": "extract_screen_info",
        "trigger": [
            "is website me kya hai", "isme last date kab hai", "last date batao",
            "contact number batao", "phone number batao", "page scan karo", "website check karo"
        ]
    },
    "stop_web_agent": {
        "type": "info",
        "action": "stop_web_agent",
        "trigger": [
            "browser automation roko", "agent roko", "web agent band karo", "automation band karo", "automation roko"
        ]
    },
    "cursor_paste_replace": {
        "type": "guardian",
        "action": "replace_at_cursor",
        "trigger": [
            "replace karo", "code replace karo", "yahan daal do", "yahan paste karo",
            "cursor par paste karo", "paste kar do", "replace kar do", "vahan daal do",
            "wahan paste karo", "code daal do"
        ]
    }
}

COMMANDS.update(WHATSAPP_COMMANDS)
def find_command(user_text: str):
    """
    Smart multi-layer command matcher — koi bhi spelling mistake ya Hinglish
    variation ho, phir bhi sahi command dhoondhta hai.

    Layer 1: Exact substring match (fastest, highest priority)
    Layer 2: Fuzzy match via difflib (spelling mistakes, pronunciation errors)
    Layer 3: Token overlap match (word-level partial matching)

    Return: (cmd_id, data, matched_trigger_text) - teeno None agar match na ho.
    """
    import difflib

    text = user_text.lower().strip()
    all_commands = {**COMMANDS, **CUSTOM_COMMANDS}

    # ---------- Layer 1: Exact substring ----------
    best_id, best_score, best_trig = None, 0, None
    for cmd_id, data in all_commands.items():
        for trig in data["trigger"]:
            if trig in text:
                score = len(trig)
                if score > best_score:
                    best_score, best_id, best_trig = score, cmd_id, trig
    if best_id:
        return best_id, all_commands[best_id], best_trig

    # ---------- Layer 2: Fuzzy similarity ----------
    best_ratio = 0.0
    for cmd_id, data in all_commands.items():
        for trig in data["trigger"]:
            ratio = difflib.SequenceMatcher(None, trig, text).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_id, best_trig = cmd_id, trig
    if best_ratio >= 0.72:   # 72% similarity kaafi hai safe match ke liye
        return best_id, all_commands[best_id], best_trig

    # ---------- Layer 3: Token overlap (word-level) ----------
    text_words = set(text.split())
    best_overlap = 0
    for cmd_id, data in all_commands.items():
        for trig in data["trigger"]:
            trig_words = set(trig.split())
            overlap = len(trig_words & text_words)
            # Require majority of trigger words to match
            if trig_words and overlap / len(trig_words) >= 0.75:
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_id, best_trig = cmd_id, trig
    if best_overlap >= 2:
        return best_id, all_commands[best_id], best_trig

    return None, None, None