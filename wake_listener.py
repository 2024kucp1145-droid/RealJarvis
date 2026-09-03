# -*- coding: utf-8 -*-
"""
wake_listener.py
=================
Upgraded WakeListener wrapper around the Ultra-Fast Edge WakeEngine.
Supports instant on-device wake-word detection, visual cues, and futuristic activation sound.
"""

import threading
import time
import config
from wake_engine import wake_engine, WakeEngine


class WakeListener:
    """High-performance edge wake listener for Jarvis."""

    def __init__(self, voice, gui=None):
        self.voice = voice
        self.gui = gui
        self.engine = wake_engine
        if self.gui:
            self.engine.gui = self.gui

    def start(self):
        """Starts the background wake engine."""
        self.engine.start()

    def stop(self):
        """Stops the wake engine."""
        self.engine.stop()

    def pause(self):
        """Pauses wake listening during active command sessions."""
        self.engine.pause()

    def resume(self):
        """Resumes wake listening when idle."""
        self.engine.resume()

    def wait_for_wake(self, timeout=None):
        """Blocks until a wake event is fired."""
        return self.engine.wait_for_wake(timeout=timeout)

    def trigger_now(self):
        """Forces an immediate wake trigger."""
        self.engine.trigger_now()