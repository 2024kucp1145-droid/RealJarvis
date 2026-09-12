# -*- coding: utf-8 -*-
"""
memory.py
=========
Production-Grade Neural Semantic Vector Memory and Knowledge Graph Engine for Real Jarvis.
Persists long-term conversational memory, auto-extracts user facts, stores dense vector
embeddings (Google GenAI gemini-embedding-001 + local neural hashing fallback), and performs
hybrid vector + lexical associative recall so Jarvis remembers past discussions,
preferences, code contexts, and episodic workflows with deep contextual intelligence.
"""

import os
import sqlite3
import datetime
import re
import math
import json
import array
import threading
import queue
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple

try:
    import config
except ImportError:
    config = None

try:
    from google import genai
except ImportError:
    genai = None

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "memory.db")

FACT_KEYWORDS = [
    "birthday", "janam din", "janm tithi", "date of birth", "dob",
    "pasand", "favorite", "favourite", "pasandida", "man pasand",
    "naam", "name", "mera naam", "uska naam",
    "email", "phone", "number", "mobile", "contact",
    "address", "ghar", "rehta hoon", "rehti hoon",
    "kaam", "job", "company", "college", "school", "project", "repo", "folder",
    "yaad rakhna", "remember", "note", "important", "zaroori",
    "goal", "target", "bana raha", "bana rahi", "seekh raha", "seekh rahi",
    "ide", "editor", "vscode", "python", "framework", "database", "stack"
]

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
    "hai", "hain", "karo", "karna", "tha", "thi", "the", "ko", "se", "ka", "ki", "ke", "me",
    "mein", "par", "pe", "bhi", "toh", "kya", "kyu", "kyun", "kaise", "kaha", "kahan", "aur",
    "mujhe", "mera", "meri", "mere", "tum", "aap", "batao", "bolo", "hoga", "hogi"
}

_EMBEDDING_CACHE: Dict[str, List[float]] = {}
_MAX_CACHE_SIZE = 1000

_INDEXING_QUEUE: queue.Queue = queue.Queue()
_WORKER_THREAD: Optional[threading.Thread] = None
_WORKER_LOCK = threading.Lock()


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
    except Exception:
        pass
    return conn


