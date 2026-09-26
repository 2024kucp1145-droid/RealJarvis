# -*- coding: utf-8 -*-
"""
message_scheduler.py
====================
Sequential FIFO Query Scheduler & Message Queue for Jarvis.

Solves the multi-message collision and voice cut-off problem:
1. Thread-safe sequential execution of all incoming queries (Voice, Chat GUI, WhatsApp, Sentries).
2. Intelligent Compound Query Splitting: Splits multi-part questions ("aur", "and also", "?")
   into sequential tasks so Jarvis answers each one by one.
3. Zero Message Dropping: Prevents parallel execution conflicts, audio mixer cut-offs,
   and race conditions.
"""

import re
import time
import queue
import threading
from typing import List, Callable, Optional, Dict, Any


def split_compound_queries(text: str) -> List[str]:
    """
    Splits compound user prompts containing multiple questions or commands
    into individual sequential queries.
    
    Examples:
      - "weather kaisa hai aur mere reminders check karo"
        -> ["weather kaisa hai", "mere reminders check karo"]
      - "what time is it? and also tell me today's date"
        -> ["what time is it?", "tell me today's date"]
      - "youtube open karo aur fir news search karo"
        -> ["youtube open karo", "news search karo"]
    """
    if not text or not isinstance(text, str):
        return []

    cleaned = text.strip()
    if not cleaned:
        return []

    # Common imperative command/question verbs in Hindi & English
    ACTION_WORDS = {
        "karo", "khol", "kholo", "batao", "dikhao", "sunao", "chalu", "band",
        "laga", "lagao", "check", "bhejo", "send", "open", "close", "tell",
        "show", "what", "how", "why", "who", "when", "where", "kya", "kaun",
        "kab", "kahan", "kaise", "search", "dhoondo", "play", "run", "type",
        "likho", "read", "padho", "organize", "commit", "save"
    }

    # Explicit multi-action connectors that always split
    EXPLICIT_SPLIT_PATTERN = re.compile(
        r"(?:[\.\?;\n]+|\s+(?:aur\s+(?:fir|phir|tab|bhi|sath\s+me|sath\s+hi|batao|karo|dekho)|and\s+(?:then|also|furthermore|after\s+that))\s+)",
        re.IGNORECASE
    )

    # First pass: split on explicit separators
    preliminary_parts = [p.strip() for p in EXPLICIT_SPLIT_PATTERN.split(cleaned) if p.strip()]
    if not preliminary_parts:
        preliminary_parts = [cleaned]

    # Second pass: check for standard " aur " or " and " splits
    final_queries = []
    for part in preliminary_parts:
        # Check if part has internal " aur " or " and "
        subparts = re.split(r"\s+(?:aur|and)\s+", part, flags=re.IGNORECASE)
        if len(subparts) > 1:
            # Validate whether each subpart is a meaningful standalone clause
            can_split = True
            for sp in subparts:
                words = sp.strip().lower().split()
                if len(words) < 2:
                    can_split = False
                    break
                # Must contain at least one action/question keyword OR have >= 3 words
                has_action = any(w in ACTION_WORDS for w in words)
                if not has_action and len(words) < 3:
                    can_split = False
                    break
            
            if can_split:
                for sp in subparts:
                    clean_sp = re.sub(r"^(?:aur|and|fir|phir|then|also)\s+", "", sp.strip(), flags=re.IGNORECASE).strip()
                    if clean_sp:
                        final_queries.append(clean_sp)
                continue

        clean_part = re.sub(r"^(?:aur|and|fir|phir|then|also)\s+", "", part, flags=re.IGNORECASE).strip()
        if clean_part:
            final_queries.append(clean_part)

    return final_queries if final_queries else [cleaned]


class ScheduledMessage:
    """Represents a queued task/message waiting to be answered by Jarvis."""

    _counter = 0
    _counter_lock = threading.Lock()

    def __init__(self, text: str, source: str = "general", metadata: Optional[Dict[str, Any]] = None):
        with self._counter_lock:
            ScheduledMessage._counter += 1
            self.id = f"msg_{ScheduledMessage._counter}"
        
        self.text = text.strip()
        self.source = source  # voice, chat, whatsapp, remote, sentry
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.completion_event = threading.Event()
        self.status = "pending"  # pending, processing, completed, error
        self.result: Optional[Any] = None

    def mark_completed(self, result: Any = None):
        self.result = result
        self.status = "completed"
        self.completion_event.set()

    def mark_error(self, error: Any = None):
        self.result = error
        self.status = "error"
        self.completion_event.set()


