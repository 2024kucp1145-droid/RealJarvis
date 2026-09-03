# -*- coding: utf-8 -*-
"""
memory.py
=========
Permanent Associative Memory & Knowledge Graph Engine for Real Jarvis.
Persists long-term conversational memory, auto-extracts user facts and projects,
and performs semantic relevance matching so Jarvis never forgets past discussions.
"""

import os
import sqlite3
import datetime
import re
import math
from collections import Counter

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "memory.db")

# ── Keywords that signal a fact/preference/project worth indexing ──
FACT_KEYWORDS = [
    "birthday", "janam din", "janm tithi", "date of birth", "dob",
    "pasand", "favorite", "favourite", "pasandida", "man pasand",
    "naam", "name", "mera naam", "uska naam",
    "email", "phone", "number", "mobile", "contact",
    "address", "ghar", "rehta hoon", "rehti hoon",
    "kaam", "job", "company", "college", "school", "project", "repo", "folder",
    "yaad rakhna", "remember", "note", "important", "zaroori",
    "goal", "target", "bana raha", "bana rahi", "seekh raha", "seekh rahi"
]


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """App startup: ensures all database tables and indexes exist."""
    try:
        conn = _connect()
        c = conn.cursor()
        
        # 1. Permanent Notes
        c.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                content TEXT NOT NULL
            )
        """)
        try:
            c.execute("ALTER TABLE notes ADD COLUMN category TEXT DEFAULT 'general'")
        except Exception:
            pass
        
        # 2. Historical Conversations
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_text TEXT NOT NULL,
                ai_text TEXT NOT NULL,
                topic TEXT DEFAULT ''
            )
        """)
        try:
            c.execute("ALTER TABLE conversations ADD COLUMN topic TEXT DEFAULT ''")
        except Exception:
            pass
        
        # 3. User Knowledge Graph (Profile & Preferences)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # 4. Reminders
        c.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                remind_at TEXT NOT NULL,
                message TEXT NOT NULL,
                done INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[memory init_db error: {e}]")


# ------------------------------------------------------------------
# 1. USER KNOWLEDGE GRAPH (Profile & Permanent Facts)
# ------------------------------------------------------------------
def set_profile_fact(key: str, value: str, category: str = "general") -> bool:
    """Store or update a structured fact in user knowledge graph."""
    if not key or not value:
        return False
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute("""
            INSERT INTO user_profile (key, category, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                updated_at = excluded.updated_at
        """, (key.strip().lower(), category, value.strip(), datetime.datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[memory set_profile_fact error: {e}]")
        return False


def get_all_profile_facts() -> dict:
    """Retrieve full user profile dictionary."""
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT key, category, value FROM user_profile ORDER BY updated_at DESC")
        rows = c.fetchall()
        conn.close()
        profile = {}
        for k, cat, v in rows:
            profile[k] = {"value": v, "category": cat}
        return profile
    except Exception as e:
        print(f"[memory get_all_profile_facts error: {e}]")
        return {}


# ------------------------------------------------------------------
# 2. NOTES & FACTS STORAGE
# ------------------------------------------------------------------
def save_note(content: str, category: str = "general") -> bool:
    if not content or not content.strip():
        return False
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO notes (timestamp, category, content) VALUES (?, ?, ?)",
            (datetime.datetime.now().isoformat(), category, content.strip()),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[memory save_note error: {e}]")
        return False


def get_recent_notes(limit: int = 5):
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT timestamp, content FROM notes ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"[memory get_recent_notes error: {e}]")
        return []


# ------------------------------------------------------------------
# 3. SEMANTIC TOKEN SIMILARITY ENGINE (Associative Recall)
# ------------------------------------------------------------------
_STOPWORDS = {
    "a", "about", "above", "after", "again", "all", "am", "an", "and", "any", "are", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from", "further",
    "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most",
    "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other",
    "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she", "should", "so", "some",
    "such", "t", "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there",
    "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very",
    "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why", "will",
    "with", "you", "your", "yours", "yourself", "yourselves",
    # Hindi/Hinglish fillers
    "hai", "hain", "karo", "karna", "tha", "thi", "the", "ko", "se", "ka", "ki", "ke", "me",
    "mein", "par", "pe", "bhi", "toh", "kya", "kyu", "kyun", "kaise", "kaha", "kahan", "aur"
}


def _tokenize(text: str):
    words = re.findall(r"\w+", text.lower())
    return [w for w in words if len(w) > 1 and w not in _STOPWORDS]


def _similarity_score(query_tokens, doc_tokens):
    if not query_tokens or not doc_tokens:
        return 0.0
    q_counts = Counter(query_tokens)
    d_counts = Counter(doc_tokens)
    
    intersection = set(q_counts.keys()) & set(d_counts.keys())
    if not intersection:
        return 0.0
    
    dot = sum(q_counts[k] * d_counts[k] for k in intersection)
    mag_q = math.sqrt(sum(v * v for v in q_counts.values()))
    mag_d = math.sqrt(sum(v * v for v in d_counts.values()))
    if mag_q == 0 or mag_d == 0:
        return 0.0
    return dot / (mag_q * mag_d)


def search_semantic_memory(query: str, limit: int = 5):
    """
    Searches notes, user profile, and past conversations for semantic matches.
    Returns list of relevant memory strings.
    """
    if not query:
        return []
    
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    
    results = []
    try:
        conn = _connect()
        c = conn.cursor()
        
        # 1. Search Notes
        c.execute("SELECT id, timestamp, content FROM notes")
        for nid, ts, content in c.fetchall():
            doc_tokens = _tokenize(content)
            score = _similarity_score(query_tokens, doc_tokens)
            if score > 0.15:
                results.append((score, f"Note: {content}"))
        
        # 2. Search User Profile
        c.execute("SELECT key, category, value FROM user_profile")
        for k, cat, val in c.fetchall():
            doc_tokens = _tokenize(f"{k} {cat} {val}")
            score = _similarity_score(query_tokens, doc_tokens)
            if score > 0.15:
                results.append((score + 0.1, f"Profile [{cat}] {k}: {val}"))
                
        # 3. Search Historical Conversations
        c.execute("SELECT id, timestamp, user_text, ai_text FROM conversations ORDER BY id DESC LIMIT 150")
        for cid, ts, ut, at in c.fetchall():
            doc_tokens = _tokenize(f"{ut} {at}")
            score = _similarity_score(query_tokens, doc_tokens)
            if score > 0.2:
                results.append((score, f"Past Convo: User said '{ut}' -> Jarvis replied '{at[:100]}...'"))
                
        conn.close()
    except Exception as e:
        print(f"[search_semantic_memory error: {e}]")
    
    # Sort by relevance score desc
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]


