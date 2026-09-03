# -*- coding: utf-8 -*-
"""
skill_spec_formulator.py  (Phase 3: Skill Goal & Trigger Specification Formulator)
=====================================================================================
Transforms unstructured user queries & Phase 2 DesktopContextSnapshots into formal,
deterministic `SkillSpec` schemas.

Every self-learned skill must adhere to this contract so that:
1. The Code Synthesizer (Phase 4) knows exact boundaries, inputs, and outputs.
2. The Dynamic Hot-Reloader (Phase 11) knows which triggers to register.
3. The Permanent Registry (Phase 12) stores standardized skill metadata.
"""

import os
import re
import sys
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from context_sniffer import DesktopContextSnapshot


@dataclass
class SkillSpec:
    skill_id: str                              # e.g. "flipkart_price_checker"
    skill_name: str                            # e.g. "Flipkart Price Checker"
    description: str                           # Precise functional description
    category: str                              # "browser_web" | "desktop_app" | "file_system" | "system_utility" | "data_processing"
    triggers: List[str]                        # ["flipkart price", "price check karo", "check flipkart price"]
    target_app: str                            # "chrome", "vscode", "desktop", "excel", "general"
    inputs: List[Dict[str, str]] = field(default_factory=list)      # [{"name": "product_name", "type": "str"}]
    expected_output: str = "Voice confirmation and spoken/copied result"
    fallback_behavior: str = "Speak graceful error explanation if target window or element is missing"
    created_at: float = field(default_factory=time.time)
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class SkillSpecFormulator:
    """Formulates a formal SkillSpec from natural language + environment snapshot."""

    @staticmethod
    def _clean_task_text(query: str) -> str:
        """Strips meta instructions like 'Jarvis, naya skill seekho jo'."""
        clean = query.strip().strip('"\'“”')
        # Remove meta learning prefixes
        clean = re.sub(r"^(jarvis\s*,?\s*)?(ek\s+)?(naya|nayi)?\s*(skill|feature|tool|kaam)\s*(seekho|seekh\s+lo|banao|bana\s+do)?\s*(jo|ki)?\s*", "", clean, flags=re.IGNORECASE).strip()
        clean = clean.strip('"\'“”').strip()
        return clean or query.strip()

    @staticmethod
    def formulate_spec(query: str, snapshot: Optional[DesktopContextSnapshot] = None, ai_brain=None) -> SkillSpec:
        clean_task = SkillSpecFormulator._clean_task_text(query)

        # 1. Generate normalized clean ID
        skill_id = SkillSpecFormulator._generate_skill_id(clean_task)
        skill_name = SkillSpecFormulator._generate_human_name(skill_id)

        # 2. Determine Category & Target App from Context and Query
        category, target_app = SkillSpecFormulator._classify_category_and_app(clean_task, snapshot)

        # 3. Generate Multi-Phrasing Triggers
        triggers = SkillSpecFormulator._generate_triggers(clean_task)

        # 4. Formulate Detailed Description
        description = f"Autonomous skill to {clean_task.rstrip('.?!')}. Tailored for {target_app} environment."

        spec = SkillSpec(
            skill_id=skill_id,
            skill_name=skill_name,
            description=description,
            category=category,
            triggers=triggers,
            target_app=target_app,
            inputs=[{"name": "query_text", "type": "str", "description": "Original user command text"}],
            expected_output="Executes automation and returns Hinglish vocal summary of outcome",
            fallback_behavior="Log failure, gracefully handle missing windows/elements and inform user vocally"
        )

        return spec

    @staticmethod
    def _generate_skill_id(query: str) -> str:
        """Creates a clean, PEP8 snake_case skill identifier."""
        clean = query.lower()
        # Remove common Hinglish filler words
        clean = re.sub(r"\b(karo|kardo|kariye|banao|bana|do|mujhe|mera|mere|ka|ke|ki|aur|par|pe|se|ko|in|the|a|an|please|jarvis|naya|skill|seekho|jo)\b", "", clean)
        clean = re.sub(r"[^\w\s]", "", clean)
        words = clean.strip().split()
        if not words:
            words = ["custom", "task", str(int(time.time()))]
        words = words[:4]  # Max 4 words in ID
        return "_".join(words)

    @staticmethod
    def _generate_human_name(skill_id: str) -> str:
        """Converts snake_case ID to Title Case Human Name."""
        parts = skill_id.split("_")
        return " ".join(p.capitalize() for p in parts)

    @staticmethod
    def _classify_category_and_app(query: str, snapshot: Optional[DesktopContextSnapshot] = None) -> tuple[str, str]:
        q = query.lower()
        
        # 1. Browser / Web Automation
        if any(w in q for w in ["browser", "chrome", "edge", "youtube", "tab", "page", "website", "url", "flipkart", "amazon", "github", "leetcode", "search", "scrape", "speedtest"]):
            return "browser_web", (snapshot.browser_domain if snapshot and snapshot.browser_domain else "browser")

        # 2. File & Directory System
        if any(w in q for w in ["file", "folder", "directory", "pdf", "excel", "sheet", "csv", "zip", "txt", "download", "save", "organize", "cache", "temp"]):
            return "file_system", "file_explorer"

        # 3. Development / Code Tools
        if any(w in q for w in ["code", "vscode", "terminal", "git", "python", "compile", "run", "debug", "test"]):
            return "desktop_app", "vscode"

        # 4. Desktop Native Apps
        if snapshot and snapshot.active_process not in ("unknown", "", "explorer.exe"):
            return "desktop_app", snapshot.active_app_label

        return "system_utility", "windows_desktop"

    @staticmethod
    def _generate_triggers(query: str) -> List[str]:
        """Generates diverse variations of voice/text triggers."""
        clean = query.strip().rstrip(".?!")
        triggers = [clean.lower()]

        # Generate Hinglish variations
        base = re.sub(r"\b(karo|kardo|kariye|banao|do|please)\b", "", clean, flags=re.IGNORECASE).strip()
        if base and base.lower() != clean.lower():
            triggers.append(base.lower())
            triggers.append(f"{base.lower()} karo")
            triggers.append(f"{base.lower()} kardo")

        return list(dict.fromkeys(triggers))[:6]


formulator = SkillSpecFormulator()
