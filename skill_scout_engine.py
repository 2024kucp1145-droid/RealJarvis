# -*- coding: utf-8 -*-
"""
skill_scout_engine.py
=====================
Autonomous Skill Discovery & Human-in-the-Loop Proposal Curator for Real Jarvis (Phase 2).

Proactively explores candidate automation capabilities, queries AI models for innovative
desktop skills, curates a structured daily proposal list, and requests user approval before
initiating the 16-phase code synthesis, AST safety scanning, and sandboxing pipeline.

Features:
- Persistent Shown Skills History (data/shown_skills_history.json)
- Dynamic Non-Repeating Daily Pool (never repeats already shown or learned skills)
- Cycle to Next Batch on "kuch aur" / "ye nahi chahiye"
- Retrieve Unchosen Historical Skills on "previous kaun si thi" / "purani list"
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

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PROPOSALS_FILE = os.path.join(DATA_DIR, "skill_proposals.json")
SHOWN_SKILLS_FILE = os.path.join(DATA_DIR, "shown_skills_history.json")
PROPOSALS_MD = os.path.join(DATA_DIR, "PENDING_SKILL_PROPOSALS.md")
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
        "id": "pdf_smart_multitool",
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
    },
    {
        "id": "screenshot_ocr_extractor",
        "title": "Screen OCR Text & Table Snatcher",
        "domain": "Vision/Utility",
        "description": "Captures any screen area, extracts uncopyable text, error messages or tables, and copies to clipboard.",
        "technical_approach": "Uses PIL and pytesseract/easyocr to parse screen bounding boxes into UTF-8 text.",
        "safety_rating": "SAFE"
    },
    {
        "id": "bulk_file_renamer",
        "title": "Smart Batch File Renamer",
        "domain": "Files/Storage",
        "description": "Renames hundreds of files with clean prefixes, sequential numbers, date stamps or regex patterns.",
        "technical_approach": "Uses pathlib and os.rename with collision checking and dry-run confirmation.",
        "safety_rating": "SAFE"
    },
    {
        "id": "clipboard_multi_vault",
        "title": "Smart Clipboard History Searcher",
        "domain": "Productivity",
        "description": "Stores last 20 clipboard copies, allows search by keywords, and pastes any previous snippet instantly.",
        "technical_approach": "Maintains a local SQLite or in-memory deque with pyperclip clipboard listeners.",
        "safety_rating": "SAFE"
    },
    {
        "id": "csv_to_interactive_chart",
        "title": "CSV to Interactive HTML Chart Builder",
        "domain": "Data Analysis",
        "description": "Reads raw CSV data, generates interactive Plotly/Chart.js graphs, and opens them in the browser.",
        "technical_approach": "Uses pandas to aggregate columns and generates lightweight standalone HTML graphs.",
        "safety_rating": "SAFE"
    },
    {
        "id": "wifi_latency_sentry",
        "title": "Network Latency & WiFi Speed Monitor",
        "domain": "Network/Diagnostics",
        "description": "Tests ping, jitter, and packet loss continuously, alerting when your internet drops or lags.",
        "technical_approach": "Uses socket and ping ICMP echo checks with structured rolling statistics.",
        "safety_rating": "SAFE"
    },
    {
        "id": "markdown_cheatsheet_builder",
        "title": "Instant Topic Cheat-Sheet Generator",
        "domain": "Developer/Study",
        "description": "Summarizes any programming topic, library, or framework into a clean PDF/Markdown cheat-sheet.",
        "technical_approach": "Generates structured reference cards with code snippets and saves to desktop.",
        "safety_rating": "SAFE"
    },
    {
        "id": "battery_saver_sentry",
        "title": "Smart Battery & Thermal Optimizer",
        "domain": "System/Hardware",
        "description": "Monitors laptop battery drain, identifies power-hungry background apps, and throttles idle processes.",
        "technical_approach": "Queries psutil sensors_battery and process CPU times with eco-mode recommendations.",
        "safety_rating": "SAFE"
    },
    {
        "id": "duplicate_photo_cleaner",
        "title": "Duplicate Photo & Image Cleaner",
        "domain": "Files/Storage",
        "description": "Finds identical or near-identical images in a folder using perceptual hashing and frees up disk space.",
        "technical_approach": "Calculates MD5 and dHash values of images to detect exact duplicates safely.",
        "safety_rating": "SAFE"
    },
    {
        "id": "meeting_notes_synthesizer",
        "title": "Audio & Voice Meeting Notes Summarizer",
        "domain": "Audio/Speech",
        "description": "Listens to a recorded meeting or discussion, identifies action items, and writes meeting minutes.",
        "technical_approach": "Processes audio chunks, extracts speaker bullet points, and generates action checklist.",
        "safety_rating": "SAFE"
    },
    {
        "id": "web_price_drop_tracker",
        "title": "E-Commerce Price Drop Watchdog",
        "domain": "Web Automation",
        "description": "Periodically checks product prices on Amazon and Flipkart, alerting when price drops below threshold.",
        "technical_approach": "Uses requests and BeautifulSoup with random user-agents to parse price tags.",
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

    def _get_shown_history(self) -> List[Dict]:
        """Loads the permanent history of all proposals ever presented to the user."""
        if os.path.exists(SHOWN_SKILLS_FILE):
            try:
                with open(SHOWN_SKILLS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _record_to_history(self, proposals: List[SkillProposal], status: str = "shown_not_selected"):
        """Records proposals into the persistent history log."""
        os.makedirs(DATA_DIR, exist_ok=True)
        history = self._get_shown_history()
        history_map = {item["id"]: item for item in history}

        now = time.time()
        for p in proposals:
            if p.id in history_map:
                history_map[p.id]["last_shown_at"] = now
                if status == "approved":
                    history_map[p.id]["status"] = "approved"
            else:
                history_map[p.id] = {
                    "id": p.id,
                    "title": p.title,
                    "domain": p.domain,
                    "description": p.description,
                    "technical_approach": p.technical_approach,
                    "safety_rating": p.safety_rating,
                    "status": status,
                    "first_shown_at": now,
                    "last_shown_at": now
                }

        with open(SHOWN_SKILLS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(history_map.values()), f, indent=2)

    def _load_proposals(self):
        if os.path.exists(PROPOSALS_FILE):
            try:
                with open(PROPOSALS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.active_proposals = [SkillProposal(**item) for item in data]
            except Exception:
                self.active_proposals = []

    def save_proposals(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(PROPOSALS_FILE, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in self.active_proposals], f, indent=2)
        self._render_markdown_summary()

    def _render_markdown_summary(self):
        os.makedirs(DATA_DIR, exist_ok=True)
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
            "### 🎤 How to Approve / Navigate:",
            "- **Approve:** *\"Jarvis, skill number 1 approve karo\"*",
            "- **Cycle New Batch:** *\"Jarvis, kuch aur dikhao\"*",
            "- **Previous Unchosen:** *\"Jarvis, previous kaun si thi\"*",
            "- **Terminal:** `python skill_scout_engine.py approve 1`"
        ])

        with open(PROPOSALS_MD, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def scout_candidate_skills(self, count: int = 4, force_fresh: bool = False) -> List[SkillProposal]:
        """
        Explores candidate skills. Guarantees fresh, non-repeating skills by excluding:
        1. All already synthesized skills in custom_skills/
        2. All active skills in current view
        3. If force_fresh=True, prioritizes skills not yet shown to user.
        """
        existing_skills = set()
        if os.path.exists(CUSTOM_SKILLS_DIR):
            for f in os.listdir(CUSTOM_SKILLS_DIR):
                if f.endswith(".py"):
                    existing_skills.add(f[:-3].lower())

        shown_history = {h["id"] for h in self._get_shown_history()}
        current_active_ids = {p.id for p in self.active_proposals} if force_fresh else set()

        new_proposals: List[SkillProposal] = []

        # 1. First pass: Curated taxonomy skills that have NEVER been shown and NEVER learned
        for item in CURATED_CAPABILITY_TAXONOMY:
            s_id = item["id"]
            if s_id not in existing_skills and s_id not in current_active_ids:
                if s_id not in shown_history or not force_fresh:
                    new_proposals.append(SkillProposal(
                        id=s_id,
                        title=item["title"],
                        domain=item["domain"],
                        description=item["description"],
                        technical_approach=item["technical_approach"],
                        safety_rating=item["safety_rating"]
                    ))
                    if len(new_proposals) >= count:
                        break

        # 2. Second pass: If still need more, take any taxonomy skill not in custom_skills and not in active
        if len(new_proposals) < count:
            for item in CURATED_CAPABILITY_TAXONOMY:
                s_id = item["id"]
                if s_id not in existing_skills and s_id not in current_active_ids and not any(p.id == s_id for p in new_proposals):
                    new_proposals.append(SkillProposal(
                        id=s_id,
                        title=item["title"],
                        domain=item["domain"],
                        description=item["description"],
                        technical_approach=item["technical_approach"],
                        safety_rating=item["safety_rating"]
                    ))
                    if len(new_proposals) >= count:
                        break

        # 3. Dynamic GenAI Discovery (Lightning fast gemini-flash-lite-latest)
        if len(new_proposals) < count and self._gemini_client:
            try:
                needed = count - len(new_proposals)
                prompt = f"""Generate {needed} brand new, unique desktop automation skills for Windows.
