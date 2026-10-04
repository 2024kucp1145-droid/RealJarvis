# -*- coding: utf-8 -*-
"""
keyword_routes.py
=================
Keyword-triggered handlers ka declarative table.

`handle_text()` me same pattern 12 baar repeat tha:

    if any(w in clean_lower for w in ("...", "...")):
        import something
        something.do_thing(text)
        return True

Ab har trigger ek `Route` hai: keywords + handler method name. Router sirf
table iterate karta hai, handler `self` par hota hai.

Teen groups hain, aur order matter karta hai:

  PRE_COMMAND  — `find_command()` se *pehle* (highest priority)
  PRE_BRAIN    — AI brain router se *pehle*
  POST_BRAIN   — AI brain router ke *baad* (brain ne handle nahi kiya)

Route handler `True` return karta hai = sentence consume ho gayi.
"""

from dataclasses import dataclass
from typing import Tuple

from .prompts import matches, normalize


@dataclass(frozen=True)
class Route:
    name: str
    keywords: Tuple[str, ...]
    handler: str      # Jarvis class ka method name


# --------------------------------------------------------------------------
# find_command() se pehle — inko fixed command table se bhi zyada priority hai
# --------------------------------------------------------------------------
PRE_COMMAND_ROUTES: Tuple[Route, ...] = (
    Route("game_synthesizer", (
        "game bana", "game chalu", "game generate", "subway surfer",
        "subway surfers", "3d runner", "snake game", "space shooter",
        "shooter game", "racing game", "flappy bird", "puzzle game",
        "play game", "arcade game",
    ), "_route_game_synthesizer"),
    Route("dots_stealth_browser", (
        "dots chalu", "dots kholo", "stealth browser", "stealth agent",
        "anti bot browser", "dots agent",
    ), "_route_dots_browser"),
)

# --------------------------------------------------------------------------
# AI brain router se pehle
# --------------------------------------------------------------------------
PRE_BRAIN_ROUTES: Tuple[Route, ...] = (
    Route("predictive_copilot", (
        "next step", "agla step", "aage kya", "suggest step",
        "predict workflow", "mera kaam dekho", "workflow suggest", "aage ka step",
    ), "_route_predictive_copilot"),
    Route("avengers_protocol", (
        "avengers assemble", "avenger assemble", "avengers ready",
        "assemble avengers", "system diagnostics", "all systems check",
        "system health check",
    ), "_route_avengers_protocol"),
    Route("self_evolution_learning", (
        "naya skill seekho", "naya feature seekho", "ye kaam seekh lo",
        "ye automate karo", "naya skill banao", "seekh lo",
    ), "_route_learn_skill"),
    Route("skills_manual", (
        "skills manual", "skill manual", "manual kholo", "manual khol do",
        "manual dikhao", "skills guide", "custom skills manual", "skills document",
    ), "_route_skills_manual"),
    Route("skill_scout_discovery", (
        "naye skills dhundo", "naye skills propose", "skills propose",
        "propose skills", "skills scout karo", "scout skills",
    ), "_route_skill_scout"),
    Route("skill_scout_next_batch", (
        "kuch aur skills", "kuch aur dikhao", "kuch naya batao", "ye nahi chahiye",
        "next skills", "kuch aur skill", "aur skills dikhao", "doosri skills",
        "kuch aur",
    ), "_route_skill_scout_next"),
    Route("skill_scout_previous", (
        "previous kaun si thi", "purani skills", "purani list", "previous skills",
        "jo choose nahi ki", "jo dikhayi thi", "pehle wali skills", "unchosen skills",
    ), "_route_skill_scout_previous"),
    Route("skill_dashboard", (
        "kya kya seekha", "kya seekha", "learned skills", "skills batao",
        "apne skills", "skills dashboard", "show skills",
    ), "_route_skill_dashboard"),
)

# --------------------------------------------------------------------------
# AI brain router ke baad
# --------------------------------------------------------------------------
POST_BRAIN_ROUTES: Tuple[Route, ...] = (
    Route("morning_briefing", (
        "good morning", "morning briefing", "daily briefing", "aaj ka update",
        "morning update", "stark briefing", "aaj ka schedule", "morning report",
    ), "_route_morning_briefing"),
    Route("universal_web_operator", (
        "compare price", "price check", "flipkart", "amazon", "leetcode problem",
        "search on google", "web operator",
    ), "_route_web_operator"),
    Route("google_maps_travel", (
        "google map", "route dikhao", "kitna time lagta", "se jaipur", "to jaipur",
        "train dikhao", "bus dikhao", "flight dikhao", "travel time", "kaise jaye",
        "kaise jaana", "rasta dikhao", "maps", "distance batao",
    ), "_route_travel_hub"),
    # Same handler as PRE_COMMAND, slightly different (older) keyword list —
    # dono jagah chalti thi, isliye dono tables me entry rakhi hai.
    Route("game_synthesizer", (
        "subway surfer", "subway surfers", "3d game", "runner game", "game bana",
        "game chalu karo", "game generate", "snake game", "space game",
        "shooter game", "play game", "arcade game",
    ), "_route_game_synthesizer"),
)


def first_match(routes: Tuple[Route, ...], text: str):
    """Pehla route jiske keywords text me mile, ya None."""
    text_lower = normalize(text.strip())
    for route in routes:
        if matches(text_lower, route.keywords):
            return route
    return None


def dispatch(jarvis, routes: Tuple[Route, ...], text: str) -> bool:
    """
    Matching route ka handler chalao.
    True  -> handler ne sentence consume kar liya
    False -> koi route match nahi (ya handler ne handle na kiya)
    """
    route = first_match(routes, text)
    if route is None:
        return False
    try:
        return bool(getattr(jarvis, route.handler)(text))
    except Exception as exc:  # noqa: BLE001 - ek feature fail ho toh aage badho
        print(f"[route:{route.name}] failed: {exc}")
        return False