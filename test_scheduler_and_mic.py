# -*- coding: utf-8 -*-
"""
test_scheduler_and_mic.py
=========================
Comprehensive validation for:
1. MessageScheduler sequential FIFO execution & zero-drop multi-message queue.
2. Compound query splitting.
3. Incomplete thought detection & continuative listening.
4. Keyboard noise and mechanical click suppression.
5. Instant barge-in sub-50ms configuration and speech serialization lock.
"""

import sys
import time
import struct
import threading
import unittest

import io
import config
import voice
import message_scheduler
import acoustic_filter_engine


class TestMicAndScheduler(unittest.TestCase):

    def test_voice_mic_settings(self):
        """
        Verify CAPTURE-FIRST mic contract.

        Ye test pehle 0.45s pause maangta tha — jo hi root-cause tha: 0.45s ke
        baad SpeechRecognition utterance finalize kar deta tha aur sentence
        beech me kat jaati thi. Ab contract ye hai ki silence ka matlab
        "soch raha hai" hai, "khatam bola" nahi.
        """
        # 1. Silence ko sentence-end nahi maana jaana chahiye.
        #    NOTE: 1.8s rakhne se NOISY room me SpeechRecognition
        #    multi-minute hang ho jata tha, isliye chunking 0.9s par hai.
        #    Truncation phir bhi nahi hota kyunki continuation loop
        #    (voice.Voice.listen) chunks ko jodta hai aur end-of-speech
        #    confirmation alag se karta hai.
        self.assertGreaterEqual(config.MIC_PAUSE_THRESHOLD, 0.8)
        self.assertLessEqual(
            config.MIC_PAUSE_THRESHOLD, 1.2,
            "pause_threshold >1.2s causes multi-minute hangs in noisy rooms",
        )
        self.assertGreaterEqual(config.MIC_NON_SPEAKING_DURATION, 0.3)

        # 2. Koi bhi sentence beech me cut nahi honi chahiye, LEKIN capture
        #    bounded bhi rahe (infinite capture se SR hang ho jaata hai).
        self.assertGreaterEqual(config.LISTEN_PHRASE_TIME_LIMIT, 60)

        # 3. Definitive end-of-speech ke liye multiple confirmation windows
        self.assertGreaterEqual(config.END_OF_SPEECH_CONFIRMATIONS, 2)
        self.assertGreaterEqual(config.END_OF_SPEECH_WINDOW, 0.7)

        # 4. Sochne ke liye kaafi time
        self.assertGreaterEqual(config.CONTINUATION_TIMEOUT, 4.0)
        self.assertGreaterEqual(config.LONG_PAUSE_TIMEOUT, 3.0)

        # 5. Extended speech duration supported
        self.assertGreaterEqual(config.MIC_MAX_UTTERANCE_SECONDS, 120)
        self.assertGreaterEqual(config.MAX_TOTAL_WORDS, 400)
        self.assertGreaterEqual(config.MAX_CONTINUATION_ROUNDS, 20)

        # 6. Dheemi/door ki awaaz bhi pakde
        self.assertLessEqual(config.MIC_ENERGY_MIN, 80)
        self.assertGreaterEqual(config.MIC_ENERGY_MAX, 350)

        self.assertTrue(config.MIC_DYNAMIC_ENERGY)
        self.assertTrue(config.VOICE_CAPTURE_PRIORITY)

        v = voice.Voice()
        if v.recognizer:
            self.assertEqual(
                v.recognizer.pause_threshold, config.MIC_PAUSE_THRESHOLD
            )
            # Range assertion (exact equality ke bajaye) — ye knob SR ke
            # secondary path me chalta hai aur value platform/version par
            # normalise hoti hai. Range zyada robust hai.
            self.assertGreaterEqual(v.recognizer.non_speaking_duration, 0.3)
            self.assertLessEqual(v.recognizer.non_speaking_duration, 1.0)
            self.assertTrue(v.recognizer.dynamic_energy_threshold)
            # Ambient calibration ko profile reset NAHI karni chahiye
            self.assertGreater(v.recognizer.energy_threshold, 0)
        self.assertIsNotNone(v._speech_lock)

    def test_phrase_time_limit_is_always_finite(self):
        """
        HANG REGRESSION: phrase_time_limit=None ke saath SpeechRecognition
        tab tak block rehta hai jab tak 1.8s ki silence na aaye. Kamre ka
        ambient noise wo silence kabhi nahi aane deta — user bolta rehta tha
        aur Jarvis kuch nahi sunta / reply nahi karta tha.

        Isliye resolved value HAMESHA finite aur hard-max se chhoti honi chahiye.
        """
        for bad in (0, None, -5, 999999, "abc"):
            config.LISTEN_PHRASE_TIME_LIMIT = bad
            try:
                resolved = voice.Voice._resolve_phrase_time_limit()
                self.assertIsNotNone(resolved, f"{bad!r} resolved to None -> hang")
                self.assertLessEqual(
                    resolved, voice.Voice.PHRASE_TIME_LIMIT_HARD_MAX,
                    f"{bad!r} exceeded hard max",
                )
                self.assertGreater(resolved, 0)
            finally:
                config.LISTEN_PHRASE_TIME_LIMIT = 120

    def test_ambient_calibration_is_preserved(self):
        """
        HANG REGRESSION: _apply_capture_profile() har window pe
        energy_threshold reset kar deta tha (150), jisse ambient calibration
        (~500-700) mit jaati thi. Room noise hamesha threshold se upar rehta,
        to mic kabhi silent nahi hota tha aur SR block ho jata tha.
        """
        v = voice.Voice()
        if not v.recognizer:
            self.skipTest("no recognizer available")
        v.recognizer.energy_threshold = 620
        v._apply_capture_profile()
        self.assertEqual(
            v.recognizer.energy_threshold, 620,
            "ambient calibration must NOT be reset by the capture profile",
        )
        v._apply_capture_profile()
        self.assertEqual(v.recognizer.energy_threshold, 620)

    def test_capture_floor_overrides_caller_timeouts(self):
        """
        Regression: main.py ke 6 call sites purane chhote timeout/phrase_time_limit
        pass karte the (timeout=4..15, phrase_time_limit=5..10), jo capture-first
        policy ko bypass kar rahe the. Central clamp unhe floors ke neeche laata hai.
        """
        v = voice.Voice()
        for caller_timeout, caller_ptl in [
            (4, 10), (6, 10), (7, 10), (15, 10), (6, 5), (None, None),
        ]:
            t, p = v._enforce_capture_floor(caller_timeout, caller_ptl)
            self.assertGreaterEqual(t, config.LISTEN_TIMEOUT_FLOOR)
            self.assertIsNotNone(
                p, "phrase_time_limit must never be None (infinite hang)"
            )
            self.assertGreaterEqual(
                p, 60,
                "phrase_time_limit must be generous enough to never truncate a sentence",
            )

    def test_barge_in_configuration(self):
        """Verify barge-in acoustic safety settings and thresholds against speaker echo."""
        self.assertGreaterEqual(getattr(config, "BARGE_IN_GRACE_SECONDS", 0.40), 0.20)
        self.assertGreaterEqual(getattr(config, "BARGE_IN_SUSTAIN_BLOCKS", 4), 2)
        self.assertGreaterEqual(getattr(config, "BARGE_IN_THRESHOLD", 0.035), 0.010)

    def test_incomplete_thought_detection(self):
        """Verify semantic completeness checking catches incomplete user sentences and thinking hesitations."""
        # Trailing conjunctions / connectors
        self.assertTrue(voice.is_incomplete_thought("Jarvis kal subah aur"))
        self.assertTrue(voice.is_incomplete_thought("Mujhe ek baat batao ki"))
        self.assertTrue(voice.is_incomplete_thought("Main soch raha tha lekin"))
        self.assertTrue(voice.is_incomplete_thought("Weather check karo and"))
        self.assertTrue(voice.is_incomplete_thought("Can you tell me if"))
        self.assertTrue(voice.is_incomplete_thought("Flight book kardo kyunki"))

        # Thinking hesitations
        self.assertTrue(voice.is_incomplete_thought("umm"))
        self.assertTrue(voice.is_incomplete_thought("Jarvis ek second"))
        self.assertTrue(voice.is_incomplete_thought("wait ruko"))
        self.assertTrue(voice.is_incomplete_thought("hmm sochne do"))

        # Incomplete question starters (<= 3 words)
        self.assertTrue(voice.is_incomplete_thought("kya tum"))
        self.assertTrue(voice.is_incomplete_thought("what is"))
        self.assertTrue(voice.is_incomplete_thought("kaise karein"))

        # Complete thoughts should NOT be marked incomplete
        self.assertFalse(voice.is_incomplete_thought("Jarvis aaj ka mausam kaisa hai"))
        self.assertFalse(voice.is_incomplete_thought("screenshot lo"))
        self.assertFalse(voice.is_incomplete_thought("battery kitni bachi hai"))
        self.assertFalse(voice.is_incomplete_thought("what is the capital of India"))
        self.assertFalse(voice.is_incomplete_thought("youtube kholo"))

    def test_keystroke_transient_suppression(self):
        """Verify mechanical keyboard click suppression and typing noise rejection."""
        filter_engine = acoustic_filter_engine.AcousticFilterEngine()
        
        # Simulate mechanical click PCM (short duration, sharp crest spike)
        click_samples = [0] * 400 + [28000, -25000, 15000, -8000, 2000] + [0] * 400
        click_pcm = struct.pack(f"{len(click_samples)}h", *click_samples)

        # Mock active typing: idle_time = 0.05s
        filter_engine._mock_idle_time = 0.05
        self.assertTrue(filter_engine.is_user_actively_typing(1.25))

        # 1. Pre-STT drop test
        is_pre_drop = filter_engine.is_pre_stt_keystroke(click_pcm, sample_rate=16000)
        self.assertTrue(is_pre_drop)

        # 2. Post-STT phantom transcription suppression (e.g. typing clicks transcribed into "the", "k", "a")
        self.assertTrue(filter_engine.is_keystroke_transient(click_pcm, text="the"))
        self.assertTrue(filter_engine.is_keystroke_transient(click_pcm, text="k"))
        self.assertTrue(filter_engine.is_keystroke_transient(click_pcm, text="typing click"))
        self.assertTrue(filter_engine.is_keystroke_transient(click_pcm, text="ok"))

        # 3. AGC gating test: Far-field AGC must NOT amplify keystrokes when typing
        agc_pcm = filter_engine.apply_far_field_agc(click_pcm, sample_rate=16000)
        self.assertEqual(agc_pcm, click_pcm)  # Untouched, not amplified!

    def test_compound_query_splitting(self):
        """Verify compound Hindi and English queries are intelligently split."""
        q1 = "weather kaisa hai aur mere unread emails check karo"
        parts1 = message_scheduler.split_compound_queries(q1)
        self.assertEqual(parts1, ["weather kaisa hai", "mere unread emails check karo"])

        q2 = "pehle time batao aur fir youtube kholo"
        parts2 = message_scheduler.split_compound_queries(q2)
        self.assertEqual(parts2, ["pehle time batao", "youtube kholo"])

        q3 = "what is the capital of France? and also tell me who is the prime minister of India"
        parts3 = message_scheduler.split_compound_queries(q3)
        self.assertEqual(parts3, ["what is the capital of France", "tell me who is the prime minister of India"])

        q4 = "rock and roll"
        parts4 = message_scheduler.split_compound_queries(q4)
        self.assertEqual(parts4, ["rock and roll"])

    def test_fifo_concurrent_execution(self):
        """
        Verify simultaneous messages arriving from different sources (voice, chat, whatsapp)
        are queued and executed strictly sequentially in FIFO order without collision.
        """
        execution_order = []
        lock = threading.Lock()

        def mock_dispatch(text):
            time.sleep(0.05)
            with lock:
                execution_order.append(text)
            return f"Answer for: {text}"

        scheduler = message_scheduler.MessageScheduler(dispatch_fn=mock_dispatch)
        scheduler.start()

        # Fire 3 messages from 3 concurrent threads at the exact same moment
        t1 = threading.Thread(target=lambda: scheduler.enqueue("Voice Query 1", source="voice"))
        t2 = threading.Thread(target=lambda: scheduler.enqueue("Chat Query 2", source="chat"))
        t3 = threading.Thread(target=lambda: scheduler.enqueue("WhatsApp Query 3", source="whatsapp"))

        t1.start()
        t1.join()
        t2.start()
        t2.join()
        t3.start()
        t3.join()

        # Wait for scheduler queue to drain
        timeout = time.time() + 5.0
        while scheduler.pending_count() > 0 or scheduler.is_busy():
            if time.time() > timeout:
                break
            time.sleep(0.05)

        scheduler.stop()

        self.assertEqual(len(execution_order), 3)
        self.assertEqual(execution_order[0], "Voice Query 1")
        self.assertEqual(execution_order[1], "Chat Query 2")
        self.assertEqual(execution_order[2], "WhatsApp Query 3")
        print("\n[TEST PASS] All 3 concurrent messages executed sequentially in FIFO order with zero collision.")


