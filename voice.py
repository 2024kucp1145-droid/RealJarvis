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

# ── SELF-HEARING GUARD ──────────────────────────────────────────────────────
# Jab Jarvis bol raha ho, tab mic BILKUL band rehti hai.
# Isse Jarvis apni hi awaaz sun ke khud trigger nahi karta.
IS_SPEAKING = False          # True = Jarvis is currently producing audio output
_POST_SPEECH_DEAF_SECS = 0.30  # Mic opens 300ms AFTER Jarvis stops (echo tail guard)
_speech_end_time = 0.0       # Epoch time when last TTS finished

def _mark_speaking_start():
    """Call when Jarvis starts producing TTS audio."""
    global IS_SPEAKING
    IS_SPEAKING = True

def _mark_speaking_end():
    """Call when Jarvis finishes TTS audio (including echo tail guard)."""
    global IS_SPEAKING, _speech_end_time
    IS_SPEAKING = False
    _speech_end_time = time.time()

def is_in_deaf_window() -> bool:
    """Returns True if we are still in the post-speech deaf window."""
    return IS_SPEAKING or (time.time() - _speech_end_time < _POST_SPEECH_DEAF_SECS)

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
    Detects whether an utterance is an incomplete thought, hanging clause,
    or trailing thinking hesitation in Hindi or English.
    """
    if not text:
        return False
    words = text.strip().lower().split()
    if not words:
        return False

    last_word = words[-1].strip(".,?!:;-")
    first_word = words[0].strip(".,?!:;-")

    # Incomplete trailing conjunctions / connectors / prepositions
    TRAILING_CONNECTORS = {
        # Hindi
        "ki", "aur", "toh", "to", "lekin", "par", "kyunki", "matlab", "jaise",
        "agar", "jab", "kahan", "kaise", "waise", "sun", "suno", "yaar", "achha",
        "batao na", "bata do na", "ek", "do", "kuch", "jo", "woh", "wo", "mere", "mera", "meri",
        "apna", "apne", "apni", "ka", "ke", "ko", "se", "pe", "par", "mein", "me", "fir", "phir",
        # English
        "and", "or", "because", "so", "that", "if", "but", "then", "like", "when",
        "who", "what", "where", "how", "to", "for", "with", "about", "by", "of", "my",
        "your", "our", "the", "a", "an", "this", "that", "these", "those", "is", "are"
    }
    if last_word in TRAILING_CONNECTORS:
        return True

    # Thinking markers / fillers
    THINKING_MARKERS = {
        "umm", "uhh", "hmm", "ek second", "ek minute", "ruko", "sochne do",
        "wait", "hang on", "hold on", "let me think", "actually", "basically"
    }
    if any(m in text.lower() for m in THINKING_MARKERS):
        return True

    # Fragmentary question (starts with question word but has <= 3 words)
    QUESTION_STARTERS = {"kya", "kaise", "kyun", "kab", "kahan", "kaun", "what", "how", "why", "when", "where", "who"}
    if first_word in QUESTION_STARTERS and len(words) <= 3:
        return True

    # Complete short imperative commands with terminal verbs
    TERMINAL_ACTION_VERBS = {
        "kholo", "chalu", "band", "ruko", "batao", "dikhao", "sunao", "status", "screenshot",
        "help", "lo", "le", "karo", "do", "bhejo", "send", "stop", "exit", "quit", "start",
        "open", "close", "sleep", "so", "banao", "chalao", "padho", "read", "type", "likho",
        "search", "play", "pause", "mute", "unmute", "save", "commit", "lock"
    }
    if len(words) <= 2 and last_word not in TERMINAL_ACTION_VERBS:
        return True

    return False


class Voice:
    def __init__(self):
        self.recognizer = sr.Recognizer() if sr else None
        if self.recognizer:
            self.recognizer.pause_threshold = getattr(config, "MIC_PAUSE_THRESHOLD", 0.45)
            self.recognizer.non_speaking_duration = getattr(config, "MIC_NON_SPEAKING_DURATION", 0.20)
            self.recognizer.dynamic_energy_threshold = getattr(config, "MIC_DYNAMIC_ENERGY", True)
            self.recognizer.dynamic_energy_adjustment_damping = 0.15
            self.recognizer.dynamic_energy_ratio = 1.2
            self.recognizer.energy_threshold = 55
        self._calibrated = False
        self._speech_lock = threading.Lock()
        if pygame:
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"[pygame mixer init fail: {e}]")

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
        """Applies global TTS_RATE_OFFSET on top of emotion rate for a sweeter, slower delivery."""
        offset = getattr(config, "TTS_RATE_OFFSET", "-12%")
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
                # Priority 1: ElevenLabs Ultra-Realistic Human Voice (if API key is provided)
                if getattr(config, "ELEVENLABS_API_KEY", "").strip() and has_internet():
                    try:
                        did_interrupt = self._speak_elevenlabs(text, emotion=emotion, interruptible=interruptible)
                        return did_interrupt
                    except Exception as _e_el:
                        print(f"[voice] ElevenLabs playback failed: {_e_el}, falling back to Neural voice")

                # Priority 2: High-Speed Microsoft Natural Neural Streaming Engine (100% Free, Unlimited)
                mode = getattr(config, "TTS_MODE", "auto")
                use_online = (mode in ("online", "edge", "auto")) and has_internet()
                rate, pitch = self.EMOTION_PROSODY.get(emotion, self.EMOTION_PROSODY["calm"])
                rate = self._apply_rate_offset(rate)  # Apply global speed slowdown

                if use_online and edge_tts:
                    try:
                        import streaming_audio_engine
                        return streaming_audio_engine.streaming_engine.speak_streaming(text, emotion=emotion, interruptible=interruptible)
                    except Exception as e:
                        print(f"[streaming audio engine fail, fallback to standard: {e}]")
                        try:
                            return self._speak_online_interruptible(text, rate, pitch, is_first_chunk)
                        except Exception:
                            pass

                # Priority 3: Offline SAPI5 / espeak fallback
                self._speak_offline(text, emotion)
                return False
            finally:
                _mark_speaking_end()

    def _speak_elevenlabs(self, text: str, emotion: str = "calm", interruptible: bool = True) -> bool:
        """Plays ultra-realistic speech from ElevenLabs Multilingual v2 with streaming buffer and instant barge-in."""
        api_key = getattr(config, "ELEVENLABS_API_KEY", "").strip()
        if not api_key:
            return False

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
                return False

            audio_buf = io.BytesIO()
            for chunk in resp.iter_content(chunk_size=4096):
                if chunk:
                    audio_buf.write(chunk)
            audio_buf.seek(0)

            pygame.mixer.music.load(audio_buf)
            pygame.mixer.music.play()

            interrupted = False
            start_time = time.time()
            grace_period = getattr(config, "BARGE_IN_GRACE_SECONDS", 0.15)
            barge_threshold = getattr(config, "BARGE_IN_THRESHOLD", 0.0030)
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
                if consecutive_loud >= 2:
                    interrupted = True
                    print("[voice] INSTANT BARGE-IN TRIGGERED ON ELEVENLABS STREAM!")

            mic_stream = None
            if interruptible and sd and np:
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
            return False

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

        async def _stream_to_buffer():
            communicate = edge_tts.Communicate(text, config.ONLINE_VOICE, rate=rate, pitch=pitch)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

        asyncio.run(_stream_to_buffer())
        audio_buffer.seek(0)

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

        # Stream audio chunks into memory buffer
        async def _stream_to_buf():
            communicate = edge_tts.Communicate(text, config.ONLINE_VOICE, rate=rate, pitch=pitch)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

        asyncio.run(_stream_to_buf())
        audio_buffer.seek(0)

        interrupted = False
        peak_volume = 0.0
        start_time = time.time()

        grace_period = getattr(config, "BARGE_IN_GRACE_SECONDS", 0.15) if is_first_chunk else 0.05

        try:
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()

            consecutive_loud = 0
            SUSTAIN_BLOCKS_NEEDED = getattr(config, "BARGE_IN_SUSTAIN_BLOCKS", 2)
            barge_threshold = getattr(config, "BARGE_IN_THRESHOLD", 0.0030)

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

            with sd.InputStream(channels=1, samplerate=16000, blocksize=1024,
                                 callback=callback):
                while pygame.mixer.music.get_busy():
                    if interrupted:
                        pygame.mixer.music.stop()
                        break
                    time.sleep(0.02)

            pygame.mixer.music.unload()
            print(f"[barge-in: peak mic={peak_volume:.4f}, threshold={barge_threshold}]")
        except Exception as e:
            print(f"[interruptible stream error: {e}]")

        return interrupted


    # -------------------------------------------------------------- listen
    # -------------------------------------------------------------- listen
    def _listen_raw_phrase(self, timeout=6, phrase_time_limit=10) -> str:
        """Mic se single phrase capture karta hai aur keystroke noise filter karta hai."""
        if not self.recognizer:
            return ""

        # ── SELF-HEARING GUARD ─────────────────────────────────────────────
        # Jarvis apni hi awaaz sun ke trigger na ho iske liye:
        # Agar Jarvis abhi bol raha hai ya abhi abhi ruka hai (300ms deaf window),
        # toh mic ko immediately khali string return karao.
        if is_in_deaf_window():
            print("[voice] Mic blocked — Jarvis apni awaaz sun raha tha, skip kar raha hai.")
            return ""

        with sr.Microphone() as source:
            if not self._calibrated:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                self._calibrated = True

            min_energy = getattr(config, "MIC_ENERGY_MIN", 45)
            max_energy = getattr(config, "MIC_ENERGY_MAX", 180)
            if self.recognizer.energy_threshold < min_energy:
                self.recognizer.energy_threshold = min_energy
            elif self.recognizer.energy_threshold > max_energy:
                self.recognizer.energy_threshold = max_energy

            self.recognizer.dynamic_energy_threshold = getattr(config, "MIC_DYNAMIC_ENERGY", True)
            self.recognizer.pause_threshold = getattr(config, "MIC_PAUSE_THRESHOLD", 0.45)
            self.recognizer.non_speaking_duration = getattr(config, "MIC_NON_SPEAKING_DURATION", 0.20)

            try:
                audio = self.recognizer.listen(source, timeout=timeout,
                                                phrase_time_limit=phrase_time_limit)
            except sr.WaitTimeoutError:
                return ""

        raw_pcm = audio.get_raw_data()

        # Step 1: Pre-STT Mechanical Keystroke Transient Filter (instant drop without STT delay)
        try:
            from acoustic_filter_engine import acoustic_filter
            if acoustic_filter.is_pre_stt_keystroke(raw_pcm, sample_rate=audio.sample_rate):
                print("[acoustic_filter] Pre-STT dropped typing keystroke transient.")
                return ""
        except Exception:
            pass

        # Step 2: Far-Field AGC Pre-Amp (blocked during active typing)
        try:
            from acoustic_filter_engine import acoustic_filter
            amplified_pcm = acoustic_filter.apply_far_field_agc(raw_pcm, sample_rate=audio.sample_rate)
            audio = sr.AudioData(amplified_pcm, audio.sample_rate, audio.sample_width)
        except Exception:
            amplified_pcm = raw_pcm

        # Step 3: STT Recognition
        mode = getattr(config, "STT_MODE", "auto")
        use_online = (mode == "google") or (mode == "auto" and has_internet())
        result_text = ""

        if use_online:
            for lang in getattr(config, "RECOGNITION_LANGUAGES", ["en-IN", "hi-IN"]):
                try:
                    res = self.recognizer.recognize_google(audio, language=lang)
                    if res:
                        result_text = res
                        break
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    break
            if not result_text:
                result_text = self._recognize_offline_safe(audio)
        else:
            result_text = self._recognize_offline_safe(audio)

        # Step 4: Post-STT Keystroke & Typing Transient Filter
        try:
            from acoustic_filter_engine import acoustic_filter
            if acoustic_filter.is_keystroke_transient(raw_pcm, sample_rate=audio.sample_rate, text=result_text):
                print(f"[acoustic_filter] Silently suppressed keystroke click (phantom: '{result_text}')")
                return ""
        except Exception as e:
            print(f"[acoustic_filter check error: {e}]")

        return result_text

    def listen(self, timeout=6, phrase_time_limit=10, wait_for_thought=True) -> str:
        """
        Instant snappy conversational listening with high sensitivity and zero lag.
        
        If a complete command/question is spoken, it returns INSTANTLY (< 0.5s).
        Only if the sentence is explicitly trailing/incomplete (e.g. ends with 'aur', 'ki')
        does it wait a brief 1.2s buffer for continuation.
        """
        initial_phrase = self._listen_raw_phrase(timeout=timeout, phrase_time_limit=phrase_time_limit)
        if not initial_phrase:
            return ""

        accumulated = initial_phrase.strip()

        # If thought is already complete (standard command or question), return INSTANTLY!
        # Zero unnecessary 5-7s waiting!
        if not is_incomplete_thought(accumulated):
            return accumulated

        # Only wait for continuation if thought is explicitly incomplete (e.g. 'aur...', 'ki...')
        if wait_for_thought:
            print(f"[voice] Incomplete thought detected ('{accumulated}'), waiting 1.2s for continuation...")
            next_phrase = self._listen_raw_phrase(timeout=1.2, phrase_time_limit=8)
            if next_phrase:
                accumulated = f"{accumulated} {next_phrase.strip()}".strip()
                print(f"[voice] Stitched continuation: '{accumulated}'")

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