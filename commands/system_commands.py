# -*- coding: utf-8 -*-
"""
system_commands.py
===================
Hardware/system level actions: brightness, volume, power, wifi, bluetooth,
storage/RAM/battery info. Sab Windows-native libraries se, bina touch ke.
"""

import os
import re
import json
import glob
import difflib
import shutil
import subprocess
import datetime

try:
    import screen_brightness_control as sbc
except ImportError:
    sbc = None

try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
except ImportError:
    AudioUtilities = None
    cast = None
    POINTER = None
    CLSCTX_ALL = None
    IAudioEndpointVolume = None

try:
    import psutil
except ImportError:
    psutil = None


def _volume_interface():
    if AudioUtilities is None:
        return None

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_,
        CLSCTX_ALL,
        None
    )
    return cast(interface, POINTER(IAudioEndpointVolume))


def brightness_up(voice, **kw):
    if not sbc:
        voice.speak("Brightness control library install nahi hai.")
        return
    try:
        cur = sbc.get_brightness()[0]
        sbc.set_brightness(min(cur + 20, 100))
        voice.speak("Brightness badha di maine.")
    except Exception as e:
        voice.speak("Brightness badhane mein error aa gaya.")
        print(f"[brightness_up error: {e}]")


def brightness_down(voice, **kw):
    if not sbc:
        voice.speak("Brightness control library install nahi hai.")
        return
    try:
        cur = sbc.get_brightness()[0]
        sbc.set_brightness(max(cur - 20, 0))
        voice.speak("Brightness kam kar di maine.")
    except Exception as e:
        voice.speak("Brightness kam karne mein error aa gaya.")
        print(f"[brightness_down error: {e}]")


def brightness_set(voice, value=50, **kw):
    if not sbc:
        voice.speak("Brightness control library install nahi hai.")
        return
    try:
        sbc.set_brightness(value)
        voice.speak(f"Brightness {value} percent kar di.")
    except Exception as e:
        voice.speak("Brightness set karne mein error aa gaya.")
        print(f"[brightness_set error: {e}]")


def volume_up(voice, **kw):
    try:
        import keyboard
        for _ in range(3):
            keyboard.send("volume up")
        voice.speak("Volume badha diya.")
    except ImportError:
        voice.speak("Keyboard control library install nahi hai.")
    except Exception as e:
        voice.speak("Volume badhane mein error aa gaya.")
        print(f"[volume_up error: {e}]")


def volume_down(voice, **kw):
    try:
        import keyboard
        for _ in range(3):
            keyboard.send("volume down")
        voice.speak("Volume kam kar diya.")
    except ImportError:
        voice.speak("Keyboard control library install nahi hai.")
    except Exception as e:
        voice.speak("Volume kam karne mein error aa gaya.")
        print(f"[volume_down error: {e}]")


def volume_mute(voice, **kw):
    try:
        import keyboard
        keyboard.send("volume mute")
        voice.speak("Mute kar diya.")
    except ImportError:
        voice.speak("Keyboard control library install nahi hai.")
    except Exception as e:
        voice.speak("Mute karne mein error aa gaya.")
        print(f"[volume_mute error: {e}]")


def volume_unmute(voice, **kw):
    try:
        import keyboard
        if AudioUtilities:
            try:
                vol = _volume_interface()
                if vol.GetMute():
                    keyboard.send("volume mute")
                    voice.speak("Awaz wapas chalu kar di.")
                else:
                    voice.speak("Pehle se hi unmute hai.")
                return
            except Exception:
                pass
        # Fallback: state pata nahi hai, sirf toggle kar sakte hain
        keyboard.send("volume mute")
        voice.speak("Mute toggle kar diya.")
    except ImportError:
        voice.speak("Keyboard control library install nahi hai.")
    except Exception as e:
        voice.speak("Unmute karne mein error aa gaya.")
        print(f"[volume_unmute error: {e}]")


