# -*- coding: utf-8 -*-
"""
agentic_cot_brain.py
====================
Autonomous Cognitive Super-Brain for Real Jarvis (Phase 1).

Features:
1. Multi-Tier Model Cascade:
   Primary 'gemini-flash-latest' -> Fallback 'gemini-2.5-flash-lite' -> 'gemini-pro-latest'.
2. Metacognitive Self-Reflection & Auto-Recovery:
   When any tool execution encounters an error, the brain reflects on the failure
   and attempts an alternative execution path instead of crashing or giving up.
3. Expanded Autonomous Tool Suite:
   System controls, apps, browser, vision/screen, terminal, files, travel, whatsapp, skills.
4. Continuous Episodic & Fact Memory Linking:
   Seamlessly integrates user facts and past conversations from memory.py.
"""

import os
import sys
import json
import time
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

try:
    import memory
except ImportError:
    memory = None

try:
    import platform_compat
except ImportError:
    platform_compat = None


@dataclass
class AgentStep:
    thought: str
    plan: List[str]
    action_name: Optional[str] = None
    action_args: Dict[str, Any] = field(default_factory=dict)
    response_text: str = ""
    emotion: str = "calm"
    recovery_attempted: bool = False


SYSTEM_COT_PROMPT = """You are JARVIS, an autonomous, highly intelligent AI agent inspired by Tony Stark's JARVIS.
You operate with a dynamic Chain-of-Thought (CoT) Cognitive Decision Engine.

When the user gives a request (in English, Hindi, or Hinglish):
1. Reason deeply about the user's intent, current desktop state, and memory context.
2. Formulate a step-by-step Execution Plan.
3. Determine if an action/tool needs to be called, or if this is conversational/analytical reasoning.
4. Respond in structured JSON matching this exact schema:

{
  "thought": "Step-by-step internal reasoning explaining why you chose this action.",
  "plan": ["Step 1: ...", "Step 2: ..."],
  "action": "tool_name_or_none",
  "args": { "param1": "value" },
  "response": "Fluid, natural Hinglish or English reply with [emotion] prefix (e.g. [happy], [calm], [excited], [serious], [concerned])."
}

AVAILABLE TOOLS:
- 'open_app': { "app_name": "notepad|vscode|spotify|calculator|chrome|..." }
- 'open_url': { "url": "https://..." }
- 'web_search': { "query": "search query" }
- 'compare_prices': { "product": "product name" }
- 'travel_route': { "origin": "city1", "destination": "city2", "mode": "train|bus|car|flight" }
- 'read_screen': { "question": "specific visual question about the screen" }
- 'system_control': { "action": "volume_up|volume_down|volume_mute|volume_unmute|lock|shutdown|restart|sleep|screenshot|battery_check|ram_check|storage_check|brightness_up|brightness_down" }
- 'execute_terminal_cmd': { "command": "shell command to run safely" }
- 'create_or_edit_file': { "filename": "filename.ext", "content": "content to write" }
- 'avengers_diagnostics': {}
- 'send_whatsapp': { "phone": "number", "message": "text" }
- 'learn_new_skill': { "task_description": "detailed task" }
- 'computer_use': { "goal": "autonomous screen automation goal like fill form, click element, extract table" }
- 'propose_daily_skills': {}
- 'approve_skill': { "skill_number": 1 }
- 'none': (Use when user is chatting, asking questions, discussing concepts, coding help, or general talk)

Always maintain a witty, capable, and respectful JARVIS personality. Output ONLY valid JSON.
"""