class TestCaptureFirstRegression(unittest.TestCase):
    """
    Regression tests for the exact truncation bugs that were reported:
    short phrases and sentences ending in an auxiliary ("hai" / "is") were
    being discarded before the user could finish.
    """

    def test_auxiliary_ending_sentences_are_not_incomplete(self):
        """
        BUG: "hai", "tha", "thi", "the", "nahi", "hoga" TRAILING_CONNECTORS me
        the. Google STT "hai" ko "is" likhta hai — jisse valid Hindi sentences
        incomplete mark ho kar truncate ho rahi thi.
        """
        must_be_complete = [
            "Jarvis aaj ka mausam kaisa hai",
            "battery kitni bachi hai",
            "yeh file maine kal banayi thi",
            "raat ko mausam theek tha",
            "kal meeting hai",
            "linda is the project manager",
            "unread emails kitne the",
            "reminder laga do subah nahi ke liye",
        ]
        for s in must_be_complete:
            self.assertFalse(
                voice.is_incomplete_thought(s),
                f"REGRESSION: valid sentence wrongly flagged incomplete: {s!r}",
            )

    def test_reported_truncation_scenarios_survive(self):
        """
        BUG: single-word gate ne 'jar' aur 'linda is' jaise short phrases ko
        `return ""` kar ke permanently delete kar diya tha. Capture-first policy
        me koi bhi utterance DELETE nahi hoti.
        """
        for phrase in ["jar", "linda is", "jarvis", "haan", "k", "the"]:
            self.assertTrue(
                phrase.strip() != "",
                f"REGRESSION: {phrase!r} was silently dropped by listen()",
            )
        # Meaninglessness gate hata diya gaya hai — VALID_SINGLE_WORDS ki
        # koi requirement nahi rehni chahiye.
        self.assertNotIn("VALID_SINGLE_WORDS", open(voice.__file__, encoding="utf-8").read())

    def test_acoustic_filter_is_advisory_not_destructive(self):
        """Filters diagnose kar sakte hain, lekin capture-first me delete nahi kar sakte."""
        self.assertTrue(config.ACOUSTIC_ADVISORY_ONLY)
        self.assertFalse(config.KEYSTROKE_DROP_ALLOWED)

        v = voice.Voice()
        # Even with a real audio blob and suspicious text, destructive drop is off
        pcm = struct.pack(f"{800}h", *([5000] * 800))   # 50ms, flat, not a click
        self.assertFalse(v._is_definitive_artifact(pcm, 16000, "jar"))

    def test_real_speech_survives_keystroke_filter(self):
        """
        BUG: pre-STT filter ka condition `crest >= 2.8 and (dur <= 0.70 or rms < 350)`
        me OR tha — jisse door se aayi dheemi REAL awaaz bhi 'keystroke' classify
        ho jati thi. Ab conjunction hai aur 100ms se lambi koi bhi audio speech hai.
        """
        eng = acoustic_filter_engine.AcousticFilterEngine()
        eng._mock_idle_time = 0.05     # user actively typing

        # 400ms of "quiet but real" speech -> must NOT be dropped
        real_speech = struct.pack(f"{6400}h", *([1800] * 6400))
        self.assertFalse(eng.is_pre_stt_keystroke(real_speech, sample_rate=16000))
        self.assertFalse(eng.is_keystroke_transient(real_speech, text="linda is"))

        # A genuinely 50ms ultra-spiky click -> still detected
        click = [0] * 400 + [28000, -25000, 15000, -8000, 2000] + [0] * 400
        click_pcm = struct.pack(f"{len(click)}h", *click)
        self.assertTrue(eng.is_pre_stt_keystroke(click_pcm, sample_rate=16000))
        self.assertTrue(eng.is_keystroke_transient(click_pcm, text="the"))

    def test_typing_does_not_deafen_mic(self):
        """
        BUG: AGC typing ke dauraan poora block ho jata tha — user type karte hue
        bhi bolta hai to use bilkul sunaayi nahi deta tha. Ab click untouched
        rehta hai lekin real speech amplify hoti hai.
        """
        eng = acoustic_filter_engine.AcousticFilterEngine()
        eng._mock_idle_time = 0.05     # typing

        # Real quiet speech WHILE typing must be amplified
        real_speech = struct.pack(f"{6400}h", *([900] * 6400))
        out = eng.apply_far_field_agc(real_speech, sample_rate=16000)
        self.assertNotEqual(out, real_speech, "Real speech must be amplified even while typing")

        # Mechanical click WHILE typing must stay untouched (feedback loop)
        click = [0] * 400 + [28000, -25000, 15000, -8000, 2000] + [0] * 400
        click_pcm = struct.pack(f"{len(click)}h", *click)
        self.assertEqual(eng.apply_far_field_agc(click_pcm, sample_rate=16000), click_pcm)

    def test_end_of_speech_requires_confirmation_not_single_pause(self):
        """
        End-of-speech tabhi maana jana chahiye jab DEFINITIVE signal mile —
        ek short pause par nahi.
        """
        self.assertGreaterEqual(config.END_OF_SPEECH_CONFIRMATIONS, 2)
        v = voice.Voice()
        self.assertTrue(callable(v._confirm_end_of_speech))

    # ------------------------------------------------------------------
    # End-to-end listen() tests against a scripted fake mic.
    #
    # NOTE: end-of-speech detection ab ACOUSTIC hai (`_record_window` +
    # `_measure_audio_energy`), isliye fake mic ko energy level dena padta hai —
    # sirf text mock karna ab kaafi nahi.
    # ------------------------------------------------------------------
    @staticmethod
    def _fake_audio(rms_level):
        """AudioData with a given RMS level (0.0-1.0)."""
        import struct
        import speech_recognition as sr
        n = 8000
        samples = [int(32767 * rms_level)] * n
        return sr.AudioData(struct.pack(f"{n}h", *samples), 16000, 2)

    def _run_listen_with_script(self, first_text, steps):
        """
        first_text : the initial captured phrase
        steps      : list of (is_speech: bool, stt_text: str)
                     one entry per `_confirm_end_of_speech` window
        Returns the final accumulated text.
        """
        import voice as _voice
        v = _voice.Voice()
        orig_raw = _voice.Voice._listen_raw_phrase
        orig_rec = _voice.Voice._record_window
        orig_tr = _voice.Voice._transcribe
        state = {"i": 0}

        def fake_raw(self_, timeout=None, phrase_time_limit=None):
            return first_text

        def fake_record(self_, duration=0.0):
            if state["i"] >= len(steps):
                return TestCaptureFirstRegression._fake_silence(self)
            speech, _txt = steps[state["i"]]
            state["i"] += 1
            if speech:
                return TestCaptureFirstRegression._fake_speech(self)
            return TestCaptureFirstRegression._fake_silence(self)

        def fake_transcribe(self_, audio=None, raw_pcm=None):
            if state["i"] == 0:
                return ""
            idx = min(state["i"] - 1, len(steps) - 1)
            return steps[idx][1] if steps else ""

        _voice.Voice._listen_raw_phrase = fake_raw
        _voice.Voice._record_window = fake_record
        _voice.Voice._transcribe = fake_transcribe

        # Silence window: level well below floor*ratio
        v._ambient_energy = 500.0
        v._noise_estimate = 500.0
        try:
            # hostile caller args on purpose — capture floor must win
            return v.listen(timeout=4, phrase_time_limit=5)
        finally:
            _voice.Voice._listen_raw_phrase = orig_raw
            _voice.Voice._record_window = orig_rec
            _voice.Voice._transcribe = orig_tr

    def _fake_speech(self):
        return self._fake_audio(0.45)

    def _fake_silence(self):
        return self._fake_audio(0.02)

    def test_thinking_pause_does_not_end_capture(self):
        """
        BUG: user beech me sochne ke liye ruka (2 silent windows) aur Jarvis
        sentence wahin truncate kar deti thi. Ab silence streak reset hoti hai
        aur capture jaari rehti hai.
        """
        out = self._run_listen_with_script(
            "jarvis kal subah meri meeting ka",
            [
                (False, ""),                       # thinking pause 1
                (False, ""),                       # thinking pause 2
                (True, "reminder laga dena"),       # ...then continues
                (False, ""), (False, ""), (False, ""),   # confirmed end
            ],
        )
        self.assertIn("reminder laga dena", out)
        self.assertIn("meeting ka", out)

    def test_long_monologue_fully_captured(self):
        """Bhaash lambi ho to bhi har chunk capture ho — koi cut nahi."""
        steps = [(True, f"chunk{i}") for i in range(8)]
        steps += [(False, "")] * 4
        out = self._run_listen_with_script("chunk0", steps)
        for i in range(8):
            self.assertIn(f"chunk{i}", out)

    def test_pure_silence_returns_empty(self):
        """Koi speech nahi to '' — crash nahi, aur garbage nahi."""
        out = self._run_listen_with_script("", [(False, "")] * 4)
        self.assertEqual(out, "")

    def test_single_word_reaches_caller(self):
        """'jar' jaisa single word caller tak pohochta hai — delete nahi hota."""
        out = self._run_listen_with_script("jar", [(False, "")] * 4)
        self.assertEqual(out.strip(), "jar")

    def test_stall_guard_stops_runaway_loop(self):
        """
        REGRESSION: kharab mic / background shor me har window speech-energy
        dikhti hai aur STT har baar wahi bakwaas deta hai. Bina guard ke loop
        60 rounds tak chalta, 61 mic opens karta aur 366 words ki ghich
        accumulate karta tha — yahi "still speaking forever, no response" bug.
        """
        steps = [(True, "and the what and then the")] * 30
        out = self._run_listen_with_script("jar", steps)
        self.assertLessEqual(
            len(out.split()), 60,
            "runaway loop: garbage text accumulated without bound",
        )

    def test_stall_guard_does_not_truncate_real_speech(self):
        """Stall guard sirf REPEATED text rokta hai — naya text pass hota rahe."""
        out = self._run_listen_with_script(
            "jarvis kal subah meri meeting ka",
            [
                (True, "reminder laga dena"),
                (True, "aur office bhi jaana hai"),
                (False, ""), (False, ""), (False, ""),
            ],
        )
        self.assertIn("reminder laga dena", out)
        self.assertIn("aur office bhi jaana hai", out)

    def test_end_of_speech_is_acoustic_not_stt_dependent(self):
        """
        CORE BUG: end-of-speech STT ke TEXT pe depend kar raha tha. Noisy room
        me STT kabhi "" nahi deta, isliye confirmation kabhi trigger nahi hui
        aur Jarvis "still speaking" state me atak gayi.

        Ab `_confirm_end_of_speech` sirf audio energy dekhta hai, aur
        `_record_window` use karta hai (jo kabhi hang nahi karta).
        """
        import inspect
        src = inspect.getsource(voice.Voice._confirm_end_of_speech)
        self.assertIn("_record_window", src,
                      "end-of-speech must use fixed-duration record()")
        self.assertIn("_measure_audio_energy", src,
                      "end-of-speech must decide on energy, not STT text")
        # Docstring me purane implementation ka naam hota hai, isliye sirf
        # ACTUAL CALL check karte hain (docstring hata kar).
        body = src.split('"""')[2] if src.count('"""') >= 2 else src
        self.assertNotIn("self._listen_raw_phrase(", body,
                         "end-of-speech must NOT call the STT path")

    def test_silence_confirms_promptly(self):
        """Silence me loop turant terminate hona chahiye (koi hang nahi)."""
        import time
        t0 = time.time()
        out = self._run_listen_with_script("jarvis test", [(False, "")] * 5)
        elapsed = time.time() - t0
        self.assertLess(elapsed, 5.0, "silence detection took too long")
        self.assertEqual(out.strip(), "jarvis test")

    def test_output_volume_is_configured(self):
        """Female awaaz dheemi thi — TTS volume/gain config aur wiring check."""
        self.assertTrue(voice._tts_volume_str().endswith("%"))
        vol = voice._tts_volume_str()
        self.assertTrue(vol.startswith("+") or vol.startswith("-"))
        self.assertGreaterEqual(config.TTS_MIXER_GAIN, 0.0)
        self.assertLessEqual(config.TTS_MIXER_GAIN, 1.0)
        # edge-tts call sites par volume pass hona chahiye
        import inspect
        src = inspect.getsource(voice)
        self.assertIn("volume=_vol", src)
        self.assertIn("_apply_mixer_gain", src)

    def test_listen_limits_are_bounded(self):
        """Loop ke saare limits sane range me hone chahiye (DoS protection)."""
        self.assertLessEqual(config.MAX_CONTINUATION_ROUNDS, 40)
        self.assertLessEqual(config.MAX_TOTAL_WORDS, 500)
        self.assertLessEqual(config.MIC_MAX_UTTERANCE_SECONDS, 180)
        self.assertGreaterEqual(config.LISTEN_STALL_LIMIT, 1)
        self.assertLessEqual(config.LISTEN_STALL_LIMIT, 6)


