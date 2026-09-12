# -*- coding: utf-8 -*-
"""
acoustic_filter_engine.py
=========================
Production-Grade Acoustic Human Bio-Sensing & Intelligent Far-Field Voice Filter for Real Jarvis.
"""

import os
import sys
import time
import math
import struct
import re
import array
from typing import Tuple, Dict, Any, Optional

try:
    import audioop
except ImportError:
    audioop = None

try:
    import config
except ImportError:
    config = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

_IS_WINDOWS = sys.platform.startswith("win")
if _IS_WINDOWS:
    import ctypes
    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]


class AcousticFilterEngine:
    """Intelligent audio filter, keystroke noise suppressor, and human paralinguistic detector."""

    def __init__(self):
        self.enabled = True
        self.keystroke_suppression_enabled = True
        self.far_field_agc_enabled = True
        self.paralinguistic_detection_enabled = True
        self.gain_multiplier = 2.4
        self.ambient_noise_floor = 120.0
        self._last_event_time = 0.0
        self._suppressed_keystrokes_count = 0
        self._paralinguistic_events_count = 0
        self._event_cooldown = 4.0
        self._mock_idle_time: Optional[float] = None

    def get_time_since_last_user_input(self) -> float:
        """Returns elapsed seconds since last physical keyboard/mouse interaction."""
        if self._mock_idle_time is not None:
            return self._mock_idle_time
        if _IS_WINDOWS:
            try:
                info = _LASTINPUTINFO()
                info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
                ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
                elapsed_ms = ctypes.windll.kernel32.GetTickCount() - info.dwTime
                return max(0.0, elapsed_ms / 1000.0)
            except Exception:
                return 999.0
        return 999.0

    def is_user_actively_typing(self, threshold_seconds: float = 0.50) -> bool:
        """True if user pressed a key or clicked within threshold_seconds."""
        return self.get_time_since_last_user_input() < threshold_seconds

    def extract_features(self, pcm_bytes: bytes, sample_rate: int = 16000) -> Dict[str, float]:
        """Calculates RMS, Peak amplitude, Crest Factor, Zero Crossing Rate, and Autocorrelation."""
        if not pcm_bytes or len(pcm_bytes) < 2:
            return {"rms": 0.0, "peak": 0.0, "crest": 0.0, "zcr": 0.0, "autocorr": 0.0, "duration": 0.0}

        num_samples = len(pcm_bytes) // 2
        duration = num_samples / float(sample_rate)

        samples = struct.unpack(f"{num_samples}h", pcm_bytes[:num_samples * 2])
        if not samples:
            return {"rms": 0.0, "peak": 0.0, "crest": 0.0, "zcr": 0.0, "autocorr": 0.0, "duration": 0.0}

        peak = max(abs(s) for s in samples)
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / float(num_samples))
        crest = (peak / (rms + 1e-6)) if rms > 0 else 0.0

        zcr_count = sum(1 for i in range(1, num_samples) if (samples[i] >= 0 and samples[i - 1] < 0) or (samples[i] < 0 and samples[i - 1] >= 0))
        zcr = zcr_count / float(num_samples)

        max_autocorr = 0.0
        if num_samples > 400 and rms > 50:
            step = max(1, num_samples // 1000)
            sub_samples = samples[::step]
            sub_n = len(sub_samples)
            if sub_n > 100:
                denom = sum(s * s for s in sub_samples)
                if denom > 1e-6:
                    for lag in range(16, min(100, sub_n // 2)):
                        dot = sum(sub_samples[i] * sub_samples[i + lag] for i in range(sub_n - lag))
                        r = dot / denom
                        if r > max_autocorr:
                            max_autocorr = r

        return {
            "rms": round(rms, 2),
            "peak": peak,
            "crest": round(crest, 2),
            "zcr": round(zcr, 4),
            "autocorr": round(max_autocorr, 4),
            "duration": round(duration, 3)
        }

    def is_keystroke_transient(self, pcm_bytes: bytes, sample_rate: int = 16000, text: str = "") -> bool:
        """Determines whether the captured audio is a keyboard click or mechanical transient."""
        if not self.keystroke_suppression_enabled:
            return False

        feats = self.extract_features(pcm_bytes, sample_rate)
        idle_time = self.get_time_since_last_user_input()
        is_typing = idle_time < 0.45

        clean_text = text.strip().lower()
        noise_syllables = {
            "k", "t", "c", "d", "p", "f", "s", "sh", "ch", "th", "g", "b", "m", "n",
            "the", "uh", "um", "ah", "click", "tap", "space", "enter", "key", "typing",
            "a", "i", "o", "u", "e", "tu", "ko", "ki", "ka", "se", "pe", "."
        }
        
        if is_typing and (clean_text in noise_syllables or len(clean_text) <= 2):
            self._suppressed_keystrokes_count += 1
            return True

        if feats["duration"] <= 0.08 and feats["crest"] >= 4.0:
            self._suppressed_keystrokes_count += 1
            return True

        if is_typing and feats["crest"] > 3.8 and feats["duration"] < 0.40:
            self._suppressed_keystrokes_count += 1
            return True

        return False

    def apply_far_field_agc(self, pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
        """Dynamically boosts far-field quiet vocal signals (2.0x - 3.2x) with a smooth soft limiter."""
        if not self.far_field_agc_enabled or not pcm_bytes:
            return pcm_bytes

        num_samples = len(pcm_bytes) // 2
        if num_samples == 0:
            return pcm_bytes

        samples = struct.unpack(f"{num_samples}h", pcm_bytes[:num_samples * 2])
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / float(num_samples)) if num_samples > 0 else 0.0

        if rms < 300:
            gain = 3.0
        elif rms < 800:
            gain = 2.2
        elif rms < 1500:
            gain = 1.4
        else:
            gain = 1.0

        amplified = []
        max_limit = 32760
        for s in samples:
            val = s * gain
            if abs(val) > max_limit:
                val = math.copysign(max_limit, val)
            amplified.append(int(val))

        return struct.pack(f"{len(amplified)}h", *amplified)

    def detect_paralinguistic_event(self, pcm_bytes: bytes, text: str = "") -> Dict[str, Any]:
        """Identifies non-speech emotional / physical human acoustic events (Yawn, Laugh, Hum, Cry)."""
        if not self.paralinguistic_detection_enabled:
            return {"event": "none", "confidence": 0.0, "message": ""}

        now = time.time()
        if now - self._last_event_time < self._event_cooldown:
            return {"event": "none", "confidence": 0.0, "message": ""}

        feats = self.extract_features(pcm_bytes)
        clean_text = text.lower().strip()

        # 1. YAWNING / TIRED EXHALATION
        yawn_phrases = ("yawn", "[sigh]", "aahh", "oohhh", "ubasi", "jamhai", "thak gaya", "thak gayi", "neend aa rahi")
        is_yawn_text = any(p in clean_text for p in yawn_phrases)
        is_yawn_acoustic = (feats["duration"] >= 2.0 and feats["zcr"] < 0.12 and 120 < feats["rms"] < 1400 and feats["autocorr"] > 0.35 and not clean_text)

        if is_yawn_text or is_yawn_acoustic:
            self._last_event_time = now
            self._paralinguistic_events_count += 1
            return {
                "event": "yawning",
                "confidence": 0.88 if is_yawn_text else 0.75,
                "emotion": "caring",
                "message": "Boss, badi lambi ubasi li aapne! Kaafi der se kaam kar rahe hain. Kya main 5 minute ka relax break timer laga doon ya ek energetic song play kar doon?"
            }

        # 2. CRYING / DISTRESS (Check before laughing)
        cry_phrases = ("[crying]", "[sniffle]", "sob", "ro raha", "ro rahi", "rona aa raha", "bohot dard", "udas hoon")
        is_cry_text = any(p in clean_text for p in cry_phrases)
        if is_cry_text:
            self._last_event_time = now
            self._paralinguistic_events_count += 1
            return {
                "event": "crying_distress",
                "confidence": 0.85,
                "emotion": "concerned",
                "message": "Boss, kya hua? Aap pareshan lag rahe hain. Sab theek ho jaayega, main hamesha aapke sath hoon. Agar kuch baat karni ho toh batayein."
            }

        # 3. LAUGHING / CHUCKLING
        laugh_phrases = ("hahaha", "hehehe", "hahah", "haha", "hehe", "[laughter]", "lol", "lmao", "rofl", "khilkhilana")
        is_laugh_text = any(p in clean_text for p in laugh_phrases) or bool(re.search(r"\b(ha){2,}\b|\b(he){2,}\b", clean_text))
        is_laugh_acoustic = (feats["crest"] > 4.2 and feats["zcr"] > 0.14 and feats["rms"] > 350 and 0.30 < feats["autocorr"] < 0.65 and not clean_text)

        if is_laugh_text or is_laugh_acoustic:
            self._last_event_time = now
            self._paralinguistic_events_count += 1
            return {
                "event": "laughing",
                "confidence": 0.92 if is_laugh_text else 0.78,
                "emotion": "happy",
                "message": "Aapki hasi sunkar maza aa gaya boss! Lagta hai koi bohot zabardast joke ya funny cheez mili hai!"
            }

        # 4. SINGING / HUMMING
        sing_phrases = ("[music]", "la la la", "la la", "hmm hmm", "hmmm hmmm", "singing", "gungunana", "sa re ga ma", "sur")
        is_sing_text = any(p in clean_text for p in sing_phrases)
        is_sing_acoustic = (feats["autocorr"] >= 0.65 and feats["zcr"] < 0.10 and feats["duration"] >= 1.4 and feats["rms"] > 150)

        if is_sing_text or is_sing_acoustic:
            self._last_event_time = now
            self._paralinguistic_events_count += 1
            return {
                "event": "singing_humming",
                "confidence": 0.90 if is_sing_text else 0.82,
                "emotion": "excited",
                "message": "Wah boss! Kya khoob sur lagaye hain! Gaane ka mood ho toh batayein, Spotify par aapke manpasand gaane chala doon?"
            }

        return {"event": "none", "confidence": 0.0, "message": ""}

    def get_diagnostics(self) -> Dict[str, Any]:
        """Returns live statistics of keystroke rejections and acoustic state."""
        return {
            "keystroke_suppression_enabled": self.keystroke_suppression_enabled,
            "far_field_agc_enabled": self.far_field_agc_enabled,
            "paralinguistic_detection_enabled": self.paralinguistic_detection_enabled,
            "gain_multiplier": self.gain_multiplier,
            "suppressed_keystrokes_count": self._suppressed_keystrokes_count,
            "paralinguistic_events_count": self._paralinguistic_events_count,
            "time_since_last_input_sec": round(self.get_time_since_last_user_input(), 2)
        }


acoustic_filter = AcousticFilterEngine()
