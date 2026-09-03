# -*- coding: utf-8 -*-
"""
skill_registry.py  (Phase 12: Permanent SQLite Database & Disk Registry)
==========================================================================
Persists verified custom skills to disk and maintains an SQLite database index
with metadata, trigger mappings, execution statistics, and success rates.
"""

import os
import sys
import json
import time
import sqlite3
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_spec_formulator import SkillSpec

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_skills")
os.makedirs(SKILLS_DIR, exist_ok=True)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "skills_registry.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


class SkillRegistry:
    """Manages disk persistence and SQLite metadata index for custom skills."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Initializes SQLite schema for skills registry."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS custom_skills (
                        skill_id TEXT PRIMARY KEY,
                        skill_name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        target_app TEXT NOT NULL,
                        description TEXT,
                        triggers_json TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        usage_count INTEGER DEFAULT 0,
                        last_executed_at REAL DEFAULT 0,
                        success_rate REAL DEFAULT 1.0,
                        version TEXT DEFAULT '1.0.0'
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[skill_registry db init error: {e}]")

    def save_skill(self, spec: SkillSpec, code_content: str) -> Optional[str]:
        """
        Saves verified code to custom_skills/<skill_id>.py and registers in SQLite DB.
        Returns absolute file path if successful, None otherwise.
        """
        file_name = f"{spec.skill_id}.py"
        file_path = os.path.join(SKILLS_DIR, file_name)

        try:
            # 1. Write Code File to Disk
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code_content)

            # 2. Update SQLite Database Index
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO custom_skills (
                        skill_id, skill_name, category, target_app, description,
                        triggers_json, file_path, created_at, usage_count, last_executed_at, success_rate, version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(skill_id) DO UPDATE SET
                        skill_name=excluded.skill_name,
                        category=excluded.category,
                        target_app=excluded.target_app,
                        description=excluded.description,
                        triggers_json=excluded.triggers_json,
                        file_path=excluded.file_path,
                        version=excluded.version
                """, (
                    spec.skill_id,
                    spec.skill_name,
                    spec.category,
                    spec.target_app,
                    spec.description,
                    json.dumps(spec.triggers, ensure_ascii=False),
                    file_path,
                    time.time(),
                    0,
                    0,
                    1.0,
                    spec.version
                ))
                conn.commit()

            print(f"[skill_registry] Persisted skill '{spec.skill_id}' to: {file_path}")
            return file_path
        except Exception as e:
            print(f"[skill_registry save error: {e}]")
            return None

    def get_all_skills(self) -> List[Dict[str, Any]]:
        """Returns metadata for all registered custom skills."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM custom_skills ORDER BY created_at DESC")
                rows = cur.fetchall()
                results = []
                for r in rows:
                    item = dict(r)
                    item["triggers"] = json.loads(item.get("triggers_json", "[]"))
                    results.append(item)
                return results
        except Exception as e:
            print(f"[skill_registry query error: {e}]")
            return []

    def record_execution(self, skill_id: str, success: bool = True):
        """Increments usage count and updates success rate."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE custom_skills
                    SET usage_count = usage_count + 1,
                        last_executed_at = ?
                    WHERE skill_id = ?
                """, (time.time(), skill_id))
                conn.commit()
        except Exception as e:
            print(f"[skill_registry record_execution error: {e}]")


registry = SkillRegistry()
