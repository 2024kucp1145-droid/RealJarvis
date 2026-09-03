# -*- coding: utf-8 -*-
"""
chat_gui.py
===========
Jarvis Chat Mode — Modern dark-themed chat interface.
Type commands, drag-drop files, voice input, aur full conversation history.
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import os
import time

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    Image = None

# ---- Drag & Drop (same fallback as gui.py) ----
try:
    import windnd
    _WINDND_AVAILABLE = True
except ImportError:
    _WINDND_AVAILABLE = False

try:
    from tkinterdnd2 import DND_FILES
    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False

# ── Colors (Kimi-like dark theme) ──
BG = "#1a1a2e"
HEADER_BG = "#16162a"
CHAT_BG = "#1e1e2e"
USER_BUBBLE = "#4a9eff"
JARVIS_BUBBLE = "#2d2d44"
INPUT_BG = "#252538"
TEXT_WHITE = "#ffffff"
TEXT_GRAY = "#a0a0b0"
ACCENT = "#e94560"
JARVIS_EYE = "#4FC3F7"


class JarvisChatGUI:
    def __init__(self, parent_root, on_send=None, on_voice=None, on_file_drop=None, on_close=None):
        self.parent_root = parent_root
        self.on_send = on_send
        self.on_voice = on_voice
        self.on_file_drop = on_file_drop
        self.on_close = on_close

        self.window = tk.Toplevel(parent_root)
        self.window.title("Jarvis Chat")
        self.window.geometry("900x650+200+100")
        self.window.configure(bg=BG)
        self.window.minsize(600, 400)
        self.window.protocol("WM_DELETE_WINDOW", self._on_close_click)

        # Hide initially
        self.window.withdraw()

        self._typing_active = False
        self._msg_count = 0

        self._build_ui()
        self._setup_drag_drop()

    # -----------------------------------------------------------------
    # UI BUILD
    # -----------------------------------------------------------------
    def _build_ui(self):
        # ===== HEADER =====
        header = tk.Frame(self.window, bg=HEADER_BG, height=60)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        # Small Jarvis Avatar (left)
        avatar_frame = tk.Frame(header, bg=HEADER_BG, width=50, height=50)
        avatar_frame.pack(side="left", padx=(15, 10), pady=5)
        self._draw_avatar(avatar_frame)

        # Title
        title = tk.Label(header, text="Jarvis", font=("Segoe UI", 16, "bold"),
                         bg=HEADER_BG, fg=TEXT_WHITE)
        title.pack(side="left")

        status = tk.Label(header, text="● Online", font=("Segoe UI", 9),
                          bg=HEADER_BG, fg="#00d26a")
        status.pack(side="left", padx=(8, 0))

        # Floating mode button
        float_btn = tk.Label(header, text="⛶ Floating Mode", font=("Segoe UI", 9),
                             bg=HEADER_BG, fg=TEXT_GRAY, cursor="hand2")
        float_btn.pack(side="right", padx=15)
        float_btn.bind("<Button-1>", lambda e: self._on_close_click())

        # ===== CHAT AREA (Scrollable) =====
        chat_outer = tk.Frame(self.window, bg=CHAT_BG)
        chat_outer.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 0))

        self.chat_canvas = tk.Canvas(chat_outer, bg=CHAT_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(chat_outer, command=self.chat_canvas.yview)
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.chat_canvas.pack(side="left", fill="both", expand=True)

        self.messages_frame = tk.Frame(self.chat_canvas, bg=CHAT_BG)
        self.canvas_window = self.chat_canvas.create_window((0, 0), window=self.messages_frame,
                                                            anchor="nw", width=860)
        self.messages_frame.bind("<Configure>", self._on_frame_configure)

        # Typing indicator (hidden by default)
        self.typing_label = tk.Label(self.messages_frame, text="Jarvis soch rahi hai...",
                                     font=("Segoe UI", 10, "italic"),
                                     bg=CHAT_BG, fg=TEXT_GRAY)
        # Not packed yet

        # ===== INPUT AREA =====
        input_frame = tk.Frame(self.window, bg=INPUT_BG, height=70)
        input_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        input_frame.pack_propagate(False)

        # File drop hint
        self.drop_hint = tk.Label(input_frame, text="📎 File yahan drop kar sakte ho",
                                  font=("Segoe UI", 8), bg=INPUT_BG, fg="#555577")
        self.drop_hint.place(relx=0.5, y=8, anchor="n")

        # Text input
        self.input_box = tk.Text(input_frame, font=("Segoe UI", 11), height=2,
                                 bg="#2d2d44", fg=TEXT_WHITE, insertbackground=TEXT_WHITE,
                                 relief="flat", wrap="word", padx=10, pady=8)
        self.input_box.place(relx=0.02, rely=0.35, relwidth=0.74, relheight=0.55)
        self.input_box.bind("<Return>", self._on_enter_pressed)
        self.input_box.bind("<Shift-Return>", lambda e: None)  # Allow Shift+Enter for new line
        self.input_box.focus_set()

        # Voice button
        voice_btn = tk.Button(input_frame, text="🎤", font=("Segoe UI", 14),
                              bg=INPUT_BG, fg=ACCENT, activebackground=INPUT_BG,
                              activeforeground=ACCENT, relief="flat", cursor="hand2",
                              command=self._on_voice_click)
        voice_btn.place(relx=0.78, rely=0.35, relwidth=0.08, relheight=0.55)

        # Send button
        send_btn = tk.Button(input_frame, text="➤", font=("Segoe UI", 14, "bold"),
                             bg=ACCENT, fg="white", activebackground="#ff6b81",
                             activeforeground="white", relief="flat", cursor="hand2",
                             command=self._on_send_click)
        send_btn.place(relx=0.87, rely=0.35, relwidth=0.11, relheight=0.55)

        # Welcome message
        self.window.after(100, lambda: self.add_jarvis_message(
            "Jarvis Chat Mode mein welcome hain! Yahan type karke, voice se, ya file drop karke kuch bhi karwa sakte ho.", "happy"))

    def _draw_avatar(self, parent):
        """Small 40x40 robot face on header."""
        c = tk.Canvas(parent, width=40, height=40, bg=HEADER_BG, highlightthickness=0)
        c.pack()
        cx, cy = 20, 20
        # Body
        c.create_oval(cx-18, cy-16, cx+18, cy+16, fill="#F5F5F5", outline="#E0E0E0")
        # Eyes
        c.create_oval(cx-10, cy-6, cx-4, cy+2, fill=JARVIS_EYE, outline="")
        c.create_oval(cx+4, cy-6, cx+10, cy+2, fill=JARVIS_EYE, outline="")
        # Mouth
        c.create_line(cx-6, cy+10, cx+6, cy+10, fill=JARVIS_EYE, width=2, capstyle="round")

    def _on_frame_configure(self, event=None):
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        # Auto-scroll to bottom
        self.chat_canvas.yview_moveto(1.0)

    # -----------------------------------------------------------------
    # DRAG & DROP
    # -----------------------------------------------------------------
    def _setup_drag_drop(self):
        if _WINDND_AVAILABLE:
            try:
                windnd.hook_dropfiles(self.window, self._on_windnd_drop)
            except Exception:
                pass
        elif _DND_AVAILABLE:
            try:
                self.window.drop_target_register(DND_FILES)
                self.window.dnd_bind('<<Drop>>', self._on_tkdnd_drop)
            except Exception:
                pass

    def _on_windnd_drop(self, files):
        for f in files:
            try:
                filepath = f.decode('utf-8') if isinstance(f, bytes) else str(f)
                filepath = os.path.normpath(filepath.strip().strip('"'))
                if os.path.exists(filepath) and self.on_file_drop:
                    self.window.after(0, lambda fp=filepath: self.on_file_drop(fp))
            except Exception:
                pass

    def _on_tkdnd_drop(self, event):
        raw = event.data or ""
        import re
        paths = re.findall(r'\{([^}]+)\}', raw)
        if not paths:
            paths = [raw.strip().strip('"').strip('{}')]
        for filepath in paths:
            filepath = os.path.normpath(filepath)
            if os.path.exists(filepath) and self.on_file_drop:
                self.window.after(0, lambda fp=filepath: self.on_file_drop(fp))

    # -----------------------------------------------------------------
    # MESSAGE HANDLING
    # -----------------------------------------------------------------
    def add_user_message(self, text: str):
        """Thread-safe user message add."""
        self.window.after(0, lambda: self._create_bubble(text, "user"))

    def add_jarvis_message(self, text: str, emotion: str = "calm"):
        """Thread-safe Jarvis message add."""
        self.window.after(0, lambda: self._create_bubble(text, "jarvis", emotion))

    def _create_bubble(self, text, sender, emotion="calm"):
        # Remove typing indicator if present
        self._hide_typing()

        container = tk.Frame(self.messages_frame, bg=CHAT_BG)
        container.pack(fill="x", pady=4, padx=10)

        if sender == "user":
            # Right align
            wrapper = tk.Frame(container, bg=CHAT_BG)
            wrapper.pack(side="right")

            bubble = tk.Label(wrapper, text=text, font=("Segoe UI", 11),
                              bg=USER_BUBBLE, fg="white", wraplength=500,
                              padx=14, pady=8, justify="left", cursor="arrow")
            bubble.pack(side="right")

            time_lbl = tk.Label(wrapper, text="You", font=("Segoe UI", 8),
                                bg=CHAT_BG, fg=TEXT_GRAY)
            time_lbl.pack(side="right", padx=(0, 8))

        else:
            # Left align — Jarvis
            wrapper = tk.Frame(container, bg=CHAT_BG)
            wrapper.pack(side="left")

            # Emotion color
            emotion_colors = {
                "happy": "#4ade80", "excited": "#fbbf24", "sad": "#94a3b8",
                "concerned": "#fb923c", "calm": JARVIS_EYE, "serious": "#f87171"
            }
            left_bar_color = emotion_colors.get(emotion, JARVIS_EYE)

            # Small left accent bar
            accent = tk.Frame(wrapper, bg=left_bar_color, width=4)
            accent.pack(side="left", fill="y", padx=(0, 8))

            bubble = tk.Label(wrapper, text=text, font=("Segoe UI", 11),
                              bg=JARVIS_BUBBLE, fg=TEXT_WHITE, wraplength=500,
                              padx=14, pady=8, justify="left")
            bubble.pack(side="left")

            name_lbl = tk.Label(wrapper, text="Jarvis", font=("Segoe UI", 8, "bold"),
                                bg=CHAT_BG, fg=JARVIS_EYE)
            name_lbl.pack(side="left", padx=(8, 0), anchor="n")

        self._msg_count += 1
        self._on_frame_configure()

    def set_typing(self, active: bool):
        """Show/hide 'Jarvis typing...' indicator."""
        self.window.after(0, lambda: self._set_typing_ui(active))

    def _set_typing_ui(self, active):
        if active:
            if not self._typing_active:
                self.typing_label.pack(side="top", anchor="w", padx=20, pady=(5, 0))
                self._typing_active = True
                self._animate_typing()
        else:
            self._hide_typing()

    def _hide_typing(self):
        if self._typing_active:
            self.typing_active = False
            try:
                self.typing_label.pack_forget()
            except Exception:
                pass

    def _animate_typing(self):
        if not self._typing_active:
            return
        dots = ["", ".", "..", "..."]
        phase = int(time.time() * 2) % 4
        self.typing_label.config(text=f"Jarvis soch rahi hai{dots[phase]}")
        self.window.after(500, self._animate_typing)

    # -----------------------------------------------------------------
    # INPUT HANDLING
    # -----------------------------------------------------------------
    def _on_enter_pressed(self, event):
        # Shift+Enter allows newline, plain Enter sends
        if not event.state & 0x1:  # Shift not pressed
            self._on_send_click()
            return "break"
        return None

    def _on_send_click(self):
        text = self.input_box.get("1.0", "end-1c").strip()
        if not text:
            return
        self.input_box.delete("1.0", "end")
        self.add_user_message(text)
        if self.on_send:
            self.on_send(text)

    def _on_voice_click(self):
        if self.on_voice:
            self.on_voice()

    def _on_close_click(self):
        if self.on_close:
            self.on_close()

    # -----------------------------------------------------------------
    # SHOW / HIDE
    # -----------------------------------------------------------------
    def show(self):
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
        self.input_box.focus_set()

    def hide(self):
        self.window.withdraw()

    def is_visible(self) -> bool:
        return self.window.winfo_viewable()