# -*- coding: utf-8 -*-
"""
agentic_cot_brain.py
====================
Autonomous Chain-of-Thought (ReAct) Decision & Reasoning Engine for Jarvis.

Instead of rigid if-else rule matching, this brain:
1. Ingests User Query + Live Desktop Snapshot + Associative Memory
2. Generates explicit multi-step Chain-of-Thought (CoT) Reasoning & Action Plan
3. Autonomously selects, chains, and executes tools across the entire system
4. Observes execution feedback and synthesizes fluid, conversational responses.
"""

import os
import sys
import json
import time
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None


@dataclass
class AgentStep:
    thought: str
    plan: List[str]
    action_name: Optional[str] = None
    action_args: Dict[str, Any] = field(default_factory=dict)
    response_text: str = ""
    emotion: str = "calm"


SYSTEM_COT_PROMPT = """You are JARVIS, an autonomous, highly intelligent AI assistant inspired by Tony Stark's JARVIS.
You do NOT simply match hardcoded commands. You operate with an autonomous Chain-of-Thought (CoT) Reasoning Engine.

When the user gives a request (in English, Hindi, or Hinglish):
1. Reason deeply about the user's intent, current desktop state, and memory context.
2. Formulate a step-by-step Execution Plan.
3. Determine if an action/tool needs to be called, or if this is conversational/analytical reasoning.
4. Respond in structured JSON matching this exact schema:

{
  "thought": "Brief step-by-step internal reasoning explaining why you chose this action.",
  "plan": ["Step 1: ...", "Step 2: ..."],
  "action": "tool_name_or_none",
  "args": { "param1": "value" },
  "response": "Fluid, natural Hinglish reply to speak to the user with [emotion] prefix (e.g. [happy], [calm], [excited], [serious])."
}

AVAILABLE TOOLS:
- 'open_app': { "app_name": "notepad|vscode|spotify|calculator|chrome|..." }
- 'open_url': { "url": "https://..." }
- 'web_search': { "query": "search query" }
- 'compare_prices': { "product": "product name" }
- 'travel_route': { "origin": "city1", "destination": "city2", "mode": "train|bus|car|flight" }
- 'read_screen': { "question": "specific visual question about the screen" }
- 'system_control': { "action": "volume_up|volume_down|mute|lock|screenshot|battery_check" }
- 'avengers_diagnostics': {}
- 'send_whatsapp': { "phone": "number", "message": "text" }
- 'learn_new_skill': { "task_description": "detailed task" }
- 'none': (Use when user is chatting, asking a question, discussing concepts, coding help, or general talk)

Always maintain a witty, capable, and respectful JARVIS personality. Output ONLY valid JSON.
"""


