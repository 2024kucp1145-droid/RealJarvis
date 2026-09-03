# -*- coding: utf-8 -*-
"""
gui.py
======
Floating robot widget — drag & drop support (windnd primary, tkinterdnd2 fallback).
"""

import threading
import queue
import tkinter as tk
from tkinter import simpledialog, filedialog
import os

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageTk
except ImportError:
    Image = None

# ---- PRIMARY: windnd (Windows native, reliable for ALL file types) ----
try:
    import windnd
    _WINDND_AVAILABLE = True
    print("[GUI] windnd loaded successfully")
except ImportError as e:
    print(f"[GUI] windnd import failed: {e}")
    _WINDND_AVAILABLE = False

# ---- FALLBACK: tkinterdnd2 ----
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _DND_AVAILABLE = True
    print("[GUI] tkinterdnd2 loaded successfully")
except ImportError as e:
    print(f"[GUI] tkinterdnd2 import failed: {e}")
    _DND_AVAILABLE = False


SIZE = 120

EYE_COLORS = {
    "idle": "#4FC3F7",
    "listening": "#29D0FF",
    "speaking": "#3DE3C8",
    "thinking": "#FFCA28",
    "file_intake": "#FF6B6B",
    "sleeping": "#1A1A1A",
}

EMOTION_TILT = {
    "happy": 0, "excited": 0, "sad": 6, "concerned": 3, "calm": 0, "serious": 0,
}


def _build_body_image():
    S = SIZE
    scale = 4
    big = S * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = big / 2, big / 2 + 8 * scale

    shadow = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse([cx - 30 * scale, cy + 30 * scale, cx + 30 * scale, cy + 42 * scale],
               fill=(0, 0, 0, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6 * scale))
    img = Image.alpha_composite(img, shadow)
    draw = ImageDraw.Draw(img)

    layers = 40
    for i in range(layers):
        t = i / (layers - 1)
        w = (40 - t * 3) * scale
        h = (36 - t * 3) * scale
        shade = int(255 - t * 14)
        draw.ellipse([cx - w, cy - h, cx + w, cy + h],
                     fill=(shade, shade, min(255, shade + 3), 255))

    draw.pieslice([cx - 30 * scale, cy - 40 * scale, cx + 30 * scale, cy - 6 * scale],
                   start=195, end=345, fill=(126, 214, 199, 255))

    draw.rounded_rectangle(
        [cx - 27 * scale, cy - 16 * scale, cx + 27 * scale, cy + 16 * scale],
        radius=16 * scale, fill=(24, 27, 31, 255))

    highlight = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.ellipse([cx - 26 * scale, cy - 30 * scale, cx - 4 * scale, cy - 14 * scale],
               fill=(255, 255, 255, 110))
    highlight = highlight.filter(ImageFilter.GaussianBlur(4 * scale))
    img = Image.alpha_composite(img, highlight)

    img = img.resize((S, S), Image.LANCZOS)
    return img


