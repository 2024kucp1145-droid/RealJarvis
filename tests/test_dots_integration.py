# -*- coding: utf-8 -*-
"""
test_dots_integration.py
========================
Tests for Dots & Invisible-Playwright stealth browser integration in Real Jarvis.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from command_data import find_command
import dots_browser_agent


class TestDotsIntegration(unittest.TestCase):
    def test_dots_agent_module_loads(self):
        self.assertIsNotNone(dots_browser_agent.dots_agent)
        self.assertTrue(dots_browser_agent.dots_agent.is_available())

    def test_dots_configuration(self):
        self.assertTrue(hasattr(config, "DOTS_ENABLED"))
        self.assertTrue(hasattr(config, "DOTS_PORT"))
        self.assertEqual(config.DOTS_PORT, 8766)

    def test_dots_voice_triggers(self):
        # Trigger 1: "dots chalu karo"
        cmd_id, data, trigger = find_command("dots chalu karo")
        self.assertEqual(cmd_id, "launch_dots_ui")
        self.assertEqual(data["type"], "dots")
        self.assertEqual(data["action"], "launch_dots_ui")

        # Trigger 2: "stealth browser kholo"
        cmd_id, data, trigger = find_command("stealth browser kholo")
        self.assertEqual(cmd_id, "launch_dots_ui")

        # Trigger 3: "stealth search karo best laptop"
        cmd_id, data, trigger = find_command("stealth search karo best laptop")
        self.assertEqual(cmd_id, "stealth_search")
        self.assertEqual(data["type"], "dots")

    def test_stealth_compare_prices_structure(self):
        res = dots_browser_agent.dots_agent.stealth_compare_prices("iphone 15")
        self.assertTrue(res.get("success"))
        self.assertIn("flipkart.com", res.get("flipkart_url", ""))
        self.assertIn("amazon.in", res.get("amazon_url", ""))


if __name__ == "__main__":
    unittest.main()
