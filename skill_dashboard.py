# -*- coding: utf-8 -*-
"""
skill_dashboard.py  (Phase 16: Skill Dashboard & Memory Inspector)
====================================================================
Provides visual and spoken introspection of all self-learned custom skills.
Voice trigger: "tumne kya-kya seekha hai" / "apne skills batao" / "show learned skills".
"""

import sys
import os
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_registry import registry
from dynamic_hot_reloader import hot_reloader


class SkillDashboard:
    """Manages visual UI and spoken summaries of learned skills."""

    @staticmethod
    def get_summary_speech() -> str:
        """Returns a natural spoken summary of all learned skills."""
        skills = registry.get_all_skills()
        if not skills:
            return "Boss, abhi tak maine koi naya custom skill nahi seekha hai. Aap koi bhi naya task boliye, main use seekh loongi!"

        count = len(skills)
        names = [s["skill_name"] for s in skills[:3]]
        sample_str = ", ".join(names)
        if count > 3:
            sample_str += f" aur {count - 3} aur"

        return f"Boss, maine abhi tak total {count} skills seekhe hain, jaise ki {sample_str}. Sabhi live memory mein active hain."

    @staticmethod
    def open_dashboard_gui(parent_root=None):
        """Builds and displays a dark-themed modern Tkinter dashboard."""
        skills = registry.get_all_skills()

        top = tk.Toplevel(parent_root) if parent_root else tk.Tk()
        top.title("Jarvis — Self-Learned Skills Memory Dashboard")
        top.geometry("780x480")
        top.configure(bg="#1a1c23")
        top.attributes("-topmost", True)

        # Header Frame
        hdr_frame = tk.Frame(top, bg="#1a1c23", padx=20, pady=15)
        hdr_frame.pack(fill="x")

        title_lbl = tk.Label(
            hdr_frame,
            text=f"🧠 Jarvis Self-Evolution Skills Hub ({len(skills)} Active)",
            font=("Segoe UI", 16, "bold"),
            fg="#00e5ff",
            bg="#1a1c23"
        )
        title_lbl.pack(side="left")

        # Treeview Table
        table_frame = tk.Frame(top, bg="#1a1c23", padx=20, pady=5)
        table_frame.pack(fill="both", expand=True)

        columns = ("name", "category", "triggers", "uses", "version")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)

        tree.heading("name", text="Skill Name")
        tree.heading("category", text="Category")
        tree.heading("triggers", text="Voice / Text Triggers")
        tree.heading("uses", text="Execution Count")
        tree.heading("version", text="Version")

        tree.column("name", width=180, anchor="w")
        tree.column("category", width=110, anchor="center")
        tree.column("triggers", width=280, anchor="w")
        tree.column("uses", width=90, anchor="center")
        tree.column("version", width=70, anchor="center")

        # Style Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#242834", foreground="#ffffff", fieldbackground="#242834", font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#12141a", foreground="#00e5ff", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#007acc")])

        # Populate rows
        for s in skills:
            trigs_str = ", ".join(s.get("triggers", [])[:3])
            tree.insert("", "end", values=(
                s["skill_name"],
                s["category"],
                trigs_str,
                s["usage_count"],
                s.get("version", "1.0.0")
            ))

        tree.pack(fill="both", expand=True)

        # Footer Buttons
        btn_frame = tk.Frame(top, bg="#1a1c23", padx=20, pady=15)
        btn_frame.pack(fill="x")

        close_btn = tk.Button(
            btn_frame,
            text="Close Dashboard",
            font=("Segoe UI", 10, "bold"),
            bg="#333842",
            fg="#ffffff",
            padx=15,
            pady=5,
            relief="flat",
            command=top.destroy
        )
        close_btn.pack(side="right")

        if not parent_root:
            top.mainloop()


dashboard = SkillDashboard()