def lock_pc(voice, **kw):
    try:
        voice.speak("Lock kar rahi hoon.")
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
    except Exception as e:
        voice.speak("Lock karne mein error aa gaya.")
        print(f"[lock_pc error: {e}]")


def shutdown_pc(voice, **kw):
    try:
        voice.speak("Laptop band kar rahi hoon, bye!")
        subprocess.run(["shutdown", "/s", "/t", "5"], check=True)
    except Exception as e:
        voice.speak("Shutdown karne mein error aa gaya.")
        print(f"[shutdown_pc error: {e}]")


def restart_pc(voice, **kw):
    try:
        voice.speak("Restart kar rahi hoon.")
        subprocess.run(["shutdown", "/r", "/t", "5"], check=True)
    except Exception as e:
        voice.speak("Restart karne mein error aa gaya.")
        print(f"[restart_pc error: {e}]")


def sleep_pc(voice, **kw):
    try:
        voice.speak("Sleep mode me ja rahe hain.")
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=True)
    except Exception as e:
        voice.speak("Sleep mode mein jaane mein error aa gaya.")
        print(f"[sleep_pc error: {e}]")


def show_desktop(voice, **kw):
    try:
        import keyboard
        keyboard.send("win+d")
        voice.speak("Desktop dikha diya.")
    except ImportError:
        voice.speak("Keyboard control library install nahi hai.")
    except Exception as e:
        voice.speak("Desktop dikhane mein error aa gaya.")
        print(f"[show_desktop error: {e}]")


def click_here(voice, **kw):
    """Jahan bhi mouse cursor abhi hai, wahi click kar deta hai - kisi bhi
    app/website me kaam karta hai (YouTube button, LeetCode "Run" button, etc)."""
    try:
        import pyautogui
        pyautogui.click()
        voice.speak("Click kar diya.")
    except ImportError:
        voice.speak("Mouse control library install nahi hai.")
    except Exception as e:
        voice.speak("Click karte waqt error aa gaya.")
        print(f"[click_here error: {e}]")


def double_click_here(voice, **kw):
    try:
        import pyautogui
        pyautogui.doubleClick()
        voice.speak("Double click kar diya.")
    except ImportError:
        voice.speak("Mouse control library install nahi hai.")
    except Exception as e:
        voice.speak("Double click karte waqt error aa gaya.")
        print(f"[double_click_here error: {e}]")


def scroll_down(voice, **kw):
    try:
        import pyautogui
        pyautogui.scroll(-500)
        voice.speak("Neeche scroll kar diya.")
    except ImportError:
        voice.speak("Mouse control library install nahi hai.")
    except Exception as e:
        voice.speak("Scroll karte waqt error aa gaya.")
        print(f"[scroll_down error: {e}]")


def scroll_up(voice, **kw):
    try:
        import pyautogui
        pyautogui.scroll(500)
        voice.speak("Upar scroll kar diya.")
    except ImportError:
        voice.speak("Mouse control library install nahi hai.")
    except Exception as e:
        voice.speak("Scroll karte waqt error aa gaya.")
        print(f"[scroll_up error: {e}]")


def screenshot(voice, **kw):
    try:
        import pyautogui
        import os
        screenshots_dir = os.path.join(os.path.expanduser("~"), "Pictures", "JarvisScreenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")
        pyautogui.screenshot(filename)
        voice.speak("Screenshot le liya, Pictures folder mein JarvisScreenshots naam se save hai.")
    except ImportError:
        voice.speak("Screenshot library install nahi hai.")
    except Exception as e:
        voice.speak("Screenshot lene mein error aa gaya.")
        print(f"[screenshot error: {e}]")


def storage_check(voice, **kw):
    if not psutil:
        voice.speak("Storage check library install nahi hai.")
        return
    try:
        usage = psutil.disk_usage("C:\\")
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        voice.speak(f"{free_gb:.1f} GB free hai, total {total_gb:.1f} GB me se.")
    except Exception as e:
        voice.speak("Storage info nahi mil payi.")
        print(f"[storage_check error: {e}]")


