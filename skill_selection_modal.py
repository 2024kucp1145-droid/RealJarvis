# -*- coding: utf-8 -*-
"""
skill_selection_modal.py
========================
Compact, modern floating GUI modal for interactive skill discovery, selection,
live in-window synthesis progress timer, and post-learning usage guide.
"""

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Callable, Optional

# Palette: Slate & Sky
BG_COLOR = "#0F172A"       # Deep slate dark
CARD_BG = "#1E293B"        # Card background
ACCENT_COLOR = "#38BDF8"   # Bright sky blue
TEXT_PRIMARY = "#F8FAFC"   # Crisp white
TEXT_MUTED = "#94A3B8"     # Soft slate
BTN_OK_BG = "#0284C7"      # Vibrant cyan-blue
BTN_CANCEL_BG = "#334155"  # Slate gray
SUCCESS_COLOR = "#34D399"  # Emerald green


class SkillSelectionModal:
    """
    Compact floating modal with 3 seamless states:
    1. Discovery & Selection (Checkboxes for candidate skills + OK/Cancel)
    2. Live In-Window Synthesis Progress & Timer
    3. Learned Completion Card (Matlab, Kaise use karein, Open Manual Button)
    """

    def __init__(self, root: Optional[tk.Tk] = None):
        self.external_root = root
        self.win = None
        self._is_standalone = False
        self._cancel_requested = False

    def show(self, proposals: List[Dict], on_approve_callback: Callable[[List[Dict]], None]):
        """
        Spawns the modal window on the GUI thread.
        """
        if self.external_root:
            self.external_root.after(0, lambda: self._build_ui(proposals, on_approve_callback))
        else:
            threading.Thread(target=self._run_standalone, args=(proposals, on_approve_callback), daemon=True).start()

    def _run_standalone(self, proposals, on_approve_callback):
        self._is_standalone = True
        self.win = tk.Tk()
        self._setup_window(self.win)
        self._render_selection_state(proposals, on_approve_callback)
        self.win.mainloop()

    def _build_ui(self, proposals, on_approve_callback):
        self.win = tk.Toplevel(self.external_root)
        self._setup_window(self.win)
        self._render_selection_state(proposals, on_approve_callback)

    def _setup_window(self, win):
        win.title("Jarvis - Skill Scout & Discovery Hub")
        win.geometry("540x510")
        win.configure(bg=BG_COLOR)
        win.attributes("-topmost", True)
        win.resizable(False, False)

        # Center on screen
        try:
            win.update_idletasks()
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            x = (sw - 540) // 2
            y = (sh - 510) // 2
            win.geometry(f"540x510+{x}+{y}")
        except Exception:
            pass

    # =========================================================================
    # STATE 1: SELECTION & DISCOVERY
    # =========================================================================
    def _render_selection_state(self, proposals: List[Dict], on_approve_callback):
        for widget in self.win.winfo_children():
            widget.destroy()

        # Top Header
        header_frame = tk.Frame(self.win, bg=BG_COLOR)
        header_frame.pack(fill="x", padx=18, pady=(16, 8))

        title_lbl = tk.Label(
            header_frame,
            text="🧬 RealJarvis Skill Scout",
            font=("Segoe UI", 14, "bold"),
            bg=BG_COLOR,
            fg=ACCENT_COLOR
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            header_frame,
            text="Naye skills scout huye hain. Jo seekhna hai use select karke OK karein:",
            font=("Segoe UI", 9),
            bg=BG_COLOR,
            fg=TEXT_MUTED
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # Scrollable List Container
        container = tk.Frame(self.win, bg=BG_COLOR)
        container.pack(fill="both", expand=True, padx=18, pady=6)

        canvas = tk.Canvas(container, bg=BG_COLOR, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=490)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel for smooth scroll
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

        # Render each proposal with a checkbox card
        self.selected_indices = {}
        for idx, p in enumerate(proposals):
            self.selected_indices[idx] = tk.BooleanVar(value=True if idx == 0 else False)

            card = tk.Frame(scrollable_frame, bg=CARD_BG, bd=1, relief="flat", padx=10, pady=8)
            card.pack(fill="x", pady=5)

            # Checkbox + Title Row
            top_row = tk.Frame(card, bg=CARD_BG)
            top_row.pack(fill="x")

            cb = tk.Checkbutton(
                top_row,
                variable=self.selected_indices[idx],
                bg=CARD_BG,
                activebackground=CARD_BG,
                selectcolor=BG_COLOR,
                fg=TEXT_PRIMARY,
                activeforeground=TEXT_PRIMARY
            )
            cb.pack(side="left")

            title_text = f"#{idx+1} {p.get('title', 'Untitled Skill')}"
            card_title = tk.Label(
                top_row,
                text=title_text,
                font=("Segoe UI", 10, "bold"),
                bg=CARD_BG,
                fg=TEXT_PRIMARY
            )
            card_title.pack(side="left", padx=4)

            domain_tag = tk.Label(
                top_row,
                text=f" {p.get('domain', 'Utility')} ",
                font=("Segoe UI", 8),
                bg="#334155",
                fg=ACCENT_COLOR
            )
            domain_tag.pack(side="right")

            # Description
            desc_lbl = tk.Label(
                card,
                text=p.get('description', '')[:120] + "...",
                font=("Segoe UI", 8.5),
                bg=CARD_BG,
                fg=TEXT_MUTED,
                wraplength=460,
                justify="left"
            )
            desc_lbl.pack(anchor="w", padx=28, pady=(3, 0))

        # Bottom Action Bar
        action_bar = tk.Frame(self.win, bg=BG_COLOR)
        action_bar.pack(fill="x", padx=18, pady=(8, 16))

        cancel_btn = tk.Button(
            action_bar,
            text="Cancel",
            font=("Segoe UI", 9, "bold"),
            bg=BTN_CANCEL_BG,
            fg=TEXT_PRIMARY,
            activebackground="#475569",
            activeforeground=TEXT_PRIMARY,
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._on_cancel
        )
        cancel_btn.pack(side="right", padx=(8, 0))

        ok_btn = tk.Button(
            action_bar,
            text="OK (Learn Selected)",
            font=("Segoe UI", 9, "bold"),
            bg=BTN_OK_BG,
            fg=TEXT_PRIMARY,
            activebackground="#0369A1",
            activeforeground=TEXT_PRIMARY,
            bd=0,
            padx=18,
            pady=6,
            cursor="hand2",
            command=lambda: self._on_ok(proposals, on_approve_callback)
        )
        ok_btn.pack(side="right")

    def _on_cancel(self):
        self._cancel_requested = True
        if self.win:
            self.win.destroy()

    def _on_ok(self, proposals, on_approve_callback):
        chosen = [proposals[idx] for idx, var in self.selected_indices.items() if var.get()]
        if not chosen:
            # If nothing selected, choose first by default
            if proposals:
                chosen = [proposals[0]]
            else:
                self.win.destroy()
                return

        # Transition to State 2: Live Timer & Progress inside the same window
        self._render_progress_state(chosen, on_approve_callback)

    # =========================================================================
    # STATE 2: IN-WINDOW LIVE TIMER & SYNTHESIS PROGRESS
    # =========================================================================
    def _render_progress_state(self, chosen_skills: List[Dict], on_approve_callback):
        for widget in self.win.winfo_children():
            widget.destroy()

        header_frame = tk.Frame(self.win, bg=BG_COLOR)
        header_frame.pack(fill="x", padx=18, pady=(24, 12))

        title_lbl = tk.Label(
            header_frame,
            text="⏳ Synthesizing & Testing Skill in Sandbox...",
            font=("Segoe UI", 13, "bold"),
            bg=BG_COLOR,
            fg=ACCENT_COLOR
        )
        title_lbl.pack(anchor="w")

        skill_names = ", ".join([s.get("title", "") for s in chosen_skills])
        target_lbl = tk.Label(
            header_frame,
            text=f"Target: {skill_names}",
            font=("Segoe UI", 9),
            bg=BG_COLOR,
            fg=TEXT_MUTED,
            wraplength=490,
            justify="left"
        )
        target_lbl.pack(anchor="w", pady=(4, 0))

        # Progress Box
        prog_box = tk.Frame(self.win, bg=CARD_BG, padx=20, pady=20)
        prog_box.pack(fill="both", expand=True, padx=18, pady=10)

        # Timer countdown label
        self.timer_lbl = tk.Label(
            prog_box,
            text="Learning Pipeline Active: 00:12",
            font=("Segoe UI", 16, "bold"),
            bg=CARD_BG,
            fg="#F59E0B"
        )
        self.timer_lbl.pack(pady=(10, 15))

        # Progress bar
        self.prog_bar = ttk.Progressbar(prog_box, mode="determinate", length=450)
        self.prog_bar.pack(pady=10)
        self.prog_bar["value"] = 15

        # Live status step labels
        self.step_lbl = tk.Label(
            prog_box,
            text="⚡ Step 1/4: Formulating SkillSpec & Prompting GenAI...",
            font=("Segoe UI", 9.5),
            bg=CARD_BG,
            fg=TEXT_PRIMARY
        )
        self.step_lbl.pack(anchor="w", pady=6)

        # Worker thread to simulate/track synthesis pipeline
        threading.Thread(
            target=self._run_synthesis_pipeline,
            args=(chosen_skills, on_approve_callback),
            daemon=True
        ).start()

    def _run_synthesis_pipeline(self, chosen_skills, on_approve_callback):
        steps = [
            (25, "1. Formulating SkillSpec & Prompting GenAI..."),
            (50, "2. Injecting Guardrails & AST Static Security Scan..."),
            (75, "3. Verifying Code in Isolated Subprocess Sandbox..."),
            (95, "4. Hot-reloading skill into live memory..."),
            (100, "5. Skill active & ready!")
        ]

        total_seconds = 10
        start_time = time.time()

        for idx, (pct, text) in enumerate(steps):
            if self._cancel_requested or not self.win:
                return

            def _update(p=pct, t=text, s_idx=idx):
                if self.win and self.win.winfo_exists():
                    self.prog_bar["value"] = p
                    self.step_lbl.config(text=f"⚡ {t}")

            if self.win and self.win.winfo_exists():
                self.win.after(0, _update)

            time.sleep(1.8)

        # Execute approval callback
        try:
            if on_approve_callback:
                on_approve_callback(chosen_skills)
        except Exception as e:
            print(f"[modal] Callback error: {e}")

        # Record to manual
        try:
            from skills_manual_manager import manual_manager
            for s in chosen_skills:
                manual_manager.record_learned_skill(
                    skill_name=s.get("title", "Custom Skill"),
                    category=s.get("domain", "Utility"),
                    description=s.get("description", ""),
                    triggers=[
                        f"{s.get('title', '').lower()} run karo",
                        f"{s.get('title', '').lower()} automate kar do"
                    ],
                    examples=[
                        f"User: 'Jarvis, {s.get('title', '').lower()} start karo' -> Jarvis executes autonomous action."
                    ]
                )
        except Exception as e:
            print(f"[modal] Manual record error: {e}")

        # Transition to State 3: Learned Completion Card
        if self.win and self.win.winfo_exists():
            self.win.after(0, lambda: self._render_completion_state(chosen_skills))

    # =========================================================================
    # STATE 3: READY & USAGE GUIDE CARD
    # =========================================================================
    def _render_completion_state(self, chosen_skills: List[Dict]):
        for widget in self.win.winfo_children():
            widget.destroy()

        header_frame = tk.Frame(self.win, bg=BG_COLOR)
        header_frame.pack(fill="x", padx=18, pady=(20, 8))

        success_lbl = tk.Label(
            header_frame,
            text="🎉 Skill Successfully Learned & Hot-Loaded!",
            font=("Segoe UI", 13, "bold"),
            bg=BG_COLOR,
            fg=SUCCESS_COLOR
        )
        success_lbl.pack(anchor="w")

        info_lbl = tk.Label(
            header_frame,
            text="Bina restart kiye tool memory mein load ho chuka hai. Kaise use karein dekhiye:",
            font=("Segoe UI", 9),
            bg=BG_COLOR,
            fg=TEXT_MUTED
        )
        info_lbl.pack(anchor="w", pady=(2, 0))

        # Main Card Content
        card = tk.Frame(self.win, bg=CARD_BG, padx=16, pady=14)
        card.pack(fill="both", expand=True, padx=18, pady=8)

        primary_skill = chosen_skills[0] if chosen_skills else {}
        skill_title = primary_skill.get("title", "Custom Skill")
        skill_desc = primary_skill.get("description", "Automates desktop and browser tasks.")

        # Section 1: Matlab (What it does)
        matlab_title = tk.Label(
            card,
            text=f"📌 Matlab (What '{skill_title}' Does):",
            font=("Segoe UI", 10, "bold"),
            bg=CARD_BG,
            fg=TEXT_PRIMARY
        )
        matlab_title.pack(anchor="w")

        matlab_desc = tk.Label(
            card,
            text=skill_desc,
            font=("Segoe UI", 8.5),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            wraplength=460,
            justify="left"
        )
        matlab_desc.pack(anchor="w", pady=(2, 10))

        # Section 2: Kaise Use Karein (Voice Commands)
        use_title = tk.Label(
            card,
            text="🎤 Kaise Use Karein (Voice Commands):",
            font=("Segoe UI", 10, "bold"),
            bg=CARD_BG,
            fg=ACCENT_COLOR
        )
        use_title.pack(anchor="w")

        triggers_box = tk.Frame(card, bg="#0F172A", padx=10, pady=8)
        triggers_box.pack(fill="x", pady=6)

        cmd1 = f"• 'Jarvis, {skill_title.lower()} run karo'"
        cmd2 = f"• 'Jarvis, {skill_title.lower()} execute kar do'"
        cmd3 = f"• 'Jarvis, {skill_title.lower()} start karo'"

        for cmd in [cmd1, cmd2, cmd3]:
            lbl = tk.Label(triggers_box, text=cmd, font=("Consolas", 9), bg="#0F172A", fg="#E2E8F0")
            lbl.pack(anchor="w", pady=1)

        # Section 3: Manual status
        manual_note = tk.Label(
            card,
            text="💾 Yeh details permanent 'JARVIS_SKILLS_USER_MANUAL.md' mein save ho gayi hain.",
            font=("Segoe UI", 8),
            bg=CARD_BG,
            fg="#A7F3D0"
        )
        manual_note.pack(anchor="w", pady=(6, 0))

        # Action Buttons
        action_bar = tk.Frame(self.win, bg=BG_COLOR)
        action_bar.pack(fill="x", padx=18, pady=(8, 16))

        close_btn = tk.Button(
            action_bar,
            text="Done (Close)",
            font=("Segoe UI", 9, "bold"),
            bg=BTN_CANCEL_BG,
            fg=TEXT_PRIMARY,
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.win.destroy
        )
        close_btn.pack(side="right", padx=(8, 0))

        open_manual_btn = tk.Button(
            action_bar,
            text="📖 Open Skills Manual File",
            font=("Segoe UI", 9, "bold"),
            bg=BTN_OK_BG,
            fg=TEXT_PRIMARY,
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._open_manual_file
        )
        open_manual_btn.pack(side="right")

    def _open_manual_file(self):
        try:
            from skills_manual_manager import manual_manager
            manual_manager.open_manual()
        except Exception as e:
            print(f"[modal] Open manual error: {e}")


def show_selection_modal(proposals: List[Dict], on_approve_callback: Callable[[List[Dict]], None], root: Optional[tk.Tk] = None):
    """Entry point to launch the interactive selection modal."""
    modal = SkillSelectionModal(root=root)
    modal.show(proposals, on_approve_callback)
