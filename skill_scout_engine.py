# -*- coding: utf-8 -*-
"""
skill_scout_engine.py
=====================
Autonomous Skill Discovery & Human-in-the-Loop Proposal Curator for Real Jarvis (Phase 2).

Proactively explores candidate automation capabilities, queries AI models for innovative
desktop skills, curates a structured daily proposal list, and requests user approval before
initiating the 16-phase code synthesis, AST safety scanning, and sandboxing pipeline.
"""

import os
import sys
import json
import time
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

try:
    import self_evolution_engine
except ImportError:
    self_evolution_engine = None

PROPOSALS_FILE = os.path.join(os.path.dirname(__file__), "data", "skill_proposals.json")
PROPOSALS_MD = os.path.join(os.path.dirname(__file__), "data", "PENDING_SKILL_PROPOSALS.md")
CUSTOM_SKILLS_DIR = os.path.join(os.path.dirname(__file__), "custom_skills")


@dataclass
class SkillProposal:
    id: str
    title: str
    domain: str
    description: str
    technical_approach: str
    safety_rating: str  # "SAFE" | "RESTRICTED"
    status: str = "pending_approval"  # "pending_approval" | "approved" | "rejected" | "synthesized"
    created_at: float = field(default_factory=time.time)


CURATED_CAPABILITY_TAXONOMY = [
    {
        "id": "excel_smart_cleaner",
        "title": "Excel Data Normalizer & Cleaner",
        "domain": "Office/Data",
        "description": "Scans CSV and Excel files, removes duplicate rows, formats dates uniformly, and fixes missing cells.",
        "technical_approach": "Uses pandas and openpyxl to parse, clean, and write back structured workbooks.",
        "safety_rating": "SAFE"
    },
    {
        "id": "pdf_watermark_remover",
        "title": "PDF Smart Multi-tool",
        "domain": "Documents",
        "description": "Extracts tables from PDF files into Excel, merges multiple documents, and creates encrypted backups.",
        "technical_approach": "Uses PyPDF2 and fpdf2 to manipulate page trees and format extracts.",
        "safety_rating": "SAFE"
    },
    {
        "id": "browser_tab_consolidator",
        "title": "Active Workflow Context Archiver",
        "domain": "Productivity",
        "description": "Takes a snapshot of all active research windows, saves reference URLs, and organizes notes.",
        "technical_approach": "Integrates with desktop_context and browser commands to archive session state.",
        "safety_rating": "SAFE"
    },
    {
        "id": "system_cache_purger",
        "title": "Intelligent Disk Junk & Temp Purger",
        "domain": "System Optimization",
        "description": "Cleans temporary directories (%TEMP%, browser caches) safely without touching personal files.",
        "technical_approach": "Uses os.walk and safe pathlib checks with whitelisted temp paths.",
        "safety_rating": "SAFE"
    },
    {
        "id": "git_commit_auto_doctor",
        "title": "Git Pit-Crew Auto-Diagnoser",
        "domain": "Developer Tools",
        "description": "Checks local git repository for untracked files, unpushed commits, and formats clean semantic commit messages.",
        "technical_approach": "Executes git status and diff commands in subprocess with formatted markdown outputs.",
        "safety_rating": "SAFE"
    }
]