def ram_check(voice, **kw):
    if not psutil:
        voice.speak("RAM check library install nahi hai.")
        return
    try:
        mem = psutil.virtual_memory()
        voice.speak(f"RAM abhi {mem.percent} percent use ho rahi hai.")
    except Exception as e:
        voice.speak("RAM info nahi mil payi.")
        print(f"[ram_check error: {e}]")


def battery_check(voice, **kw):
    if not psutil:
        voice.speak("Battery check library install nahi hai.")
        return
    try:
        batt = psutil.sensors_battery()
        if not batt:
            voice.speak("Battery info nahi mil payi.")
            return
        status = "charge ho rahi hai" if batt.power_plugged else "charge pe nahi hai"
        voice.speak(f"Battery {int(batt.percent)} percent hai, {status}.")
    except Exception as e:
        voice.speak("Battery info nahi mil payi.")
        print(f"[battery_check error: {e}]")


def wifi_on(voice, **kw):
    try:
        subprocess.run(
            ["netsh", "interface", "set", "interface", "Wi-Fi", "enabled"],
            check=True, capture_output=True, text=True
        )
        voice.speak("Wifi on kar diya.")
    except Exception as e:
        voice.speak("Wifi on karne mein error aa gaya.")
        print(f"[wifi_on error: {e}]")


def wifi_off(voice, **kw):
    try:
        subprocess.run(
            ["netsh", "interface", "set", "interface", "Wi-Fi", "disabled"],
            check=True, capture_output=True, text=True
        )
        voice.speak("Wifi off kar diya.")
    except Exception as e:
        voice.speak("Wifi off karne mein error aa gaya.")
        print(f"[wifi_off error: {e}]")


def bluetooth_on(voice, **kw):
    try:
        voice.speak("Bluetooth settings khol rahi hoon.")
        subprocess.run(
            ["powershell", "-Command", "Start-Process ms-settings:bluetooth"],
            check=True
        )
    except Exception as e:
        voice.speak("Bluetooth settings kholne mein error aa gaya.")
        print(f"[bluetooth_on error: {e}]")


def bluetooth_off(voice, **kw):
    try:
        voice.speak("Bluetooth settings khol rahi hoon, waha se off kar dijiye.")
        subprocess.run(
            ["powershell", "-Command", "Start-Process ms-settings:bluetooth"],
            check=True
        )
    except Exception as e:
        voice.speak("Bluetooth settings kholne mein error aa gaya.")
        print(f"[bluetooth_off error: {e}]")



# Known app aliases — koi bhi naam bolo, sahi app khul jata hai
_APP_ALIASES = {
    "antigravity": r"C:\Users\User\.gemini\antigravity\antigravity.exe",
    "jarvis": r"python C:\RealJarvis_v2\RealJarvis\main.py",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "whatsapp": "whatsapp",
    "spotify": "spotify",
    "discord": "discord",
    "telegram": "telegram",
    "vlc": "vlc",
    "zoom": "zoom",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "cmd": "cmd",
    "powershell": "powershell",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "teams": "msteams",
    "terminal": "wt",
    "windows terminal": "wt",
    "file manager": "explorer",
    "files": "explorer",
    "explorer": "explorer",
    "settings": "ms-settings:",
    "task manager": "taskmgr",
}


def _find_startmenu_shortcut(name: str):
    """Start Menu mein fuzzy search karo .lnk files ke liye."""
    start_paths = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
    ]
    all_lnks = []
    for sp in start_paths:
        if os.path.exists(sp):
            all_lnks += glob.glob(os.path.join(sp, "**", "*.lnk"), recursive=True)

    if not all_lnks:
        return None

    # Normalize names for comparison
    lnk_names = [os.path.splitext(os.path.basename(p))[0].lower() for p in all_lnks]
    matches = difflib.get_close_matches(name.lower(), lnk_names, n=1, cutoff=0.50)
    if matches:
        idx = lnk_names.index(matches[0])
        return all_lnks[idx]
    return None


