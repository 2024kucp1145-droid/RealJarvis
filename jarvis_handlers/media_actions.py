# -*- coding: utf-8 -*-
"""
media_actions.py
================
Video file drop hone ke baad ke actions: notes / transcript / summary.

Flow (video_notes.VideoNotes): video -> ffmpeg audio -> STT transcript ->
AI notes -> PDF (Desktop pe save + open). Notes ke notes ek import ki hui
`video_notes` module handle karta hai, yahan orchestration hai.
"""

import datetime
import os


class MediaActionsMixin:
    """Video mode handlers."""

    # ------------------------------------------------------------------ router
    def _handle_video_commands(self, text: str) -> bool:
        """Video drop hone ke baad user ka command handle karta hai."""
        t = text.lower()
        if any(w in t for w in ("notes", "note", "banao", "bana do")):
            self._finish_video(self._make_video_notes)
        elif any(w in t for w in ("transcribe", "transcription", "likh do", "text")):
            self._finish_video(self._transcribe_video)
        elif any(w in t for w in ("summary", "samajh", "batao", "short")):
            self._finish_video(self._summarize_video)
        elif any(w in t for w in ("cancel", "band", "nahi", "exit", "chhodo")):
            self._finish_video()
            self.speak("Video mode band kar diya.")
        else:
            self.speak("Kya karna hai? 'notes banao', 'summary do', ya 'transcribe karo'?")
        return True

    def _finish_video(self, action=None):
        """Video mode band karo aur (optional) action chalao."""
        path = self.video_path
        self.video_mode = False
        self.video_path = None
        if action is not None and path:
            action(path)

    # ------------------------------------------------------------------ actions
    def _make_video_notes(self, video_path: str):
        """Full flow: video -> audio -> transcript -> notes -> PDF."""
        from video_notes import VideoNotes

        vn = VideoNotes(video_path, self.ai, self.voice)
        self.gui.set_state("thinking")

        self.speak("Video se audio nikaal rahi hoon...")
        if not vn.extract_audio():
            self.speak("Audio extract karne mein dikkat aa gayi. Shayad video corrupt hai "
                       "ya ffmpeg missing hai.")
            return

        if not vn.transcribe():
            self.speak("Transcribe karne mein dikkat aa gayi.")
            vn.cleanup()
            return

        self.gui.show_message("Smart notes bana rahi hoon...")
        if not vn.generate_notes():
            self.speak("Notes generate karne mein dikkat aa gayi.")
            vn.cleanup()
            return

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pdf_name = f"Jarvis_Notes_{timestamp}.pdf"
        pdf_path = os.path.join(desktop, pdf_name)

        self.speak("PDF bana rahi hoon...")
        if vn.create_pdf(pdf_path):
            self.speak(f"Notes ban gayi hain! Desktop pe save ho gayi: {pdf_name}")
            try:
                os.startfile(pdf_path)
            except Exception:  # noqa: BLE001
                pass
        else:
            txt_path = pdf_path.replace(".pdf", ".txt")
            try:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(vn.notes)
                self.speak("PDF banane mein dikkat aa gayi, lekin notes text file mein "
                           "save ho gayi.")
                os.startfile(txt_path)
            except Exception:  # noqa: BLE001
                self.speak("Notes save karne mein dikkat aa gayi.")

        vn.cleanup()

    def _transcribe_video(self, video_path: str):
        """Sirf transcript generate karo aur bol do."""
        from video_notes import VideoNotes

        vn = VideoNotes(video_path, self.ai, self.voice)
        if not vn.extract_audio() or not vn.transcribe():
            self.speak("Transcribe nahi ho paya.")
            vn.cleanup()
            return

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = os.path.join(desktop, f"Jarvis_Transcript_{timestamp}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(vn.transcript)
        self.speak(f"Transcript ban gayi. Desktop pe save ho gayi. "
                   f"{len(vn.transcript)} characters.")
        os.startfile(path)
        vn.cleanup()

    def _summarize_video(self, video_path: str):
        """Video ka short summary banao."""
        from video_notes import VideoNotes

        vn = VideoNotes(video_path, self.ai, self.voice)
        if not vn.extract_audio() or not vn.transcribe():
            self.speak("Summary nahi bana payi.")
            vn.cleanup()
            return

        prompt = (f"Video ka transcript:\n{vn.transcript[:8000]}\n\n"
                  f"Iska ek chhota aur precise summary do - 5-6 sentences mein. "
                  f"Hinglish mein.")
        summary, emotion = self.ai.ask(prompt, skip_history_append=True)
        self.speak(summary, interruptible=True, emotion=emotion)
        vn.cleanup()