class MessageScheduler:
    """
    Central sequential message processing engine for Jarvis.
    Guarantees FIFO order and ensures no messages are dropped or cut off.
    """

    def __init__(self, dispatch_fn: Optional[Callable[[str], Any]] = None, gui=None):
        self.dispatch_fn = dispatch_fn
        self.gui = gui
        self.query_queue: queue.Queue[ScheduledMessage] = queue.Queue()
        self.running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._current_message: Optional[ScheduledMessage] = None
        self._history: List[ScheduledMessage] = []

    def start(self):
        """Starts the background sequential processing worker thread."""
        with self._lock:
            if self.running:
                return
            self.running = True
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="MessageSchedulerWorker"
            )
            self._worker_thread.start()
            print("[scheduler] Sequential MessageScheduler worker started.")

    def stop(self):
        """Stops the scheduler gracefully."""
        self.running = False

    def enqueue(self, text: str, source: str = "general", wait: bool = False,
                split_compound: bool = True) -> List[ScheduledMessage]:
        """
        Enqueues text queries. Automatically splits compound questions into separate
        tasks and schedules them in FIFO order.
        
        If wait=True, blocks until all messages in this batch finish execution.
        """
        if not text or not text.strip():
            return []

        queries = split_compound_queries(text) if split_compound else [text.strip()]
        scheduled_msgs: List[ScheduledMessage] = []

        total_parts = len(queries)
        for idx, q in enumerate(queries, 1):
            meta = {
                "batch_total": total_parts,
                "batch_index": idx,
                "original_text": text
            }
            msg = ScheduledMessage(text=q, source=source, metadata=meta)
            scheduled_msgs.append(msg)
            self.query_queue.put(msg)
            depth = self.query_queue.qsize()
            print(f"[scheduler] Queued ({source}): '{q}' [Queue depth: {depth}]")

        if total_parts > 1 and self.gui and hasattr(self.gui, "show_message"):
            try:
                self.gui.show_message(f"Scheduled {total_parts} tasks sequentially...")
            except Exception:
                pass

        if wait and scheduled_msgs:
            # Wait for the last message in this batch to finish
            for m in scheduled_msgs:
                m.completion_event.wait()

        return scheduled_msgs

    def _worker_loop(self):
        """Sequential consumer loop: pulls one message at a time and executes to completion."""
        while self.running:
            try:
                msg = self.query_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            with self._lock:
                self._current_message = msg
                msg.status = "processing"

            try:
                remaining = self.query_queue.qsize()
                batch_info = ""
                if msg.metadata.get("batch_total", 1) > 1:
                    batch_info = f" ({msg.metadata.get('batch_index')}/{msg.metadata.get('batch_total')})"
                
                print(f"[scheduler] Executing query{batch_info}: '{msg.text}' [Remaining in queue: {remaining}]")

                if self.gui and hasattr(self.gui, "show_message"):
                    try:
                        self.gui.show_message(f"Executing: {msg.text}")
                    except Exception:
                        pass

                if self.dispatch_fn:
                    res = self.dispatch_fn(msg.text)
                    msg.mark_completed(res)
                else:
                    msg.mark_completed("No dispatch function registered")

            except Exception as e:
                print(f"[scheduler] Query execution error on '{msg.text}': {e}")
                msg.mark_error(str(e))
            finally:
                with self._lock:
                    self._history.append(msg)
                    if len(self._history) > 100:
                        self._history.pop(0)
                    self._current_message = None
                self.query_queue.task_done()
                # Brief pacing buffer (0.15s) so audio device & GUI settle cleanly before next query
                time.sleep(0.15)

    def pending_count(self) -> int:
        """Returns number of queries waiting in the queue."""
        return self.query_queue.qsize()

    def is_busy(self) -> bool:
        """Returns True if a query is currently executing."""
        with self._lock:
            return self._current_message is not None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "busy": self._current_message is not None,
                "current_query": self._current_message.text if self._current_message else None,
                "pending_count": self.query_queue.qsize(),
                "history_count": len(self._history)
            }


# Global scheduler instance
scheduler = MessageScheduler()