def init_db():
    """App startup: ensures all database tables, vector structures, and indexes exist."""
    try:
        conn = _connect()
        c = conn.cursor()
        
        # 1. Notes
        c.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                content TEXT NOT NULL
            )
        """)
        
        # 2. Conversations
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_text TEXT NOT NULL,
                ai_text TEXT NOT NULL,
                topic TEXT DEFAULT ''
            )
        """)
        
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

        # 5. Dense Vector Embeddings Store
        c.execute("""
            CREATE TABLE IF NOT EXISTS vector_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                text_content TEXT NOT NULL,
                vector_blob BLOB NOT NULL,
                dim INTEGER NOT NULL,
                model TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(entity_type, entity_id)
            )
        """)
        
        c.execute("CREATE INDEX IF NOT EXISTS idx_vec_entity ON vector_embeddings (entity_type, entity_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_vec_category ON vector_embeddings (category)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_vec_model ON vector_embeddings (model)")
        
        # 6. Episodic Knowledge & Tool Outcomes
        c.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action_name TEXT NOT NULL,
                user_intent TEXT NOT NULL,
                solution_details TEXT NOT NULL,
                success INTEGER DEFAULT 1,
                metadata_json TEXT DEFAULT '{}'
            )
        """)
        
        conn.commit()
        conn.close()
        _start_background_worker()
    except Exception as e:
        print(f"[memory init_db error: {e}]", flush=True)


def _vector_to_blob(vec: List[float]) -> bytes:
    return array.array('f', vec).tobytes()


def _blob_to_vector(blob: bytes) -> List[float]:
    a = array.array('f')
    a.frombytes(blob)
    return a.tolist()


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < 1e-9:
        return vec
    return [x / norm for x in vec]


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def _generate_local_fallback_embedding(text: str, dim: int = 512) -> List[float]:
    vec = [0.0] * dim
    clean_text = text.lower().strip()
    words = re.findall(r"\w+", clean_text)
    if not words:
        return vec

    for i, w in enumerate(words):
        h = hash(w) % dim
        vec[h] += 1.2
        if i + 1 < len(words):
            h_bi = hash(f"{w}_{words[i+1]}") % dim
            vec[h_bi] += 0.8

    for i in range(len(clean_text) - 2):
        tri = clean_text[i:i+3]
        h_tri = hash(f"tri_{tri}") % dim
        vec[h_tri] += 0.4

    return _l2_normalize(vec)


def generate_embedding(text: str) -> Tuple[List[float], str]:
    clean_text = text.strip() if text else ""
    if not clean_text:
        return ([0.0] * 512, "empty")

    if clean_text in _EMBEDDING_CACHE:
        return (_EMBEDDING_CACHE[clean_text], "cache")

    api_key = getattr(config, "GEMINI_API_KEY", None) if config else os.environ.get("GEMINI_API_KEY")
    
    if genai and api_key:
        try:
            client = genai.Client(api_key=api_key)
            resp = client.models.embed_content(
                model="gemini-embedding-001",
                contents=clean_text
            )
            if resp and resp.embeddings and len(resp.embeddings) > 0:
                raw_values = resp.embeddings[0].values
                norm_vec = _l2_normalize(raw_values)
                if len(_EMBEDDING_CACHE) >= _MAX_CACHE_SIZE:
                    _EMBEDDING_CACHE.pop(next(iter(_EMBEDDING_CACHE)))
                _EMBEDDING_CACHE[clean_text] = norm_vec
                return (norm_vec, "gemini-embedding-001")
        except Exception:
            pass

    local_vec = _generate_local_fallback_embedding(clean_text, dim=512)
    if len(_EMBEDDING_CACHE) >= _MAX_CACHE_SIZE:
        _EMBEDDING_CACHE.pop(next(iter(_EMBEDDING_CACHE)))
    _EMBEDDING_CACHE[clean_text] = local_vec
    return (local_vec, "local-neural-hash-512")


def _background_worker_loop():
    while True:
        try:
            item = _INDEXING_QUEUE.get()
            if item is None:
                break
            entity_type, entity_id, text, category, metadata = item
            _store_vector_internal(entity_type, entity_id, text, category, metadata)
            _INDEXING_QUEUE.task_done()
        except Exception as e:
            print(f"[memory background worker error: {e}]", flush=True)


def _start_background_worker():
    global _WORKER_THREAD
    with _WORKER_LOCK:
        if _WORKER_THREAD is None or not _WORKER_THREAD.is_alive():
            _WORKER_THREAD = threading.Thread(target=_background_worker_loop, daemon=True, name="MemoryVectorWorker")
            _WORKER_THREAD.start()


def store_vector(entity_type: str, entity_id: str, text: str, category: str = "general", metadata: dict = None, sync: bool = False):
    if not text or not text.strip():
        return
    if sync:
        _store_vector_internal(entity_type, entity_id, text, category, metadata)
    else:
        _INDEXING_QUEUE.put((entity_type, entity_id, text, category, metadata or {}))


def _store_vector_internal(entity_type: str, entity_id: str, text: str, category: str = "general", metadata: dict = None):
    try:
        vec, model_name = generate_embedding(text)
        blob = _vector_to_blob(vec)
        dim = len(vec)
        now = datetime.datetime.now().isoformat()
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)
        
        conn = _connect()
        c = conn.cursor()
        c.execute("""
            INSERT INTO vector_embeddings 
            (entity_type, entity_id, category, text_content, vector_blob, dim, model, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                category = excluded.category,
                text_content = excluded.text_content,
                vector_blob = excluded.vector_blob,
                dim = excluded.dim,
                model = excluded.model,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
        """, (entity_type, str(entity_id), category, text.strip(), blob, dim, model_name, meta_str, now, now))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[memory _store_vector_internal error: {e}]", flush=True)


def set_profile_fact(key: str, value: str, category: str = "general") -> bool:
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
        
        vector_text = f"User profile {category} {key}: {value.strip()}"
        store_vector("profile", key.strip().lower(), vector_text, category=category, metadata={"key": key, "value": value})
        return True
    except Exception as e:
        print(f"[memory set_profile_fact error: {e}]", flush=True)
        return False


def get_all_profile_facts() -> dict:
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
        print(f"[memory get_all_profile_facts error: {e}]", flush=True)
        return {}


def save_note(content: str, category: str = "general") -> bool:
    if not content or not content.strip():
        return False
    try:
        now = datetime.datetime.now().isoformat()
        conn = _connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO notes (timestamp, category, content) VALUES (?, ?, ?)",
            (now, category, content.strip()),
        )
        note_id = c.lastrowid
        conn.commit()
        conn.close()
        
        store_vector("note", str(note_id), content.strip(), category=category, metadata={"timestamp": now, "note_id": note_id})
        return True
    except Exception as e:
        print(f"[memory save_note error: {e}]", flush=True)
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
        print(f"[memory get_recent_notes error: {e}]", flush=True)
        return []


def search_notes(query: str, limit: int = 5) -> List[Tuple[str, str]]:
    results = search_vector_memory(query, entity_type="note", top_k=limit)
    if results:
        return [(r.get("created_at", ""), r.get("text", "")) for r in results]
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute("SELECT timestamp, content FROM notes WHERE content LIKE ? ORDER BY id DESC LIMIT ?", (f"%{query}%", limit))
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def store_episodic_memory(action_name: str, user_intent: str, solution_details: str, success: bool = True, metadata: dict = None) -> bool:
    try:
        now = datetime.datetime.now().isoformat()
        meta = metadata or {}
        meta_str = json.dumps(meta, ensure_ascii=False)
        
        conn = _connect()
        c = conn.cursor()
        c.execute("""
            INSERT INTO episodic_memory (timestamp, action_name, user_intent, solution_details, success, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (now, action_name, user_intent.strip(), solution_details.strip(), 1 if success else 0, meta_str))
        ep_id = c.lastrowid
        conn.commit()
        conn.close()
        
        text_for_vec = f"Action: {action_name} | Intent: {user_intent} | Solution: {solution_details}"
        store_vector("episodic", str(ep_id), text_for_vec, category="episodic", metadata={"action": action_name, "success": success})
        return True
    except Exception as e:
        print(f"[memory store_episodic_memory error: {e}]", flush=True)
        return False


def search_episodic_memory(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    return search_vector_memory(query, entity_type="episodic", top_k=top_k)


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"\w+", text.lower())
    return [w for w in words if len(w) > 1 and w not in _STOPWORDS]


def _lexical_similarity(query_tokens: List[str], doc_tokens: List[str]) -> float:
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


def search_vector_memory(
    query: str,
    category: Optional[str] = None,
    entity_type: Optional[str] = None,
    top_k: int = 5,
    threshold: float = 0.20
) -> List[Dict[str, Any]]:
    if not query or not query.strip():
        return []

    clean_query = query.strip()
    query_vec, query_model = generate_embedding(clean_query)
    query_tokens = _tokenize(clean_query)

    results = []
    try:
        conn = _connect()
        c = conn.cursor()
        
        query_sql = "SELECT id, entity_type, entity_id, category, text_content, vector_blob, dim, model, metadata_json, created_at FROM vector_embeddings WHERE 1=1"
        params = []
        
        if category:
            query_sql += " AND category = ?"
            params.append(category)
        if entity_type:
            query_sql += " AND entity_type = ?"
            params.append(entity_type)
            
        c.execute(query_sql, params)
        rows = c.fetchall()
        conn.close()
        
        for row in rows:
            vid, e_type, e_id, cat, text, blob, dim, model, meta_json, created_at = row
            doc_vec = _blob_to_vector(blob)
            
            if len(doc_vec) != len(query_vec):
                fallback_q_vec = _generate_local_fallback_embedding(clean_query, dim=512)
                fallback_d_vec = _generate_local_fallback_embedding(text, dim=512)
                vec_sim = cosine_similarity(fallback_q_vec, fallback_d_vec)
            else:
                vec_sim = cosine_similarity(query_vec, doc_vec)

            doc_tokens = _tokenize(text)
            lex_sim = _lexical_similarity(query_tokens, doc_tokens)
            
            hybrid_score = (0.70 * max(0.0, vec_sim)) + (0.30 * max(0.0, lex_sim))
            if clean_query.lower() in text.lower():
                hybrid_score += 0.15

            if hybrid_score >= threshold or vec_sim >= threshold:
                try:
                    meta = json.loads(meta_json) if meta_json else {}
                except Exception:
                    meta = {}
                results.append({
                    "id": vid,
                    "entity_type": e_type,
                    "entity_id": e_id,
                    "category": cat,
                    "text": text,
                    "score": round(hybrid_score, 4),
                    "vector_similarity": round(vec_sim, 4),
                    "lexical_similarity": round(lex_sim, 4),
                    "model": model,
                    "metadata": meta,
                    "created_at": created_at
                })
                
    except Exception as e:
        print(f"[search_vector_memory error: {e}]", flush=True)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def search_semantic_memory(query: str, limit: int = 5) -> List[str]:
    if not query:
        return []
    
    vec_results = search_vector_memory(query, top_k=limit, threshold=0.18)
    if vec_results:
        formatted = []
        for r in vec_results:
            e_type = r["entity_type"]
            cat = r["category"]
            text = r["text"]
            score = r["score"]
            if e_type == "profile":
                formatted.append(f"Profile [{cat}]: {text} (Relevance: {score})")
            elif e_type == "note":
                formatted.append(f"Note: {text} (Relevance: {score})")
            elif e_type == "convo":
                formatted.append(f"Past Discussion: {text} (Relevance: {score})")
            elif e_type == "episodic":
                formatted.append(f"Episodic Experience: {text}")
            else:
                formatted.append(f"Knowledge [{cat}]: {text}")
        return formatted

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    
    results = []
    try:
        conn = _connect()
        c = conn.cursor()
        
        c.execute("SELECT id, timestamp, content FROM notes")
        for nid, ts, content in c.fetchall():
            score = _lexical_similarity(query_tokens, _tokenize(content))
            if score > 0.15:
                results.append((score, f"Note: {content}"))
        
        c.execute("SELECT key, category, value FROM user_profile")
        for k, cat, val in c.fetchall():
            score = _lexical_similarity(query_tokens, _tokenize(f"{k} {cat} {val}"))
            if score > 0.15:
                results.append((score + 0.1, f"Profile [{cat}] {k}: {val}"))
                
        c.execute("SELECT id, timestamp, user_text, ai_text FROM conversations ORDER BY id DESC LIMIT 50")
        for cid, ts, ut, at in c.fetchall():
            score = _lexical_similarity(query_tokens, _tokenize(f"{ut} {at}"))
            if score > 0.2:
                results.append((score, f"Past Convo: User said '{ut}' -> Jarvis replied '{at[:100]}...'"))
                
        conn.close()
    except Exception as e:
        print(f"[search_semantic_memory fallback error: {e}]", flush=True)
    
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]