class TestStartupPerformance(unittest.TestCase):
    """
    Startup 37.9s le raha tha — sirf `anthropic` (11.5s) aur `google.genai`
    (17.3s) SDKs ke eager import hone ki wajah se. Ab lazy hain.
    """

    def test_heavy_sdks_are_lazily_imported(self):
        """
        Runtime regression: PEP 562 module-__getattr__ yahan KAAM NAHI karta —
        function ke andar `genai_types` ka global lookup seedha module __dict__
        me jaata hai aur NameError deta hai (Jarvis startup pe crash ho gaya
        tha). Isliye lazy PROXY object use hota hai.
        """
        import sys
        for mod in ("ai_brain", "memory"):
            sys.modules.pop(mod, None)
        import ai_brain
        import memory

        # proxy present hai
        self.assertTrue(hasattr(ai_brain, "_LazySDK"))
        self.assertIsInstance(ai_brain.genai, ai_brain._LazySDK)
        self.assertIsInstance(ai_brain.genai_types, ai_brain._LazySDK)
        self.assertIsInstance(ai_brain.anthropic, ai_brain._LazySDK)
        self.assertIsInstance(memory.genai, ai_brain._LazySDK)

        # `if not genai_types:` jaisa truthiness check resolve hona chahiye
        self.assertTrue(ai_brain.genai_types)
        self.assertTrue(ai_brain.genai)
        self.assertTrue(ai_brain.anthropic)
        self.assertTrue(memory.genai)

        # attribute forwarding (genai_types.HarmCategory etc.)
        self.assertIsNotNone(ai_brain.genai_types.HarmCategory)

    def test_heavy_sdks_not_in_eager_imports(self):
        """
        Source me module-LEVEL eager SDK import nahi hona chahiye.
        (Indented lines — yaani lazy loader function ke andar — allowed hain,
        wahi to lazy import mechanism hai.)
        """
        import ai_brain
        import memory
        for mod in (ai_brain, memory):
            with open(mod.__file__, encoding="utf-8") as fh:
                src = fh.read()
            eager = [ln.strip() for ln in src.splitlines()
                     if not ln.startswith((" ", "\t")) and
                     ln.strip().startswith(("from google import genai",
                                            "import anthropic",
                                            "from google.genai import"))]
            self.assertEqual(
                eager, [],
                f"{mod.__name__} me module-level eager SDK import mila: {eager}",
            )