class AgenticCotBrain:
    def __init__(self):
        self._gemini_client = None
        self._model_cascade = [
            getattr(config, "GEMINI_MODEL", "gemini-flash-latest"),
            "gemini-flash-latest",
            "gemma-4-26b-a4b-it",
            "gemma-4-31b-it"
        ]
        # De-duplicate cascade order
        seen = set()
        self._model_cascade = [m for m in self._model_cascade if m and not (m in seen or seen.add(m))]
        self._active_model_index = 0
        self._init_client()

    def _init_client(self):
        api_key = getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        if genai and api_key:
            try:
                self._gemini_client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"[agentic_cot_brain] Client init error: {e}")

    def get_current_model(self) -> str:
        if self._active_model_index < len(self._model_cascade):
            return self._model_cascade[self._active_model_index]
        return "gemini-flash-latest"

    def rotate_model(self) -> str:
        self._active_model_index = (self._active_model_index + 1) % len(self._model_cascade)
        next_model = self.get_current_model()
        print(f"[agentic_cot_brain] [*] Rotating AI Brain to model: '{next_model}'")
        return next_model

    def reason_and_plan(self, user_text: str, context: str = "") -> AgentStep:
        """
        Executes Chain-of-Thought reasoning with automatic multi-model fallback cascade.
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

        # Inject long-term user profile facts if available
        user_facts_str = ""
        if memory and hasattr(memory, "get_all_facts"):
            try:
                facts = memory.get_all_facts()
                if facts:
                    fact_lines = [f"- {k}: {v}" for k, v in list(facts.items())[:8]]
                    user_facts_str = "KNOWN USER PROFILE & FACTS:\n" + "\n".join(fact_lines) + "\n\n"
            except Exception:
                pass

        prompt_contents = f"{user_facts_str}LIVE DESKTOP & MEMORY CONTEXT:\n{context}\n\nUSER COMMAND / INPUT:\n\"{user_text}\""

        # Try models in cascade
        attempts = 0
        max_attempts = len(self._model_cascade)
        last_error = None

        while attempts < max_attempts:
            current_model = self.get_current_model()
            try:
                gen_config = genai_types.GenerateContentConfig(
                    system_instruction=SYSTEM_COT_PROMPT,
                    max_output_tokens=1000,
                    temperature=0.2,
                    response_mime_type="application/json"
                )

                response = self._gemini_client.models.generate_content(
                    model=current_model,
                    contents=prompt_contents,
                    config=gen_config
                )

                raw_json = response.text.strip()
                # Clean markdown fences if model outputs ```json ... ```
                if raw_json.startswith("```"):
                    raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json, flags=re.I)
                    raw_json = re.sub(r"\s*```$", "", raw_json)
                data = json.loads(raw_json.strip())
                if isinstance(data, list):
                    data = data[0] if data else {}

                thought = data.get("thought", "Autonomous reasoning completed.")
                plan = data.get("plan", [])
                action = data.get("action")
                action_name = action if (action and action.lower() != "none") else None
                args = data.get("args", {})
                raw_response = data.get("response", "Ji boss, maine samajh liya.")

                # Extract emotion prefix
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

                # Asynchronously record episodic memory & facts
                if memory and hasattr(memory, "add_conversation"):
                    try:
                        memory.add_conversation(user_text, clean_resp, topic=action_name or "chat")
                    except Exception:
                        pass

                return step

            except Exception as e:
                last_error = e
                print(f"[agentic_cot_brain] Attempt with '{current_model}' failed: {e}")
                self.rotate_model()
                attempts += 1

        # If all cloud models fail, return intelligent fallback (not a broken canned phrase)
        print(f"[agentic_cot_brain] All cascade models exhausted. Last error: {last_error}")
        return AgentStep(
            thought=f"All models failed. Fallback: {last_error}",
            plan=["Fallback conversation"],
            action_name=None,
            response_text="Mujhe connection mein thodi dikkat aa rahi hai boss, lekin main sun rahi hoon. Boliye, main offline mode mein kya madad karun?",
            emotion="concerned"
        )

    def reflect_and_recover(self, failed_tool: str, failed_args: dict, error_msg: str, original_goal: str, jarvis_instance=None) -> bool:
        """
        Metacognitive Self-Reflection Loop:
        When an action fails, Jarvis reflects on why it failed and formulates an alternative execution step.
        """
        print(f"\n[agentic_cot_brain] [!] INITIATING SELF-REFLECTION & RECOVERY FOR TOOL: '{failed_tool}'")
        if not self._gemini_client:
            return False

        reflection_prompt = f"""You are JARVIS. An autonomous tool call just FAILED.
Failed Tool: '{failed_tool}'
Failed Arguments: {json.dumps(failed_args)}
Error Encountered: "{error_msg}"
Original User Goal: "{original_goal}"

