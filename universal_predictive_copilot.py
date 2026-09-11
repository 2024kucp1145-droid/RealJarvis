# -*- coding: utf-8 -*-
"""
universal_predictive_copilot.py
===============================
Astra-Style Universal Predictive Copilot & Multi-Domain Stateful Workflow Engine.

Observes user activity across 6 core digital domains:
1. Coding & Software Development (VS Code, PyCharm, Terminal)
2. Web Design & Frontend (HTML, CSS, React, Figma)
3. Academic Study & Research (PDFs, Research Papers, Docs)
4. Office & Data Spreadsheets (Excel, Sheets, CSVs)
5. E-Commerce & Product Research (Amazon, Flipkart, Browsers)
6. Creative Canvas & Design (Paint, Graphics, Wireframes)

Predicts the next 3 logical workflow steps, generates iterative modifications,
and executes autonomous multi-turn updates with 1-voice confirmation.
"""

import os
import sys
import json
import time
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import desktop_context

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None


@dataclass
class WorkflowPrediction:
    domain: str
    current_task: str
    next_steps: List[str]
    suggested_action: str
    action_type: str
    generated_payload: str
    speech_summary: str


PREDICTIVE_PROMPT = """You are JARVIS, an autonomous Astra-level Predictive Workflow Copilot.
Your job is to analyze the user's active window, recent work context, and current task, then PREDICT the next logical steps and prepare the execution payload.

DOMAINS SUPPORTED:
1. CODING (Writing code, debugging, APIs, scripts)
2. WEB_DESIGN (HTML/CSS, landing pages, UI components)
3. STUDY_RESEARCH (Reading textbooks, research papers, notes, PDFs)
4. OFFICE_DATA (Spreadsheets, tables, financial data, reports)
5. E_COMMERCE (Shopping, tech specs, product comparison)
6. CREATIVE_CANVAS (Drawing, wireframing, designing visual graphics)

OUTPUT JSON SCHEMA:
{
  "domain": "CODING|WEB_DESIGN|STUDY_RESEARCH|OFFICE_DATA|E_COMMERCE|CREATIVE_CANVAS|GENERAL",
  "current_task": "Brief description of what the user is currently doing",
  "next_steps": [
    "1. Immediate next logical step",
    "2. Secondary enhancement/refinement",
    "3. Verification/Testing/Export"
  ],
  "suggested_action": "Clear 1-line proposal to ask the user (e.g. 'Kya main JWT authentication handler ka code likh kar inject kar doon?')",
  "action_type": "inject_code|create_file|open_url|synthesize_notes|canvas_update|speak_only",
  "generated_payload": "The actual Python/HTML/Markdown/Formula payload ready for instant execution if user says Yes",
  "speech_summary": "Natural, witty Jarvis speech in Hinglish asking the user if they want to execute this step."
}

Always respond in valid JSON only.
"""


class UniversalPredictiveCopilot:
    def __init__(self):
        self._gemini_client = None
        self._pending_prediction: Optional[WorkflowPrediction] = None
        self._active_artifact: Dict[str, Any] = {}
        self._init_client()

    def _init_client(self):
        api_key = getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        if genai and api_key:
            try:
                self._gemini_client = genai.Client(api_key=api_key)
            except Exception as e:
                print(f"[predictive_copilot] Client init error: {e}")

    def analyze_and_predict(self, query: str = "", extra_context: str = "") -> Optional[WorkflowPrediction]:
        """
        Analyzes the current desktop state and predicts the next 3 steps.
        """
        if not self._gemini_client:
            self._init_client()

        # Build live environment snapshot
        desktop_summary = desktop_context.build_context_summary()
        full_context = f"DESKTOP STATE:\n{desktop_summary}\n\nUSER REMARK / QUERY:\n{query}\n\nADDITIONAL CONTEXT:\n{extra_context}"

        try:
            gen_config = genai_types.GenerateContentConfig(
                system_instruction=PREDICTIVE_PROMPT,
                max_output_tokens=1500,
                temperature=0.2,
                response_mime_type="application/json"
            )

            response = self._gemini_client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=full_context,
                config=gen_config
            )

            data = json.loads(response.text.strip())
            prediction = WorkflowPrediction(
                domain=data.get("domain", "GENERAL"),
                current_task=data.get("current_task", "General Desktop Work"),
                next_steps=data.get("next_steps", []),
                suggested_action=data.get("suggested_action", "Agla step continue karein?"),
                action_type=data.get("action_type", "speak_only"),
                generated_payload=data.get("generated_payload", ""),
                speech_summary=data.get("speech_summary", "Boss, agla logical step ready hai. Kya main continue karoon?")
            )

            self._pending_prediction = prediction
            self._log_prediction(prediction)
            return prediction

        except Exception as e:
            print(f"[predictive_copilot] Prediction error: {e}")
            return None

    def execute_pending_prediction(self, voice=None, gui=None) -> str:
        """Executes the predicted action when the user says 'Yes' or 'Kar do'."""
        if not self._pending_prediction:
            return "Koi pending workflow action nahi hai, boss."

        pred = self._pending_prediction
        atype = pred.action_type
        payload = pred.generated_payload
        result_msg = "Step successfully execute ho gaya hai, boss."

        try:
            if atype == "inject_code" or atype == "create_file":
                # Save generated code to a workspace file
                import tempfile
                file_ext = ".py" if pred.domain == "CODING" else (".html" if pred.domain == "WEB_DESIGN" else ".md")
                temp_dir = tempfile.gettempdir()
                out_path = os.path.join(temp_dir, f"jarvis_workflow_step_{int(time.time())}{file_ext}")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(payload)

                if pred.domain == "WEB_DESIGN":
                    import webbrowser
                    webbrowser.open(f"file:///{out_path}")
                result_msg = f"Maine naya code synthesize karke {os.path.basename(out_path)} mein save aur open kar diya hai."

            elif atype == "synthesize_notes":
                import tempfile, webbrowser
                temp_dir = tempfile.gettempdir()
                out_path = os.path.join(temp_dir, f"jarvis_study_notes_{int(time.time())}.md")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(payload)
                result_msg = "Maine is topic ke summary notes aur formula sheet ready kar diye hain."

            elif atype == "canvas_update":
                import game_synthesizer
                game_synthesizer.synthesizer.synthesize_custom_game(pred.current_task)
                result_msg = "Canvas update karke browser mein live render kar diya hai."

        except Exception as e:
            result_msg = f"Action execute karne mein error: {e}"

        self._pending_prediction = None
        if voice and hasattr(voice, "speak"):
            voice.speak(result_msg, emotion="happy")
        return result_msg

    def has_pending_prediction(self) -> bool:
        return self._pending_prediction is not None

    def clear_pending(self):
        self._pending_prediction = None

    def _log_prediction(self, pred: WorkflowPrediction):
        print("\n" + "=" * 65)
        print("[*] [ASTRA-STYLE PREDICTIVE WORKFLOW COPILOT]")
        print("=" * 65)
        print(f"[*] Detected Domain : {pred.domain}")
        print(f"[*] Current Task    : {pred.current_task}")
        print("[*] Predicted Steps :")
        for s in pred.next_steps:
            print(f"    - {s}")
        print(f"[*] Suggested Action: {pred.suggested_action}")
        print(f"[*] Action Type     : {pred.action_type}")
        print(f"[*] Vocal Prompt    : \"{pred.speech_summary}\"")
        print("=" * 65 + "\n")


predictive_copilot = UniversalPredictiveCopilot()
