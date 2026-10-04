# -*- coding: utf-8 -*-
"""
main.py
=======
Real Jarvis - entry point. Isi file ko chalao:

    python main.py          # normal GUI + voice mode
    python main.py --daemon # 24/7 REST/WhatsApp gateway (no GUI/audio)

Ye file deliberately chhoti hai: sirf composition + startup. Poori behaviour
`jarvis_handlers/` package me hai (11 focused modules) — ek feature badalna ho
toh wahi file padho, 2000+ line ka ek class nahi.

Flow:
  1. App start hote hi Jarvis apna intro deta hai aur SEEDHA password poochta hai
     (wake word ka wait nahi karta pehli baar)
  2. Password sahi -> "Welcome, <naam>!" bolke commands sunna shuru
     Password ki jagah EXIT_PHRASE bola (jaise "jarvis not required") -> khud band ho jaata hai
  3. "so jao" bolne se sleep mode me jaata hai - dubara "Jarvis" naam se jagana padega
     (us case me dubara password nahi maangega, session yaad rehta hai)
  4. Lambe AI jawab ke beech me bolna shuru karo toh Jarvis turant ruk jaata hai
     aur tumhari baat sunta hai (barge-in) - best earphones ke saath kaam karta hai
  5. Poora system background me chalta hai - chota floating icon se control hota hai

Behaviour flow ke liye dekho:
  jarvis_handlers/router.py       -> handle_text() ka pura pipeline
  jarvis_handlers/lifecycle.py    -> wake / auth / speak / shutdown
"""

import sys
import threading

# Windows ka Command Prompt default me sirf limited characters (cp1252)
# print kar paata hai - special characters aane par crash ho sakta tha.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def _run_daemon_mode():
    """24/7 Always-On Daemon Mode — zero GUI / audio overhead."""
    import os

    print("=" * 60)
    print("  Starting RealJarvis in 24/7 Always-On Daemon Mode")
    print("=" * 60)
    from daemon_api_server import run_api_server
    port = int(os.environ.get("DAEMON_PORT", 8765))
    run_api_server(port=port)


# Check for 24/7 Always-On Daemon mode early (zero GUI / audio overhead).
# Heavy imports (voice, GUI, AI) skip ho jaate hain is path pe.
if "--daemon" in sys.argv or "-d" in sys.argv:
    _run_daemon_mode()
    sys.exit(0)

from gui import JarvisGUI  # noqa: E402  (daemon early-exit ke baad import zaroori)

from jarvis_handlers.core import JarvisCore as Jarvis  # noqa: E402


def main():
    gui = JarvisGUI()
    jarvis = Jarvis(gui)

    # Start 24/7 Persistent Mission Scheduler in background
    try:
        from jarvis_daemon import daemon as _jdaemon
        _jdaemon.start()
    except Exception as _e_dm:  # noqa: BLE001
        print(f"[main] Daemon worker start notice: {_e_dm}")

    # Jarvis ki poori logic (mic sunna, wake, commands) background thread me
    # chalti hai. pywebview GUI hamesha MAIN thread pe chalni chahiye, isliye
    # yaha split kiya gaya hai.
    worker = threading.Thread(target=jarvis.run_forever, daemon=True)
    worker.start()

    gui.run_mainloop()  # yehi window band hone tak block karega (main thread)


if __name__ == "__main__":
    main()