class JarvisGUI:
    def __init__(self):
        # Use regular tk.Tk() — windnd works with it. tkinterdnd2 needs special Tk.
        if _DND_AVAILABLE and not _WINDND_AVAILABLE:
            self.root = TkinterDnD.Tk()
            print("[GUI] TkinterDnD.Tk() created")
        else:
            self.root = tk.Tk()
            print("[GUI] Regular tk.Tk() created")

        self.root.title("Jarvis")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry(f"{SIZE}x{SIZE}+40+40")
        self.root.configure(bg="black")
        try:
            self.root.attributes("-transparentcolor", "black")
        except tk.TclError:
            try:
                self.root.attributes("-alpha", 0.97)
            except tk.TclError:
                pass

        self.canvas = tk.Canvas(self.root, width=SIZE, height=SIZE, bg="black",
                                 highlightthickness=0)
        self.canvas.pack()

        self._state = "idle"
        self._emotion = "calm"
        self._tick = 0
        self._quit_callback = None
        self._file_drop_callback = None

        self._body_photo = None
        self._body_item = None
        self._build_face()

        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._do_drag)
        self.canvas.bind("<Button-3>", self._show_menu)

        # ---- DRAG & DROP: windnd (primary) ----
        windnd_hooked = False
        if _WINDND_AVAILABLE:
            try:
                windnd.hook_dropfiles(self.root, self._on_windnd_drop)
                print("[GUI] windnd drag & drop hooked successfully")
                windnd_hooked = True
            except Exception as e:
                print(f"[GUI] windnd hook failed: {e}")

        # ---- DRAG & DROP: tkinterdnd2 (fallback) ----
        if _DND_AVAILABLE and not windnd_hooked:
            try:
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind('<<DropEnter>>', self._on_drag_enter)
                self.root.dnd_bind('<<DropLeave>>', self._on_drag_leave)
                self.root.dnd_bind('<<Drop>>', self._on_drop)
                print("[GUI] tkinterdnd2 Drag & Drop registered")
            except Exception as e:
                print(f"[GUI] tkinterdnd2 DND registration failed: {e}")

        self.root.after(60, self._animate)
        
    def hide(self):
        """Chat mode ke liye floating widget chhupao."""
        self.root.withdraw()

    def show(self):
        """Floating widget wapas lao."""
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
    
    def _build_face(self):
        c = self.canvas
        cx, cy = SIZE / 2, SIZE / 2 + 8

        if Image:
            body_img = _build_body_image()
            self._body_photo = ImageTk.PhotoImage(body_img)
            self._body_item = c.create_image(0, 0, anchor="nw", image=self._body_photo)
        else:
            c.create_oval(cx - 40, cy - 34, cx + 40, cy + 34, fill="#F5F5F5", outline="#E0E0E0")

        eye_y = cy - 2
        self._eye_l = c.create_oval(cx - 15, eye_y - 6, cx - 3, eye_y + 6,
                                     fill=EYE_COLORS["idle"], outline="")
        self._eye_r = c.create_oval(cx + 3, eye_y - 6, cx + 15, eye_y + 6,
                                     fill=EYE_COLORS["idle"], outline="")
        self._mouth = c.create_line(cx - 6, cy + 10, cx + 6, cy + 10,
                                     fill="#4FC3F7", width=2, capstyle="round")
        # Band aankhein (sleeping ke liye) — hidden by default
        self._eye_l_closed = c.create_line(cx - 15, eye_y, cx - 3, eye_y,
                                            fill="#111111", width=3, state="hidden")
        self._eye_r_closed = c.create_line(cx + 3, eye_y, cx + 15, eye_y,
                                            fill="#111111", width=3, state="hidden")
        # File intake ke liye wide open mouth (hidden by default)
        self._mouth_open = c.create_oval(cx - 10, cy + 6, cx + 10, cy + 22,
                                          fill="#FF6B6B", outline="#FF4757", state="hidden")
        self._cx, self._cy, self._eye_y = cx, cy, eye_y

    # --------------------------------------------------------------- windnd drop
    def _on_windnd_drop(self, files):
        """windnd gives list of bytes — decode and handle."""
        print(f"[GUI] windnd drop received: {len(files)} files")
        self.set_state("file_intake")
        try:
            for f in files:
                try:
                    if isinstance(f, bytes):
                        filepath = None
                        for enc in ('utf-8', 'mbcs', 'gbk', 'latin-1'):
                            try:
                                filepath = f.decode(enc)
                                break
                            except (UnicodeDecodeError, LookupError):
                                continue
                        if filepath is None:
                            filepath = f.decode('utf-8', errors='replace')
                    else:
                        filepath = str(f)
                    
                    filepath = os.path.normpath(filepath.strip().strip('"').strip("'"))
                    print(f"[GUI] Decoded path: {filepath}")
                    
                    if self._file_drop_callback:
                        if os.path.exists(filepath):
                            self._file_drop_callback(filepath)
                        else:
                            print(f"[GUI] Path does not exist: {filepath}")
                except Exception as inner_e:
                    print(f"[GUI] Single file drop error: {inner_e}")
        finally:
            self.root.after(800, lambda: self.set_state("idle"))

    # --------------------------------------------------------------- tkinterdnd2 drop
    def _on_drag_enter(self, event):
        print(f"[GUI] Drag enter: {event.data}")
        self.set_state("file_intake")

    def _on_drag_leave(self, event):
        print("[GUI] Drag leave")
        self.set_state("idle")

    def _on_drop(self, event):
        """tkinterdnd2 drop event."""
        print(f"[GUI] tkinterdnd2 drop raw data: {repr(event.data)}")
        self.set_state("idle")

        raw = event.data or ""
        import re
        paths = []

        # Pattern 1: Braced paths {C:\...}
        braced = re.findall(r'\{([^}]+)\}', raw)
        paths.extend(braced)

        # Pattern 2: Quoted paths "C:\..."
        quoted = re.findall(r'"([^"]+)"', raw)
        paths.extend([p for p in quoted if p not in paths])

        # Pattern 3: Raw path
        if not paths:
            stripped = raw.strip().strip('"').strip("'").strip('{}')
            if stripped and os.path.exists(stripped):
                paths.append(stripped)

        print(f"[GUI] tkinterdnd2 parsed paths: {paths}")

        for filepath in paths:
            filepath = os.path.normpath(filepath.strip())
            if self._file_drop_callback and os.path.exists(filepath):
                print(f"[GUI] Calling callback with: {filepath}")
                self._file_drop_callback(filepath)

    def _start_drag(self, event):
        self._drag_x, self._drag_y = event.x, event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_x)
        y = self.root.winfo_y() + (event.y - self._drag_y)
        self.root.geometry(f"+{x}+{y}")

    def _show_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Jarvis chal raha hai", state="disabled")
        menu.add_separator()
        menu.add_command(label="File Load Karo", command=self._open_file_dialog)
        menu.add_separator()
        menu.add_command(label="Quit", command=self._on_quit)
        menu.tk_popup(event.x_root, event.y_root)

    def _open_file_dialog(self):
        """Fallback agar drag & drop kaam nahi karta."""
        filepath = filedialog.askopenfilename(
            title="Jarvis ko file do",
            filetypes=[
                ("All Files", "*.*"),
                ("Text", "*.txt"), ("PDF", "*.pdf"),
                ("Images", "*.png;*.jpg;*.jpeg"),
                ("Word", "*.docx"),
                ("Videos", "*.mp4;*.avi;*.mkv;*.mov;*.wmv"),
            ]
        )
        if filepath and self._file_drop_callback:
            self._file_drop_callback(filepath)

    def _on_quit(self):
        if self._quit_callback:
            self._quit_callback()
        self.root.destroy()

    def set_quit_callback(self, fn):
        self._quit_callback = fn

    def set_file_drop_callback(self, fn):
        self._file_drop_callback = fn

    def trigger_shatter(self):
        pass

    def append_conversation(self, who, text):
        pass

    def set_state(self, state: str):
        try:
            self.root.after(0, lambda: setattr(self, "_state", state))
        except Exception:
            self._state = state

    def set_emotion(self, emotion: str):
        try:
            self.root.after(0, lambda: setattr(self, "_emotion", emotion))
        except Exception:
            self._emotion = emotion

    def _animate(self):
        self._tick += 1
        state = self._state
        emotion = self._emotion
        color = EYE_COLORS.get(state, EYE_COLORS["idle"])
        c = self.canvas
        cx, cy = SIZE / 2, SIZE / 2 + 8

        tilt = EMOTION_TILT.get(emotion, 0)
        bounce = 0
        if emotion in ("happy", "excited") and state == "speaking":
            bounce = -abs((self._tick % 12) - 6)
        gy = cy + tilt + bounce

        # ---- SLEEPING STATE ----
        if state == "sleeping":
            c.itemconfig(self._mouth, state="normal")
            c.itemconfig(self._mouth_open, state="hidden")
            c.itemconfig(self._eye_l, state="hidden")
            c.itemconfig(self._eye_r, state="hidden")
            c.itemconfig(self._eye_l_closed, state="normal")
            c.itemconfig(self._eye_r_closed, state="normal")
            c.itemconfig(self._mouth, fill="#333333")
            self.root.after(60, self._animate)
            return

        # ---- WAKE UP: Open eyes wapas lao ----
        c.itemconfig(self._eye_l, state="normal")
        c.itemconfig(self._eye_r, state="normal")
        c.itemconfig(self._eye_l_closed, state="hidden")
        c.itemconfig(self._eye_r_closed, state="hidden")

        # ---- FILE INTAKE STATE ----
        if state == "file_intake":
            c.itemconfig(self._eye_l, state="normal")
            c.itemconfig(self._eye_r, state="normal")
            c.itemconfig(self._eye_l_closed, state="hidden")
            c.itemconfig(self._eye_r_closed, state="hidden")
            c.itemconfig(self._mouth, state="hidden")
            c.itemconfig(self._mouth_open, state="normal")
            c.coords(self._eye_l, cx - 16, gy - 8, cx - 2, gy + 8)
            c.coords(self._eye_r, cx + 2, gy - 8, cx + 16, gy + 8)
            c.itemconfig(self._eye_l, fill=color)
            c.itemconfig(self._eye_r, fill=color)
            self.root.after(60, self._animate)
            return

        # Normal mouth visible
        c.itemconfig(self._mouth, state="normal")
        c.itemconfig(self._mouth_open, state="hidden")

        if state == "listening":
            pulse = 1 + 0.2 * abs((self._tick % 20) - 10) / 10
            r = 6 * pulse
            c.coords(self._eye_l, cx - 15, gy - r - 2, cx - 3, gy + r - 2)
            c.coords(self._eye_r, cx + 3, gy - r - 2, cx + 15, gy + r - 2)
            c.coords(self._mouth, cx - 5, gy + 10, cx + 5, gy + 10)
        elif state == "thinking":
            offset = 3 * ((self._tick % 24) / 12 - 1)
            c.coords(self._eye_l, cx - 15 + offset, gy - 6, cx - 3 + offset, gy + 6)
            c.coords(self._eye_r, cx + 3 + offset, gy - 6, cx + 15 + offset, gy + 6)
            c.coords(self._mouth, cx - 4, gy + 10, cx + 4, gy + 10)
        elif state == "speaking":
            open_amt = abs((self._tick % 10) - 5) * 1.6
            c.coords(self._eye_l, cx - 15, gy - 6, cx - 3, gy + 6)
            c.coords(self._eye_r, cx + 3, gy - 6, cx + 15, gy + 6)
            c.coords(self._mouth, cx - 6, gy + 8, cx + 6, gy + 8 + open_amt)
        else:
            breathe = 1 + 0.1 * abs((self._tick % 40) - 20) / 20
            r = 6 * breathe
            c.coords(self._eye_l, cx - 15, gy - r - 2, cx - 3, gy + r - 2)
            c.coords(self._eye_r, cx + 3, gy - r - 2, cx + 15, gy + r - 2)
            c.coords(self._mouth, cx - 6, gy + 10, cx + 6, gy + 10)

        c.itemconfig(self._eye_l, fill=color)
        c.itemconfig(self._eye_r, fill=color)
        c.itemconfig(self._mouth, fill=color)

        self.root.after(60, self._animate)

    def ask_password(self) -> str:
        result_queue = queue.Queue()

        def _popup():
            pw = simpledialog.askstring("Jarvis Verification", "Apna password daaliye:",
                                         show="*", parent=self.root)
            result_queue.put(pw or "")

        self.root.after(0, _popup)
        return result_queue.get()

    def show_message(self, text: str, ms: int = 2800):
        try:
            self.root.after(0, lambda: self._show_tooltip(text, ms))
        except Exception:
            pass

    def _show_tooltip(self, text, ms):
        if hasattr(self, "_current_tooltip") and self._current_tooltip:
            try:
                self._current_tooltip.destroy()
            except Exception:
                pass

        tip = tk.Toplevel(self.root)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        x = self.root.winfo_x() + SIZE + 10
        y = self.root.winfo_y()
        tip.geometry(f"+{x}+{y}")
        label = tk.Label(tip, text=text, bg="#222222", fg="white",
                          font=("Segoe UI", 10), padx=10, pady=6, wraplength=260)
        label.pack()
        self._current_tooltip = tip
        tip.after(ms, lambda: self._destroy_tooltip(tip))

    def _destroy_tooltip(self, tip):
        try:
            tip.destroy()
        except Exception:
            pass
        if getattr(self, "_current_tooltip", None) is tip:
            self._current_tooltip = None

    def open_email_inbox(self, emails):
        self.root.after(0, lambda: self._build_inbox_window(emails))

    def _build_inbox_window(self, emails):
        win = tk.Toplevel(self.root)
        win.title("Jarvis - Inbox")
        win.geometry("620x420+220+150")
        win.configure(bg="#f4f4f4")

        list_frame = tk.Frame(win, bg="#f4f4f4")
        list_frame.pack(side="left", fill="y", padx=(8, 0), pady=8)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        listbox = tk.Listbox(list_frame, width=38, height=22,
                              yscrollcommand=scrollbar.set, font=("Segoe UI", 9))
        for e in emails:
            preview = f"{e.get('from', '')[:26]}\n  {e.get('subject', '(no subject)')[:34]}"
            listbox.insert("end", preview)
        listbox.pack(side="left", fill="y")
        scrollbar.config(command=listbox.yview)

        body_frame = tk.Frame(win, bg="#ffffff")
        body_frame.pack(side="right", fill="both", expand=True, padx=8, pady=8)
        body_text = tk.Text(body_frame, wrap="word", font=("Segoe UI", 10),
                             bg="#ffffff", relief="flat")
        body_scroll = tk.Scrollbar(body_frame, command=body_text.yview)
        body_text.configure(yscrollcommand=body_scroll.set)
        body_scroll.pack(side="right", fill="y")
        body_text.pack(side="left", fill="both", expand=True)
        body_text.insert("end", "<- Kisi bhi email pe click karke poora padhiye")
        body_text.config(state="disabled")

        def on_select(evt):
            sel = listbox.curselection()
            if not sel:
                return
            e = emails[sel[0]]
            body_text.config(state="normal")
            body_text.delete("1.0", "end")
            body_text.insert("end", f"From: {e.get('from','')}\n")
            body_text.insert("end", f"Subject: {e.get('subject','')}\n")
            body_text.insert("end", f"Date: {e.get('date','')}\n")
            body_text.insert("end", "-" * 50 + "\n\n")
            body_text.insert("end", e.get("body", "(khaali)"))
            body_text.config(state="disabled")

        listbox.bind("<<ListboxSelect>>", on_select)

    def run_mainloop(self):
        self.root.mainloop()