class AgenticCotBrain:
    def __init__(self):
        self._gemini_client = None
        self._init_client()

    def _init_client(self):
        api_key = getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        if genai and api_key:
            try:
                self._gemini_client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"[agentic_cot_brain] Client init error: {e}")

    def reason_and_plan(self, user_text: str, context: str = "") -> AgentStep:
        """
        Executes Chain-of-Thought reasoning loop on the user input.
        """
        if not self._gemini_client:
            self._init_client()

        if not self._gemini_client:
            return AgentStep(
                thought="Gemini API Key missing or client offline.",
                plan=["Direct fallback response"],
                action_name=None,
                response_text="AI Engine offline hai. Kripya config.py mein apni API key check kijiye.",
                emotion="concerned"
            )

        prompt_contents = f"LIVE DESKTOP & MEMORY CONTEXT:\n{context}\n\nUSER COMMAND / INPUT:\n\"{user_text}\""

        try:
            gen_config = genai_types.GenerateContentConfig(
                system_instruction=SYSTEM_COT_PROMPT,
                max_output_tokens=1000,
                temperature=0.2,
                response_mime_type="application/json"
            )

            response = self._gemini_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt_contents,
                config=gen_config
            )

            raw_json = response.text.strip()
            data = json.loads(raw_json)

            thought = data.get("thought", "Autonomous reasoning completed.")
            plan = data.get("plan", [])
            action = data.get("action")
            action_name = action if (action and action.lower() != "none") else None
            args = data.get("args", {})
            raw_response = data.get("response", "Ji boss, maine samajh liya.")

            # Extract emotion
            emotion = "calm"
            clean_resp = raw_response
            emo_match = re.match(r"^\s*\[(\w+)\]\s*", raw_response)
            if emo_match:
                emotion = emo_match.group(1).lower()
                clean_resp = raw_response[emo_match.end():].strip()

            step = AgentStep(
                thought=thought,
                plan=plan,
                action_name=action_name,
                action_args=args,
                response_text=clean_resp,
                emotion=emotion
            )

            self._log_cot_trace(step, user_text)
            return step

        except Exception as e:
            print(f"[agentic_cot_brain] Reasoning error: {e}")
            return AgentStep(
                thought=f"Exception during reasoning: {e}",
                plan=["Fallback to natural conversation"],
                action_name=None,
                response_text="Main is par dhyan de rahi hoon, boliye boss.",
                emotion="calm"
            )

    def execute_step_action(self, step: AgentStep, jarvis_instance=None) -> bool:
        """
        Executes the autonomous tool selected during Chain-of-Thought reasoning.
        """
        if not step.action_name:
            return False

        tool = step.action_name.lower().strip()
        args = step.action_args or {}
        print(f"[agentic_cot_brain] [*] Executing Autonomous Tool: '{tool}' with args: {args}")

        try:
            if tool == "open_app":
                app_name = args.get("app_name", "")
                if app_name:
                    import commands.system_commands as sys_cmd
                    sys_cmd.open_any_app(getattr(jarvis_instance, "voice", None), name=app_name)
                    return True

            elif tool == "open_url":
                url = args.get("url", "")
                if url:
                    import webbrowser
                    webbrowser.open(url)
                    return True

            elif tool == "web_search":
                query = args.get("query", "")
                if query:
                    import universal_web_operator
                    universal_web_operator.web_operator.voice = getattr(jarvis_instance, "voice", None)
                    universal_web_operator.web_operator.run_web_research(query)
                    return True

            elif tool == "compare_prices":
                product = args.get("product", "")
                if product:
                    import universal_web_operator
                    universal_web_operator.web_operator.voice = getattr(jarvis_instance, "voice", None)
                    universal_web_operator.web_operator.compare_ecommerce_prices(product)
                    return True

            elif tool == "travel_route":
                import google_maps_travel_hub
                google_maps_travel_hub.travel_hub.voice = getattr(jarvis_instance, "voice", None)
                google_maps_travel_hub.travel_hub.ai = getattr(jarvis_instance, "ai", None)
                google_maps_travel_hub.travel_hub.gui = getattr(jarvis_instance, "gui", None)
                query_str = f"{args.get('origin', '')} to {args.get('destination', '')} {args.get('mode', '')}"
                google_maps_travel_hub.travel_hub.answer_travel_query(query_str)
                return True

            elif tool == "system_control":
                action = args.get("action", "")
                import commands.system_commands as sys_cmd
                v = getattr(jarvis_instance, "voice", None)
                if action == "volume_up": sys_cmd.volume_up(v)
                elif action == "volume_down": sys_cmd.volume_down(v)
                elif action == "mute": sys_cmd.mute_volume(v)
                elif action == "lock": sys_cmd.lock_screen(v)
                elif action == "screenshot": sys_cmd.take_screenshot(v)
                elif action == "battery_check": sys_cmd.battery_status(v)
                return True

            elif tool == "avengers_diagnostics":
                import avengers_protocol
                avengers_protocol.protocol.execute_assemble_protocol(
                    voice=getattr(jarvis_instance, "voice", None),
                    ai=getattr(jarvis_instance, "ai", None),
                    gui=getattr(jarvis_instance, "gui", None)
                )
                return True

            elif tool == "send_whatsapp":
                import commands.whatsapp_commands as wa_cmd
                phone = args.get("phone", "")
                msg = args.get("message", "")
                if phone and msg:
                    wa_cmd.send_whatsapp_message(getattr(jarvis_instance, "voice", None), phone=phone, message=msg)
                    return True

            elif tool == "learn_new_skill":
                import self_evolution_engine
                task = args.get("task_description", "")
                if task:
                    self_evolution_engine.evolution_engine.triage_missing_skill(task)
                    return True

        except Exception as e:
            print(f"[agentic_cot_brain] Tool execution error for '{tool}': {e}")

        return False

    def _log_cot_trace(self, step: AgentStep, query: str):
        """Displays formatted Chain-of-Thought visualization in terminal (Windows ASCII safe)."""
        safe_q = query.encode('ascii', 'ignore').decode()
        safe_thought = step.thought.encode('ascii', 'ignore').decode()
        safe_resp = step.response_text.encode('ascii', 'ignore').decode()

        print("\n" + "=" * 65)
        print("[*] [AGENTIC CHAIN-OF-THOUGHT REASONING TRACE]")
        print("=" * 65)
        print(f"[*] User Input   : \"{safe_q}\"")
        print(f"[*] Reasoning    : {safe_thought}")
        if step.plan:
            print("[*] Action Plan  :")
            for p in step.plan:
                safe_p = p.encode('ascii', 'ignore').decode()
                print(f"   - {safe_p}")
        if step.action_name:
            print(f"[*] Selected Tool: '{step.action_name}' | Args: {step.action_args}")
        else:
            print("[*] Response Mode: Conversational / Direct Synthesis")
        print(f"[*] Speech Output: [{step.emotion}] \"{safe_resp}\"")
        print("=" * 65 + "\n")


cot_brain = AgenticCotBrain()