Focus on novel productivity, study tools, data extraction, or system optimization.
Output ONLY a JSON array of objects with keys: id (snake_case), title, domain, description, technical_approach, safety_rating ("SAFE")."""
                
                resp = self._gemini_client.models.generate_content(
                    model="gemini-flash-lite-latest",
                    contents=prompt
                )
                txt = resp.text.strip()
                if txt.startswith("```"):
                    txt = re.sub(r"^```(?:json)?\s*", "", txt, flags=re.I)
                    txt = re.sub(r"\s*```$", "", txt)
                items = json.loads(txt.strip())
                for it in items:
                    if it.get("id") not in existing_skills and not any(p.id == it.get("id") for p in new_proposals):
                        new_proposals.append(SkillProposal(
                            id=it.get("id", f"skill_{int(time.time())}"),
                            title=it.get("title", "Novel Skill"),
                            domain=it.get("domain", "Productivity"),
                            description=it.get("description", ""),
                            technical_approach=it.get("technical_approach", "Python Standard Library"),
                            safety_rating=it.get("safety_rating", "SAFE")
                        ))
            except Exception as e:
                print(f"[skill_scout] Dynamic LLM generation note: {e}")

        self.active_proposals = new_proposals
        self.save_proposals()
        self._record_to_history(new_proposals, status="shown_not_selected")
        print(f"[skill_scout] Formulated {len(self.active_proposals)} fresh candidate skills.")
        return self.active_proposals

    def cycle_to_next_batch(self, voice=None, gui=None):
        """
        Triggered when user says 'kuch aur dikhao', 'ye nahi chahiye', 'next skills':
        Archives current proposals to history as unchosen, scouts a fresh new batch,
        and presents them in the modal.
        """
        print("[skill_scout] User requested different skills ('kuch aur'). Cycling to fresh batch...")
        if self.active_proposals:
            self._record_to_history(self.active_proposals, status="shown_not_selected")

        fresh_props = self.scout_candidate_skills(count=4, force_fresh=True)

        titles = [f"'{p.title}'" for p in fresh_props[:3]]
        titles_str = ", ".join(titles)
        briefing = f"Theek hai boss! Yeh lijiye kuch aur naye skills jo maine scout kiye hain: {titles_str}. Inme se koi pasand hai?"

        self._launch_modal(fresh_props, voice=voice, gui=gui)

        if voice and hasattr(voice, "speak"):
            voice.speak(briefing, emotion="excited")
        else:
            print(f"[JARVIS VOCAL]: {briefing}")

    def present_previous_unchosen(self, voice=None, gui=None):
        """
        Triggered when user says 'previous kaun si thi', 'purani list dikhao', 'jo choose nahi ki':
        Retrieves all skills that were shown but not yet approved or learned.
        """
        print("[skill_scout] Retrieving historical unchosen skills...")
        history = self._get_shown_history()
        existing_skills = set()
        if os.path.exists(CUSTOM_SKILLS_DIR):
            existing_skills = {f[:-3].lower() for f in os.listdir(CUSTOM_SKILLS_DIR) if f.endswith(".py")}

        unchosen = []
        seen_ids = set()
        for item in history:
            s_id = item.get("id")
            if s_id not in existing_skills and s_id not in seen_ids and item.get("status") == "shown_not_selected":
                seen_ids.add(s_id)
                unchosen.append(SkillProposal(
                    id=s_id,
                    title=item.get("title", "Skill"),
                    domain=item.get("domain", "General"),
                    description=item.get("description", ""),
                    technical_approach=item.get("technical_approach", ""),
                    safety_rating=item.get("safety_rating", "SAFE"),
                    status="pending_approval"
                ))

        if not unchosen:
            msg = "Boss, abhi tak aisi koi purani skill nahi hai jo aapne miss ki ho. Sabhi skills up to date hain."
            if voice and hasattr(voice, "speak"):
                voice.speak(msg, emotion="calm")
            else:
                print(f"[JARVIS VOCAL]: {msg}")
            return False

        self.active_proposals = unchosen
        self.save_proposals()

        briefing = f"Boss, abhi tak jo {len(unchosen)} skills maine aapko propose ki thi lekin choose nahi hui, unki poori list screen par aa gayi hai. Aap inme se kisi ko bhi select kar sakte hain."
        self._launch_modal(unchosen, voice=voice, gui=gui)

        if voice and hasattr(voice, "speak"):
            voice.speak(briefing, emotion="happy")
        else:
            print(f"[JARVIS VOCAL]: {briefing}")
        return True

    def present_proposals_vocally(self, voice=None, gui=None, force_fresh: bool = False):
        """
        Presents the candidate skills to the user with an executive spoken briefing
        and launches the interactive selection modal.
        """
        if not self.active_proposals or force_fresh:
            self.scout_candidate_skills(count=4, force_fresh=force_fresh)

        titles = [f"'{p.title}'" for p in self.active_proposals[:3]]
        titles_str = ", ".join(titles)
        briefing = f"Boss, maine naye automation skills scout kiye hain jinhe main seekh sakti hoon: {titles_str}. Maine list screen par open kar di hai. Kya inme se kisi ko sikhna approve karte hain?"

        if gui and hasattr(gui, "show_message"):
            try:
                gui.show_message(f"🧬 New Skills Scouted: {len(self.active_proposals)} Available", ms=6000)
            except Exception:
                pass

        self._launch_modal(self.active_proposals, voice=voice, gui=gui)

        if voice and hasattr(voice, "speak"):
            voice.speak(briefing, emotion="excited")
        else:
            print(f"[JARVIS VOCAL]: {briefing}")

    def _launch_modal(self, proposals: List[SkillProposal], voice=None, gui=None):
        """Launches the interactive floating selection modal safely."""
        try:
            import skill_selection_modal
            props_data = []
            for p in proposals:
                if hasattr(p, "title"):
                    props_data.append({
                        "title": p.title,
                        "domain": p.domain,
                        "description": p.description,
                        "status": p.status
                    })
                elif isinstance(p, dict):
                    props_data.append(p)

            root_tk = getattr(gui, "root", None) if gui else None

            def _on_modal_approve(chosen):
                for skill_dict in chosen:
                    s_title = skill_dict.get("title")
                    for i, p in enumerate(self.active_proposals):
                        if (hasattr(p, "title") and p.title == s_title) or (isinstance(p, dict) and p.get("title") == s_title):
                            self.approve_skill_by_index(i + 1, voice=voice)
                            break

            skill_selection_modal.show_selection_modal(
                props_data,
                on_approve_callback=_on_modal_approve,
                root=root_tk
            )
        except Exception as e:
            print(f"[skill_scout modal launch error: {e}]")

    def approve_skill_by_index(self, index: int, voice=None) -> bool:
        """
        Approves a skill by its 1-indexed position and triggers the 16-phase synthesis pipeline.
        """
        if 1 <= index <= len(self.active_proposals):
            target = self.active_proposals[index - 1]
            target.status = "approved"
            self.save_proposals()
            self._record_to_history([target], status="approved")

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
    proposals = scout_engine.scout_candidate_skills(count=5, force_fresh=True)
    print("\n" + "=" * 60)
    print("PROPOSED CANDIDATE SKILLS FOR USER CONFIRMATION:")
    print("=" * 60)
    for i, p in enumerate(proposals, 1):
        print(f"[{i}] {p.title} ({p.domain})")
        print(f"    - Description: {p.description}")
        print(f"    - Safety     : {p.safety_rating}")
    print("=" * 60)
    print(f"[*] Full dashboard written to: {PROPOSALS_MD}")