Reflect on why this failed and formulate an ALTERNATIVE plan.
Respond in JSON:
{{
  "reflection": "Why it failed and what alternative strategy will succeed.",
  "action": "alternative_tool_name_or_none",
  "args": {{ ... }},
  "recovery_speech": "Brief reassurance to user explaining the alternative action being taken with [emotion] prefix."
}}
"""
        try:
            gen_config = genai_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1500,
                response_mime_type="application/json"
            )
            resp = None
            for model_cand in self._model_cascade:
                try:
                    resp = self._gemini_client.models.generate_content(
                        model=model_cand,
                        contents=reflection_prompt,
                        config=gen_config
                    )
                    if resp and resp.text:
                        break
                except Exception:
                    continue

            if not resp or not resp.text:
                return False

            raw_txt = resp.text.strip()
            if raw_txt.startswith("```"):
                raw_txt = re.sub(r"^```(?:json)?\s*", "", raw_txt, flags=re.I)
                raw_txt = re.sub(r"\s*```$", "", raw_txt)
            raw_txt = raw_txt.strip()
            match = re.search(r"\{.*\}", raw_txt, re.DOTALL)
            if match:
                raw_txt = match.group(0)
            rec_data = json.loads(raw_txt)
            reflection = rec_data.get("reflection", "Attempting alternative recovery action.")
            alt_action = rec_data.get("action")
            alt_args = rec_data.get("args", {})
            recovery_speech = rec_data.get("recovery_speech", "Pehle tareeqe mein dikkat aayi, main dusra tareeqa aazma rahi hoon.")

            print(f"[agentic_cot_brain] [*] Reflection: {reflection}")
            print(f"[agentic_cot_brain] [*] Alternative Action: '{alt_action}' | Args: {alt_args}")

            class _FallbackVoice:
                def speak(self, text, *args, **kwargs):
                    print(f"[JARVIS SPEECH]: {text}")

            v = getattr(jarvis_instance, "voice", None) or _FallbackVoice()
            if v and hasattr(v, "speak"):
                clean_speech = re.sub(r"^\s*\[\w+\]\s*", "", recovery_speech)
                v.speak(clean_speech, emotion="calm")

            if alt_action and alt_action.lower() != "none" and alt_action != failed_tool:
                alt_step = AgentStep(
                    thought=reflection,
                    plan=["Alternative recovery action"],
                    action_name=alt_action,
                    action_args=alt_args,
                    response_text=recovery_speech,
                    recovery_attempted=True
                )
                return self.execute_step_action(alt_step, jarvis_instance=jarvis_instance, can_reflect=False)

        except Exception as ref_err:
            print(f"[agentic_cot_brain] Self-reflection error: {ref_err}")

        return False

    def execute_step_action(self, step: AgentStep, jarvis_instance=None, can_reflect: bool = True) -> bool:
        """
        Executes autonomous tools with deep error handling and auto-recovery.
        """
        if not step.action_name:
            return False

        tool = step.action_name.lower().strip()
        args = step.action_args or {}

        # Autonomous Tool Alias Normalization
        if tool in ["battery_check", "get_battery_status", "check_battery"]:
            tool = "system_control"
            args = {"action": "battery_check"}
        elif tool in ["lock_pc", "lock_screen", "lock"]:
            tool = "system_control"
            args = {"action": "lock"}
        elif tool in ["volume_up", "increase_volume"]:
            tool = "system_control"
            args = {"action": "volume_up"}
        elif tool in ["volume_down", "decrease_volume"]:
            tool = "system_control"
            args = {"action": "volume_down"}
        elif tool in ["open_application", "launch_app", "run_app"]:
            tool = "open_app"
            if "application_name" in args:
                args["app_name"] = args["application_name"]
        print(f"[agentic_cot_brain] [*] Executing Autonomous Tool: '{tool}' with args: {args}")

        try:
            class _FallbackVoice:
                def speak(self, text, *args, **kwargs):
                    print(f"[JARVIS SPEECH]: {text}")

            v = getattr(jarvis_instance, "voice", None) or _FallbackVoice()

            # 1. OPEN APPLICATION
            if tool == "open_app":
                app_name = args.get("app_name", "")
                if app_name:
                    import commands.system_commands as sys_cmd
                    sys_cmd.open_any_app(v, name=app_name)
                    return True

            # 2. OPEN URL
            elif tool == "open_url":
                url = args.get("url", "")
                if url:
                    import webbrowser
                    webbrowser.open(url)
                    return True

            # 3. WEB SEARCH & RESEARCH
            elif tool == "web_search":
                query = args.get("query", "")
                if query:
                    import universal_web_operator
                    universal_web_operator.web_operator.voice = v
                    universal_web_operator.web_operator.run_web_research(query)
                    return True

            # 4. ECOMMERCE PRICE COMPARISON
            elif tool == "compare_prices":
                product = args.get("product", "")
                if product:
                    import universal_web_operator
                    universal_web_operator.web_operator.voice = v
                    universal_web_operator.web_operator.compare_ecommerce_prices(product)
                    return True

            # 5. TRAVEL ROUTE QUERY
            elif tool == "travel_route":
                import google_maps_travel_hub
                google_maps_travel_hub.travel_hub.voice = v
                google_maps_travel_hub.travel_hub.ai = getattr(jarvis_instance, "ai", None)
                google_maps_travel_hub.travel_hub.gui = getattr(jarvis_instance, "gui", None)
                query_str = f"{args.get('origin', '')} to {args.get('destination', '')} {args.get('mode', '')}"
                google_maps_travel_hub.travel_hub.answer_travel_query(query_str)
                return True

            # 6. SYSTEM CONTROLS
            elif tool == "system_control":
                action = args.get("action", "")
                import commands.system_commands as sys_cmd
                if action == "volume_up": sys_cmd.volume_up(v)
                elif action == "volume_down": sys_cmd.volume_down(v)
                elif action == "volume_mute": sys_cmd.volume_mute(v)
                elif action == "volume_unmute": sys_cmd.volume_unmute(v)
                elif action == "lock": sys_cmd.lock_pc(v)
                elif action == "shutdown": sys_cmd.shutdown_pc(v)
                elif action == "restart": sys_cmd.restart_pc(v)
                elif action == "sleep": sys_cmd.sleep_pc(v)
                elif action == "screenshot": sys_cmd.screenshot(v)
                elif action == "battery_check": sys_cmd.battery_check(v)
                elif action == "ram_check": sys_cmd.ram_check(v)
                elif action == "storage_check": sys_cmd.storage_check(v)
                elif action == "brightness_up": sys_cmd.brightness_up(v)
                elif action == "brightness_down": sys_cmd.brightness_down(v)
                else:
                    raise ValueError(f"Unknown system action: {action}")
                return True

            # 7. READ SCREEN (VISION)
            elif tool == "read_screen":
                question = args.get("question", "What is currently visible on the screen?")
                if hasattr(jarvis_instance, "handle_monitor_vision"):
                    jarvis_instance.handle_monitor_vision(question)
                    return True
                else:
                    import vision
                    snap = vision.capture_screen_fast()
                    if snap:
                        desc = vision.analyze_image_gemini(snap, prompt=question)
                        if v: v.speak(desc)
                        return True

            # 8. EXECUTE SAFE TERMINAL COMMAND
            elif tool == "execute_terminal_cmd":
                command = args.get("command", "")
                if command:
                    # Sanitize command to prevent dangerous operations
                    dangerous = ["format", "rmdir /s /q c:", "del /f /s /q c:", "mkfs", "dd if="]
                    if any(d in command.lower() for d in dangerous):
                        if v: v.speak("Suraksha kaaranon se yeh command execute nahi kiya ja sakta, boss.")
                        return False
                    res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
                    output_text = res.stdout or res.stderr or "Command executed with no output."
                    print(f"[agentic_cot_brain] Command output:\n{output_text[:300]}")
                    if v:
                        v.speak(f"Command execute ho gaya. Output: {output_text[:120]}")
                    return True

            # 9. CREATE OR EDIT FILE
            elif tool == "create_or_edit_file":
                filename = args.get("filename", "notes.txt")
                content = args.get("content", "")
                # Save to Documents by default
                docs_dir = os.path.join(os.path.expanduser("~"), "Documents")
                file_path = os.path.join(docs_dir, os.path.basename(filename))
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                if v: v.speak(f"File {filename} aapke Documents folder mein save kar di hai.")
                return True

            # 10. AVENGERS DIAGNOSTICS
            elif tool == "avengers_diagnostics":
                import avengers_protocol
                avengers_protocol.protocol.execute_assemble_protocol(
                    voice=v,
                    ai=getattr(jarvis_instance, "ai", None),
                    gui=getattr(jarvis_instance, "gui", None)
                )
                return True

            # 11. SEND WHATSAPP
            elif tool == "send_whatsapp":
                import commands.whatsapp_commands as wa_cmd
                phone = args.get("phone", "")
                msg = args.get("message", "")
                if phone and msg:
                    wa_cmd.send_whatsapp_message(v, phone=phone, message=msg)
                    return True

            # 12. AUTONOMOUS SKILL DISCOVERY
            elif tool == "learn_new_skill":
                import self_evolution_engine
                task = args.get("task_description", "")
                if task:
                    self_evolution_engine.evolution_engine.triage_missing_skill(task)
                    return True

            # 13. AUTONOMOUS MULTIMODAL COMPUTER USE
            elif tool == "computer_use":
                goal = args.get("goal", "")
                if goal:
                    import web_control
                    agent = web_control.AutonomousWebAgent(
                        voice=v,
                        ai=getattr(jarvis_instance, "ai", None)
                    )
                    agent.run_goal(goal)
                    return True

            elif tool == "propose_daily_skills":
                import skill_scout_engine
                skill_scout_engine.scout_engine.present_proposals_vocally(voice=v, gui=getattr(jarvis_instance, "gui", None))
                return True

            elif tool == "approve_skill":
                import skill_scout_engine
                idx = int(args.get("skill_number", 1))
                return skill_scout_engine.scout_engine.approve_skill_by_index(idx, voice=v)

        except Exception as e:
            print(f"[agentic_cot_brain] Tool execution error for '{tool}': {e}")
            # Trigger Metacognitive Self-Reflection
            if can_reflect:
                return self.reflect_and_recover(
                    failed_tool=tool,
                    failed_args=args,
                    error_msg=str(e),
                    original_goal=step.thought,
                    jarvis_instance=jarvis_instance
                )

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