def open_any_app(voice, name="", **kw):
    if not name:
        voice.speak("Kaunsa app kholu, naam batayein?")
        return

    safe_name = re.sub(r'[\"&|><`;]', '', name).strip()
    name_lower = safe_name.lower()

    # Strategy 1: Known alias map
    alias_keys = list(_APP_ALIASES.keys())
    alias_matches = difflib.get_close_matches(name_lower, alias_keys, n=1, cutoff=0.60)
    if alias_matches:
        cmd_val = _APP_ALIASES[alias_matches[0]]
        print(f"[open_any_app] Alias match: '{name}' -> '{cmd_val}'")
        try:
            if cmd_val.startswith("shell:") or "\\" in cmd_val or " " in cmd_val:
                subprocess.Popen(f'start "" "{cmd_val}"', shell=True)
            else:
                subprocess.Popen(f'start "" {cmd_val}', shell=True)
            voice.speak(f"{safe_name} khol diya.")
            return
        except Exception as e:
            print(f"[open_any_app alias error: {e}]")

    # Strategy 2: Check in PATH / shutil.which
    which_path = shutil.which(safe_name) or shutil.which(safe_name + ".exe")
    if which_path:
        print(f"[open_any_app] Found in PATH: {which_path}")
        try:
            subprocess.Popen(f'start "" "{which_path}"', shell=True)
            voice.speak(f"{safe_name} khol diya.")
            return
        except Exception as e:
            print(f"[open_any_app which error: {e}]")

    # Strategy 3: Start Menu .lnk fuzzy search
    try:
        lnk_path = _find_startmenu_shortcut(safe_name)
        if lnk_path:
            print(f"[open_any_app] Start Menu match: {lnk_path}")
            os.startfile(lnk_path)
            voice.speak(f"{safe_name} khol diya.")
            return
    except Exception as e:
        print(f"[open_any_app lnk error: {e}]")

    # Strategy 4: Direct 'start' command fallback
    print(f"[open_any_app] Direct start fallback: '{safe_name}'")
    try:
        subprocess.Popen(f'start "" "{safe_name}"', shell=True)
        voice.speak(f"{safe_name} kholne ki koshish ki.")
    except Exception as e:
        voice.speak(f"Sorry, {safe_name} nahi khol paayi.")
        print(f"[open_any_app error: {e}]")



def time_check(voice, **kw):
    now = datetime.datetime.now().strftime("%I:%M %p")
    voice.speak(f"Abhi {now} baje hain.")


def date_check(voice, **kw):
    today = datetime.datetime.now().strftime("%d %B %Y")
    voice.speak(f"Aaj {today} hai.")


def yt_forward(voice, **kw):
    try:
        import pyautogui
        pyautogui.press('l')
        voice.speak("10 second aage kar diya.")
    except Exception:
        pass


def yt_backward(voice, **kw):
    try:
        import pyautogui
        pyautogui.press('j')
        voice.speak("10 second peeche kar diya.")
    except Exception:
        pass


def yt_subtitles(voice, **kw):
    try:
        import pyautogui
        pyautogui.press('c')
        voice.speak("Subtitles toggle kar diye.")
    except Exception:
        pass


def yt_speed_up(voice, **kw):
    try:
        import pyautogui
        pyautogui.hotkey('shift', '>')
        voice.speak("Playback speed badha di.")
    except Exception:
        pass


def yt_speed_down(voice, **kw):
    try:
        import pyautogui
        pyautogui.hotkey('shift', '<')
        voice.speak("Playback speed kam kar di.")
    except Exception:
        pass


def yt_theater(voice, **kw):
    try:
        import pyautogui
        pyautogui.press('t')
        voice.speak("Theater mode switch kar diya.")
    except Exception:
        pass