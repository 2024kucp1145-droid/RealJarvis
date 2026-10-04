# -*- coding: utf-8 -*-
"""
feature_routes.py
=================
`keyword_routes.py` table ke handlers — yaani wo features jo user ke *bale
sentence* se trigger hote hain (fixed command table se nahi).

Har handler ka contract simple hai:
    True  -> feature ne sentence handle kar li (router yahin ruk jata hai)
    False -> feature available nahi tha ya kuch predict nahi hua — router
             apna agla step try kare

Optional feature modules import time par fail ho sakte hain, isliye har handler
apna module import karta hai (startup pe sab load karne ka koi matlab nahi —
sirf ek feature chahiye toh bas wahi import ho).
"""

from .optional_deps import deps


class FeatureRoutesMixin:
    """Keyword-triggered features (games, scouting, travel, briefing, ...)."""

    # ------------------------------------------------------------------- games
    def _route_game_synthesizer(self, text: str) -> bool:
        """Browser me chalne wala game synthesize karke launch karo."""
        import game_synthesizer
        game_synthesizer.synthesizer.synthesize_custom_game(text)
        self.speak("Boss, maine game synthesize karke aapke browser mein launch kar diya "
                   "hai. Enjoy kijiye!", emotion="excited")
        return True

    def _route_dots_browser(self, text: str) -> bool:
        """Dots stealth (anti-bot) browser agent launch karo."""
        import dots_browser_agent
        agent = dots_browser_agent.dots_agent
        agent.voice = self.voice
        agent.ai = self.ai
        agent.gui = self.gui
        agent.launch_browser("https://www.google.com")
        return True

    # ------------------------------------------------------------ productivity
    def _route_predictive_copilot(self, text: str) -> bool:
        """Current workflow analyze karke agla step predict karo."""
        import universal_predictive_copilot
        prediction = universal_predictive_copilot.predictive_copilot.analyze_and_predict(text)
        if not prediction:
            return False
        self.speak(prediction.speech_summary, emotion="excited")
        return True

    def _route_avengers_protocol(self, text: str) -> bool:
        """Full system diagnostic — sab components ka status."""
        import avengers_protocol
        avengers_protocol.protocol.execute_assemble_protocol(
            voice=self.voice, ai=self.ai, gui=self.gui)
        return True

    def _route_morning_briefing(self, text: str) -> bool:
        """Daily morning intelligence briefing (on-demand)."""
        sentry = deps.singleton("morning_briefing_sentry", "briefing_sentry")
        if sentry is None:
            return False
        sentry.voice = self.voice
        sentry.ai = self.ai
        sentry.gui = self.gui
        sentry.deliver_briefing(is_auto=False)
        return True

    def _route_web_operator(self, text: str) -> bool:
        """Autonomous web operator — price compare, search, agentic tasks."""
        import universal_web_operator
        operator = universal_web_operator.web_operator
        operator.voice = self.voice
        operator.ai = self.ai
        operator.gui = self.gui
        result = operator.execute_web_goal(text)
        return bool(result and result.get("success"))

    def _route_travel_hub(self, text: str) -> bool:
        """Google Maps / travel queries (route, distance, trains, flights)."""
        import google_maps_travel_hub
        hub = google_maps_travel_hub.travel_hub
        hub.voice = self.voice
        hub.ai = self.ai
        hub.gui = self.gui
        return bool(hub.answer_travel_query(text))

    # --------------------------------------------------------- self-evolution
    def _route_learn_skill(self, text: str) -> bool:
        """"seekh lo" — nayi skill triage karo (code likhna, scan, sandbox)."""
        engine = deps.singleton("self_evolution_engine", "evolution_engine")
        if engine is not None:
            engine.triage_missing_skill(text)
        return True

    def _route_skills_manual(self, text: str) -> bool:
        """Learned skills ka user manual open karo."""
        import skills_manual_manager
        if not skills_manual_manager.manual_manager.open_manual():
            return False
        self.speak("Boss, maine learned skills ka complete manual screen par open kar diya "
                   "hai. Aap wahan se sabhi voice commands aur unka use padh sakte hain.",
                   emotion="happy")
        return True

    def _route_skill_scout(self, text: str) -> bool:
        """Naye skill proposals laao (scout engine)."""
        import skill_scout_engine
        skill_scout_engine.scout_engine.present_proposals_vocally(
            voice=self.voice, gui=self.gui, force_fresh=True)
        return True

    def _route_skill_scout_next(self, text: str) -> bool:
        """Scout ka next proposal batch dikhao ("kuch aur")."""
        import skill_scout_engine
        skill_scout_engine.scout_engine.cycle_to_next_batch(voice=self.voice, gui=self.gui)
        return True

    def _route_skill_scout_previous(self, text: str) -> bool:
        """Pichla un-chosen batch dobara dikhao."""
        import skill_scout_engine
        skill_scout_engine.scout_engine.present_previous_unchosen(voice=self.voice, gui=self.gui)
        return True

    def _route_skill_dashboard(self, text: str) -> bool:
        """Skills ka summary bol do + dashboard GUI kholo."""
        import skill_dashboard
        self.speak(skill_dashboard.dashboard.get_summary_speech(), emotion="happy")
        try:
            if self.gui and hasattr(self.gui, "root"):
                self.gui.root.after(
                    0, lambda: skill_dashboard.dashboard.open_dashboard_gui(self.gui.root))
        except Exception:  # noqa: BLE001 - GUI optional hai, speech par focus
            pass
        return True