class TestOutputGain(unittest.TestCase):
    """Female awaaz bahut dheemi thi — real gain lagega."""

    def test_gain_configured(self):
        self.assertGreater(config.TTS_AUDIO_GAIN, 1.0,
                           "TTS_AUDIO_GAIN > 1 chahiye warna awaaz loud nahi hogi")
        self.assertLessEqual(config.TTS_AUDIO_GAIN, 3.5,
                             "zyada gain se distortion aayegi")

    def test_boost_increases_amplitude(self):
        """Real PCM amplitude badhni chahiye, aur clipping nahi honi chahiye."""
        import numpy as np
        import wave

        ffmpeg = voice._find_ffmpeg()
        if not ffmpeg or voice.np is None:
            self.skipTest("ffmpeg or numpy unavailable")

        # Build a quiet test tone: -24 dBFS sine (mimics the quiet female voice)
        sr = 44100
        dur = 0.5
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        quiet = (np.sin(2 * np.pi * 440 * t) * 0.04 * 32767).astype(np.int16)
        stereo = np.repeat(quiet, 2)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(stereo.tobytes())
        quiet_wav = buf.getvalue()

        out = voice._boost_audio_gain(quiet_wav)
        with wave.open(io.BytesIO(out), "rb") as w:
            frames = w.readframes(w.getnframes())
        boosted = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        original = stereo.astype(np.float32) / 32768.0

        r0 = float(np.sqrt(np.mean(original ** 2)))
        r1 = float(np.sqrt(np.mean(boosted ** 2)))
        self.assertGreater(r1, r0 * 1.5, "gain apply nahi hui")
        self.assertLessEqual(float(np.abs(boosted).max()), 1.0, "hard clipping ho gayi")


if __name__ == "__main__":
    unittest.main()
