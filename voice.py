# -*- coding: utf-8 -*-
"""
voice.py
========
Jarvis ki awaaz aur kaan. Bolna (TTS) aur sunna (STT) - dono yahan.

TTS: pyttsx3 offline hai (Windows SAPI5 voice se), lekin uski Hindi/quality
laptop pe install hindi voice pack pe depend karti hai. Jab internet ho, hum
edge-tts use karte hain jo Microsoft ki natural "hi-IN-SwaraNeural" (pyaari
ladki wali) awaaz deta hai - bahut better sunayi deta hai. TTS_MODE="auto"
rakhoge toh dono ka best mila milega.
"""

import os
import io
import socket
import tempfile
import asyncio
import uuid
import time
import threading

import config

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    import audioop
except ImportError:      # Python 3.13+ me audioop hata diya gaya
    audioop = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import playsound
except ImportError:
    playsound = None

try:
    import pygame
except ImportError:
    pygame = None

try:
    import sounddevice as sd
    import numpy as np
except (ImportError, OSError):
    # sounddevice pip package can import successfully but still raise
    # OSError('PortAudio library not found') if the native lib is missing
    # on the system - treat that the same as "not installed" so barge-in
    # just quietly falls back instead of crashing the whole module.
    sd = None
    np = None


import time
_last_net_check = 0
_last_net_result = False

# Quota/auth fail ke baad ElevenLabs ko skip karo — warna har sentence silent ho jaati hai.
_ELEVENLABS_COOLDOWN_UNTIL = 0.0
_ELEVENLABS_QUOTA_CODES = {401, 402, 403, 429}

# ── OUTPUT GAIN ──────────────────────────────────────────────────────────
# Female awaaz dheemi thi. Gain do jagah lagta hai:
#   1) edge-tts ka SSML volume param  (TTS_VOLUME, e.g. "+45%")
#   2) pygame mixer ka software volume (TTS_MIXER_GAIN, 0.0-1.0)
def _tts_volume_str() -> str:
    """edge-tts ke liye SSML volume string, e.g. '+45%'."""
    raw = getattr(config, "TTS_VOLUME", "+0%")
    if raw is None:
        return "+0%"
    s = str(raw).strip()
    if not s:
        return "+0%"
    if not s.endswith("%"):
        s += "%"
    if not s.startswith(("+", "-")):
        s = "+" + s
    return s


def _apply_mixer_gain() -> None:
    """pygame mixer par output gain lagaata hai (0.0-1.0)."""
    if not pygame:
        return
    try:
        gain = float(getattr(config, "TTS_MIXER_GAIN", 1.0))
        gain = max(0.0, min(1.0, gain))
        pygame.mixer.music.set_volume(gain)
    except Exception:
        pass


_FFMPEG_PATH = None


def _find_ffmpeg():
    """System ffmpeg, warna imageio_ffmpeg ka bundled binary."""
    global _FFMPEG_PATH
    if _FFMPEG_PATH:
        return _FFMPEG_PATH
    import shutil
    exe = shutil.which("ffmpeg")
    if not exe:
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            exe = None
    if exe and os.path.exists(exe):
        _FFMPEG_PATH = exe
        return exe
    return None


def _boost_audio_gain(mp3_bytes: bytes) -> bytes:
    """
    REAL output gain — MP3 decode karke samples amplify karta hai, phir WAV
    me wapas deta hai (pygame WAV natively play karta hai).

    Ye zaroori hai kyunki edge-tts / Microsoft ka `volume` param neural voices
    par bilkul KAAM NAHI karta — measurement me -50% se +100% tak ke beech
    decoded RMS ka spread sirf 1.06 tha (yaani koi farak hi nahi).

    `tanh` soft-clip lagaya gaya hai taaki gain badhane par hard clipping
    ya crackling na aaye.

    Direct ffmpeg CLI use hoti hai (pydub nahi) — pydub `ffprobe` binary
    maangta hai jo imageio ke bundle me nahi hota, isliye wo fail ho jata tha.
    """
    gain = float(getattr(config, "TTS_AUDIO_GAIN", 1.0))
    if gain <= 1.01 or not mp3_bytes or np is None:
        return mp3_bytes

    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        print("[voice] ffmpeg not available — skipping output gain")
        return mp3_bytes

    try:
        import subprocess
        import wave

        raw = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error",
             "-i", "pipe:0", "-f", "s16le", "-acodec", "pcm_s16le",
             "-ar", "44100", "-ac", "2", "pipe:1"],
            input=mp3_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if raw.returncode != 0 or not raw.stdout:
            print(f"[voice] ffmpeg decode failed: {raw.stderr[:120]!r}")
            return mp3_bytes

        pcm = np.frombuffer(raw.stdout, dtype=np.int16).astype(np.float32) / 32768.0
        if pcm.size == 0:
            return mp3_bytes

        amplified = np.tanh(pcm * gain)                    # soft clip
        out = (amplified * 32767.0).astype(np.int16)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(out.tobytes())
        return buf.getvalue()
    except Exception as e:
        print(f"[voice] output gain skipped ({e}) — playing original volume")
        return mp3_bytes

# ── SELF-HEARING GUARD ──────────────────────────────────────────────────────
# Jab Jarvis bol raha ho, tab mic BILKUL band rehti hai.
# Isse Jarvis apni hi awaaz sun ke khud trigger nahi karta.
IS_SPEAKING = False
_speech_end_time = 0.0
_speech_start_time = 0.0

def _mark_speaking_start():
    global IS_SPEAKING, _speech_start_time
    IS_SPEAKING = True
    _speech_start_time = time.time()

def _mark_speaking_end():
    global IS_SPEAKING, _speech_end_time
    IS_SPEAKING = False
    _speech_end_time = time.time()

def is_in_deaf_window() -> bool:
    """Self-hearing guard: Returns True if Jarvis is currently speaking or just finished within 0.35s."""
    if IS_SPEAKING:
        return True
    if time.time() - _speech_end_time < 0.35:
        return True
    return False

def has_internet(timeout=1.5) -> bool:
    global _last_net_check, _last_net_result
    now = time.time()
    if now - _last_net_check < 30:  # 30 sec tak cache rakho
        return _last_net_result
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        _last_net_result = True
    except OSError:
        _last_net_result = False
    _last_net_check = now
    return _last_net_result


