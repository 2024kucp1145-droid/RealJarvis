# -*- coding: utf-8 -*-
"""
video_notes.py
==============
Video se audio nikaalna → transcribe → AI notes → PDF save
"""

import os
import sys
import tempfile
import textwrap

# Whisper ko ffmpeg mil sake — imageio-ffmpeg se path set karo
try:
    import imageio_ffmpeg
    _ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
    if _ffmpeg_dir and os.path.exists(_ffmpeg_dir):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass


class VideoNotes:
    def __init__(self, video_path: str, ai_brain, voice):
        self.video_path = video_path
        self.ai = ai_brain
        self.voice = voice
        self.audio_path = None
        self.transcript = ""
        self.notes = ""

    # ------------------------------------------------------- extract audio
    def extract_audio(self) -> bool:
        try:
            from moviepy.editor import VideoFileClip
            self.audio_path = os.path.join(
                tempfile.gettempdir(), f"jarvis_audio_{id(self)}.wav"
            )
            clip = VideoFileClip(self.video_path)
            if clip.audio is None:
                self.voice.speak("Is video mein audio track nahi mila.")
                return False
            clip.audio.write_audiofile(
                self.audio_path, fps=16000, nbytes=2, codec="pcm_s16le", verbose=False, logger=None
            )
            clip.close()
            return True
        except Exception as e:
            print(f"[extract_audio error: {e}]")
            return False

    # ------------------------------------------------------- transcribe
    def transcribe(self) -> bool:
        try:
            import whisper
            self.voice.speak("Audio transcribe kar rahi hoon, ye thoda time le sakta hai...")
            model = whisper.load_model("base")  # "small" for better accuracy
            result = model.transcribe(self.audio_path, fp16=False)
            self.transcript = result.get("text", "")
            print(f"[transcribed {len(self.transcript)} chars]")
            return bool(self.transcript)
        except Exception as e:
            print(f"[transcribe error: {e}]")
            return False

    # ------------------------------------------------------- generate notes
    def generate_notes(self) -> bool:
        if not self.transcript:
            return False

        # Transcript bada ho sakta hai — limit karo taaki token limit na toote
        transcript_chunk = self.transcript[:12000]

        prompt = f"""Tumhe ek educational video ka transcript diya gaya hai. Isse bahut hi detailed, comprehensive, aur well-structured study notes banao jo ek student ke liye perfect ho.

TRANSCRIPT:
{transcript_chunk}

INSTRUCTIONS:
1. Notes ko proper headings aur sub-headings mein organize karo
2. Har concept ko deeply explain karo — video mein jo briefly mention hua hai usse EXPAND karo
3. Extra relevant information add karo jo video mein directly nahi tha lekin topic se related hai (examples, real-world applications, related concepts)
4. Important definitions, formulas, aur code snippets ko alag se highlight karo
5. Key takeaways aur summary har section ke end mein do
6. Notes Hinglish (Roman Hindi + English) mein likho jo easily samajh aa sake
7. Koi comment mat daalna, koi markdown formatting mat daalna — sirf plain text with headings

FORMAT:
Title
Introduction
Main Topics (detailed)
Additional Insights (jo video mein nahi tha)
Summary
Key Points to Remember

SIRF NOTES LIKHO. Koi extra baat nahi."""

        self.voice.speak("Transcript se detailed notes bana rahi hoon...")
        try:
            self.notes, _ = self.ai.ask(prompt, skip_history_append=True)
            return bool(self.notes)
        except Exception as e:
            print(f"[generate_notes error: {e}]")
            return False

    # ------------------------------------------------------- create PDF
    def create_pdf(self, output_path: str) -> bool:
        if not self.notes:
            return False
        try:
            from fpdf import FPDF

            pdf = FPDF()
            font_path = self._find_unicode_font()

            if font_path:
                pdf.add_font("UniFont", "", font_path, uni=True)
                pdf.set_font("UniFont", size=12)
            else:
                pdf.set_font("Arial", size=12)

            pdf.add_page()

            # Title
            pdf.set_font_size(20)
            pdf.cell(0, 15, "Video Notes by Jarvis", ln=True, align="C")
            pdf.ln(5)

            if font_path:
                pdf.set_font("UniFont", size=12)
            else:
                pdf.set_font("Arial", size=12)

            for line in self.notes.split("\n"):
                line = line.strip()
                if not line:
                    pdf.ln(3)
                    continue

                # Heading detection
                if line.startswith("# ") or (len(line) < 60 and line.isupper()):
                    pdf.set_font_size(16)
                    pdf.cell(0, 12, line.replace("#", "").strip(), ln=True)
                    pdf.set_font_size(12)
                elif line.startswith("## ") or line.startswith("### "):
                    pdf.set_font_size(14)
                    pdf.cell(0, 10, line.replace("#", "").strip(), ln=True)
                    pdf.set_font_size(12)
                else:
                    wrapped = textwrap.wrap(line, width=95)
                    for w in wrapped:
                        pdf.cell(0, 8, w, ln=True)

            pdf.output(output_path)
            return True
        except Exception as e:
            print(f"[create_pdf error: {e}]")
            return False

    # ------------------------------------------------------- helpers
    @staticmethod
    def _find_unicode_font():
        try:
            from platform_compat import get_font_paths
            candidates = get_font_paths()
        except ImportError:
            candidates = [
                "C:/Windows/Fonts/nirmala.ttf",
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/calibri.ttf",
            ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    def cleanup(self):
        if self.audio_path and os.path.exists(self.audio_path):
            try:
                os.remove(self.audio_path)
            except Exception:
                pass