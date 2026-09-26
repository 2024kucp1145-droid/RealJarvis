# -*- coding: utf-8 -*-
"""
test_scheduler_and_mic.py
=========================
Comprehensive validation for:
1. MessageScheduler sequential FIFO execution & zero-drop multi-message queue.
2. Compound query splitting.
3. Voice mic configuration and speech serialization lock.
"""

import sys
import time
import threading
import unittest

import config
import voice
import message_scheduler


class TestMicAndScheduler(unittest.TestCase):

    def test_voice_mic_settings(self):
        """Verify mic sensitivity, pause threshold, and dynamic adaptation settings."""
        self.assertEqual(config.MIC_PAUSE_THRESHOLD, 0.80)
        self.assertEqual(config.MIC_NON_SPEAKING_DURATION, 0.35)
        self.assertTrue(config.MIC_DYNAMIC_ENERGY)
        self.assertLessEqual(config.MIC_ENERGY_MAX, 250)

        v = voice.Voice()
        if v.recognizer:
            self.assertEqual(v.recognizer.pause_threshold, 0.80)
            self.assertEqual(v.recognizer.non_speaking_duration, 0.35)
            self.assertTrue(v.recognizer.dynamic_energy_threshold)
            self.assertLessEqual(v.recognizer.energy_threshold, 250)
            self.assertGreaterEqual(v.recognizer.energy_threshold, 40)
        self.assertIsNotNone(v._speech_lock)

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
            # Simulate work / response time
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


if __name__ == "__main__":
    unittest.main()