class SkillScoutEngine:
    def __init__(self):
        self._gemini_client = None
        self._init_client()
        self.active_proposals: List[SkillProposal] = []
        self._load_proposals()

    def _init_client(self):
        api_key = getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        if genai and api_key:
            try:
                self._gemini_client = genai.Client(api_key=api_key)
            except Exception:
                pass

    def _load_proposals(self):
        if os.path.exists(PROPOSALS_FILE):
            try:
                with open(PROPOSALS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.active_proposals = [SkillProposal(**item) for item in data]
            except Exception:
                self.active_proposals = []

    def save_proposals(self):
        os.makedirs(os.path.dirname(PROPOSALS_FILE), exist_ok=True)
        with open(PROPOSALS_FILE, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in self.active_proposals], f, indent=2)
        self._render_markdown_summary()

    def _render_markdown_summary(self):
        os.makedirs(os.path.dirname(PROPOSALS_MD), exist_ok=True)
        lines = [
            "# 🧬 RealJarvis Autonomous Skill Discovery Dashboard",
            f"**Last Scout Update:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Jarvis has scouted the following candidate automation skills. Confirm which ones to learn:\n",
            "| # | Skill Title | Domain | Safety | Status | Description |",
            "|---|---|---|---|---|---|"
        ]
        for idx, p in enumerate(self.active_proposals, 1):
            status_emoji = "⏳ Pending" if p.status == "pending_approval" else ("✅ Approved" if p.status == "approved" else "🚀 Learned")
            lines.append(f"| **{idx}** | **{p.title}** | `{p.domain}` | `{p.safety_rating}` | {status_emoji} | {p.description} |")

        lines.extend([
            "",
            "### 🎤 How to Approve:",
            "- **Voice:** *\"Jarvis, skill number 1 approve karo\"* ya *\"Jarvis, learn all skills\"*",
            "- **Terminal:** `python skill_scout_engine.py approve 1`"
        ])

        with open(PROPOSALS_MD, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def scout_candidate_skills(self, count: int = 5) -> List[SkillProposal]:
        """
        Explores candidate skills. Blends curated taxonomy with dynamic LLM generation.
        """
        existing_skills = set()
        if os.path.exists(CUSTOM_SKILLS_DIR):
            existing_skills = {f[:-3].lower() for f in os.listdir(CUSTOM_SKILLS_DIR) if f.endswith(".py")}

        new_proposals: List[SkillProposal] = []

        # 1. Check curated taxonomy first
        for item in CURATED_CAPABILITY_TAXONOMY:
            if item["id"] not in existing_skills and not any(p.id == item["id"] for p in self.active_proposals):
                prop = SkillProposal(
                    id=item["id"],
                    title=item["title"],
                    domain=item["domain"],
                    description=item["description"],
                    technical_approach=item["technical_approach"],
                    safety_rating=item["safety_rating"]
                )
                new_proposals.append(prop)
                if len(new_proposals) >= count:
                    break

        # 2. Dynamic AI Discovery if more needed
        if len(new_proposals) < count and self._gemini_client:
            try:
                prompt = f"""You are JARVIS's Autonomous Skill Scout.
Generate {count - len(new_proposals)} novel, practical desktop automation skills for Windows/Linux.
Focus on: Office data, file operations, web tools, developer tools, system health.
Output JSON list of objects matching:
[{{
  "id": "snake_case_name",
  "title": "Human readable name",
  "domain": "Domain category",
  "description": "What it automates for the user",
  "technical_approach": "Python libraries to use",
  "safety_rating": "SAFE"
}}]
"""
                resp = self._gemini_client.models.generate_content(
                    model=getattr(config, "GEMINI_MODEL", "gemini-flash-latest"),
                    contents=prompt
                )
                txt = resp.text.strip()
                if txt.startswith("```"):
                    txt = re.sub(r"^```(?:json)?\s*", "", txt, flags=re.I)
                    txt = re.sub(r"\s*```$", "", txt)
                items = json.loads(txt.strip())
                for it in items:
                    if it.get("id") not in existing_skills:
                        new_proposals.append(SkillProposal(
                            id=it.get("id", f"skill_{int(time.time())}"),
                            title=it.get("title", "New Skill"),
                            domain=it.get("domain", "General"),
                            description=it.get("description", ""),
                            technical_approach=it.get("technical_approach", "Python standard library"),
                            safety_rating=it.get("safety_rating", "SAFE")
                        ))
            except Exception as e:
                print(f"[skill_scout] Dynamic scout note: {e}")

        # Add to active proposals
        self.active_proposals = new_proposals
        self.save_proposals()
        print(f"[skill_scout] Formulated {len(self.active_proposals)} candidate skills for user review.")
        return self.active_proposals

    def present_proposals_vocally(self, voice=None, gui=None):
        """
        Presents the candidate skills to the user with an executive spoken briefing.
        """
        if not self.active_proposals:
            self.scout_candidate_skills(count=4)

        titles = [f"'{p.title}'" for p in self.active_proposals[:3]]
        titles_str = ", ".join(titles)
        briefing = f"Boss, maine naye automation skills scout kiye hain jinhe main seekh sakti hoon: {titles_str}. Maine list aapke dashboard par save kar di hai. Kya inme se kisi ko sikhna approve karte hain?"

        if gui and hasattr(gui, "show_message"):
            try:
                gui.show_message(f"🧬 New Skills Scouted: {len(self.active_proposals)} Available", ms=6000)
            except Exception:
                pass

        if voice and hasattr(voice, "speak"):
            voice.speak(briefing, emotion="excited")
        else:
            print(f"[JARVIS VOCAL]: {briefing}")

    def approve_skill_by_index(self, index: int, voice=None) -> bool:
        """
        Approves a skill by its 1-indexed position and triggers the 16-phase synthesis pipeline.
        """
        if 1 <= index <= len(self.active_proposals):
            target = self.active_proposals[index - 1]
            target.status = "approved"
            self.save_proposals()

            ack = f"Theek hai boss! Skill '{target.title}' approved. Main iska code synthesize aur sandbox mein test kar rahi hoon."
            if voice and hasattr(voice, "speak"):
                voice.speak(ack, emotion="excited")
            else:
                print(f"[JARVIS VOCAL]: {ack}")

            # Trigger Self-Evolution Synthesis Directly (User already approved)
            if self_evolution_engine and hasattr(self_evolution_engine, "evolution_engine"):
                try:
                    if hasattr(self_evolution_engine.evolution_engine, "learn_skill_direct"):
                        self_evolution_engine.evolution_engine.learn_skill_direct(
                            f"Automate {target.title}: {target.description}. {target.technical_approach}",
                            notify_voice=False
                        )
                    else:
                        self_evolution_engine.evolution_engine.triage_missing_skill(
                            f"Automate {target.title}: {target.description}. {target.technical_approach}"
                        )
                    target.status = "synthesized"
                    self.save_proposals()
                    return True
                except Exception as e:
                    print(f"[skill_scout] Synthesis error: {e}")

        return False


scout_engine = SkillScoutEngine()

if __name__ == "__main__":
    print("[*] Running Autonomous Skill Scout Engine...")
    proposals = scout_engine.scout_candidate_skills(count=5)
    print("\n" + "=" * 60)
    print("PROPOSED CANDIDATE SKILLS FOR USER CONFIRMATION:")
    print("=" * 60)
    for i, p in enumerate(proposals, 1):
        print(f"[{i}] {p.title} ({p.domain})")
        print(f"    - Description: {p.description}")
        print(f"    - Safety     : {p.safety_rating}")
    print("=" * 60)
    print(f"[*] Full dashboard written to: {PROPOSALS_MD}")