def is_incomplete_thought(text: str) -> bool:
    """
    Capture-first incomplete-thought detector.

    Ye sirf ye batata hai ki sentence "shayad khuli abhi bhi hai" ya nahi.
    Ye KABHI decide nahi karta ki input process ho chuka hai — wo decision
    end-of-speech confirmation karta hai (Voice._confirm_end_of_speech).

    CRITICAL FIX (2026-09-27):
    Auxiliaries/verbs jo legitimately sentence END kar sakte hain — "hai", "tha",
    "thi", "the", "nahi", "hoga", "hogi", "hain" — in list me KABHI nahi hone
    chahiye. Pehle ye list me the, jiski wajah se "Jarvis aaj ka mausam kaisa hai"
    (poora, valid Hindi sentence) ko incomplete mark ho kar truncate ho raha tha.
    Google STT "hai" ko "is" likhta hai — isi se "linda is" jaise phantom aate the.

    Design note: galat "incomplete" bolna SAFE hai (extra der lagti hai).
    Galat "complete" bolna UNSAFE hai (input kat jaata hai). Isliye bias
    hamesha "incomplete" ki taraf rakha gaya hai.
    """
    if not text:
        return False
    words = text.strip().lower().split()
    if not words:
        return False

    last_word = words[-1].strip(".,?!:;-")
    first_word = words[0].strip(".,?!:;-")
    lowered = text.lower()

    # Sirf woh words jo SACH MEIN sentence ke end pe nahi lag sakte —
    # conjunctions, subordinators aur prepositions. Verb/noun/auxiliary NAHI.
    TRAILING_CONNECTORS = {
        # Hindi / Hinglish conjunctions & subordinators
        "aur", "lekin", "par", "kyunki", "kyuki", "matlab", "jaise", "jaisa",
        "agar", "jab", "waise", "yani", "taki", "bina", "jabki", "isliye",
        "magar", "ya", "yaa", "toh", "tab", "sirf", "bhi", "hi", "to",
        # Hindi / Hinglish prepositions
        "ki", "ke", "ko", "se", "pe", "mein", "me", "ka", "apne", "apni", "apna",
        # English conjunctions & subordinators
        "and", "or", "but", "because", "so", "that", "if", "when", "while",
        "though", "although", "since", "unless", "whereas", "plus", "also",
        # English prepositions
        "with", "about", "for", "from", "into", "onto", "over", "under", "between",
        "of", "in", "on", "at", "to", "by", "as", "near", "than", "during",
    }
    if last_word in TRAILING_CONNECTORS:
        return True

    # Trailing filler sunaayi dete hain ki user soch raha hai
    TRAILING_FILLERS = {
        "umm", "ummm", "uhh", "uhm", "hmm", "err", "ahh", "huh",
        "ruko", "ruk", "sochne", "soch", "dekho", "suno", "sunao",
        "ek second", "ek minute", "ek second ruko", "sochne do",
        "wait", "hang on", "hold on", "let me think", "one second",
    }
    if any(lowered.rstrip(" .,?!:;-").endswith(m) for m in TRAILING_FILLERS):
        return True

    # Question starter + bahut kam words = sentence abhi shuru hi hua hai.
    # 3 se zyada words ho toh sentence chal raha hai, chhod do.
    QUESTION_STARTERS = {
        "kya", "kaise", "kyun", "kyu", "kab", "kahan", "kaun", "kahan",
        "what", "how", "why", "when", "where", "who", "which", "whose",
    }
    COMPLETE_QUESTION_ENDS = {
        "jarvis", "ho", "hai", "hain", "tha", "thi", "the", "hoga", "hogi",
        "batao", "bata", "you", "this", "that", "it", "me", "karo", "do",
    }
    if first_word in QUESTION_STARTERS and len(words) <= 3:
        if last_word not in COMPLETE_QUESTION_ENDS:
            return True

    # Bahut chhoti utterance (1-2 words) jo terminal action verb par end
    # nahi hoti — sambhavit hai ki abhi aage kuch aane wala hai.
    TERMINAL_ACTION_VERBS = {
        "kholo", "chalu", "band", "batao", "dikhao", "sunao", "status", "screenshot",
        "help", "lo", "le", "karo", "do", "bhejo", "send", "stop", "exit", "quit",
        "start", "open", "close", "sleep", "so", "banao", "chalao", "padho", "read",
        "type", "likho", "search", "play", "pause", "mute", "unmute", "save",
        "commit", "lock", "haan", "nahi", "theek", "ok", "okay", "yes", "no", "done",
        "bye", "thanks", "shukriya", "bata", "chahiye", "chahta", "chahti", "dena",
        "lena", "likhna", "bolna", "karna", "jao", "ayiye", "chal", "shuru",
    }
    if len(words) <= 2 and last_word not in TERMINAL_ACTION_VERBS:
        return True

    return False


def is_thought_complete(text: str) -> bool:
    """
    True agar sentence structurally lagti hai complete.

    NOTE: Ye sirf ek HINT hai. Capture-first design me isko koi bhi "ab process
    karo" decision ke liye seedha use nahi kiya jata — end-of-speech
    confirmation (Voice._confirm_end_of_speech) hi final authority hai.
    """
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False

    # Clear terminal punctuation — strong signal
    if stripped[-1] in ".?!।":
        return True

    words = stripped.lower().split()
    if not words:
        return False

    # Terminal verb ke baad >= 4 words
    TERMINAL_ACTION_VERBS = {
        "kholo", "chalu", "band", "batao", "dikhao", "sunao", "status", "screenshot",
        "help", "lo", "le", "karo", "do", "bhejo", "send", "stop", "exit", "quit",
        "start", "open", "close", "sleep", "so", "banao", "chalao", "padho", "read",
        "type", "likho", "search", "play", "pause", "mute", "unmute", "save",
        "commit", "lock", "haan", "nahi", "theek", "ok", "okay", "yes", "no", "done",
        "bye", "thanks", "shukriya", "bata", "chahiye", "chahta", "chahti", "dena",
        "lena", "likhna", "bolna", "karna", "jao", "ayiye", "chal", "shuru",
    }
    if len(words) >= 4 and words[-1].strip(".,?!:;-") in TERMINAL_ACTION_VERBS:
        return True
    return False