def log_conversation(user_text: str, ai_text: str):
    if not user_text or not ai_text:
        return
    convo_id = None
    try:
        now = datetime.datetime.now().isoformat()
        conn = _connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO conversations (timestamp, user_text, ai_text) VALUES (?, ?, ?)",
            (now, user_text.strip(), ai_text.strip()),
        )
        convo_id = c.lastrowid
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[memory log_conversation error: {e}]", flush=True)
    
    if convo_id:
        convo_text = f"User: {user_text.strip()} | Jarvis: {ai_text.strip()}"
        store_vector("convo", str(convo_id), convo_text, category="conversation", metadata={"user": user_text, "ai": ai_text[:100]})

    _auto_extract_facts(user_text, ai_text)


def _auto_extract_facts(user_text: str, ai_text: str):
    lower_u = user_text.lower()
    
    name_match = re.search(r"(?:mera naam|my name is|i am)\s+([A-Za-z]+)", user_text, re.IGNORECASE)
    if name_match:
        set_profile_fact("user_name", name_match.group(1).capitalize(), category="identity")
        
    proj_match = re.search(r"(?:project|kaam|repo|codebase)\s+(?:hai|ka naam hai|named|called|is)\s+([A-Za-z0-9_\-\.]+)", user_text, re.IGNORECASE)
    if proj_match:
        set_profile_fact(f"project_{proj_match.group(1).lower()}", proj_match.group(1), category="project")

    pref_match = re.search(r"(?:mera|meri|my)\s+(?:favorite|favourite|pasandida)\s+([A-Za-z0-9_\s]+?)\s+(?:hai|is)\s+([A-Za-z0-9_\-\.\s]+)", user_text, re.IGNORECASE)
    if pref_match:
        pref_key = pref_match.group(1).strip().replace(" ", "_").lower()
        pref_val = pref_match.group(2).strip()
        set_profile_fact(f"pref_{pref_key}", pref_val, category="preference")
        
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
        print(f"[memory get_recent_conversations error: {e}]", flush=True)
        return []


