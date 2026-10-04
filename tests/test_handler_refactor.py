# -*- coding: utf-8 -*-
"""
tests/test_handler_refactor.py
=============================
`main.py` ke monolith ko `jarvis_handlers/` package me todne ke baad ki
regression tests.

Ye teen cheezein lock karti hain:

  1. Routing order  — `handle_text()` ka pipeline order wahi hai (interview
     mode pehle, fixed command match, follow-ups, brain, phir command dispatch)
  2. Follow-up rules — declarative table se wahi branch chalti hai jo pehle
     inline if/elif chain se chalti thi (haan / na / organize / extract / ...)
  3. Sentry registry — missing optional module ya failing start() se Jarvis
     crash nahi karta

Run:  venv\\Scripts\\python.exe -m pytest tests -v
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ===========================================================================
# Fakes — real Jarvis instance banane ki zaroorat nahi, sirf interface chahiye
# ===========================================================================


class FakeVoice:
    def speak(self, *args, **kwargs):
        return False

    def listen(self, *args, **kwargs):
        return ""


class FakeGui:
    state = "idle"

    def set_state(self, state):
        self.state = state

    def set_emotion(self, emotion):
        pass

    def show_message(self, text, ms=2800):
        pass

    def hide(self):
        pass

    def show(self):
        pass


class FakeAI:
    def __init__(self, available=True):
        self._available = available
        self.history = []

    def available(self):
        return self._available


class FakeRouterBase:
    """Stub feature handlers — sab kuch 'feature ne handle nahi kiya' bolte hain."""

    def _route_interview_mode(self, text):
        return False

    def _route_paralinguistic_event(self, text):
        return False

    def _route_macro(self, text, cmd_id):
        return False

    def file_release_requested(self, text):
        return False

    def clear_active_file(self):
        self.calls.append(("clear_active_file",))

    def handle_file_question(self, text):
        self.calls.append(("handle_file_question", text))
        return True

    def _run_custom_skill(self, text):
        return False

    def _press_shortcut(self, phrase):
        return False

    def _open_generic_app(self, clean_text):
        return False

    def _handle_explicit_vision(self, text):
        return False


class StubRouter:
    """Router ke saath-saath jo state/handlers chahiye — sab stubbed."""

    def __init__(self):
        self.gui = FakeGui()
        self.voice = FakeVoice()
        self.ai = FakeAI(False)
        self.spoken = []
        self.calls = []
        self.active_file = None
        self.video_mode = False
        self.dictation_mode = False
        self.running = True
        self._brain_handled = False

    # ---- stubs used by handle_text ----
    def speak(self, text, interruptible=True, emotion="calm", is_first_chunk=True):
        self.spoken.append(text)
        return False

    def listen(self, timeout=7, phrase_time_limit=10):
        return ""

    def dispatch_command(self, data, text, matched_trigger):
        self.calls.append(("dispatch_command", data["type"], data["action"]))
        if data["type"] == "info":
            return self.handle_info(data["action"])
        return True

    def handle_info(self, action):
        """Real handle_info ki tarah: 'sleep_assistant' session khatam karta hai."""
        self.calls.append(("handle_info", action))
        return action != "sleep_assistant"

    def _route_agentic_brain(self, text):
        self.calls.append(("brain", text))
        return self._brain_handled


def _build_router_class():
    """Real IntentRouterMixin + stubs — bina poore Jarvis ke sirf router test karne ke liye."""
    from jarvis_handlers.router import IntentRouterMixin
    return type("RouterUnderTest", (IntentRouterMixin, StubRouter), {})


RouterUnderTest = _build_router_class()


@pytest.fixture
def router():
    return RouterUnderTest()


# ===========================================================================
# 1. Routing order
# ===========================================================================


def test_router_has_stable_pipeline_steps():
    """handle_text ke comment-documented steps code me bhi usi order me hone chahiye."""
    import inspect

    from jarvis_handlers.router import IntentRouterMixin
    source = inspect.getsource(IntentRouterMixin.handle_text)
    order = [
        "_route_interview_mode",
        "_route_paralinguistic_event",
        "video_mode",
        "PRE_COMMAND_ROUTES",
        "find_command",
        "_route_macro",
        "followups.run",
        "inspect_clipboard_error",
        "PRE_BRAIN_ROUTES",
        "_run_custom_skill",
        "_route_agentic_brain",
        "POST_BRAIN_ROUTES",
        "dispatch_command",
    ]
    positions = [source.index(step) for step in order]
    assert positions == sorted(positions), f"pipeline order changed: {order}"


def test_matched_command_dispatches_by_type(router):
    router.handle_text("volume badhao")
    assert router.calls, f"expected a dispatch, got {router.calls}"
    kind, ctype, _action = router.calls[0]
    assert kind == "dispatch_command"
    assert ctype == "system"


def test_sleep_command_ends_session(router):
    """'so jao' -> sleep_assistant -> handle_text False return karta hai."""
    assert router.handle_text("so jao") is False


def test_unknown_text_falls_through_to_fallback_reply(router):
    router.handle_text("qwertyuiop asdfgh zxcvbn")
    assert any("Samajh nahi paayi" in s for s in router.spoken)


# ===========================================================================
# 2. Follow-up rules (pehle 9 inline copy-paste blocks the)
# ===========================================================================


class FakePendingOwner:
    """Ek sentry jaisa object: pending check + ek action."""

    def __init__(self, pending=True):
        self._pending = pending
        self.calls = []

    def has_pending_thing(self):
        return self._pending

    def do_the_thing(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return "Kaam ho gaya"

    def also_do_this(self):
        self.calls.append("also")
        return "Ye bhi ho gaya"


class FollowupJarvis:
    def __init__(self):
        self.voice = object()
        self.gui = object()
        self.spoken = []

    def speak(self, text, interruptible=True, emotion="calm", is_first_chunk=True):
        self.spoken.append((text, emotion))


def _install_fake_rule(monkeypatch, rule, owner):
    """followups.RULES me ek fake rule inject karo (module resolve monkeypatch)."""
    from jarvis_handlers import followups

    monkeypatch.setattr(followups.deps, "singleton",
                        lambda module_name, attr_name: owner
                        if module_name == rule.owner else None)


def test_followup_yes_branch_runs_action_and_speaks(monkeypatch):
    from jarvis_handlers.followups import Rule, Branch, run

    owner = FakePendingOwner(pending=True)
    rule = Rule("fake", "fake_module", "thing", "has_pending_thing",
                branches=[Branch(("haan", "karo"), "do_the_thing", speak_result=True)])
    _install_fake_rule(monkeypatch, rule, owner)

    jarvis = FollowupJarvis()
    assert run(jarvis, "haan karo", rules=(rule,)) is True
    assert owner.calls == [((), {})]
    assert jarvis.spoken == [("Kaam ho gaya", "happy")]


def test_followup_no_branch_is_distinct_from_yes(monkeypatch):
    from jarvis_handlers.followups import Rule, Branch, run

    owner = FakePendingOwner(pending=True)
    rule = Rule(
        "fake", "fake_module", "thing", "has_pending_thing",
        branches=[
            Branch(("haan",), "do_the_thing", args=(True,)),
            Branch(("nahi", "cancel"), "do_the_thing", args=(False,), speech="Theek hai"),
        ],
    )
    _install_fake_rule(monkeypatch, rule, owner)

    jarvis = FollowupJarvis()
    assert run(jarvis, "nahi karo", rules=(rule,)) is True
    assert owner.calls == [((False,), {})]
    assert jarvis.spoken == [("Theek hai", "happy")]


def test_followup_first_matching_branch_wins(monkeypatch):
    from jarvis_handlers.followups import Rule, Branch, run

    owner = FakePendingOwner(pending=True)
    rule = Rule(
        "fake", "fake_module", "thing", "has_pending_thing",
        branches=[
            Branch(("haan",), "do_the_thing", args=("first",)),
            Branch(("haan",), "also_do_this"),
        ],
    )
    _install_fake_rule(monkeypatch, rule, owner)

    jarvis = FollowupJarvis()
    assert run(jarvis, "haan", rules=(rule,)) is True
    assert owner.calls == [(("first",), {})]


def test_followup_not_triggered_when_nothing_pending(monkeypatch):
    from jarvis_handlers.followups import Rule, Branch, run

    owner = FakePendingOwner(pending=False)
    rule = Rule("fake", "fake_module", "thing", "has_pending_thing",
                branches=[Branch(("haan",), "do_the_thing")])
    _install_fake_rule(monkeypatch, rule, owner)

    jarvis = FollowupJarvis()
    assert run(jarvis, "haan", rules=(rule,)) is False
    assert owner.calls == []


def test_followup_action_failure_does_not_crash(monkeypatch):
    """Ek follow-up fail ho to agra rule/next step chalta hai — crash nahi."""
    from jarvis_handlers.followups import Rule, Branch, run

    class Exploding(FakePendingOwner):
        def do_the_thing(self, *args, **kwargs):
            raise RuntimeError("boom")

    owner = Exploding(pending=True)
    rule = Rule("fake", "fake_module", "thing", "has_pending_thing",
                branches=[Branch(("haan",), "do_the_thing", speak_result=True)])
    _install_fake_rule(monkeypatch, rule, owner)

    jarvis = FollowupJarvis()
    assert run(jarvis, "haan", rules=(rule,)) is False   # exception -> consume nahi hua
    assert jarvis.spoken == []


def test_all_shipped_followup_rules_have_branches_and_words():
    """Har registered rule kam se kam ek branch aur ek word rakhta hai."""
    from jarvis_handlers import followups

    assert len(followups.RULES) == 10
    for rule in followups.RULES:
        assert rule.branches, f"{rule.name} has no branches"
        for branch in rule.branches:
            assert branch.words, f"{rule.name}/{branch.method} has no trigger words"
            assert branch.method, f"{rule.name} has a branch without a method"


def test_learn_yes_words_do_not_leak_into_action_words():
    """
    Self-evolution aur predictive-copilot ki 'haan' lists jaan-boojh kar alag
    hain — 'likh do' sirf copilot ka action hai, skill-learning nahi.
    """
    from jarvis_handlers import prompts

    assert "likh do" in prompts.YES_ACTION
    assert "likh do" not in prompts.YES_LEARNING
    assert prompts.contains_any("likh do", prompts.YES_ACTION)
    assert not prompts.contains_any("likh do", prompts.YES_LEARNING)


# ===========================================================================
# 3. Keyword routes
# ===========================================================================


def test_keyword_routes_map_to_real_methods():
    from jarvis_handlers import keyword_routes
    from jarvis_handlers.core import JarvisCore

    for group in (keyword_routes.PRE_COMMAND_ROUTES,
                  keyword_routes.PRE_BRAIN_ROUTES,
                  keyword_routes.POST_BRAIN_ROUTES):
        assert group, "route group should not be empty"
        for route in group:
            assert hasattr(JarvisCore, route.handler), \
                f"{route.name} -> missing handler {route.handler}"


def test_route_dispatch_returns_handler_value():
    from jarvis_handlers import keyword_routes

    class Stub:
        def __init__(self):
            self.seen = []

        def _route_morning_briefing(self, text):
            self.seen.append(text)
            return False     # feature ne handle nahi kiya -> router aage badhe

    routes = (keyword_routes.Route("x", ("good morning",), "_route_morning_briefing"),)
    stub = Stub()
    assert keyword_routes.dispatch(stub, routes, "Good Morning Jarvis") is False
    assert stub.seen == ["Good Morning Jarvis"]
    assert keyword_routes.dispatch(stub, routes, "random unrelated sentence") is False


def test_route_handler_exception_is_contained():
    from jarvis_handlers import keyword_routes

    class Stub:
        def _route_boom(self, text):
            raise RuntimeError("feature down")

    routes = (keyword_routes.Route("boom", ("trigger",), "_route_boom"),)
    assert keyword_routes.dispatch(Stub(), routes, "please trigger this") is False


def test_game_route_exists_in_both_priority_groups():
    """Game synthesis ki keyword list dono tables me hai (purani behaviour)."""
    from jarvis_handlers import keyword_routes

    pre = {r.name for r in keyword_routes.PRE_COMMAND_ROUTES}
    post = {r.name for r in keyword_routes.POST_BRAIN_ROUTES}
    assert "game_synthesizer" in pre
    assert "game_synthesizer" in post


# ===========================================================================
# 4. Sentry registry — missing module / failing start se crash nahi
# ===========================================================================


def test_sentries_start_skips_missing_modules(monkeypatch):
    from jarvis_handlers import sentries

    started = []

    class Good:
        def start(self, **kwargs):
            started.append("good")

        def stop(self):
            started.append("good-stop")

    class Bad:
        def start(self, **kwargs):
            raise RuntimeError("start failed")

        def stop(self):
            raise RuntimeError("stop failed")

    fake_specs = (
        sentries.SentrySpec("missing", "nope_module", "thing"),
        sentries.SentrySpec("good", "good_module", "thing"),
        sentries.SentrySpec("bad", "bad_module", "thing"),
    )
    monkeypatch.setattr(sentries, "SENTRIES", fake_specs)
    monkeypatch.setattr(sentries, "STOP_ORDER", ("missing", "good", "bad"))
    monkeypatch.setattr(sentries, "_BY_NAME", {s.name: s for s in fake_specs})
    monkeypatch.setattr(sentries.deps, "singleton",
                        lambda m, a: {"good_module": Good(), "bad_module": Bad()}.get(m))

    sentries.start_all(voice="v", ai="a", gui="g", speak_fn="s")
    assert started == ["good"]          # bad wala start fail hua, good chala

    started.clear()
    sentries.stop_all()
    assert started == ["good-stop"]     # failing stop ne bhi aage nahi roka


def test_shipped_sentry_specs_match_real_module_signatures():
    """Registry ke start_kwargs real sentry signatures se match karne chahiye."""
    import inspect

    from jarvis_handlers import sentries

    for spec in sentries.SENTRIES:
        instance = spec.resolve()
        assert instance is not None, f"{spec.name} failed to resolve"
        params = inspect.signature(instance.start).parameters
        for kwarg in spec.start_kwargs:
            assert kwarg in params, f"{spec.name}.start() does not accept '{kwarg}'"
        assert spec.start_kwargs == () or "voice" in params or spec.hard


def test_stop_order_covers_every_started_sentry_that_has_stop():
    from jarvis_handlers import sentries

    for name in sentries.STOP_ORDER:
        assert name in {s.name for s in sentries.SENTRIES}, f"{name} not in SENTRIES"


# ===========================================================================
# 5. Param extraction + patterns (command dispatch ka core)
# ===========================================================================


def test_extract_param_strips_trigger_and_fillers():
    from jarvis_handlers.command_dispatch import CommandDispatchMixin

    extract = CommandDispatchMixin._extract_param
    assert extract("gaana chalao kesariya", "gaana chalao") == "kesariya"
    assert extract("youtube chalao", "youtube chalao") == ""
    assert extract("", "trigger") == ""


def test_generic_app_and_shortcut_patterns():
    from jarvis_handlers import text_patterns

    assert text_patterns.OPEN_APP_PATTERN.match("spotify kholo").group(1).strip() == "spotify"
    assert text_patterns.SHORTCUT_PATTERN.match("ctrl c dabao").group(1).strip() == "ctrl c"


def test_destructive_commands_still_ask_confirmation():
    """'confirm': True wale commands confirm ke bina execute nahi hone chahiye."""
    from jarvis_handlers.command_dispatch import CommandDispatchMixin

    executed = []

    class Stub(CommandDispatchMixin):
        def __init__(self):
            self.voice = FakeVoice()

        def speak(self, *args, **kwargs):
            pass

        def listen(self, timeout=None, phrase_time_limit=None):
            return "haan kar do"

    stub = Stub()
    data = {"type": "system", "action": "shutdown_pc", "confirm": True}

    class Executor:
        @staticmethod
        def shutdown_pc(voice, **kwargs):
            executed.append(kwargs)

    CommandDispatchMixin._run_executor(stub, Executor, data, "shutdown_pc",
                                      "shutdown kar do", "shutdown kar do")
    assert executed, "confirmed command should execute"