# ------------------------------------------------------------------
# 4. CONVERSATION LOGGING & AUTO FACT EXTRACTION
# ------------------------------------------------------------------
def _init_conversations_table():
    init_db()


def log_conversation(user_text: str, ai_text: str):
    """Persists conversation and runs auto-fact extraction."""
    if not user_text or not ai_text:
        return
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO conversations (timestamp, user_text, ai_text) VALUES (?, ?, ?)",
            (datetime.datetime.now().isoformat(), user_text.strip(), ai_text.strip()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[memory log_conversation error: {e}]")
    
    # Auto-extract facts
    _auto_extract_facts(user_text, ai_text)


def _auto_extract_facts(user_text: str, ai_text: str):
    """Automatically parses and preserves important user facts and projects."""
    lower_u = user_text.lower()
    
    # Name detection
    name_match = re.search(r"(?:mera naam|my name is|i am)\s+([A-Za-z]+)", user_text, re.IGNORECASE)
    if name_match:
        set_profile_fact("user_name", name_match.group(1), category="identity")
        
    # Project detection
    proj_match = re.search(r"(?:project|kaam|repo|codebase)\s+(?:hai|ka naam hai|named|called|is)\s+([A-Za-z0-9_\-\.]+)", user_text, re.IGNORECASE)
    if proj_match:
        set_profile_fact(f"project_{proj_match.group(1).lower()}", proj_match.group(1), category="project")
        
    # General fact detection
    if looks_like_fact(user_text) and len(user_text) > 10:
        save_note(f"{user_text.strip()} (Context: {ai_text[:80].strip()})", category="auto_fact")


def get_recent_conversations(limit: int = 6):
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute(
            "SELECT timestamp, user_text, ai_text FROM conversations ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = c.fetchall()
        conn.close()
        return list(reversed(rows))
    except Exception as e:
        print(f"[memory get_recent_conversations error: {e}]")
        return []


def build_memory_context(current_query: str = "", limit: int = 5) -> str:
    """
    Constructs an associative memory context containing:
    1. User Profile & Active Projects
    2. Associative Past Memories relevant to current_query
    3. Immediate Recent Conversation Turns
    """
    parts = []
    
    # 1. Profile Facts
    profile = get_all_profile_facts()
    if profile:
        profile_lines = [f"- {k}: {v['value']}" for k, v in list(profile.items())[:6]]
        parts.append("Permanent User Knowledge Graph:\n" + "\n".join(profile_lines))
        
    # 2. Semantic Associative Recall
    if current_query:
        relevant = search_semantic_memory(current_query, limit=3)
        if relevant:
            parts.append("Relevant Past Context & Memories:\n" + "\n".join(f"- {m}" for m in relevant))
            
    # 3. Recent Conversational turns
    convos = get_recent_conversations(limit=limit)
    if convos:
        convo_lines = [f"User: {u}\nJarvis: {a}" for _, u, a in convos]
        parts.append("Recent Immediate Conversation:\n" + "\n".join(convo_lines))
        
    return "\n\n".join(parts)


def looks_like_fact(user_text: str) -> bool:
    lower = user_text.lower()
    return any(kw in lower for kw in FACT_KEYWORDS)


# ------------------------------------------------------------------
# 5. REMINDERS
# ------------------------------------------------------------------
def _init_reminders_table():
    init_db()


def add_reminder(remind_at_iso: str, message: str) -> bool:
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute("INSERT INTO reminders (remind_at, message, done) VALUES (?, ?, 0)",
                   (remind_at_iso, message))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[memory add_reminder error: {e}]")
        return False


def get_due_reminders():
    try:
        conn = _connect()
        c = conn.cursor()
        now = datetime.datetime.now().isoformat()
        c.execute("SELECT id, message FROM reminders WHERE done = 0 AND remind_at <= ?", (now,))
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"[memory get_due_reminders error: {e}]")
        return []


def mark_reminder_done(reminder_id: int):
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[memory mark_reminder_done error: {e}]")


# Ensure DB initialized on module load
init_db()