def build_memory_context(current_query: str = "", limit: int = 5) -> str:
    parts = []
    
    profile = get_all_profile_facts()
    if profile:
        profile_lines = [f"- {k}: {v['value']} (Cat: {v['category']})" for k, v in list(profile.items())[:8]]
        parts.append("Permanent User Knowledge Graph:\n" + "\n".join(profile_lines))
        
    if current_query:
        relevant = search_semantic_memory(current_query, limit=limit)
        if relevant:
            parts.append("Neural Semantic Memory Recall (Vector Search):\n" + "\n".join(f"- {m}" for m in relevant))
            
    convos = get_recent_conversations(limit=limit)
    if convos:
        convo_lines = [f"User: {u}\nJarvis: {a}" for _, u, a in convos]
        parts.append("Recent Immediate Conversation:\n" + "\n".join(convo_lines))
        
    return "\n\n".join(parts)


def looks_like_fact(user_text: str) -> bool:
    lower = user_text.lower()
    return any(kw in lower for kw in FACT_KEYWORDS)


def reindex_all_memories(limit_conversations: int = 15) -> int:
    count = 0
    try:
        conn = _connect()
        c = conn.cursor()
        
        c.execute("SELECT entity_type, entity_id FROM vector_embeddings")
        existing = set((r[0], str(r[1])) for r in c.fetchall())
        
        # 1. Profile facts
        c.execute("SELECT key, category, value FROM user_profile")
        for k, cat, val in c.fetchall():
            if ("profile", str(k)) not in existing:
                store_vector("profile", k, f"User profile {cat} {k}: {val}", category=cat, sync=True)
                count += 1
            
        # 2. Notes
        c.execute("SELECT id, timestamp, category, content FROM notes")
        for nid, ts, cat, content in c.fetchall():
            if ("note", str(nid)) not in existing:
                store_vector("note", str(nid), content, category=cat, metadata={"timestamp": ts}, sync=True)
                count += 1
            
        # 3. Conversations (recent limit)
        c.execute("SELECT id, timestamp, user_text, ai_text FROM conversations ORDER BY id DESC LIMIT ?", (limit_conversations,))
        for cid, ts, ut, at in c.fetchall():
            if ("convo", str(cid)) not in existing:
                store_vector("convo", str(cid), f"User: {ut} | AI: {at}", category="conversation", sync=True)
                count += 1
            
        conn.close()
    except Exception as e:
        print(f"[memory reindex_all_memories error: {e}]", flush=True)
    return count


