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


class Voice:
    def __init__(self):
        self.recognizer = sr.Recognizer() if sr else None
        if self.recognizer:
            self.recognizer.pause_threshold = 0.28
            self.recognizer.non_speaking_duration = 0.10
        self._calibrated = False
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

    def speak(self, text: str, interruptible: bool = False, emotion: str = "calm",
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
        print(f"Jarvis [{emotion}]: {text}")
        mode = config.TTS_MODE
        use_online = (mode == "online") or (mode == "auto" and has_internet())
        rate, pitch = self.EMOTION_PROSODY.get(emotion, self.EMOTION_PROSODY["calm"])

        if interruptible:
            can_interrupt = getattr(config, "BARGE_IN_ENABLED", True) and use_online and edge_tts and pygame and sd
            if not can_interrupt:
                missing = []
                if not getattr(config, "BARGE_IN_ENABLED", True): missing.append("BARGE_IN_ENABLED=False")
                if not use_online: missing.append("internet/online-mode nahi hai")
                if not edge_tts: missing.append("edge_tts install nahi")
                if not pygame: missing.append("pygame install nahi")
                if not sd: missing.append("sounddevice install nahi")
                print(f"[barge-in skip ho gaya, wajah: {', '.join(missing)}]")
            else:
                threshold = getattr(config, "BARGE_IN_THRESHOLD", 0.02)
                print(f"[barge-in active hai, threshold={threshold}]")
                try:
                    return self._speak_online_interruptible(text, rate, pitch, is_first_chunk)
                except Exception as e:
                    print(f"[interruptible voice fail, normal pe switch: {e}]")

        if use_online and edge_tts:
            try:
                self._speak_online(text, rate, pitch)
                return False
            except Exception as e:
                print(f"[online voice fail, offline pe switch: {e}]")

        self._speak_offline(text, emotion)
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

        if is_first_chunk:
            grace_period = getattr(config, "BARGE_IN_GRACE_SECONDS", 1.2)
        else:
            grace_period = getattr(config, "BARGE_IN_GRACE_SECONDS_LATER", 0.1)

        try:
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()

            consecutive_loud = 0
            SUSTAIN_BLOCKS_NEEDED = getattr(config, "BARGE_IN_SUSTAIN_BLOCKS", 4)

            def callback(indata, frames, time_info, status):
                nonlocal interrupted, peak_volume, consecutive_loud
                if interrupted:
                    return
                if time.time() - start_time < grace_period:
                    return
                volume = float(np.linalg.norm(indata) / len(indata)) if len(indata) else 0.0
                peak_volume = max(peak_volume, volume)
                if volume > getattr(config, "BARGE_IN_THRESHOLD", 0.0025):
                    consecutive_loud += 1
                else:
                    consecutive_loud = 0
                if consecutive_loud >= SUSTAIN_BLOCKS_NEEDED:
                    interrupted = True

            with sd.InputStream(channels=1, samplerate=16000, blocksize=1024,
                                 callback=callback):
                while pygame.mixer.music.get_busy():
                    if interrupted:
                        pygame.mixer.music.stop()
                        break
                    time.sleep(0.03)

            pygame.mixer.music.unload()
            print(f"[barge-in: peak mic={peak_volume:.4f}, threshold={getattr(config, 'BARGE_IN_THRESHOLD', 0.02)}]")
        except Exception as e:
            print(f"[interruptible stream error: {e}]")

        return interrupted


    # -------------------------------------------------------------- listen
    def listen(self, timeout=6, phrase_time_limit=8) -> str:
        """Mic se sunta hai aur text return karta hai. Kuch na sune toh ''."""
        if not self.recognizer:
            return ""

        with sr.Microphone() as source:
            if not self._calibrated:
                    # Sirf pehli baar ek baar calibrate — 0.4s kaafi hai
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                    self._calibrated = True

            # Calibration kabhi-kabhi bahut high threshold set kar deta hai
            # (noisy room me) - jisse dur se ya halka bolna sunayi nahi deta
            # tha ("paas aa kar bolna padta tha"). Isse ek sensible range me
            # clamp karte hain taaki sensitivity zyada rahe.
            self.recognizer.energy_threshold = min(
                max(self.recognizer.energy_threshold, getattr(config, "MIC_ENERGY_MIN", 20)),
                getattr(config, "MIC_ENERGY_MAX", 400),
            )
            self.recognizer.dynamic_energy_threshold = False  # calibration ke baad fixed rakho, upar nahi jaane do

            # pause_threshold: bolna khatam hone ke baad kitna wait karo
            # 0.28s = Ultra-fast instant response, zero dead air latency
            self.recognizer.pause_threshold = 0.28
            self.recognizer.non_speaking_duration = 0.10

            try:
                audio = self.recognizer.listen(source, timeout=timeout,
                                                phrase_time_limit=phrase_time_limit)
            except sr.WaitTimeoutError:
                return ""

        mode = config.STT_MODE
        use_online = (mode == "google") or (mode == "auto" and has_internet())

        if use_online:
            # Hinglish/English/Hindi teeno cover karne ke liye pehle en-IN try
            # karo (English + roman Hindi dono usually pakड़ leta hai), fir
            # nahi mila toh hi-IN (Devanagari accurate Hindi ke liye) try karo.
            for lang in config.RECOGNITION_LANGUAGES:
                try:
                    result = self.recognizer.recognize_google(audio, language=lang)
                    if result:
                        return result
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    break  # internet chala gaya beech mein, offline pe jao
            # online se kuch nahi mila - offline try karo
            return self._recognize_offline_safe(audio)
        else:
            return self._recognize_offline_safe(audio)

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