class Voice:
    def __init__(self):
        self.recognizer = sr.Recognizer() if sr else None
        if self.recognizer:
            self._apply_capture_profile()
        self._calibrated = False
        self._last_calibration_time = 0.0               # Track when we last calibrated
        self._ambient_energy = None                     # Measured room noise floor
        self._noise_estimate = None                     # Adaptive floor (see _noise_floor)
        self._speech_lock = threading.Lock()
        self._silence_streak = 0                        # consecutive silent windows
        if pygame:
            try:
                pygame.mixer.init()
                _apply_mixer_gain()
            except Exception as e:
                print(f"[pygame mixer init fail: {e}]")

    def _apply_capture_profile(self):
        """
        Recognizer ko CAPTURE-FIRST profile me set karta hai.

        SpeechRecognition ke do knobs hi truncation ka main source the:
          - pause_threshold: is se bada gap aaye to SR utterance finalize kar deta
            hai. 0.8s bahut chhota tha — beech me sochne par baat kat rahi thi.
          - non_speaking_duration: pause ke baad finalization buffer.
        Dono ab bohot generous hain, aur dynamic energy ratio bhi relaxed hai taaki
        kamzor/door ki awaaz threshold se upar nahi nikal jaaye.

        !!! CRITICAL — energy_threshold yahan RESET NAHI karni hai !!!
        Kisi pehle version ne har window pe `energy_threshold = 150` likha diya,
        jisse `adjust_for_ambient_noise()` ka calibrated value har 1.5s me mit
        jaata tha. Room ka ambient noise (~500-700) hamesha 150 se upar rehta,
        to `pause_threshold=1.8` kabhi satisfy nahi hota tha aur SR HAMESHA ke
        liye block ho jata tha — Jarvis na sunta, na reply karta.
        Ab calibration ko ZAROOR preserve karte hain.
        """
        if not self.recognizer:
            return
        self.recognizer.pause_threshold = getattr(config, "MIC_PAUSE_THRESHOLD", 1.8)
        self.recognizer.non_speaking_duration = getattr(config, "MIC_NON_SPEECHING_DURATION", 0.7)
        self.recognizer.dynamic_energy_threshold = getattr(config, "MIC_DYNAMIC_ENERGY", True)
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = getattr(config, "MIC_DYNAMIC_ENERGY_RATIO", 1.2)
        # Energy threshold ko chhodo — wo ambient calibration ka result hai.
        # Sirf tab set karo jab recognizer naya hai aur value 0/unset ho.
        if not getattr(self.recognizer, "energy_threshold", 0):
            self.recognizer.energy_threshold = 150


    # ---------------------------------------------------------------- speak
    EMOTION_PROSODY = {
        # (rate, pitch) - edge-tts format: "+N%"/"-N%" aur "+NHz"/"-NHz"
        # Khoobsoorat, soft, melodious aur natural female tone ke liye optimized
        "happy":     ("+4%", "+18Hz"),
        "excited":   ("+10%", "+26Hz"),
        "sad":       ("-10%", "-12Hz"),
        "concerned": ("-4%",  "+6Hz"),
        "calm":      ("+0%",  "+12Hz"),
        "serious":   ("-3%",  "+2Hz"),
    }

    @staticmethod
    def _apply_rate_offset(rate: str) -> str:
        """Applies global TTS_RATE_OFFSET on top of emotion rate for a sweeter, relaxed delivery."""
        offset = getattr(config, "TTS_RATE_OFFSET", "-6%")
        try:
            b = int(rate.replace('%', '').replace('+', ''))
            o = int(offset.replace('%', '').replace('+', ''))
            total = b + o
            return f"+{total}%" if total >= 0 else f"{total}%"
        except Exception:
            return rate

    def speak(self, text: str, interruptible: bool = True, emotion: str = "calm",
              is_first_chunk: bool = True) -> bool:
        """
        Bolta hai, emotion ke hisaab se tone/speed thodi badal jaati hai.
        Agar interruptible=True aur user beech me bolna shuru kar de, turant
        ruk jaata hai aur True return karta hai (matlab "interrupted").

        is_first_chunk: agar ek hi jawab (streaming) ke kayi sentences bol
        rahe ho, sirf PEHLE sentence pe "grace period" lagao - baaki sentences
        turant interruptible hone chahiye, warna lambe jawab me kabhi interrupt
        hi nahi kar paoge (grace period har naye sentence pe reset ho jaata).
        """
        try:
            from interview_mode import interview_mode as _imode
            if _imode.is_active:
                return False
        except Exception:
            pass

        with self._speech_lock:
            print(f"Jarvis [{emotion}]: {text}")
            _mark_speaking_start()
            try:
                mode = str(getattr(config, "TTS_MODE", "edge") or "edge").strip().lower()
                online = has_internet()
                rate, pitch = self.EMOTION_PROSODY.get(emotion, self.EMOTION_PROSODY["calm"])
                rate = self._apply_rate_offset(rate)

                # ElevenLabs sirf tab jab explicitly auto/elevenlabs ho — quota fail par
                # False return silent crash tha; ab None = fallback Edge unlimited.
                want_elevenlabs = (
                    mode in ("auto", "elevenlabs")
                    and getattr(config, "ELEVENLABS_API_KEY", "").strip()
                    and online
                    and time.time() >= _ELEVENLABS_COOLDOWN_UNTIL
                )
                if want_elevenlabs:
                    try:
                        el_result = self._speak_elevenlabs(
                            text, emotion=emotion, interruptible=interruptible
                        )
                        if el_result is not None:
                            return el_result
                    except Exception as _e_el:
                        print(f"[voice] ElevenLabs playback failed: {_e_el}, falling back to Neural voice")

                use_online = (mode in ("online", "edge", "auto", "elevenlabs")) and online
                if use_online and edge_tts:
                    try:
                        import streaming_audio_engine
                        return streaming_audio_engine.streaming_engine.speak_streaming(
                            text, emotion=emotion, interruptible=interruptible
                        )
                    except Exception as e:
                        print(f"[streaming audio engine fail, fallback to standard: {e}]")
                        try:
                            return self._speak_online_interruptible(text, rate, pitch, is_first_chunk)
                        except Exception as e2:
                            print(f"[edge interruptible TTS fail: {e2}]")

                self._speak_offline(text, emotion)
                return False
            finally:
                _mark_speaking_end()

    def _speak_elevenlabs(self, text: str, emotion: str = "calm", interruptible: bool = True):
        """ElevenLabs stream. Success: bool interrupted. Fail: None so caller Edge TTS use kare."""
        global _ELEVENLABS_COOLDOWN_UNTIL
        api_key = getattr(config, "ELEVENLABS_API_KEY", "").strip()
        if not api_key:
            return None

        voice_id = getattr(config, "ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
        model_id = getattr(config, "ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability":         getattr(config, "ELEVENLABS_STABILITY",        0.65),  # 0.65 = stable, clean
                "similarity_boost":  getattr(config, "ELEVENLABS_SIMILARITY_BOOST", 0.85),  # closer to Jessica's real voice
                "style":             getattr(config, "ELEVENLABS_STYLE",             0.35),  # warmth & expressiveness
                "speed":             getattr(config, "ELEVENLABS_SPEED",             0.90),  # 0.90 = thoda slow = meethi madhur
                "use_speaker_boost": True
            }
        }

        try:
            import requests
            import io
            print("[voice] Synthesizing via ElevenLabs Ultra-Realistic AI Engine...")
            resp = requests.post(url, json=payload, headers=headers, stream=True, timeout=12)
            if resp.status_code != 200:
                print(f"[elevenlabs] API returned HTTP {resp.status_code}: {resp.text[:120]}, falling back to Neural voice")
                if resp.status_code in _ELEVENLABS_QUOTA_CODES:
                    _ELEVENLABS_COOLDOWN_UNTIL = time.time() + 86400
                    print("[voice] ElevenLabs quota/auth — 24h cooldown, unlimited Edge neural voice on.")
                return None

            audio_buf = io.BytesIO()
            for chunk in resp.iter_content(chunk_size=4096):
                if chunk:
                    audio_buf.write(chunk)
            audio_buf.seek(0)
            if audio_buf.getbuffer().nbytes < 64:
                print("[elevenlabs] Empty audio body, falling back to Neural voice")
                return None

            audio_buf.name = "jarvis_el.mp3"
            pygame.mixer.music.load(audio_buf)
            pygame.mixer.music.play()

            interrupted = False
            start_time = time.time()
            barge_enabled = getattr(config, "BARGE_IN_ENABLED", False)
            grace_period = getattr(config, "BARGE_IN_GRACE_SECONDS", 0.40)
            barge_threshold = getattr(config, "BARGE_IN_THRESHOLD", 0.035)
            sustain_blocks = getattr(config, "BARGE_IN_SUSTAIN_BLOCKS", 4)
            consecutive_loud = 0

            def mic_callback(indata, frames, time_info, status):
                nonlocal interrupted, consecutive_loud
                if time.time() - start_time < grace_period:
                    return
                vol = float(np.linalg.norm(indata) / len(indata)) if len(indata) else 0.0
                if vol > barge_threshold:
                    consecutive_loud += 1
                else:
                    consecutive_loud = 0
                if consecutive_loud >= sustain_blocks:
                    interrupted = True
                    print("[voice] INSTANT BARGE-IN TRIGGERED ON ELEVENLABS STREAM!")

            mic_stream = None
            if interruptible and barge_enabled and sd and np:
                try:
                    mic_stream = sd.InputStream(channels=1, samplerate=16000, blocksize=1024, callback=mic_callback)
                    mic_stream.start()
                except Exception:
                    mic_stream = None

            try:
                while pygame.mixer.music.get_busy():
                    if interrupted:
                        pygame.mixer.music.stop()
                        break
                    time.sleep(0.02)
            finally:
                if mic_stream:
                    try:
                        mic_stream.stop()
                        mic_stream.close()
                    except Exception:
                        pass
                pygame.mixer.music.unload()

            return interrupted

        except Exception as e:
            print(f"[elevenlabs] Error: {e}, falling back to Neural voice")
            return None

    def _edge_voice_list(self):
        voices = []
        primary = getattr(config, "ONLINE_VOICE", "en-IN-NeerjaExpressiveNeural")
        voices.append(primary)
        for v in getattr(config, "EDGE_VOICE_FALLBACKS", []):
            if v and v not in voices:
                voices.append(v)
        return voices

    def _speak_online(self, text: str, rate: str = "+0%", pitch: str = "+0Hz"):
        """
        Streaming TTS:
        1. edge-tts se audio chunks seedha memory buffer (BytesIO) me stream hote hain
        2. Buffer ready hote hi pygame se directly play — disk pe kuch likhna nahi padta
        3. Isse ~1 second ka pre-generation + disk write ka delay khatam ho jaata hai

        ffmpeg ya pydub ki zaroorat nahi — pygame MP3 natively support karta hai.
        """
        import io

        audio_buffer = io.BytesIO()
        _vol = _tts_volume_str()

        async def _stream_to_buffer():
            last_err = None
            for voice_name in self._edge_voice_list():
                try:
                    communicate = edge_tts.Communicate(text, voice_name, rate=rate, pitch=pitch, volume=_vol)
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_buffer.write(chunk["data"])
                    if audio_buffer.tell() > 0:
                        return
                except Exception as err:
                    last_err = err
                    audio_buffer.seek(0)
                    audio_buffer.truncate(0)
                    print(f"[edge-tts] voice {voice_name} failed: {err}")
            if last_err:
                raise last_err

        asyncio.run(_stream_to_buffer())
        audio_buffer.seek(0)
        # Real output gain (edge-tts volume param neural voices par kaam nahi karta)
        boosted = _boost_audio_gain(audio_buffer.getvalue())
        audio_buffer = io.BytesIO(boosted)
        audio_buffer.name = "jarvis_edge.wav"

        # pygame se directly BytesIO play karo (no temp file)
        if pygame:
            try:
                pygame.mixer.music.load(audio_buffer)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.03)
                pygame.mixer.music.unload()
                return
            except Exception as e:
                print(f"[pygame stream play failed: {e}], fallback to temp file]")

        # --- Fallback: temp file se play karo ---
        audio_buffer.seek(0)
        out_path = os.path.join(tempfile.gettempdir(), f"jarvis_speech_{uuid.uuid4().hex}.mp3")
        with open(out_path, "wb") as f:
            f.write(audio_buffer.read())
        if playsound:
            playsound.playsound(out_path)
        else:
            os.startfile(out_path)
        try:
            os.remove(out_path)
        except OSError:
            pass



    OFFLINE_RATE_ADJUST = {
        "happy": 25, "excited": 45, "sad": -25, "concerned": -15, "calm": 0, "serious": -10,
    }

    _offline_engine = None

    def _speak_offline(self, text: str, emotion: str = "calm"):
        # Try platform_compat espeak-ng path first (Linux)
        try:
            from platform_compat import offline_speak as _compat_speak, IS_LINUX
            if IS_LINUX:
                _compat_speak(text, rate=config.SPEECH_RATE)
                return
        except ImportError:
            pass

        if not pyttsx3:
            print("[TTS engine available nahi hai]")
            return

        com_initialized = False
        try:
            import pythoncom
            pythoncom.CoInitialize()
            com_initialized = True
        except ImportError:
            pass

        try:
            if self._offline_engine is None:
                self._offline_engine = pyttsx3.init()
                for v in self._offline_engine.getProperty("voices"):
                    name = (v.name or "").lower()
                    if "hindi" in name or "female" in name or "zira" in name or "heera" in name:
                        self._offline_engine.setProperty("voice", v.id)
                        break

            rate_adjust = self.OFFLINE_RATE_ADJUST.get(emotion, 0)
            self._offline_engine.setProperty("rate", config.SPEECH_RATE + rate_adjust)
            self._offline_engine.say(text)
            self._offline_engine.runAndWait()
        except Exception as e:
            print(f"[offline TTS error: {e}]")
            self._offline_engine = None  # next time naya ban jayega

        finally:
            if com_initialized:
                import pythoncom
                pythoncom.CoUninitialize()

    def _speak_online_interruptible(self, text: str, rate: str = "+0%", pitch: str = "+0Hz",
                                     is_first_chunk: bool = True) -> bool:
        """
        Streaming interruptible TTS:
        1. edge-tts se audio chunks stream hokar memory buffer me aate hain
        2. Poora buffer ready hote hi pygame se play shuru — disk I/O nahi
        3. Mic continuously monitor hoti hai — user bola toh turant ruk jao

        NOTE: Earphones ke saath best kaam karta hai.
        """
        import io

        audio_buffer = io.BytesIO()
        _vol = _tts_volume_str()

        # Stream audio chunks into memory buffer
        async def _stream_to_buf():
            last_err = None
            for voice_name in self._edge_voice_list():
                try:
                    communicate = edge_tts.Communicate(text, voice_name, rate=rate, pitch=pitch, volume=_vol)
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_buffer.write(chunk["data"])
                    if audio_buffer.tell() > 0:
                        return
                except Exception as err:
                    last_err = err
                    audio_buffer.seek(0)
                    audio_buffer.truncate(0)
                    print(f"[edge-tts] voice {voice_name} failed: {err}")
            if last_err:
                raise last_err

        asyncio.run(_stream_to_buf())
        audio_buffer.seek(0)
        # Real output gain (edge-tts volume param neural voices par kaam nahi karta)
        boosted = _boost_audio_gain(audio_buffer.getvalue())
        audio_buffer = io.BytesIO(boosted)
        audio_buffer.name = "jarvis_edge.wav"

        interrupted = False
        peak_volume = 0.0
        start_time = time.time()
        barge_enabled = getattr(config, "BARGE_IN_ENABLED", False)
        barge_threshold = getattr(config, "BARGE_IN_THRESHOLD", 0.035)
        grace_period = getattr(config, "BARGE_IN_GRACE_SECONDS", 0.40) if is_first_chunk else 0.20
        SUSTAIN_BLOCKS_NEEDED = getattr(config, "BARGE_IN_SUSTAIN_BLOCKS", 4)
        consecutive_loud = 0

        try:
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()

            def callback(indata, frames, time_info, status):
                nonlocal interrupted, peak_volume, consecutive_loud
                if interrupted:
                    return
                if time.time() - start_time < grace_period:
                    return
                volume = float(np.linalg.norm(indata) / len(indata)) if len(indata) else 0.0
                peak_volume = max(peak_volume, volume)
                if volume > barge_threshold:
                    consecutive_loud += 1
                else:
                    consecutive_loud = 0
                if consecutive_loud >= SUSTAIN_BLOCKS_NEEDED:
                    interrupted = True
                    print("[voice] INSTANT USER BARGE-IN INTERRUPTION DETECTED!")

            mic_stream = None
            if interruptible and barge_enabled and sd and np:
                try:
                    mic_stream = sd.InputStream(channels=1, samplerate=16000, blocksize=1024,
                                                 callback=callback)
                    mic_stream.start()
                except Exception:
                    mic_stream = None

            try:
                while pygame.mixer.music.get_busy():
                    if interrupted:
                        pygame.mixer.music.stop()
                        break
                    time.sleep(0.02)
            finally:
                if mic_stream:
                    try:
                        mic_stream.stop()
                        mic_stream.close()
                    except Exception:
                        pass

            pygame.mixer.music.unload()
            print(f"[barge-in: peak mic={peak_volume:.4f}, threshold={barge_threshold}, enabled={barge_enabled}]")
        except Exception as e:
            print(f"[interruptible stream error: {e}]")

        return interrupted


    # -------------------------------------------------------------- listen
    # -------------------------------------------------------------- listen
    #
    # CAPTURE-FIRST LISTENING
    # ======================
    # Invariants (in par regress mat karna):
    #   * _listen_raw_phrase() kabhi bhi akele acoustic verdict par "" nahi
    #     lautata. Wo sirf capture karta hai aur ADVISORY flag lagata hai.
    #   * Input tab process hota hai jab DEFINITIVE end-of-speech mile —
    #     yaani END_OF_SPEECH_CONFIRMATIONS consecutive silent windows.
    #   * Ek sochne wala pause streak ko reset karta hai, complete nahi karta.
    #   * Sentence beech me kabhi cut nahi hota (phrase_time_limit = None).

    #: Absolute safety net — chahe config galat set ho, capture kabhi
    #: bounded nahi hoga. 120s ek insaan ke liye ek saans mein
    #: practically sabse lambi sentence se bhi zyada hai.
    PHRASE_TIME_LIMIT_HARD_MAX = 120.0

    # ---- microphone selection state ----
    _mic_index = None                 # resolved device index (None = system default)
    _mic_detected_at = 0.0
    _mic_swing = 0.0

    @classmethod
    def _detect_best_microphone(cls, force: bool = False):
        """
        Sab input devices ko probe karke wo wala chunta hai jismein aapki
        awaaz sabse SAIF aati hai.

        Kyun zaroori hai: is machine par 5 input devices hain. Default (idx=1)
        ka signal swing sirf 395 hai — wo lagbhag sirf kamre ka shor pakadta
        hai, aapki awaaz nahi. Asli mic idx=4 ("Primary Sound Capture Driver")
        par hai jiska swing 3637 hai. Default pe sunne se Jarvis ko aapki awaaz
        hi nahi milti.

        Measurement: har device se 1.5s record karke (p90 - p10) nikalte hain.
        Ye "swing" batata hai ki signal kitna upar-neeche hil raha hai — asli
        bolne waali awaaz ka swing bada hota hai, flat/dead device ka zero.

        Dead device (swing ~0) aur khulne wale device skip ho jaate hain.
        """
        # Config se device resolve karo:
        #   "default" -> system default (None) — sabse safe
        #   "scan"    -> sab devices probe karke best
        #   <int>     -> forced index
        forced = getattr(config, "MICROPHONE_DEVICE_INDEX", "default")
        if isinstance(forced, str):
            low = forced.strip().lower()
            if low in ("default", "", "none", "system"):
                cls._mic_index = None
                return None
            if low != "scan":
                print(f"[voice] Unknown MICROPHONE_DEVICE_INDEX {forced!r}; using system default.")
                cls._mic_index = None
                return None
        else:
            try:
                cls._mic_index = int(forced)
                print(f"[voice] Microphone forced by config: index {cls._mic_index}")
                return cls._mic_index
            except (TypeError, ValueError):
                pass

        # --- scan mode ---
        # Cache use karo (device indices reboot/reconnect ke baad badalte hain)
        cache_min = getattr(config, "MIC_DETECT_CACHE_MINUTES", 30) * 60
        if (not force and cls._mic_index is not None
                and (time.time() - cls._mic_detected_at) < cache_min):
            return cls._mic_index

        if not (sd and np):
            return None

        try:
            import sounddevice as _sd
        except Exception:
            return None

        try:
            devices = [
                (i, d["name"]) for i, d in enumerate(_sd.query_devices())
                if d["max_input_channels"] > 0
            ]
        except Exception as e:
            print(f"[voice] Could not enumerate microphones: {e}")
            return None

        max_dev = getattr(config, "MIC_DETECT_MAX_DEVICES", 8)
        devices = devices[:max_dev]
        if not devices:
            return None

        dur = float(getattr(config, "MIC_DETECT_DURATION", 1.5))
        best_idx, best_swing, best_name = None, -1.0, ""
        print(f"[voice] Scanning {len(devices)} input devices for the clearest mic...")

        for idx, name in devices:
            try:
                stream = _sd.InputStream(
                    device=idx, channels=1, samplerate=16000, blocksize=1024,
                    dtype="float32",
                )
                stream.start()
                chunks = []
                deadline = time.time() + dur
                while time.time() < deadline:
                    data, _ = stream.read(1024)
                    chunks.append(float(np.sqrt(np.mean(np.square(data)))) * 32768.0)
                stream.stop()
                stream.close()
                if not chunks:
                    continue
                chunks.sort()
                p10 = chunks[int(len(chunks) * 0.10)]
                p90 = chunks[int(len(chunks) * 0.90)]
                swing = p90 - p10
                print(f"         idx={idx:<3} swing={swing:>7.0f}  {name[:40]}")
                # Dead/flat device (swing ~0) ko kabhi mat chuno.
                #
                # BUG: pehle `swing > 150` tha, jo is kamre me KABHI satisfy
                # nahi hua (measured: idx=0 → 91, idx=1 → 136, idx=4/5 → 0).
                # Isliye detection hamesha "no usable mic" bol kar system
                # default par gir jaati thi. Ab dead device (swing < 25) hi
                # reject hota hai, baaki me se sabse saaf wala jeeta.
                # NOTE: "Microsoft Sound Mapper" ek Windows VIRTUAL router hai.
                # Ye hamesha system default par route hota hai, jo aksar ek dead
                # ya galat device hota hai. Inhe KABHI choose mat karo — warna
                # scan sahi device dhoondhne ke bawajood galat input par settle
                # ho jaata hai aur STT ko sirf "ow ow ow" milta hai.
                if "sound mapper" in name.lower():
                    print("         -> skipped (Windows virtual router)")
                    continue

                # Dead/flat device (swing ~0) ko reject karo.
                if swing >= 25 and swing > best_swing:
                    best_idx, best_swing, best_name = idx, swing, name
            except Exception:
                continue

        if best_idx is None:
            print("[voice] No usable mic detected — falling back to system default.")
            return None

        # NOTE: "Microsoft Sound Mapper" upar ke loop me already skip ho jaata
        # hai, ye note sirf is baat ka yaad dilane ke liye hai ki ek virtual
        # router ko kabhi bhi winner na banne dena chahiye.

        # Winner ko persist karo — device indices reboot/reconnect ke baad
        # badal sakte hain, par ek baar accha mic mil jaaye to use yaad rakhna
        # behtar hai (detection har startup me 6-10s lega thi).
        persisted = cls._persist_mic_choice(best_idx, best_name, best_swing)
        if persisted:
            print(f"[voice] Saved mic choice to {persisted} for next start.")

        cls._mic_index = best_idx
        cls._mic_swing = best_swing
        cls._mic_detected_at = time.time()
        print(f"[voice] Using microphone idx={best_idx} ({best_name}) — swing={best_swing:.0f}")
        return best_idx

    @staticmethod
    def _persist_mic_choice(idx, name, swing):
        try:
            import json
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            os.makedirs(data_dir, exist_ok=True)
            path = os.path.join(data_dir, "best_microphone.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(
                    {"index": idx, "name": name, "swing": round(swing, 1),
                     "saved_at": time.time()},
                    fh, indent=2,
                )
            return path
        except Exception:
            return None

    @staticmethod
    def _load_persisted_mic_choice():
        try:
            import json
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            path = os.path.join(data_dir, "best_microphone.json")
            if not os.path.exists(path):
                return None
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
            return int(d["index"])
        except Exception:
            return None

    def _speech_energy_gate(self, source, duration: float = 0.6):
        """
        ACOUSTIC speech-presence test — STT se PEHLE.

        Ye batata hai ki audio me ASLI bolne wali awaaz hai ya sirf kamre ka
        shor. Text nahi dekhta, sirf energy dekhta — isliye STT ki
        "and gerdes jarreau" jaisi bakwaas par depend nahi karta.

        Ye zaroori tha kyunki pehle end-of-speech ka faisla STT ke output se
        hota tha. Kamre ka shor STT ko "and the what" jaisa garbage de deta
        tha, isliye confirmation kabhi trigger nahi hui aur Jarvis 4 minute
        tak 73 words ki bakwaas accumulate karta raha.

        Returns: (has_speech: bool, peak: float, p90: float)
        """
        try:
            audio = self.recognizer.record(source, duration=duration)
        except Exception:
            return True, 0.0, 0.0            # fail OPEN — kabhi speech mat chup karo

        raw = audio.get_raw_data()
        w = audio.sample_width
        if w < 1:
            return True, 0.0, 0.0
        blk = 1024 * w
        vals = []
        if audioop is not None:
            vals = [audioop.rms(raw[i:i + blk], w) for i in range(0, len(raw) - blk, blk)]
        elif np is not None:
            # Python 3.13+ fallback (audioop removed)
            usable = (len(raw) // blk) * blk
            if usable > 0:
                arr = np.frombuffer(raw[:usable], dtype=np.int16).astype(np.float32)
                arr = arr[: (len(arr) // 1024) * 1024].reshape(-1, 1024)
                vals = [float(np.sqrt(np.mean(np.square(c)))) for c in arr]
        if not vals:
            return False, 0.0, 0.0
        vals.sort()
        p90 = float(vals[int(len(vals) * 0.9)])
        peak = float(vals[-1])

        ambient = getattr(self, "_ambient_energy", None)
        if ambient is None:
            ambient = float(self.recognizer.energy_threshold or 0.0)
        ratio = float(getattr(config, "SPEECH_PRESENCE_RATIO", 1.6))
        # Awaaz ko ambient se saaf alag hona chahiye — warna shor speech ban jata hai
        has_speech = p90 > (ambient * ratio)
        return has_speech, peak, p90

    def _open_microphone(self):
        """
        Device-detected mic kholta hai. Detection fail ho jaaye to system
        default par gir jaata hai (purana behaviour).
        """
        idx = self._detect_best_microphone()
        try:
            if idx is not None:
                return sr.Microphone(device_index=idx)
            return sr.Microphone()
        except Exception as e:
            print(f"[voice] Mic open failed on idx={idx} ({e}); trying system default")
            return sr.Microphone()

    @classmethod

    def _resolve_phrase_time_limit(cls):
        """
        Returns a FINITE phrase_time_limit, always.

        !!! HANG SAFETY — ye kabhi None return NAHI karta !!!
        SpeechRecognition.listen(source, phrase_time_limit=None) tab tak
        record karta rehta hai jab tak pause_threshold (1.8s) ki silence na
        aaye. Kamre ka ambient noise us silence ko kabhi nahi aane deta, to
        SR hamesha ke liye block ho jata tha — user bolta rehta, Jarvis kuch
        nahi sunta, koi reply nahi aata.

        Isliye: config 0/None ho ya bahut bada ho, hard max par clamp karo.
        Sentence phir bhi kabhi beech me nahi kat-ta (purani limit 10s thi,
        ye 120s hai = 12x zyada), lekin infinite hang impossible hai.
        """
        raw = getattr(config, "LISTEN_PHRASE_TIME_LIMIT", 120.0)
        try:
            raw = float(raw)
        except (TypeError, ValueError):
            raw = 0.0
        if raw <= 0:                      # 0 / None / negative = "unlimited" maango
            return cls.PHRASE_TIME_LIMIT_HARD_MAX
        return min(raw, cls.PHRASE_TIME_LIMIT_HARD_MAX)

    def _is_definitive_artifact(self, raw_pcm: bytes, sample_rate: int, text: str) -> bool:
        """
        Sirf TABHI True jab captured audio DEFINITIVELY mechanical artifact hai.

        Deletion ke liye saare signals ek saath chahiye:
          1. Acoustic filter ka verdict (sharp crest, chhoti duration)
          2. Audio duration genuinely sub-100ms ho (insaan itna bolta hi nahi)
          3. User abhi typing kar raha ho
          4. Text ya to khali ho ya ek random non-word token ho

        Capture-first design me default ye hamesha False rahega — kyunki ek
        keyboard click ka pakka pata na chalega to user ka bolna delete karna
        galat hai. Sirf "us kaam ka nahi" bolna safe hai.
        """
        if not getattr(config, "KEYSTROKE_DROP_ALLOWED", False):
            return False
        try:
            from acoustic_filter_engine import acoustic_filter
            if not acoustic_filter.is_keystroke_transient(raw_pcm, sample_rate=sample_rate, text=text):
                return False
            feats = acoustic_filter.extract_features(raw_pcm, sample_rate)
        except Exception:
            return False

        if feats["duration"] > 0.10:
            return False
        if not acoustic_filter.is_user_actively_typing(1.25):
            return False
        return not text or len(text.strip()) <= 2

    def _listen_raw_phrase(self, timeout=None, phrase_time_limit=None) -> str:
        """
        Mic se ek capture window leta hai. Kabhi input DELETE nahi karta —
        sirf capture karta hai, transcribe karta hai, aur advisory flags
        diagnose log me likhta hai.
        """
        if not self.recognizer:
            return ""

        if timeout is None:
            timeout = getattr(config, "LISTEN_INITIAL_TIMEOUT", 20.0)
        if phrase_time_limit is None:
            phrase_time_limit = self._resolve_phrase_time_limit()

        try:
            with self._open_microphone() as source:
                # Recalibrate ambient noise on first use, and every 5 minutes after that
                now = time.time()
                needs_recalibrate = (
                    not self._calibrated or
                    (now - self._last_calibration_time) > 300
                )
                if needs_recalibrate:
                    cal_dur = float(getattr(config, "MIC_AMBIENT_CALIBRATION", 2.0))
                    self.recognizer.adjust_for_ambient_noise(source, duration=cal_dur)
                    self._calibrated = True
                    self._last_calibration_time = now
                    self._ambient_energy = self.recognizer.energy_threshold
                    print(f"[voice] Ambient calibrated. Energy threshold: {self._ambient_energy:.1f}")

                # ── SAFE THRESHOLD CLAMP ───────────────────────────────────
                # !!! HANG ROOT CAUSE !!!
                # Purana code threshold ko [MIC_ENERGY_MIN, MIC_ENERGY_MAX] me
                # clamp karta tha. Jab kamre ka ambient noise (e.g. 647) us
                # MAX (400) se upar hota, threshold 400 par gira diya gaya —
                # yaani room ka noise HAMESHA threshold se upar reh gaya.
                # Result: mic kabhi "silent" nahi hui, SpeechRecognition ka
                # pause_threshold kabhi satisfy nahi hua, aur LISTEN HANG ho
                # gayi. User bolta raha, Jarvis kuch nahi sunta / reply nahi.
                #
                # Ab clamp ko AMBIENT FLOOR se upar force karte hain: threshold
                # kabhi bhi measured noise se neeche nahi jayegi.
                ambient = getattr(self, "_ambient_energy", None)
                if ambient is None:
                    ambient = self.recognizer.energy_threshold
                floor = max(
                    getattr(config, "MIC_ENERGY_MIN", 50),
                    ambient * getattr(config, "MIC_ENERGY_FLOOR_RATIO", 0.8),
                )
                ceiling = max(getattr(config, "MIC_ENERGY_MAX", 2000), ambient * 2.0)
                if self.recognizer.energy_threshold < floor:
                    self.recognizer.energy_threshold = floor
                elif self.recognizer.energy_threshold > ceiling:
                    self.recognizer.energy_threshold = ceiling

                # Capture profile RE-APPLY karo — recognizer state har window me
                # drift kar sakta hai (dynamic energy adaptation).
                self._apply_capture_profile()

                # ── ACOUSTIC SPEECH GATE ───────────────────────────────────
                # STT call karne se PEHLE energy check. Agar audio me sirf
                # kamre ka shor hai to Google STT tak pahuche hi nahi —
                # warna woh "and the what" jaisa garbage dekar end-of-speech
                # detection tod deta tha aur Jarvis ghich accumulate karta raha.
                gate = float(getattr(config, "SPEECH_GATE_WINDOW", 0.6))
                if getattr(config, "SPEECH_GATE_ENABLED", True):
                    has_speech, peak, p90 = self._speech_energy_gate(source, duration=gate)
                    if not has_speech:
                        print(f"[voice] Gate: no speech energy (p90={p90:.0f}) — skipping STT.")
                        return ""

                try:
                    audio = self.recognizer.listen(
                        source, timeout=timeout, phrase_time_limit=phrase_time_limit
                    )
                except sr.WaitTimeoutError:
                    return ""
                except Exception as e:
                    print(f"[voice] capture error: {e}")
                    return ""
        except Exception as e:
            print(f"[voice] microphone unavailable: {e}")
            return ""

        raw_pcm = audio.get_raw_data()

        # Far-Field AGC pre-amp — HAMESHA chalta hai (jab tak capture-first off na ho).
        # Purana behaviour: typing ke dauraan AGC block ho jata tha, jisse door se
        # aayi hui dheemi awaaz bilkul sunayi nahi deti thi.
        try:
            from acoustic_filter_engine import acoustic_filter
            amplified_pcm = acoustic_filter.apply_far_field_agc(raw_pcm, sample_rate=audio.sample_rate)
            audio = sr.AudioData(amplified_pcm, audio.sample_rate, audio.sample_width)
        except Exception:
            pass

        # ---- STT ----
        return self._transcribe(audio=audio, raw_pcm=raw_pcm)

    def _transcribe(self, audio, raw_pcm: bytes = None) -> str:
        """
        Raw AudioData ko text me badalta hai. Mic open/close NAHI karta.

        Isliye end-of-speech ke dauraan jo audio milta hai (jab user bol raha
        hai), use yahan directly STT kar sakte hain bina mic dobara khologe.
        """
        if audio is None or not self.recognizer:
            return ""
        if raw_pcm is None:
            try:
                raw_pcm = audio.get_raw_data()
            except Exception:
                raw_pcm = b""

        # Far-Field AGC pre-amp — door se aayi dheemi awaaz ko deta hai
        try:
            from acoustic_filter_engine import acoustic_filter
            amplified_pcm = acoustic_filter.apply_far_field_agc(
                raw_pcm, sample_rate=audio.sample_rate
            )
            if amplified_pcm != raw_pcm:
                audio = sr.AudioData(amplified_pcm, audio.sample_rate, audio.sample_width)
        except Exception:
            pass

        mode = getattr(config, "STT_MODE", "auto")
        use_online = (mode == "google") or (mode == "auto" and has_internet())
        result_text = ""

        if use_online:
            for lang in getattr(config, "RECOGNITION_LANGUAGES", ["en-IN", "hi-IN"]):
                try:
                    res = self.recognizer.recognize_google(audio, language=lang)
                    if res and res.strip():
                        result_text = res.strip()
                        break
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    break
                except Exception:
                    continue
            if not result_text:
                result_text = self._recognize_offline_safe(audio)
        else:
            result_text = self._recognize_offline_safe(audio)

        result_text = (result_text or "").strip()

        # ---- ADVISORY ONLY: diagnosis, never deletion ----
        # Keystroke phantom ka pata lagane ke liye sirf log karte hain.
        # Capture-first policy kehta hai: user ka bolna KABHI delete nahi hoga.
        try:
            from acoustic_filter_engine import acoustic_filter
            advisory = acoustic_filter.is_keystroke_transient(
                raw_pcm, sample_rate=audio.sample_rate, text=result_text
            )
            if advisory and result_text:
                print(
                    f"[acoustic_filter:ADVISORY] '{result_text}' looks like a keystroke "
                    f"phantom — kept per CAPTURE-FIRST policy."
                )
        except Exception as e:
            print(f"[acoustic_filter check error: {e}]")

        # Last-resort destructive path — default OFF (KEYSTROKE_DROP_ALLOWED=False)
        if result_text and self._is_definitive_artifact(
            raw_pcm, audio.sample_rate, result_text
        ):
            print(f"[acoustic_filter] Definitive mechanical artifact dropped: '{result_text}'")
            return ""

        return result_text

    def _noise_floor(self) -> float:
        """
        Reference noise floor for speech-vs-silence decisions.

        Ambient calibration se start hota hai, aur phir QUIET windows dekh kar
        dheere-dheere adjust hota hai. Isse:
          - ek noisy frame (koi tap / door band) se floor nahi udhakta
          - lekin steady room tone me floor sahi level par settle ho jata hai
        """
        ambient = getattr(self, "_ambient_energy", None)
        if not ambient:
            ambient = getattr(self.recognizer, "energy_threshold", 0) or 0
        if not ambient:
            ambient = 300.0
        run = getattr(self, "_noise_estimate", None)
        if run is None:
            self._noise_estimate = ambient
            return ambient
        # Calibration se kabhi bahut upar nahi jaayega
        return min(ambient, run)

    def _measure_audio_energy(self, audio) -> tuple:
        """
        (has_speech, p90, peak) — pure ACOUSTIC decision, STT se bilkul independent.

        Ye hi function end-of-speech decide karta hai. Pehle decision STT ke
        output pe tha, jo noisy room me kabhi khali nahi hota — isliye Jarvis
        "still speaking" state me atak kar rah jati thi.
        """
        try:
            raw = audio.get_raw_data()
            w = audio.sample_width
        except Exception:
            return False, 0.0, 0.0
        if not raw or w < 1:
            return False, 0.0, 0.0

        blk = 1024 * w
        vals = []
        if audioop is not None:
            vals = [audioop.rms(raw[i:i + blk], w) for i in range(0, len(raw) - blk, blk)]
        elif np is not None:
            usable = (len(raw) // blk) * blk
            if usable > 0:
                arr = np.frombuffer(raw[:usable], dtype=np.int16).astype(np.float32)
                arr = arr[: (len(arr) // 1024) * 1024].reshape(-1, 1024)
                vals = [float(np.sqrt(np.mean(np.square(c)))) for c in arr]
        if not vals:
            return False, 0.0, 0.0

        vals.sort()
        p90 = float(vals[int(len(vals) * 0.9)])
        peak = float(vals[-1])

        floor = self._noise_floor()
        ratio = float(getattr(config, "SPEECH_PRESENCE_RATIO", 1.6))
        has_speech = p90 > floor * ratio

        if not has_speech:
            # Quiet window — noise floor ko dheere neeche laao (bounded).
            #
            # BUG FIX: pehle `max(p90, ambient * 0.25)` tha, jisse ek hi
            # utterance me floor 132 -> 86 tak gir gaya. Uske baad bolne ke
            # QUIET parts (p90=127) bhi floor*1.25 se upar nikal kar "speech"
            # ban jate the, aur silence windows bhi speech lag jati thi —
            # loop ~90s tak ghumta raha.
            #
            # Ab floor: (a) har quiet window me max 15% hi girta hai,
            # (b) sirf tab girta hai jab window MEASURED QUIET ho (hysteresis),
            # (c) calibration se 50% neeche kabhi nahi jaata.
            # Isse floor stable rehta hai aur decision flicker nahi karta.
            ambient = getattr(self, "_ambient_energy", None) or floor
            if p90 < floor * 0.85:
                self._noise_estimate = max(p90, floor * 0.85, ambient * 0.5)
        return has_speech, p90, peak

    def _record_window(self, duration: float):
        """
        Exactly `duration` seconds ka raw audio — SpeechRecognition ke `listen()`
        state machine ke bina.

        `listen()` me risk ye hai ki wo 1.8s ki silence ya 120s ke phrase limit
        tak RUKEGA. Silence check ke liye chahiye to EXACT timing chahiye, isliye
        yahan `record()` use hota hai jo kabhi hang nahi karta.
        """
        try:
            with self._open_microphone() as source:
                return self.recognizer.record(source, duration=duration)
        except Exception as e:
            print(f"[voice] record window failed: {e}")
            return None

    def _confirm_end_of_speech(self, required_streak: int) -> tuple:
        """
        DEFINITIVE end-of-speech — PURELY ACOUSTIC.

        `required_streak` consecutive SILENT windows collect karta hai. Jaise hi
        ek window me speech energy milti hai, turant return karta hai (user abhi
        bol raha hai) aur wo raw audio caller ko wapas deta hai taaki STT kiya ja sake.

        !!! Ye kabhi STT ke text pe depend NAHI karta !!!
        Purana implementation `_listen_raw_phrase()` se silence check karta tha.
        Noisy room me STT "and the what" jaisa garbage wapas deta tha (kabhi "" nahi),
        isliye confirmation kabhi trigger nahi hui aur Jarvis "still speaking"
        state me chalti rahi, text accumulate karti rahi, reply kabhi nahi aayi.
        Ab decision sirf audio energy pe hai — reliable aur fast.

        Returns: (confirmed: bool, audio_or_None)
        """
        window = float(getattr(config, "END_OF_SPEECH_WINDOW", 1.5))
        required = max(1, int(required_streak))

        for i in range(required):
            audio = self._record_window(window)
            if audio is None:
                # Mic band ho gaya — maan lo silence, warna loop phas jaayega
                return True, None

            has_speech, p90, peak = self._measure_audio_energy(audio)
            if has_speech:
                print(f"[voice] End-of-speech check {i+1}/{required}: speech "
                      f"(p90={p90:.0f} > floor {self._noise_floor():.0f}x"
                      f"{getattr(config,'SPEECH_PRESENCE_RATIO',1.6)}) — still talking.")
                return False, audio
            print(f"[voice] End-of-speech check {i+1}/{required}: silent (p90={p90:.0f})")

        print(f"[voice] End-of-speech CONFIRMED after {required} silent windows.")
        return True, None

    def _enforce_capture_floor(self, timeout, phrase_time_limit):
        """
        Capture-first policy ka CENTRAL enforcement point.

        main.py ke multiple call sites (262, 277, 436, 804, 812, 985, 1905) abhi
        bhi purane chhote values pass karte hain — timeout=4..15 aur
        phrase_time_limit=5..10. Unke wajah se sentence beech me kat rahi thi.

        Jab VOICE_CAPTURE_PRIORITY on hai, ye un sab values ko capture-first
        floors ke NEECHE clamp kar deta hai, aur phrase_time_limit ko hamesha
        None (unlimited) kar deta hai. Isse policy ek jagah define rehti hai
        aur koi call site use bypass nahi kar sakti.
        """
        if not getattr(config, "VOICE_CAPTURE_PRIORITY", False):
            return timeout, phrase_time_limit

        floor = getattr(config, "LISTEN_TIMEOUT_FLOOR", 20.0)
        try:
            if timeout is None or float(timeout) < float(floor):
                timeout = float(floor)
        except (TypeError, ValueError):
            timeout = float(floor)

        # Unlimited — SR kabhi sentence beech me cut nahi karega
        phrase_time_limit = self._resolve_phrase_time_limit()
        return timeout, phrase_time_limit

    def listen(self, timeout=None, phrase_time_limit=None, wait_for_thought=True) -> str:
        """
        Fully Conversational Capture-First Listener.

        Contract:
        - Mic pehle poora sunta hai. Koi beech me cut nahi hota.
        - Input tabhi process hota hai jab DEFINITIVE end-of-speech signal mile.
        - Sochne wale pause (2-6s) ko sentence adhura nahi maana jata.
        - Sentence kitni bhi lambi ho — 10s, 60s, 3 min — poori capture hoti hai.
        - Assistant sun-ne ke baad hi sochti hai; pehle response generate
          karke baad me input jodne ka koi path nahi hai.
        """
        timeout, phrase_time_limit = self._enforce_capture_floor(timeout, phrase_time_limit)

        deadline = time.time() + getattr(config, "MIC_MAX_UTTERANCE_SECONDS", 240)

        # ── Stage 1: pehla capture ────────────────────────────────────────
        initial_phrase = self._listen_raw_phrase(
            timeout=timeout, phrase_time_limit=phrase_time_limit
        )
        if not initial_phrase:
            print("[voice] No speech in initial window — nothing to process.")
            return ""

        accumulated = initial_phrase.strip()
        print(f"[voice] Captured first phrase: '{accumulated}'")

        if not wait_for_thought:
            return accumulated

        # ── Stage 2: accumulate until DEFINITIVE end-of-speech ────────────
        max_words = getattr(config, "MAX_TOTAL_WORDS", 800)
        max_rounds = getattr(config, "MAX_CONTINUATION_ROUNDS", 30)
        window = getattr(config, "END_OF_SPEECH_WINDOW", 1.5)
        base_confirmations = getattr(config, "END_OF_SPEECH_CONFIRMATIONS", 3)
        stall_limit = getattr(config, "LISTEN_STALL_LIMIT", 3)

        rounds = 0
        seen_phrases = {accumulated.lower()}
        stall = 0
        while rounds < max_rounds:
            if time.time() > deadline:
                print("[voice] Hard utterance ceiling reached — finalising captured text.")
                break
            if len(accumulated.split()) >= max_words:
                print(f"[voice] Word cap ({max_words}) reached — finalising.")
                break

            thought_incomplete = is_incomplete_thought(accumulated)

            # Fast & Snappy End-of-Speech Confirmation (User requested: max 2 checks, no 6-round lag)
            # Incomplete hanging queries (e.g. 'aur...', 'ki...') get 3 checks (~2.4s) for thinking pause.
            # Normal/complete queries get 2 checks (~1.6s) max.
            required = min(base_confirmations + 1, 3) if thought_incomplete else min(base_confirmations, 2)

            # ACOUSTIC check — STT ke text pe nahi. Noisy room me ye reliable hai.
            confirmed, pending_audio = self._confirm_end_of_speech(required_streak=required)

            if not confirmed:
                # Abhi bhi bol raha hai. Jo raw audio mila use STT karo.
                extra = self._transcribe(audio=pending_audio)
                if not extra:
                    # Energy to thi par bolne layak text nahi mila (shor).
                    # Ye zaroori hai — warna loop bhool na jaaye.
                    rounds += 1
                    stall += 1
                    if stall >= stall_limit:
                        print("[voice] No usable speech after "
                              f"{stall} noisy windows — finalising.")
                        break
                    continue

                key = extra.strip().lower()
                no_new_info = (key in seen_phrases) or (key in accumulated.lower())
                seen_phrases.add(key)
                if no_new_info:
                    stall += 1
                    if stall >= stall_limit:
                        print(
                            f"[voice] No new speech after {stall} repeated windows "
                            f"(mic picking up noise, not voice) — finalising."
                        )
                        break
                else:
                    stall = 0

                accumulated = f"{accumulated} {extra.strip()}".strip()
                rounds += 1
                print(f"[voice] Still speaking — accumulated {len(accumulated.split())} words.")
                continue

            # ── Definitive end-of-speech mila ──────────────────────────────
            if thought_incomplete:
                print(
                    f"[voice] End-of-speech confirmed after {required} silent windows. "
                    f"Sentence still looked open ('{accumulated[-50:]}') but user stopped — respecting that."
                )
            else:
                print("[voice] End-of-speech confirmed — processing input now.")
            break

        if rounds >= max_rounds:
            print("[voice] Continuation round cap reached — finalising captured text.")

        print(f"[voice] FINAL CAPTURE ({len(accumulated.split())} words): '{accumulated}'")

        # ── Post-capture: NON-DESTRUCTIVE only ─────────────────────────────
        # Purana code yahan single-word utterance ko "" return kar deta tha,
        # jisse "jar" / "linda" jaise words permanently gayab ho jaate the.
        # Ab hum KABHI user ka bolna delete nahi karte. Agar lagta hai ki
        # artifact hai to use upstream flag karte hain, delete nahi.
        words = accumulated.strip().split()
        if not words:
            return ""

        if len(words) == 1:
            try:
                from acoustic_filter_engine import acoustic_filter
                advisory = acoustic_filter.is_keystroke_transient(b"", text=accumulated)
            except Exception:
                advisory = False
            print(
                f"[voice] Single-word capture '{accumulated}' preserved "
                f"(advisory_keystroke={advisory}) — capture-first policy forbids deletion."
            )

        return accumulated

    def _recognize_offline_safe(self, audio) -> str:
        """Safely attempts offline STT without crashing if pocketsphinx is uninstalled."""
        if not self.recognizer:
            return ""
        try:
            return self.recognizer.recognize_sphinx(audio)
        except (AttributeError, ModuleNotFoundError, ImportError):
            # pocketsphinx package is not installed
            return ""
        except Exception:
            return ""