def get_memory_statistics() -> Dict[str, Any]:
    stats = {
        "total_vectors": 0,
        "profile_facts_count": 0,
        "notes_count": 0,
        "conversations_count": 0,
        "episodic_count": 0,
        "embedding_models": [],
        "cache_size": len(_EMBEDDING_CACHE),
        "db_path": DB_PATH
    }
    try:
        conn = _connect()
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM vector_embeddings")
        stats["total_vectors"] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM user_profile")
        stats["profile_facts_count"] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM notes")
        stats["notes_count"] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM conversations")
        stats["conversations_count"] = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM episodic_memory")
        stats["episodic_count"] = c.fetchone()[0]
        
        c.execute("SELECT DISTINCT model FROM vector_embeddings")
        stats["embedding_models"] = [r[0] for r in c.fetchall()]
        
        conn.close()
    except Exception as e:
        print(f"[memory get_memory_statistics error: {e}]", flush=True)
    return stats


def delete_memory(entity_type: str, entity_id: str) -> bool:
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute("DELETE FROM vector_embeddings WHERE entity_type = ? AND entity_id = ?", (entity_type, str(entity_id)))
        if entity_type == "note":
            c.execute("DELETE FROM notes WHERE id = ?", (entity_id,))
        elif entity_type == "profile":
            c.execute("DELETE FROM user_profile WHERE key = ?", (entity_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[memory delete_memory error: {e}]", flush=True)
        return False


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
        print(f"[memory add_reminder error: {e}]", flush=True)
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
        print(f"[memory get_due_reminders error: {e}]", flush=True)
        return []


def mark_reminder_done(reminder_id: int):
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[memory mark_reminder_done error: {e}]", flush=True)


init_db()
